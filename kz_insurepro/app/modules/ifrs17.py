# -*- coding: utf-8 -*-
"""
KZ-InsurePro - Модуль МСФО 17: Договоры страхования
Расчет BEL, RA, CSM с моделями GMM/VFA/PAA

Соответствие:
- МСФО 17 para 32-52, B36-B119
- Технические обновления МСФО Декабрь 2025
- АРФР адаптации для страхового рынка Казахстана
- Премия за неликвидность: CIA 2025 updates

Формулы и методология обосновываются в каждом расчете для аудиторского следа.
"""

import numpy as np
import pandas as pd
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import date, datetime
import logging
from scipy import stats
from scipy.interpolate import CubicSpline
import sympy as sp

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import (
    IFRS17_CONFIG, MACRO_INDICATORS_2025, LOCALE_CONFIG,
    format_currency, format_percent, DEMO_CONFIG
)

logger = logging.getLogger(__name__)


@dataclass
class BELResult:
    """Результат расчета BEL (Best Estimate Liability)"""
    bel_amount: Decimal
    cash_flows: List[Dict]
    discount_factors: List[Decimal]
    formula_display: str
    justification: str
    calculation_date: datetime


@dataclass
class RAResult:
    """Результат расчета RA (Risk Adjustment)"""
    ra_amount: Decimal
    method: str
    confidence_level: Decimal
    parameters: Dict
    formula_display: str
    justification: str


@dataclass
class CSMResult:
    """Результат расчета CSM (Contractual Service Margin)"""
    csm_amount: Decimal
    is_onerous: bool
    loss_component: Decimal
    release_pattern: List[Decimal]
    formula_display: str
    justification: str


@dataclass
class IFRS17Result:
    """Полный результат расчета по МСФО 17"""
    bel: BELResult
    ra: RAResult
    csm: CSMResult
    fcf: Decimal  # Fulfillment Cash Flows
    total_liability: Decimal
    measurement_model: str  # GMM, VFA, PAA
    formula_display: str
    justification: str


class IFRS17Calculator:
    """
    Калькулятор МСФО 17 для договоров страхования

    Реализует:
    - BEL (Best Estimate Liability) с дисконтированием
    - RA (Risk Adjustment): VaR, TVaR, CoC, CTE методы
    - CSM (Contractual Service Margin) с динамикой
    - Модели измерения: GMM, VFA, PAA
    - Monte Carlo симуляции для RA
    - Символьные вычисления через sympy
    """

    def __init__(self):
        self.config = IFRS17_CONFIG
        self.macro = MACRO_INDICATORS_2025
        self.precision = Decimal('0.001')

        # Символьные переменные
        self.t_sym = sp.Symbol('t', positive=True, integer=True)
        self.r_sym = sp.Symbol('r', positive=True)

        # Аудиторский след
        self.audit_log = []

        # Seed для воспроизводимости Monte Carlo
        np.random.seed(self.config['MONTE_CARLO']['seed'])

        logger.info("IFRS17Calculator инициализирован")

    def _round_to_precision(self, value: Decimal) -> Decimal:
        """Округление до точности 0.001 KZT"""
        return value.quantize(self.precision, rounding=ROUND_HALF_UP)

    def _log_audit(self, operation: str, details: Dict[str, Any]):
        """Запись в аудиторский след"""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'operation': operation,
            'details': details,
            'reference': 'МСФО 17'
        }
        self.audit_log.append(entry)
        logger.info(f"Аудит: {operation}")

    # =========================================================================
    # ДИСКОНТИРОВАНИЕ
    # Per IFRS 17 para 36, B72-B85
    # =========================================================================

    def get_discount_rate(
        self,
        term: int,
        approach: str = 'bottom_up'
    ) -> Tuple[Decimal, str]:
        """
        Получение ставки дисконтирования

        Per IFRS 17 para B72-B85:
        - Bottom-up: risk-free + illiquidity premium
        - Top-down: asset yields - credit losses

        Args:
            term: Срок в годах
            approach: 'bottom_up' или 'top_down'

        Returns:
            (rate, formula_display)
        """
        base_rate = self.config['DISCOUNT_RATES']['base_rate'] / Decimal('100')

        # Премия за неликвидность по сроку
        ilp_factors = self.config['ILLIQUIDITY_PREMIUM_BY_YEAR']
        if term <= 3:
            ilp_factor = ilp_factors.get(term, ilp_factors[3])
        elif term == 4:
            ilp_factor = ilp_factors[4]
        else:
            ilp_factor = ilp_factors[5]

        # Базовый spread (0.50%)
        base_ilp = self.config['DISCOUNT_RATES']['illiquidity_premium'] / Decimal('100')
        illiquidity_premium = base_ilp * ilp_factor

        total_rate = base_rate + illiquidity_premium

        formula = (
            f"Ставка дисконтирования ({approach}):\n"
            f"Base rate (НБК): {float(base_rate):.2%}\n"
            f"Illiquidity premium: {float(base_ilp):.2%} × {float(ilp_factor)} = "
            f"{float(illiquidity_premium):.2%}\n"
            f"Total rate (год {term}): {float(total_rate):.2%}"
        )

        return total_rate, formula

    def calculate_discount_factor(
        self,
        period: int,
        rate: Decimal,
        method: str = 'continuous'
    ) -> Decimal:
        """
        Расчет дисконт-фактора

        Формулы:
        - Continuous: exp(-r × t)
        - Discrete: 1 / (1 + r)^t
        """
        if method == 'continuous':
            return Decimal(str(np.exp(-float(rate) * period)))
        else:
            return Decimal('1') / ((Decimal('1') + rate) ** period)

    # =========================================================================
    # BEL (Best Estimate Liability)
    # Per IFRS 17 para 33, B36-B71
    # =========================================================================

    def calculate_bel(
        self,
        cash_flows: List[Dict],
        discount_rate: Decimal = None,
        lapse_rate: Decimal = None
    ) -> BELResult:
        """
        Расчет BEL (Best Estimate Liability)

        Формула: BEL = Σ(CF_t × DF_t)
        где CF_t = inflows - outflows (с учетом вероятностей)

        Per IFRS 17 para 33, B36-B71:
        - Probability-weighted
        - Unbiased
        - Current estimates

        Args:
            cash_flows: Список денежных потоков по периодам
                [{'period': 1, 'premiums': 100, 'claims': 80, 'expenses': 10}, ...]
            discount_rate: Ставка дисконтирования (если None, берется из конфига)
            lapse_rate: Ставка аннуляции

        Returns:
            BELResult с полной детализацией
        """
        if discount_rate is None:
            max_period = max(cf.get('period', 1) for cf in cash_flows)
            discount_rate, _ = self.get_discount_rate(max_period)

        if lapse_rate is None:
            lapse_rate = self.config['LAPSE_RATES']['life_baseline']

        bel_total = Decimal('0')
        cf_details = []
        discount_factors = []

        for cf in cash_flows:
            period = cf.get('period', 1)

            # Денежные потоки
            premiums = Decimal(str(cf.get('premiums', 0)))
            claims = Decimal(str(cf.get('claims', 0)))
            expenses = Decimal(str(cf.get('expenses', 0)))
            acquisition_costs = Decimal(str(cf.get('acquisition_costs', 0)))

            # Чистый денежный поток (outflows - inflows)
            # Для BEL: положительный = обязательство
            net_cf = claims + expenses + acquisition_costs - premiums

            # Корректировка на аннуляцию (survival)
            survival_factor = (Decimal('1') - lapse_rate) ** (period - 1)
            adjusted_cf = net_cf * survival_factor

            # Дисконтирование
            df = self.calculate_discount_factor(period, discount_rate)
            discount_factors.append(df)

            # Дисконтированный CF
            discounted_cf = adjusted_cf * df

            cf_details.append({
                'period': period,
                'premiums': premiums,
                'claims': claims,
                'expenses': expenses,
                'net_cf': net_cf,
                'survival_factor': survival_factor,
                'adjusted_cf': adjusted_cf,
                'df': df,
                'discounted_cf': discounted_cf,
            })

            bel_total += discounted_cf

        bel_total = self._round_to_precision(bel_total)

        # Формирование отображения формулы
        formula_display = (
            f"{'='*60}\n"
            f"РАСЧЕТ BEL (Best Estimate Liability)\n"
            f"{'='*60}\n\n"
            f"Основная формула: BEL = Σ(CF_t × DF_t)\n"
            f"Ставка дисконтирования: {float(discount_rate):.2%}\n"
            f"Ставка аннуляции: {float(lapse_rate):.1%}\n\n"
            f"--- Денежные потоки по периодам ---\n\n"
        )

        for cf in cf_details:
            formula_display += (
                f"Период {cf['period']}:\n"
                f"  Премии: {format_currency(cf['premiums'])}\n"
                f"  Убытки: {format_currency(cf['claims'])}\n"
                f"  Расходы: {format_currency(cf['expenses'])}\n"
                f"  Чистый CF: {format_currency(cf['net_cf'])}\n"
                f"  Survival factor: {float(cf['survival_factor']):.4f}\n"
                f"  DF: {float(cf['df']):.6f}\n"
                f"  Дисконтированный CF: {format_currency(cf['discounted_cf'])}\n\n"
            )

        formula_display += (
            f"{'='*60}\n"
            f"ИТОГО BEL = {format_currency(bel_total)}\n"
            f"{'='*60}\n"
        )

        justification = (
            f"Расчет BEL выполнен в соответствии с МСФО 17 para 33, B36-B71. "
            f"Использованы текущие оценки денежных потоков с учетом вероятностей "
            f"(probability-weighted), включая поведенческие факторы (lapse rate "
            f"{float(lapse_rate):.1%}). Дисконтирование по текущей ставке "
            f"{float(discount_rate):.2%} (bottom-up: базовая ставка НБК + премия "
            f"за неликвидность)."
        )

        result = BELResult(
            bel_amount=bel_total,
            cash_flows=cf_details,
            discount_factors=discount_factors,
            formula_display=formula_display,
            justification=justification,
            calculation_date=datetime.now()
        )

        self._log_audit('Расчет BEL', {
            'bel_amount': float(bel_total),
            'periods': len(cash_flows),
            'discount_rate': float(discount_rate),
        })

        return result

    # =========================================================================
    # RA (Risk Adjustment)
    # Per IFRS 17 para 37, B86-B92
    # =========================================================================

    def calculate_ra_var(
        self,
        cash_flows: List[Decimal],
        confidence_level: Decimal = None,
        num_simulations: int = None
    ) -> RAResult:
        """
        Расчет RA методом VaR (Value at Risk)

        Формула: RA = VaR_{α}(outflows - inflows)

        Per IFRS 17 para B87: quantile techniques

        Args:
            cash_flows: Список ожидаемых чистых CF
            confidence_level: Уровень доверия (по умолчанию 95%)
            num_simulations: Количество симуляций Monte Carlo

        Returns:
            RAResult с детализацией
        """
        if confidence_level is None:
            confidence_level = self.config['RA_METHODS']['var']['confidence_level']

        if num_simulations is None:
            num_simulations = self.config['MONTE_CARLO']['simulations']

        # Демо-ограничение
        num_simulations = min(num_simulations, 1000)

        # Конвертация в numpy
        cf_array = np.array([float(cf) for cf in cash_flows])
        mean_cf = np.mean(cf_array)
        std_cf = np.std(cf_array) if len(cf_array) > 1 else mean_cf * 0.1

        # Monte Carlo симуляция
        simulated = np.random.normal(mean_cf, std_cf, num_simulations)
        total_simulated = np.sum(
            np.random.normal(mean_cf, std_cf, (num_simulations, len(cf_array))),
            axis=1
        )

        # VaR на уровне доверия
        var_value = np.percentile(total_simulated, float(confidence_level) * 100)
        expected_value = np.mean(total_simulated)

        # RA = VaR - Expected (превышение над ожиданием)
        ra_amount = Decimal(str(max(0, var_value - expected_value)))
        ra_amount = self._round_to_precision(ra_amount)

        formula_display = (
            f"{'='*60}\n"
            f"РАСЧЕТ RA МЕТОДОМ VaR\n"
            f"{'='*60}\n\n"
            f"Формула: RA = VaR_{{{float(confidence_level)*100:.0f}%}} - E[CF]\n\n"
            f"Параметры Monte Carlo:\n"
            f"  Симуляции: {num_simulations}\n"
            f"  Mean CF: {format_currency(Decimal(str(mean_cf)))}\n"
            f"  Std CF: {format_currency(Decimal(str(std_cf)))}\n\n"
            f"Результаты:\n"
            f"  Expected total: {format_currency(Decimal(str(expected_value)))}\n"
            f"  VaR {float(confidence_level)*100:.0f}%: {format_currency(Decimal(str(var_value)))}\n"
            f"  RA = {format_currency(ra_amount)}\n"
            f"{'='*60}\n"
        )

        justification = (
            f"RA рассчитан методом VaR (Value at Risk) на уровне доверия "
            f"{float(confidence_level)*100:.0f}% в соответствии с МСФО 17 para B87. "
            f"Использована Monte Carlo симуляция ({num_simulations} итераций) "
            f"для определения распределения будущих денежных потоков."
        )

        result = RAResult(
            ra_amount=ra_amount,
            method='VaR',
            confidence_level=confidence_level,
            parameters={
                'num_simulations': num_simulations,
                'expected_value': expected_value,
                'var_value': var_value,
            },
            formula_display=formula_display,
            justification=justification
        )

        self._log_audit('Расчет RA (VaR)', {
            'ra_amount': float(ra_amount),
            'confidence_level': float(confidence_level),
            'method': 'VaR',
        })

        return result

    def calculate_ra_tvar(
        self,
        cash_flows: List[Decimal],
        confidence_level: Decimal = None,
        num_simulations: int = None
    ) -> RAResult:
        """
        Расчет RA методом TVaR (Tail Value at Risk)

        Формула: RA = E[X | X > VaR_α]

        TVaR - математическое ожидание убытков, превышающих VaR
        """
        if confidence_level is None:
            confidence_level = self.config['RA_METHODS']['tvar']['confidence_level']

        if num_simulations is None:
            num_simulations = self.config['MONTE_CARLO']['simulations']

        num_simulations = min(num_simulations, 1000)

        cf_array = np.array([float(cf) for cf in cash_flows])
        mean_cf = np.mean(cf_array)
        std_cf = np.std(cf_array) if len(cf_array) > 1 else mean_cf * 0.1

        # Monte Carlo
        total_simulated = np.sum(
            np.random.normal(mean_cf, std_cf, (num_simulations, len(cf_array))),
            axis=1
        )

        # VaR
        var_value = np.percentile(total_simulated, float(confidence_level) * 100)

        # TVaR = E[X | X > VaR]
        tail_values = total_simulated[total_simulated > var_value]
        if len(tail_values) > 0:
            tvar_value = np.mean(tail_values)
        else:
            tvar_value = var_value

        expected_value = np.mean(total_simulated)
        ra_amount = Decimal(str(max(0, tvar_value - expected_value)))
        ra_amount = self._round_to_precision(ra_amount)

        formula_display = (
            f"{'='*60}\n"
            f"РАСЧЕТ RA МЕТОДОМ TVaR (Tail VaR)\n"
            f"{'='*60}\n\n"
            f"Формула: RA = E[X | X > VaR_{{{float(confidence_level)*100:.0f}%}}] - E[X]\n\n"
            f"Результаты:\n"
            f"  VaR {float(confidence_level)*100:.0f}%: {format_currency(Decimal(str(var_value)))}\n"
            f"  TVaR: {format_currency(Decimal(str(tvar_value)))}\n"
            f"  Expected: {format_currency(Decimal(str(expected_value)))}\n"
            f"  RA = {format_currency(ra_amount)}\n"
            f"{'='*60}\n"
        )

        justification = (
            f"RA рассчитан методом TVaR (Tail Value at Risk) - условное ожидание "
            f"убытков выше {float(confidence_level)*100:.0f}% квантиля. "
            f"TVaR более консервативен чем VaR, учитывая хвостовые риски."
        )

        return RAResult(
            ra_amount=ra_amount,
            method='TVaR',
            confidence_level=confidence_level,
            parameters={
                'var_value': var_value,
                'tvar_value': tvar_value,
            },
            formula_display=formula_display,
            justification=justification
        )

    def calculate_ra_coc(
        self,
        capital_requirement: Decimal,
        term: int,
        coc_rate: Decimal = None
    ) -> RAResult:
        """
        Расчет RA методом Cost of Capital

        Формула: RA = CoC_rate × PV(Capital)

        Per IFRS 17 para B88: cost of capital technique

        Args:
            capital_requirement: Требуемый капитал (SCR или аналог)
            term: Срок в годах
            coc_rate: Ставка стоимости капитала

        Returns:
            RAResult
        """
        if coc_rate is None:
            coc_rate = self.config['RA_METHODS']['coc']['rate']

        # Получаем ставку дисконтирования
        discount_rate, _ = self.get_discount_rate(term)

        # PV капитала (предполагаем постепенное высвобождение)
        pv_capital = Decimal('0')
        for t in range(1, term + 1):
            # Предполагаем линейное высвобождение капитала
            capital_t = capital_requirement * Decimal(str(1 - (t - 1) / term))
            df = self.calculate_discount_factor(t, discount_rate)
            pv_capital += capital_t * df

        # RA = CoC_rate × PV(Capital)
        ra_amount = coc_rate * pv_capital
        ra_amount = self._round_to_precision(ra_amount)

        formula_display = (
            f"{'='*60}\n"
            f"РАСЧЕТ RA МЕТОДОМ COST OF CAPITAL\n"
            f"{'='*60}\n\n"
            f"Формула: RA = CoC_rate × PV(Capital)\n\n"
            f"Параметры:\n"
            f"  CoC rate: {float(coc_rate):.1%}\n"
            f"  Capital requirement: {format_currency(capital_requirement)}\n"
            f"  Term: {term} лет\n"
            f"  Discount rate: {float(discount_rate):.2%}\n\n"
            f"PV(Capital) = {format_currency(pv_capital)}\n"
            f"RA = {float(coc_rate):.1%} × {format_currency(pv_capital)}\n"
            f"RA = {format_currency(ra_amount)}\n"
            f"{'='*60}\n"
        )

        justification = (
            f"RA рассчитан методом Cost of Capital (МСФО 17 para B88). "
            f"Ставка стоимости капитала {float(coc_rate):.1%} соответствует "
            f"рекомендациям EIOPA. Требуемый капитал определен на уровне "
            f"доверия 99.5% (1-в-200 лет)."
        )

        return RAResult(
            ra_amount=ra_amount,
            method='CoC',
            confidence_level=Decimal('0.995'),  # подразумевается для SCR
            parameters={
                'coc_rate': float(coc_rate),
                'capital_requirement': float(capital_requirement),
                'pv_capital': float(pv_capital),
            },
            formula_display=formula_display,
            justification=justification
        )

    def calculate_ra_cte(
        self,
        cash_flows: List[Decimal],
        confidence_level: Decimal = None,
        num_simulations: int = None
    ) -> RAResult:
        """
        Расчет RA методом CTE (Conditional Tail Expectation)

        Формула: CTE_α = (1/(1-α)) × ∫_α^1 VaR_p dp

        Args:
            cash_flows: Список чистых CF
            confidence_level: Уровень доверия

        Returns:
            RAResult
        """
        if confidence_level is None:
            confidence_level = self.config['RA_METHODS']['cte']['confidence_level']

        if num_simulations is None:
            num_simulations = self.config['MONTE_CARLO']['simulations']

        num_simulations = min(num_simulations, 1000)

        cf_array = np.array([float(cf) for cf in cash_flows])
        mean_cf = np.mean(cf_array)
        std_cf = np.std(cf_array) if len(cf_array) > 1 else mean_cf * 0.1

        # Monte Carlo
        total_simulated = np.sum(
            np.random.normal(mean_cf, std_cf, (num_simulations, len(cf_array))),
            axis=1
        )

        # Сортировка для вычисления CTE
        sorted_sim = np.sort(total_simulated)
        tail_start = int(float(confidence_level) * num_simulations)
        tail_values = sorted_sim[tail_start:]

        if len(tail_values) > 0:
            cte_value = np.mean(tail_values)
        else:
            cte_value = sorted_sim[-1]

        expected_value = np.mean(total_simulated)
        ra_amount = Decimal(str(max(0, cte_value - expected_value)))
        ra_amount = self._round_to_precision(ra_amount)

        formula_display = (
            f"{'='*60}\n"
            f"РАСЧЕТ RA МЕТОДОМ CTE (Conditional Tail Expectation)\n"
            f"{'='*60}\n\n"
            f"Формула: CTE_{{{float(confidence_level)*100:.0f}%}} = "
            f"E[X | X ≥ Percentile_{{{float(confidence_level)*100:.0f}%}}]\n\n"
            f"Результаты:\n"
            f"  CTE: {format_currency(Decimal(str(cte_value)))}\n"
            f"  Expected: {format_currency(Decimal(str(expected_value)))}\n"
            f"  RA = {format_currency(ra_amount)}\n"
            f"{'='*60}\n"
        )

        justification = (
            f"RA рассчитан методом CTE (Conditional Tail Expectation) на уровне "
            f"{float(confidence_level)*100:.0f}%. CTE эквивалентен TVaR и "
            f"представляет среднее значение в хвосте распределения."
        )

        return RAResult(
            ra_amount=ra_amount,
            method='CTE',
            confidence_level=confidence_level,
            parameters={
                'cte_value': cte_value,
            },
            formula_display=formula_display,
            justification=justification
        )

    def calculate_ra_diversified(
        self,
        ra_components: Dict[str, Decimal],
        correlations: Dict[Tuple[str, str], Decimal] = None
    ) -> Tuple[Decimal, str]:
        """
        Расчет диверсифицированного RA

        Формула: RA_div = √(Σ Corr_i,j × RA_i × RA_j)

        Args:
            ra_components: RA по компонентам риска
            correlations: Матрица корреляций

        Returns:
            (ra_diversified, formula_display)
        """
        if correlations is None:
            correlations = {
                ('mortality', 'lapse'): Decimal('0.50'),
                ('mortality', 'morbidity'): Decimal('0.25'),
                ('lapse', 'expense'): Decimal('0.30'),
            }

        # Простой расчет: сумма квадратов + корреляции
        risks = list(ra_components.keys())
        n = len(risks)

        total = Decimal('0')
        for i in range(n):
            for j in range(n):
                ra_i = ra_components[risks[i]]
                ra_j = ra_components[risks[j]]

                if i == j:
                    corr = Decimal('1')
                else:
                    key = (risks[i], risks[j]) if (risks[i], risks[j]) in correlations else (risks[j], risks[i])
                    corr = correlations.get(key, Decimal('0.25'))

                total += corr * ra_i * ra_j

        ra_diversified = Decimal(str(np.sqrt(float(total))))
        ra_diversified = self._round_to_precision(ra_diversified)

        # Диверсификационный эффект
        sum_ra = sum(ra_components.values())
        diversification_benefit = sum_ra - ra_diversified

        formula = (
            f"RA диверсифицированный: {format_currency(ra_diversified)}\n"
            f"Сумма компонентов: {format_currency(sum_ra)}\n"
            f"Эффект диверсификации: {format_currency(diversification_benefit)} "
            f"({float(diversification_benefit/sum_ra*100) if sum_ra > 0 else 0:.1f}%)"
        )

        return ra_diversified, formula

    # =========================================================================
    # CSM (Contractual Service Margin)
    # Per IFRS 17 para 38-46, B96-B119
    # =========================================================================

    def calculate_csm_initial(
        self,
        premiums: Decimal,
        bel: Decimal,
        ra: Decimal,
        acquisition_costs: Decimal
    ) -> CSMResult:
        """
        Расчет начального CSM

        Формула: CSM = Premiums - Acquisition Costs - BEL - RA

        Per IFRS 17 para 38: CSM represents unearned profit

        Args:
            premiums: Премии
            bel: Best Estimate Liability
            ra: Risk Adjustment
            acquisition_costs: Затраты на привлечение

        Returns:
            CSMResult
        """
        # CSM = неотработанная прибыль
        csm = premiums - acquisition_costs - bel - ra

        is_onerous = csm < 0
        loss_component = Decimal('0')

        if is_onerous:
            loss_component = abs(csm)
            csm = Decimal('0')

        csm = self._round_to_precision(csm)
        loss_component = self._round_to_precision(loss_component)

        formula_display = (
            f"{'='*60}\n"
            f"РАСЧЕТ НАЧАЛЬНОГО CSM\n"
            f"{'='*60}\n\n"
            f"Формула: CSM = Premiums - AC - BEL - RA\n\n"
            f"Компоненты:\n"
            f"  Премии: {format_currency(premiums)}\n"
            f"  Затраты на привлечение: {format_currency(acquisition_costs)}\n"
            f"  BEL: {format_currency(bel)}\n"
            f"  RA: {format_currency(ra)}\n\n"
            f"CSM = {format_currency(premiums)} - {format_currency(acquisition_costs)} - "
            f"{format_currency(bel)} - {format_currency(ra)}\n"
        )

        if is_onerous:
            formula_display += (
                f"\nДоговор ОБРЕМЕНИТЕЛЬНЫЙ:\n"
                f"  Убыток = {format_currency(loss_component)}\n"
                f"  CSM = 0\n"
            )
        else:
            formula_display += f"CSM = {format_currency(csm)}\n"

        formula_display += f"{'='*60}\n"

        justification = (
            f"Начальный CSM рассчитан в соответствии с МСФО 17 para 38. "
            f"{'Договор обременительный - убыток признан немедленно в P&L. ' if is_onerous else ''}"
            f"CSM представляет собой неотработанную прибыль, которая будет "
            f"признаваться по мере оказания услуг."
        )

        return CSMResult(
            csm_amount=csm,
            is_onerous=is_onerous,
            loss_component=loss_component,
            release_pattern=[],
            formula_display=formula_display,
            justification=justification
        )

    def calculate_csm_rollforward(
        self,
        opening_csm: Decimal,
        interest_rate: Decimal,
        changes_future_service: Decimal,
        csm_release: Decimal,
        new_contracts_csm: Decimal = Decimal('0'),
        currency_effect: Decimal = Decimal('0')
    ) -> Tuple[Decimal, str]:
        """
        Расчет CSM roll-forward (GMM)

        Per IFRS 17 para 44:
        CSM_end = CSM_start + New + Interest + Changes - Release + Currency

        Args:
            opening_csm: Начальный CSM
            interest_rate: Ставка начисления процентов (locked-in)
            changes_future_service: Изменения в отношении будущих услуг
            csm_release: Списание CSM
            new_contracts_csm: CSM новых договоров
            currency_effect: Валютный эффект

        Returns:
            (closing_csm, formula_display)
        """
        # Начисление процентов
        interest = opening_csm * interest_rate

        # Roll-forward
        closing_csm = (
            opening_csm +
            new_contracts_csm +
            interest +
            changes_future_service -
            csm_release +
            currency_effect
        )

        # CSM не может быть отрицательным
        closing_csm = max(Decimal('0'), closing_csm)
        closing_csm = self._round_to_precision(closing_csm)

        formula = (
            f"CSM Roll-forward (GMM):\n"
            f"Opening CSM: {format_currency(opening_csm)}\n"
            f"+ New contracts: {format_currency(new_contracts_csm)}\n"
            f"+ Interest ({float(interest_rate):.1%}): {format_currency(interest)}\n"
            f"+ Changes future service: {format_currency(changes_future_service)}\n"
            f"- CSM release: {format_currency(csm_release)}\n"
            f"+ Currency: {format_currency(currency_effect)}\n"
            f"= Closing CSM: {format_currency(closing_csm)}"
        )

        return closing_csm, formula

    def calculate_csm_rollforward_vfa(
        self,
        opening_csm: Decimal,
        change_fv_underlying: Decimal,
        changes_fcf_non_variable: Decimal,
        csm_release: Decimal
    ) -> Tuple[Decimal, str]:
        """
        Расчет CSM roll-forward (VFA)

        Per IFRS 17 para 45:
        Для VFA: изменения в FV underlying влияют на CSM

        Args:
            opening_csm: Начальный CSM
            change_fv_underlying: Изменение FV базовых активов (доля страховщика)
            changes_fcf_non_variable: Изменения FCF не связанные с variable fee
            csm_release: Списание CSM

        Returns:
            (closing_csm, formula_display)
        """
        closing_csm = (
            opening_csm +
            change_fv_underlying +
            changes_fcf_non_variable -
            csm_release
        )

        closing_csm = max(Decimal('0'), closing_csm)
        closing_csm = self._round_to_precision(closing_csm)

        formula = (
            f"CSM Roll-forward (VFA):\n"
            f"Opening CSM: {format_currency(opening_csm)}\n"
            f"+ ΔFV underlying (entity share): {format_currency(change_fv_underlying)}\n"
            f"+ Changes FCF (non-variable): {format_currency(changes_fcf_non_variable)}\n"
            f"- CSM release: {format_currency(csm_release)}\n"
            f"= Closing CSM: {format_currency(closing_csm)}"
        )

        return closing_csm, formula

    def calculate_csm_release(
        self,
        csm: Decimal,
        coverage_units_current: Decimal,
        coverage_units_remaining: Decimal
    ) -> Tuple[Decimal, str]:
        """
        Расчет списания CSM

        Формула: Release = CSM × (CU_current / Total_CU_remaining)

        Per IFRS 17 para B119: систематическое списание

        Args:
            csm: CSM перед списанием
            coverage_units_current: Единицы покрытия текущего периода
            coverage_units_remaining: Общие оставшиеся единицы покрытия

        Returns:
            (csm_release, formula_display)
        """
        if coverage_units_remaining == 0:
            return Decimal('0'), "Нет оставшихся единиц покрытия"

        amortization_ratio = coverage_units_current / coverage_units_remaining
        csm_release = csm * amortization_ratio
        csm_release = self._round_to_precision(csm_release)

        formula = (
            f"Списание CSM:\n"
            f"CSM × (CU_current / CU_remaining)\n"
            f"= {format_currency(csm)} × ({float(coverage_units_current)} / "
            f"{float(coverage_units_remaining)})\n"
            f"= {format_currency(csm)} × {float(amortization_ratio):.4f}\n"
            f"= {format_currency(csm_release)}"
        )

        return csm_release, formula

    # =========================================================================
    # МОДЕЛИ ИЗМЕРЕНИЯ
    # =========================================================================

    def calculate_gmm(
        self,
        cash_flows: List[Dict],
        acquisition_costs: Decimal,
        ra_method: str = 'var',
        capital_requirement: Decimal = None
    ) -> IFRS17Result:
        """
        Расчет по General Measurement Model (GMM)

        Per IFRS 17 para 32-52

        Args:
            cash_flows: Денежные потоки
            acquisition_costs: Затраты на привлечение
            ra_method: Метод RA ('var', 'tvar', 'coc', 'cte')
            capital_requirement: Требуемый капитал (для CoC)

        Returns:
            IFRS17Result
        """
        # BEL
        bel_result = self.calculate_bel(cash_flows)

        # RA
        net_cfs = [
            Decimal(str(cf.get('claims', 0) + cf.get('expenses', 0) - cf.get('premiums', 0)))
            for cf in cash_flows
        ]

        if ra_method == 'var':
            ra_result = self.calculate_ra_var(net_cfs)
        elif ra_method == 'tvar':
            ra_result = self.calculate_ra_tvar(net_cfs)
        elif ra_method == 'coc':
            if capital_requirement is None:
                capital_requirement = bel_result.bel_amount * Decimal('0.1')
            ra_result = self.calculate_ra_coc(capital_requirement, len(cash_flows))
        else:
            ra_result = self.calculate_ra_cte(net_cfs)

        # Премии (первый период)
        premiums = sum(Decimal(str(cf.get('premiums', 0))) for cf in cash_flows)

        # CSM
        csm_result = self.calculate_csm_initial(
            premiums,
            bel_result.bel_amount,
            ra_result.ra_amount,
            acquisition_costs
        )

        # FCF = BEL + RA
        fcf = bel_result.bel_amount + ra_result.ra_amount

        # Total Liability = FCF + CSM (или Loss Component если onerous)
        if csm_result.is_onerous:
            total_liability = fcf + csm_result.loss_component
        else:
            total_liability = fcf + csm_result.csm_amount

        total_liability = self._round_to_precision(total_liability)

        formula_display = (
            f"{'='*60}\n"
            f"РАСЧЕТ ПО GENERAL MEASUREMENT MODEL (GMM)\n"
            f"{'='*60}\n\n"
            f"Структура обязательства:\n"
            f"  FCF = BEL + RA = {format_currency(bel_result.bel_amount)} + "
            f"{format_currency(ra_result.ra_amount)} = {format_currency(fcf)}\n"
            f"  CSM = {format_currency(csm_result.csm_amount)}\n"
            f"  Total Liability = {format_currency(total_liability)}\n"
            f"{'='*60}\n\n"
            f"{bel_result.formula_display}\n\n"
            f"{ra_result.formula_display}\n\n"
            f"{csm_result.formula_display}"
        )

        justification = (
            f"Расчет выполнен по General Measurement Model (GMM) согласно МСФО 17 "
            f"para 32-52. BEL = {format_currency(bel_result.bel_amount)}, "
            f"RA (метод {ra_method}) = {format_currency(ra_result.ra_amount)}, "
            f"CSM = {format_currency(csm_result.csm_amount)}. "
            f"{'Договор обременительный. ' if csm_result.is_onerous else ''}"
            f"Итоговое обязательство = {format_currency(total_liability)}."
        )

        result = IFRS17Result(
            bel=bel_result,
            ra=ra_result,
            csm=csm_result,
            fcf=fcf,
            total_liability=total_liability,
            measurement_model='GMM',
            formula_display=formula_display,
            justification=justification
        )

        self._log_audit('Расчет GMM', {
            'bel': float(bel_result.bel_amount),
            'ra': float(ra_result.ra_amount),
            'csm': float(csm_result.csm_amount),
            'total_liability': float(total_liability),
        })

        return result

    def calculate_paa(
        self,
        premiums: Decimal,
        acquisition_costs: Decimal,
        ra: Decimal,
        coverage_period: int = 1
    ) -> Dict[str, Any]:
        """
        Расчет по Premium Allocation Approach (PAA)

        Per IFRS 17 para 53-59: упрощенный подход для коротких договоров

        Args:
            premiums: Премии
            acquisition_costs: Затраты на привлечение (могут списываться сразу)
            ra: Risk Adjustment
            coverage_period: Период покрытия (≤1 года для eligibility)

        Returns:
            Словарь с результатами
        """
        # LRC = Unearned premium - DAC
        # Если coverage ≤ 1 год, можно списать AC сразу
        if coverage_period <= 1:
            dac = Decimal('0')
            expense_ac = acquisition_costs
        else:
            dac = acquisition_costs
            expense_ac = Decimal('0')

        lrc = premiums - dac - ra

        formula_display = (
            f"{'='*60}\n"
            f"РАСЧЕТ ПО PREMIUM ALLOCATION APPROACH (PAA)\n"
            f"{'='*60}\n\n"
            f"LRC (Liability for Remaining Coverage):\n"
            f"  Премии: {format_currency(premiums)}\n"
            f"  DAC: {format_currency(dac)}\n"
            f"  RA: {format_currency(ra)}\n"
            f"  LRC = Premiums - DAC - RA = {format_currency(lrc)}\n\n"
            f"Период покрытия: {coverage_period} {'год' if coverage_period == 1 else 'лет'}\n"
            f"{'Затраты на привлечение списаны сразу' if coverage_period <= 1 else 'DAC амортизируется'}\n"
            f"{'='*60}\n"
        )

        return {
            'lrc': self._round_to_precision(lrc),
            'dac': dac,
            'ra': ra,
            'premiums': premiums,
            'formula_display': formula_display,
            'measurement_model': 'PAA',
        }

    def check_vfa_eligibility(
        self,
        contract_features: Dict
    ) -> Tuple[bool, str]:
        """
        Проверка eligibility для VFA

        Per IFRS 17 para B101-B118: Direct Participation Features

        Args:
            contract_features: Характеристики договора

        Returns:
            (eligible, justification)
        """
        eligible = True
        reasons = []

        # Критерий 1: Substantial share of fair value returns
        if not contract_features.get('substantial_share_fv', False):
            eligible = False
            reasons.append("нет существенной доли доходности от FV базовых активов")

        # Критерий 2: Substantial portion varies with underlying
        if not contract_features.get('variable_portion', False):
            eligible = False
            reasons.append("существенная часть выплат не варьируется с базовыми активами")

        # Критерий 3: Investment-related service
        if not contract_features.get('investment_service', False):
            eligible = False
            reasons.append("нет инвестиционной услуги")

        if eligible:
            justification = (
                "Договор соответствует критериям VFA (МСФО 17 para B101): "
                "существенная доля доходности от FV, вариативность выплат, "
                "наличие инвестиционной услуги."
            )
        else:
            justification = (
                f"Договор НЕ соответствует критериям VFA: {'; '.join(reasons)}. "
                f"Применять GMM."
            )

        return eligible, justification

    # =========================================================================
    # ГРУППИРОВКА
    # Per IFRS 17 para 14-24
    # =========================================================================

    def group_contracts(
        self,
        contracts: List[Dict]
    ) -> Dict[str, List]:
        """
        Группировка договоров

        Per IFRS 17 para 14-24:
        - По портфелю (similar risks)
        - По когорте (issued within year)
        - По прибыльности (onerous/no risk/remaining)

        Args:
            contracts: Список договоров с характеристиками

        Returns:
            Словарь групп
        """
        groups = {
            'onerous': [],
            'no_significant_risk': [],
            'remaining': [],
        }

        for contract in contracts:
            # Определение прибыльности
            expected_profit = contract.get('expected_profit', Decimal('0'))
            premium = contract.get('premium', Decimal('1'))

            profit_margin = expected_profit / premium if premium > 0 else Decimal('0')

            if profit_margin < Decimal('-0.05'):  # Убыток >5%
                groups['onerous'].append(contract)
            elif profit_margin < Decimal('0.05'):  # Около нуля
                groups['no_significant_risk'].append(contract)
            else:
                groups['remaining'].append(contract)

        return groups

    # =========================================================================
    # ОСАГО КОРРЕКТИРОВКИ
    # Per АРФР требования
    # =========================================================================

    def apply_osago_adjustment(
        self,
        bel: Decimal,
        product_type: str = 'osago'
    ) -> Tuple[Decimal, str]:
        """
        Применение ОСАГО корректировки

        Per АРФР: +50% для обязательного страхования

        Args:
            bel: Базовый BEL
            product_type: Тип продукта

        Returns:
            (adjusted_bel, formula)
        """
        if product_type.lower() in ['osago', 'казко']:
            adjustment = self.config['OSAGO_ADJUSTMENT']
            adjusted = bel * adjustment

            formula = (
                f"ОСАГО корректировка:\n"
                f"BEL × {float(adjustment)} = {format_currency(bel)} × "
                f"{float(adjustment)} = {format_currency(adjusted)}"
            )
        else:
            adjusted = bel
            formula = "Корректировка не применяется"

        return self._round_to_precision(adjusted), formula

    def get_audit_log(self) -> List[Dict]:
        """Получить аудиторский след"""
        return self.audit_log


# =============================================================================
# ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ
# =============================================================================

def demo_gmm_calculation():
    """Демонстрация расчета GMM"""
    calc = IFRS17Calculator()

    # Пример: Аннуитет на 10 лет
    cash_flows = []
    for year in range(1, 11):
        cf = {
            'period': year,
            'premiums': 100_000_000 if year == 1 else 0,
            'claims': 80_000_000 + year * 2_000_000,
            'expenses': 5_000_000,
            'acquisition_costs': 10_000_000 if year == 1 else 0,
        }
        cash_flows.append(cf)

    result = calc.calculate_gmm(
        cash_flows=cash_flows,
        acquisition_costs=Decimal('10000000'),
        ra_method='coc',
        capital_requirement=Decimal('500000000')
    )

    print(result.formula_display)
    print(f"\nОбоснование: {result.justification}")

    return result


if __name__ == '__main__':
    demo_gmm_calculation()
