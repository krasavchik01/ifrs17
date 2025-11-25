# -*- coding: utf-8 -*-
"""
KZ-InsurePro - Модуль Solvency: Платежеспособность
Расчет MMP, MGF, FMP, коэффициенты платежеспособности

Соответствие:
- АРФР Постановление №304 от 26.12.2016
- Изменения: №95 от 22.12.2023, №3 от 20.02.2023, №14 от 16.05.2025
- Solvency II (EU 2025/2, EIOPA updates Nov 2025)
- Изменения по внутреннему аудиту от 08.10.2025

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

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import (
    SOLVENCY_CONFIG, MACRO_INDICATORS_2025, LOCALE_CONFIG,
    format_currency, format_percent, DEMO_CONFIG
)

logger = logging.getLogger(__name__)


@dataclass
class MMPResult:
    """Результат расчета MMP (Минимальная маржа платежеспособности)"""
    mmp_amount: Decimal
    mmp_by_premiums: Decimal
    mmp_by_claims: Decimal
    k_coefficient: Decimal
    osago_adjustment: Decimal
    formula_display: str
    justification: str


@dataclass
class FMPResult:
    """Результат расчета FMP (Фактическая маржа платежеспособности)"""
    fmp_amount: Decimal
    components: Dict[str, Decimal]
    adjustments: Dict[str, Decimal]
    formula_display: str
    justification: str


@dataclass
class SolvencyRatioResult:
    """Результат расчета коэффициента платежеспособности"""
    ratio: Decimal
    fmp: Decimal
    mmp: Decimal
    is_compliant: bool
    formula_display: str
    justification: str


@dataclass
class StressTestResult:
    """Результат стресс-тестирования"""
    base_ratio: Decimal
    stressed_ratios: Dict[str, Decimal]
    var_99_5: Decimal
    formula_display: str
    justification: str


class SolvencyCalculator:
    """
    Калькулятор платежеспособности по требованиям АРФР

    Реализует:
    - MMP по премиям и убыткам
    - MGF (минимальный гарантийный фонд)
    - FMP с МСФО корректировками
    - Solvency II SCR модули
    - Стресс-тестирование (VaR 99.5%)
    - Monte Carlo для сценариев банкротства
    """

    def __init__(self):
        self.config = SOLVENCY_CONFIG
        self.macro = MACRO_INDICATORS_2025
        self.precision = Decimal('0.001')

        # Аудиторский след
        self.audit_log = []

        logger.info("SolvencyCalculator инициализирован")

    def _round_to_precision(self, value: Decimal) -> Decimal:
        """Округление до точности 0.001 KZT"""
        return value.quantize(self.precision, rounding=ROUND_HALF_UP)

    def _log_audit(self, operation: str, details: Dict[str, Any]):
        """Запись в аудиторский след"""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'operation': operation,
            'details': details,
            'reference': 'АРФР №304'
        }
        self.audit_log.append(entry)
        logger.info(f"Аудит: {operation}")

    # =========================================================================
    # MGF (Минимальный гарантийный фонд)
    # Per АРФР §304
    # =========================================================================

    def calculate_mgf(
        self,
        insurer_type: str = 'life_non_life'
    ) -> Tuple[Decimal, str]:
        """
        Расчет MGF (Минимальный гарантийный фонд)

        Per АРФР:
        - Life/Non-life: 500,000 МРП = 1.966 млрд KZT
        - Reinsurance: 3,500,000 МРП = 13.762 млрд KZT

        Args:
            insurer_type: 'life_non_life' или 'reinsurance'

        Returns:
            (mgf, formula_display)
        """
        mrp = self.macro['mrp']
        mgf_mrp = self.config['MGF_MRP'].get(insurer_type, 500000)
        mgf_kzt = mrp * Decimal(str(mgf_mrp))

        formula = (
            f"MGF ({insurer_type}):\n"
            f"MGF = {mgf_mrp:,} МРП × {format_currency(mrp)}/МРП\n"
            f"MGF = {format_currency(mgf_kzt)}"
        )

        return self._round_to_precision(mgf_kzt), formula

    # =========================================================================
    # MMP (Минимальная маржа платежеспособности)
    # Per АРФР §304
    # =========================================================================

    def calculate_mmp_by_premiums(
        self,
        gross_premiums: Decimal,
        k_coefficient: Decimal = None
    ) -> Tuple[Decimal, str]:
        """
        Расчет MMP по премиям

        Формула: MMP_P = max(0.18×min(P, 3.5B), 0.16×(P-3.5B)) × K

        Args:
            gross_premiums: Валовые премии за последние 12 месяцев
            k_coefficient: Поправочный коэффициент (0.5-0.85)

        Returns:
            (mmp_p, formula_display)
        """
        if k_coefficient is None:
            k_coefficient = self.config['K_COEFFICIENT']['default']

        coef = self.config['MMP_PREMIUM_COEFFICIENTS']
        threshold = coef['tier_1_threshold']

        if gross_premiums <= threshold:
            mmp_base = gross_premiums * coef['tier_1_rate']
            tier_info = f"{float(gross_premiums / 1e9):.2f}B ≤ 3.5B: применяется 18%"
        else:
            tier_1 = threshold * coef['tier_1_rate']
            tier_2 = (gross_premiums - threshold) * coef['tier_2_rate']
            mmp_base = tier_1 + tier_2
            tier_info = (
                f"Tier 1 (до 3.5B): {format_currency(tier_1)}\n"
                f"Tier 2 (свыше 3.5B): {format_currency(tier_2)}"
            )

        mmp_p = mmp_base * k_coefficient

        formula = (
            f"MMP по премиям:\n"
            f"Валовые премии: {format_currency(gross_premiums)}\n"
            f"{tier_info}\n"
            f"MMP_base = {format_currency(mmp_base)}\n"
            f"K = {float(k_coefficient)}\n"
            f"MMP_P = {format_currency(mmp_base)} × {float(k_coefficient)} = "
            f"{format_currency(mmp_p)}"
        )

        return self._round_to_precision(mmp_p), formula

    def calculate_mmp_by_claims(
        self,
        incurred_claims: Decimal,
        k_coefficient: Decimal = None
    ) -> Tuple[Decimal, str]:
        """
        Расчет MMP по убыткам

        Формула: MMP_I = max(0.26×min(D, 2.5B), 0.23×(D-2.5B)) × K

        Args:
            incurred_claims: Понесенные убытки за последние 36 месяцев (годовое среднее)
            k_coefficient: Поправочный коэффициент

        Returns:
            (mmp_i, formula_display)
        """
        if k_coefficient is None:
            k_coefficient = self.config['K_COEFFICIENT']['default']

        coef = self.config['MMP_CLAIMS_COEFFICIENTS']
        threshold = coef['tier_1_threshold']

        if incurred_claims <= threshold:
            mmp_base = incurred_claims * coef['tier_1_rate']
            tier_info = f"{float(incurred_claims / 1e9):.2f}B ≤ 2.5B: применяется 26%"
        else:
            tier_1 = threshold * coef['tier_1_rate']
            tier_2 = (incurred_claims - threshold) * coef['tier_2_rate']
            mmp_base = tier_1 + tier_2
            tier_info = (
                f"Tier 1 (до 2.5B): {format_currency(tier_1)}\n"
                f"Tier 2 (свыше 2.5B): {format_currency(tier_2)}"
            )

        mmp_i = mmp_base * k_coefficient

        formula = (
            f"MMP по убыткам:\n"
            f"Понесенные убытки (ср.год.): {format_currency(incurred_claims)}\n"
            f"{tier_info}\n"
            f"MMP_base = {format_currency(mmp_base)}\n"
            f"K = {float(k_coefficient)}\n"
            f"MMP_I = {format_currency(mmp_base)} × {float(k_coefficient)} = "
            f"{format_currency(mmp_i)}"
        )

        return self._round_to_precision(mmp_i), formula

    def calculate_mmp_life(
        self,
        annuity_reserves: Decimal,
        math_reserves: Decimal
    ) -> Tuple[Decimal, str]:
        """
        Расчет MMP для Life страхования

        Формула: MMP_life = 8% × Annuity_reserves + 3% × Math_reserves

        Args:
            annuity_reserves: Резервы по аннуитетам
            math_reserves: Математические резервы

        Returns:
            (mmp_life, formula_display)
        """
        coef = self.config['LIFE_COEFFICIENTS']

        annuity_component = annuity_reserves * coef['annuity_rate']
        math_component = math_reserves * coef['math_reserve_addon']
        mmp_life = annuity_component + math_component

        formula = (
            f"MMP для Life:\n"
            f"8% × Annuity reserves = {float(coef['annuity_rate']):.0%} × "
            f"{format_currency(annuity_reserves)} = {format_currency(annuity_component)}\n"
            f"3% × Math reserves = {float(coef['math_reserve_addon']):.0%} × "
            f"{format_currency(math_reserves)} = {format_currency(math_component)}\n"
            f"MMP_life = {format_currency(mmp_life)}"
        )

        return self._round_to_precision(mmp_life), formula

    def calculate_mmp(
        self,
        gross_premiums: Decimal,
        incurred_claims: Decimal,
        k_coefficient: Decimal = None,
        has_osago: bool = False,
        annuity_reserves: Decimal = None,
        math_reserves: Decimal = None
    ) -> MMPResult:
        """
        Полный расчет MMP

        Per АРФР §304:
        MMP = max(MMP_P, MMP_I) + Life_addon + OSAGO_adjustment

        Args:
            gross_premiums: Валовые премии
            incurred_claims: Понесенные убытки
            k_coefficient: Поправочный коэффициент
            has_osago: Наличие ОСАГО портфеля
            annuity_reserves: Резервы аннуитетов (для Life)
            math_reserves: Математические резервы (для Life)

        Returns:
            MMPResult с полной детализацией
        """
        if k_coefficient is None:
            k_coefficient = self.config['K_COEFFICIENT']['default']

        # MMP по премиям
        mmp_p, mmp_p_formula = self.calculate_mmp_by_premiums(gross_premiums, k_coefficient)

        # MMP по убыткам
        mmp_i, mmp_i_formula = self.calculate_mmp_by_claims(incurred_claims, k_coefficient)

        # Базовый MMP = max(MMP_P, MMP_I)
        mmp_base = max(mmp_p, mmp_i)

        # Life addon
        life_addon = Decimal('0')
        life_formula = ""
        if annuity_reserves and math_reserves:
            life_addon, life_formula = self.calculate_mmp_life(annuity_reserves, math_reserves)

        # OSAGO adjustment (+50%)
        osago_adjustment = Decimal('0')
        if has_osago:
            osago_adjustment = mmp_base * Decimal('0.50')

        # Итоговый MMP
        total_mmp = mmp_base + life_addon + osago_adjustment

        # MGF проверка
        mgf, _ = self.calculate_mgf()
        total_mmp = max(total_mmp, mgf)

        total_mmp = self._round_to_precision(total_mmp)

        formula_display = (
            f"{'='*60}\n"
            f"РАСЧЕТ MMP (Минимальная маржа платежеспособности)\n"
            f"{'='*60}\n\n"
            f"{mmp_p_formula}\n\n"
            f"{mmp_i_formula}\n\n"
            f"Базовый MMP = max(MMP_P, MMP_I) = max({format_currency(mmp_p)}, "
            f"{format_currency(mmp_i)}) = {format_currency(mmp_base)}\n"
        )

        if life_formula:
            formula_display += f"\n{life_formula}\n"

        if has_osago:
            formula_display += (
                f"\nОСАГО надбавка (+50%): {format_currency(osago_adjustment)}\n"
            )

        formula_display += (
            f"\nИтого MMP = {format_currency(mmp_base)} + {format_currency(life_addon)} + "
            f"{format_currency(osago_adjustment)} = {format_currency(total_mmp)}\n"
            f"\nПроверка MGF: {format_currency(mgf)}\n"
            f"{'MMP ≥ MGF ✓' if total_mmp >= mgf else 'MMP < MGF - применяется MGF'}\n"
            f"{'='*60}\n"
        )

        justification = (
            f"MMP рассчитан в соответствии с АРФР Постановление №304 от 26.12.2016 "
            f"с изменениями 2023-2025. Поправочный коэффициент K = {float(k_coefficient)}. "
            f"{'Применена ОСАГО надбавка +50%. ' if has_osago else ''}"
            f"Итоговый MMP = {format_currency(total_mmp)}."
        )

        result = MMPResult(
            mmp_amount=total_mmp,
            mmp_by_premiums=mmp_p,
            mmp_by_claims=mmp_i,
            k_coefficient=k_coefficient,
            osago_adjustment=osago_adjustment,
            formula_display=formula_display,
            justification=justification
        )

        self._log_audit('Расчет MMP', {
            'mmp': float(total_mmp),
            'mmp_p': float(mmp_p),
            'mmp_i': float(mmp_i),
            'k': float(k_coefficient),
        })

        return result

    # =========================================================================
    # FMP (Фактическая маржа платежеспособности)
    # Per АРФР §304
    # =========================================================================

    def calculate_fmp(
        self,
        equity_capital: Decimal,
        ecl_adjustment: Decimal = Decimal('0'),
        csm_adjustment: Decimal = Decimal('0'),
        subordinated_debt: Decimal = Decimal('0'),
        illiquid_assets: Decimal = Decimal('0'),
        intangible_assets: Decimal = Decimal('0'),
        repo_penalty: Decimal = Decimal('0')
    ) -> FMPResult:
        """
        Расчет FMP (Фактическая маржа платежеспособности)

        Формула: FMP = Equity - ECL - Illiquids - Intangibles + CSM + Subordinated - Penalties

        Args:
            equity_capital: Собственный капитал
            ecl_adjustment: Корректировка ECL (МСФО 9)
            csm_adjustment: Корректировка CSM (МСФО 17)
            subordinated_debt: Субординированный долг (≤50% FMP)
            illiquid_assets: Неликвидные активы
            intangible_assets: Нематериальные активы
            repo_penalty: Штраф за превышение РЕПО лимита

        Returns:
            FMPResult с детализацией
        """
        # Базовый расчет
        fmp_base = (
            equity_capital -
            ecl_adjustment -
            illiquid_assets -
            intangible_assets +
            csm_adjustment
        )

        # Субординированный долг (ограничение ≤50%)
        max_subordinated = fmp_base * self.config['SUBORDINATED_DEBT_LIMIT']
        subordinated_included = min(subordinated_debt, max_subordinated)

        # FMP до штрафов
        fmp_before_penalties = fmp_base + subordinated_included

        # Итоговый FMP
        total_fmp = fmp_before_penalties - repo_penalty
        total_fmp = self._round_to_precision(total_fmp)

        components = {
            'equity_capital': equity_capital,
            'ecl_adjustment': ecl_adjustment,
            'csm_adjustment': csm_adjustment,
            'subordinated_debt': subordinated_included,
            'illiquid_assets': illiquid_assets,
            'intangible_assets': intangible_assets,
        }

        adjustments = {
            'subordinated_cap': max_subordinated,
            'subordinated_excess': max(Decimal('0'), subordinated_debt - max_subordinated),
            'repo_penalty': repo_penalty,
        }

        formula_display = (
            f"{'='*60}\n"
            f"РАСЧЕТ FMP (Фактическая маржа платежеспособности)\n"
            f"{'='*60}\n\n"
            f"Компоненты:\n"
            f"  Собственный капитал: {format_currency(equity_capital)}\n"
            f"  - ECL (МСФО 9): {format_currency(ecl_adjustment)}\n"
            f"  - Неликвидные активы: {format_currency(illiquid_assets)}\n"
            f"  - Нематериальные активы: {format_currency(intangible_assets)}\n"
            f"  + CSM (МСФО 17): {format_currency(csm_adjustment)}\n"
            f"  = FMP_base: {format_currency(fmp_base)}\n\n"
            f"Субординированный долг:\n"
            f"  Заявленный: {format_currency(subordinated_debt)}\n"
            f"  Лимит (50% FMP): {format_currency(max_subordinated)}\n"
            f"  Включено: {format_currency(subordinated_included)}\n\n"
            f"FMP до штрафов: {format_currency(fmp_before_penalties)}\n"
        )

        if repo_penalty > 0:
            formula_display += f"- РЕПО штраф: {format_currency(repo_penalty)}\n"

        formula_display += (
            f"\nИТОГО FMP = {format_currency(total_fmp)}\n"
            f"{'='*60}\n"
        )

        justification = (
            f"FMP рассчитан с учетом корректировок МСФО 9 (ECL: "
            f"{format_currency(ecl_adjustment)}) и МСФО 17 (CSM: "
            f"{format_currency(csm_adjustment)}). "
            f"Субординированный долг ограничен 50% от FMP. "
            f"{'Применен РЕПО штраф. ' if repo_penalty > 0 else ''}"
            f"Итоговый FMP = {format_currency(total_fmp)}."
        )

        result = FMPResult(
            fmp_amount=total_fmp,
            components=components,
            adjustments=adjustments,
            formula_display=formula_display,
            justification=justification
        )

        self._log_audit('Расчет FMP', {
            'fmp': float(total_fmp),
            'equity': float(equity_capital),
            'ecl': float(ecl_adjustment),
            'csm': float(csm_adjustment),
        })

        return result

    # =========================================================================
    # КОЭФФИЦИЕНТ ПЛАТЕЖЕСПОСОБНОСТИ
    # Per АРФР §304
    # =========================================================================

    def calculate_solvency_ratio(
        self,
        fmp: Decimal,
        mmp: Decimal
    ) -> SolvencyRatioResult:
        """
        Расчет коэффициента платежеспособности (Nmп)

        Формула: Nmп = FMP / MMP

        Требование: Nmп ≥ 1.0

        Args:
            fmp: Фактическая маржа
            mmp: Минимальная маржа

        Returns:
            SolvencyRatioResult
        """
        if mmp == 0:
            ratio = Decimal('0')
            is_compliant = False
        else:
            ratio = fmp / mmp
            is_compliant = ratio >= Decimal('1.0')

        ratio = self._round_to_precision(ratio)

        # Определение статуса
        if ratio >= Decimal('2.0'):
            status = "ОТЛИЧНО (≥200%)"
        elif ratio >= Decimal('1.5'):
            status = "ХОРОШО (≥150%)"
        elif ratio >= Decimal('1.0'):
            status = "ДОСТАТОЧНО (≥100%)"
        else:
            status = "НЕДОСТАТОЧНО (<100%) - ТРЕБУЕТСЯ ДОКАПИТАЛИЗАЦИЯ"

        formula_display = (
            f"{'='*60}\n"
            f"КОЭФФИЦИЕНТ ПЛАТЕЖЕСПОСОБНОСТИ (Nmп)\n"
            f"{'='*60}\n\n"
            f"Формула: Nmп = FMP / MMP\n\n"
            f"FMP = {format_currency(fmp)}\n"
            f"MMP = {format_currency(mmp)}\n"
            f"Nmп = {float(ratio):.2%}\n\n"
            f"Статус: {status}\n"
            f"{'='*60}\n"
        )

        justification = (
            f"Коэффициент платежеспособности Nmп = {float(ratio):.2%} "
            f"{'соответствует' if is_compliant else 'НЕ соответствует'} "
            f"требованию АРФР (≥100%). "
            f"{'При Nmп < 100% требуется докапитализация или уменьшение рисков.' if not is_compliant else ''}"
        )

        result = SolvencyRatioResult(
            ratio=ratio,
            fmp=fmp,
            mmp=mmp,
            is_compliant=is_compliant,
            formula_display=formula_display,
            justification=justification
        )

        self._log_audit('Расчет Nmп', {
            'ratio': float(ratio),
            'fmp': float(fmp),
            'mmp': float(mmp),
            'compliant': is_compliant,
        })

        return result

    # =========================================================================
    # SOLVENCY II SCR МОДУЛИ
    # Per EU 2025/2, EIOPA 2025 updates
    # =========================================================================

    def calculate_scr_market(
        self,
        equity_exposure: Decimal,
        property_exposure: Decimal,
        interest_rate_sensitivity: Decimal,
        spread_exposure: Decimal
    ) -> Tuple[Decimal, str]:
        """
        Расчет SCR для рыночного риска

        Per Solvency II Standard Formula:
        SCR_market = √(Σ Corr × SCR_i × SCR_j)

        Args:
            equity_exposure: Экспозиция к акциям
            property_exposure: Экспозиция к недвижимости
            interest_rate_sensitivity: Чувствительность к процентным ставкам
            spread_exposure: Экспозиция к спредам

        Returns:
            (scr_market, formula_display)
        """
        shocks = self.config['SCR_SHOCKS']

        # Расчет компонентов
        scr_equity = equity_exposure * shocks['equity_type1']
        scr_property = property_exposure * shocks['property']
        scr_interest = interest_rate_sensitivity * shocks['interest_up']
        scr_spread = spread_exposure * shocks['spread']

        # Упрощенная агрегация (без корреляций для демо)
        scr_market = Decimal(str(np.sqrt(
            float(scr_equity)**2 +
            float(scr_property)**2 +
            float(scr_interest)**2 +
            float(scr_spread)**2
        )))

        scr_market = self._round_to_precision(scr_market)

        formula = (
            f"SCR Market Risk:\n"
            f"  Equity (39% shock): {format_currency(scr_equity)}\n"
            f"  Property (25% shock): {format_currency(scr_property)}\n"
            f"  Interest (20% shock): {format_currency(scr_interest)}\n"
            f"  Spread (10% shock): {format_currency(scr_spread)}\n"
            f"  Total: {format_currency(scr_market)}"
        )

        return scr_market, formula

    def calculate_scr_underwriting(
        self,
        premium_risk: Decimal,
        reserve_risk: Decimal,
        catastrophe_risk: Decimal
    ) -> Tuple[Decimal, str]:
        """
        Расчет SCR для страхового риска

        Args:
            premium_risk: Риск премий
            reserve_risk: Риск резервов
            catastrophe_risk: Катастрофический риск

        Returns:
            (scr_uw, formula_display)
        """
        # Агрегация
        scr_uw = Decimal(str(np.sqrt(
            float(premium_risk)**2 +
            float(reserve_risk)**2 +
            float(catastrophe_risk)**2
        )))

        scr_uw = self._round_to_precision(scr_uw)

        formula = (
            f"SCR Underwriting Risk:\n"
            f"  Premium risk: {format_currency(premium_risk)}\n"
            f"  Reserve risk: {format_currency(reserve_risk)}\n"
            f"  Catastrophe risk: {format_currency(catastrophe_risk)}\n"
            f"  Total: {format_currency(scr_uw)}"
        )

        return scr_uw, formula

    def calculate_scr_operational(
        self,
        bscr: Decimal,
        gross_premiums: Decimal,
        technical_provisions: Decimal
    ) -> Tuple[Decimal, str]:
        """
        Расчет SCR для операционного риска

        Формула: SCR_op = min(30% BSCR, max(3% Prem, 3% TP))

        Args:
            bscr: Basic SCR
            gross_premiums: Валовые премии
            technical_provisions: Технические резервы

        Returns:
            (scr_op, formula_display)
        """
        op_config = self.config['OPERATIONAL_RISK']

        # Расчет по премиям и TP
        op_premiums = gross_premiums * op_config['premium_rate']
        op_tp = technical_provisions * op_config['tp_rate']
        op_base = max(op_premiums, op_tp)

        # Ограничение 30% BSCR
        op_cap = bscr * op_config['bscr_cap']
        scr_op = min(op_base, op_cap)

        scr_op = self._round_to_precision(scr_op)

        formula = (
            f"SCR Operational Risk:\n"
            f"  3% premiums: {format_currency(op_premiums)}\n"
            f"  3% TP: {format_currency(op_tp)}\n"
            f"  Max: {format_currency(op_base)}\n"
            f"  Cap (30% BSCR): {format_currency(op_cap)}\n"
            f"  SCR_op: {format_currency(scr_op)}"
        )

        return scr_op, formula

    def calculate_bscr(
        self,
        scr_market: Decimal,
        scr_underwriting: Decimal,
        scr_counterparty: Decimal = Decimal('0')
    ) -> Tuple[Decimal, str]:
        """
        Расчет Basic SCR

        Формула: BSCR = √(Σ Corr × SCR_i × SCR_j)

        Args:
            scr_market: SCR рыночного риска
            scr_underwriting: SCR страхового риска
            scr_counterparty: SCR контрагентского риска

        Returns:
            (bscr, formula_display)
        """
        # Упрощенная агрегация
        bscr = Decimal(str(np.sqrt(
            float(scr_market)**2 +
            float(scr_underwriting)**2 +
            float(scr_counterparty)**2
        )))

        bscr = self._round_to_precision(bscr)

        formula = (
            f"Basic SCR:\n"
            f"  Market risk: {format_currency(scr_market)}\n"
            f"  Underwriting risk: {format_currency(scr_underwriting)}\n"
            f"  Counterparty risk: {format_currency(scr_counterparty)}\n"
            f"  BSCR: {format_currency(bscr)}"
        )

        return bscr, formula

    # =========================================================================
    # СТРЕСС-ТЕСТИРОВАНИЕ
    # Per АРФР требования, VaR 99.5%
    # =========================================================================

    def stress_test(
        self,
        base_fmp: Decimal,
        base_mmp: Decimal,
        scenarios: Dict[str, Dict] = None,
        num_simulations: int = 1000
    ) -> StressTestResult:
        """
        Стресс-тестирование платежеспособности

        Per АРФР: ежегодное стресс-тестирование, VaR 99.5%

        Args:
            base_fmp: Базовый FMP
            base_mmp: Базовый MMP
            scenarios: Сценарии {name: {fmp_shock: %, mmp_shock: %}}
            num_simulations: Количество симуляций Monte Carlo

        Returns:
            StressTestResult
        """
        if scenarios is None:
            scenarios = {
                'base': {'fmp_shock': Decimal('0'), 'mmp_shock': Decimal('0')},
                'adverse': {'fmp_shock': Decimal('-0.20'), 'mmp_shock': Decimal('0.10')},
                'severe': {'fmp_shock': Decimal('-0.40'), 'mmp_shock': Decimal('0.20')},
            }

        base_ratio = base_fmp / base_mmp if base_mmp > 0 else Decimal('0')
        stressed_ratios = {}

        for name, shocks in scenarios.items():
            stressed_fmp = base_fmp * (Decimal('1') + shocks['fmp_shock'])
            stressed_mmp = base_mmp * (Decimal('1') + shocks['mmp_shock'])
            ratio = stressed_fmp / stressed_mmp if stressed_mmp > 0 else Decimal('0')
            stressed_ratios[name] = self._round_to_precision(ratio)

        # Monte Carlo для VaR 99.5%
        np.random.seed(42)
        fmp_simulated = np.random.normal(
            float(base_fmp),
            float(base_fmp) * 0.15,  # 15% волатильность
            num_simulations
        )
        mmp_simulated = np.random.normal(
            float(base_mmp),
            float(base_mmp) * 0.05,  # 5% волатильность
            num_simulations
        )

        ratios_simulated = fmp_simulated / np.maximum(mmp_simulated, 1)
        var_99_5 = Decimal(str(np.percentile(ratios_simulated, 0.5)))  # 0.5 percentile для worst
        var_99_5 = self._round_to_precision(var_99_5)

        formula_display = (
            f"{'='*60}\n"
            f"СТРЕСС-ТЕСТИРОВАНИЕ ПЛАТЕЖЕСПОСОБНОСТИ\n"
            f"{'='*60}\n\n"
            f"Базовый Nmп: {float(base_ratio):.2%}\n\n"
            f"Сценарии:\n"
        )

        for name, ratio in stressed_ratios.items():
            compliant = "✓" if ratio >= Decimal('1.0') else "✗"
            formula_display += f"  {name}: {float(ratio):.2%} {compliant}\n"

        formula_display += (
            f"\nMonte Carlo VaR 99.5%: {float(var_99_5):.2%}\n"
            f"(Симуляций: {num_simulations})\n"
            f"{'='*60}\n"
        )

        justification = (
            f"Стресс-тест выполнен в соответствии с требованиями АРФР. "
            f"При стрессовом сценарии Nmп = {float(stressed_ratios.get('severe', base_ratio)):.2%}. "
            f"VaR 99.5% = {float(var_99_5):.2%} (1-в-200 лет)."
        )

        result = StressTestResult(
            base_ratio=base_ratio,
            stressed_ratios=stressed_ratios,
            var_99_5=var_99_5,
            formula_display=formula_display,
            justification=justification
        )

        self._log_audit('Стресс-тест', {
            'base_ratio': float(base_ratio),
            'var_99_5': float(var_99_5),
            'scenarios': list(scenarios.keys()),
        })

        return result

    # =========================================================================
    # IFRS IMPACT ANALYSIS
    # =========================================================================

    def calculate_ifrs_impact(
        self,
        pre_ifrs_fmp: Decimal,
        pre_ifrs_mmp: Decimal,
        ecl_impact: Decimal,
        csm_impact: Decimal,
        bel_ra_impact: Decimal
    ) -> Dict[str, Any]:
        """
        Анализ влияния МСФО на платежеспособность

        Args:
            pre_ifrs_fmp: FMP до МСФО
            pre_ifrs_mmp: MMP до МСФО
            ecl_impact: Влияние ECL на активы
            csm_impact: Влияние CSM на капитал
            bel_ra_impact: Влияние BEL/RA на резервы

        Returns:
            Словарь с анализом
        """
        # Pre-IFRS ratio
        pre_ratio = pre_ifrs_fmp / pre_ifrs_mmp if pre_ifrs_mmp > 0 else Decimal('0')

        # Post-IFRS
        post_fmp = pre_ifrs_fmp - ecl_impact + csm_impact
        post_mmp = pre_ifrs_mmp - bel_ra_impact
        post_ratio = post_fmp / post_mmp if post_mmp > 0 else Decimal('0')

        # Изменение в п.п.
        ratio_change_pp = (post_ratio - pre_ratio) * Decimal('100')

        return {
            'pre_ifrs': {
                'fmp': pre_ifrs_fmp,
                'mmp': pre_ifrs_mmp,
                'ratio': self._round_to_precision(pre_ratio),
            },
            'post_ifrs': {
                'fmp': self._round_to_precision(post_fmp),
                'mmp': self._round_to_precision(post_mmp),
                'ratio': self._round_to_precision(post_ratio),
            },
            'impacts': {
                'ecl': ecl_impact,
                'csm': csm_impact,
                'bel_ra': bel_ra_impact,
            },
            'ratio_change_pp': self._round_to_precision(ratio_change_pp),
        }

    # =========================================================================
    # НОРМАТИВЫ И ПРОВЕРКИ
    # =========================================================================

    def check_high_liquid_ratio(
        self,
        high_liquid_assets: Decimal,
        reserves: Decimal
    ) -> Dict[str, Any]:
        """
        Проверка норматива высоколиквидных активов

        Требование: High_liquid / Reserves ≥ 1.0

        Args:
            high_liquid_assets: Высоколиквидные активы
            reserves: Технические резервы

        Returns:
            Результат проверки
        """
        if reserves == 0:
            return {'compliant': False, 'ratio': None, 'message': 'Резервы = 0'}

        ratio = high_liquid_assets / reserves
        required = self.config['HIGH_LIQUID_ASSETS_RATIO']
        compliant = ratio >= required

        return {
            'compliant': compliant,
            'ratio': self._round_to_precision(ratio),
            'required': required,
            'message': f"{'Норматив соблюден' if compliant else 'НАРУШЕНИЕ'}: "
                       f"{float(ratio):.2%} vs {float(required):.0%}"
        }

    def check_diversification_limits(
        self,
        exposures: Dict[str, Decimal],
        total_assets: Decimal
    ) -> List[Dict]:
        """
        Проверка лимитов диверсификации

        Per АРФР: ≤10% на одного эмитента, ≤30% на группу

        Args:
            exposures: {issuer: amount}
            total_assets: Общие активы

        Returns:
            Список нарушений
        """
        violations = []
        single_limit = self.config['ASSET_DIVERSIFICATION_LIMITS']['single_issuer']
        group_limit = self.config['ASSET_DIVERSIFICATION_LIMITS']['group']

        for issuer, amount in exposures.items():
            ratio = amount / total_assets if total_assets > 0 else Decimal('0')

            if ratio > single_limit:
                violations.append({
                    'issuer': issuer,
                    'ratio': float(ratio),
                    'limit': float(single_limit),
                    'excess': float(ratio - single_limit),
                })

        return violations

    def check_board_diversity(
        self,
        board_composition: Dict[str, int]
    ) -> Dict[str, Any]:
        """
        Проверка диверсификации совета директоров

        Per EIOPA 2025: ≥40% недопредставленного пола

        Args:
            board_composition: {'male': N, 'female': M}

        Returns:
            Результат проверки
        """
        total = sum(board_composition.values())
        if total == 0:
            return {'compliant': False, 'message': 'Нет данных о составе'}

        min_representation = min(board_composition.values())
        ratio = Decimal(str(min_representation / total))
        required = self.config['BOARD_DIVERSITY']['min_underrepresented']
        compliant = ratio >= required

        return {
            'compliant': compliant,
            'ratio': float(ratio),
            'required': float(required),
            'composition': board_composition,
            'message': f"{'Диверсификация соблюдена' if compliant else 'Требуется улучшение'}"
        }

    def get_audit_log(self) -> List[Dict]:
        """Получить аудиторский след"""
        return self.audit_log

    def check_minimum_capital(
        self,
        charter_capital: Decimal,
        insurer_type: str,
        insurance_classes: List[str] = None
    ) -> Dict[str, Any]:
        """
        Проверка минимального уставного капитала

        Per Постановление НБ РК (adilet.zan.kz/rus/docs/V010001513_)

        Args:
            charter_capital: Уставный капитал компании
            insurer_type: Тип страховщика ('general_insurance', 'life_insurance',
                          'general_reinsurance', 'life_reinsurance', 'reinsurance_only')
            insurance_classes: Список классов страхования

        Returns:
            Результат проверки с детализацией
        """
        min_capital_config = self.config.get('MINIMUM_CHARTER_CAPITAL', {})
        additional_config = self.config.get('ADDITIONAL_CAPITAL_BY_CLASS', {})

        # Базовый минимум по типу страховщика
        base_minimum = min_capital_config.get(insurer_type, Decimal('130000000'))

        # Дополнительные требования по классам
        additional_required = Decimal('0')
        class_details = []

        if insurance_classes:
            for ins_class in insurance_classes:
                additional = additional_config.get(ins_class, Decimal('0'))
                if additional > 0:
                    additional_required += additional
                    class_details.append({
                        'class': ins_class,
                        'additional': additional
                    })

        # Итоговый минимум
        total_minimum = base_minimum + additional_required
        compliant = charter_capital >= total_minimum
        shortfall = max(Decimal('0'), total_minimum - charter_capital)

        result = {
            'compliant': compliant,
            'charter_capital': charter_capital,
            'base_minimum': base_minimum,
            'additional_required': additional_required,
            'total_minimum': total_minimum,
            'shortfall': shortfall,
            'class_details': class_details,
            'insurer_type': insurer_type,
            'message': (
                f"{'Уставный капитал соответствует требованиям' if compliant else 'НАРУШЕНИЕ: недостаточный уставный капитал'}\n"
                f"Уставный капитал: {format_currency(charter_capital)}\n"
                f"Базовый минимум ({insurer_type}): {format_currency(base_minimum)}\n"
                f"Дополнительно по классам: {format_currency(additional_required)}\n"
                f"Итого требуется: {format_currency(total_minimum)}\n"
                f"{'Дефицит: ' + format_currency(shortfall) if not compliant else 'Превышение: ' + format_currency(charter_capital - total_minimum)}"
            )
        }

        self._log_audit('Проверка уставного капитала', {
            'charter_capital': float(charter_capital),
            'minimum_required': float(total_minimum),
            'compliant': compliant,
            'insurer_type': insurer_type
        })

        return result


# =============================================================================
# ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ
# =============================================================================

def demo_solvency_calculation():
    """Демонстрация расчета платежеспособности"""
    calc = SolvencyCalculator()

    # MMP
    mmp_result = calc.calculate_mmp(
        gross_premiums=Decimal('35000000000'),  # 35 млрд
        incurred_claims=Decimal('18000000000'),  # 18 млрд
        has_osago=True
    )

    print(mmp_result.formula_display)

    # FMP
    fmp_result = calc.calculate_fmp(
        equity_capital=Decimal('20000000000'),  # 20 млрд
        ecl_adjustment=Decimal('2100000000'),   # 2.1 млрд
        csm_adjustment=Decimal('11800000000'),  # 11.8 млрд
        subordinated_debt=Decimal('3000000000'), # 3 млрд
        illiquid_assets=Decimal('500000000'),    # 0.5 млрд
    )

    print(fmp_result.formula_display)

    # Ratio
    ratio_result = calc.calculate_solvency_ratio(
        fmp_result.fmp_amount,
        mmp_result.mmp_amount
    )

    print(ratio_result.formula_display)

    return mmp_result, fmp_result, ratio_result


if __name__ == '__main__':
    demo_solvency_calculation()
