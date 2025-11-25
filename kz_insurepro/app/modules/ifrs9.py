# -*- coding: utf-8 -*-
"""
KZ-InsurePro - Модуль МСФО 9: Финансовые инструменты
Расчет ECL (Expected Credit Loss), классификация и оценка

Соответствие:
- МСФО 9 para B5.5.17, B5.5.44-52
- АРФР Постановление №269 от 29.12.2017
- Изменения: №83 от 21.10.2024, №92 от 27.12.2024
- Макроданные НБК Ноябрь 2025

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
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import (
    IFRS9_CONFIG, MACRO_INDICATORS_2025, LOCALE_CONFIG,
    format_currency, format_percent, DEMO_CONFIG
)

logger = logging.getLogger(__name__)


@dataclass
class ECLResult:
    """Результат расчета ECL с аудиторским следом"""
    ecl_amount: Decimal
    stage: int
    pd_values: List[Decimal]
    lgd: Decimal
    ead_values: List[Decimal]
    discount_factors: List[Decimal]
    formula_display: str
    justification: str
    breakdown: Dict[str, Any]
    calculation_date: datetime


@dataclass
class ClassificationResult:
    """Результат классификации финансового актива"""
    category: str  # 'AC', 'FVOCI', 'FVTPL'
    sppi_passed: bool
    business_model: str
    justification: str


class IFRS9Calculator:
    """
    Калькулятор МСФО 9 для расчета ECL и классификации

    Реализует:
    - 3-стадийную модель обесценения
    - PD модели: базовая, байесовская, ML (Random Forest, Logistic Regression)
    - LGD с макро-корректировками
    - EAD с CCF для внебалансовых
    - Форвардные сценарии (base/adverse/severe)
    - Символьные вычисления через sympy
    """

    def __init__(self):
        self.config = IFRS9_CONFIG
        self.macro = MACRO_INDICATORS_2025
        self.precision = self.config['PRECISION']

        # Символьные переменные для формул
        self.t_sym = sp.Symbol('t', positive=True, integer=True)
        self.pd_sym = sp.Symbol('PD', positive=True)
        self.lgd_sym = sp.Symbol('LGD', positive=True)
        self.ead_sym = sp.Symbol('EAD', positive=True)
        self.r_sym = sp.Symbol('r', positive=True)

        # Аудиторский след
        self.audit_log = []

        logger.info("IFRS9Calculator инициализирован с макроданными на %s",
                    self.macro['date'].strftime('%d.%m.%Y'))

    def _round_to_precision(self, value: Decimal) -> Decimal:
        """Округление до точности 0.001 KZT per АРФР требования"""
        return value.quantize(self.precision, rounding=ROUND_HALF_UP)

    def _log_audit(self, operation: str, details: Dict[str, Any]):
        """Запись в аудиторский след"""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'operation': operation,
            'details': details,
            'reference': 'МСФО 9 / АРФР №269'
        }
        self.audit_log.append(entry)
        logger.info(f"Аудит: {operation}")

    # =========================================================================
    # КЛАССИФИКАЦИЯ И ОЦЕНКА
    # Per IFRS 9 para 4.1.1-4.1.5, B4.1.1-B4.1.26
    # =========================================================================

    def classify_asset(
        self,
        cash_flows: List[Dict],
        business_model: str,
        contractual_terms: Dict
    ) -> ClassificationResult:
        """
        Классификация финансового актива

        Per IFRS 9 para 4.1.2-4.1.4:
        - Amortized Cost: SPPI + Hold-to-Collect
        - FVOCI: SPPI + Hold-and-Sell
        - FVTPL: по умолчанию или опция

        Args:
            cash_flows: Денежные потоки инструмента
            business_model: 'hold_to_collect', 'hold_and_sell', 'trading'
            contractual_terms: Контрактные условия для SPPI теста

        Returns:
            ClassificationResult с категорией и обоснованием
        """
        # SPPI тест (Solely Payments of Principal and Interest)
        sppi_passed = self._sppi_test(contractual_terms)

        # Определение категории
        if business_model == 'hold_to_collect' and sppi_passed:
            category = 'AC'  # Amortized Cost
            justification = (
                "Актив классифицирован как оцениваемый по амортизированной стоимости "
                "(AC) согласно МСФО 9 para 4.1.2: бизнес-модель 'удержание для получения' "
                "и тест SPPI пройден. Денежные потоки представляют собой исключительно "
                "платежи основной суммы и процентов."
            )
        elif business_model == 'hold_and_sell' and sppi_passed:
            category = 'FVOCI'  # Fair Value through OCI
            justification = (
                "Актив классифицирован как оцениваемый по справедливой стоимости через ПСД "
                "(FVOCI) согласно МСФО 9 para 4.1.2A: бизнес-модель 'удержание для получения "
                "и продажи', тест SPPI пройден."
            )
        else:
            category = 'FVTPL'  # Fair Value through P&L
            reason = "тест SPPI не пройден" if not sppi_passed else "бизнес-модель торговая"
            justification = (
                f"Актив классифицирован как оцениваемый по справедливой стоимости через ПиУ "
                f"(FVTPL) согласно МСФО 9 para 4.1.4: {reason}."
            )

        result = ClassificationResult(
            category=category,
            sppi_passed=sppi_passed,
            business_model=business_model,
            justification=justification
        )

        self._log_audit('Классификация актива', {
            'category': category,
            'sppi_passed': sppi_passed,
            'business_model': business_model
        })

        return result

    def _sppi_test(self, terms: Dict) -> bool:
        """
        Тест SPPI (Solely Payments of Principal and Interest)

        Per IFRS 9 para B4.1.7-B4.1.26:
        - Проверка контрактных условий
        - Наличие leveraged features, contingent events, etc.

        Args:
            terms: Контрактные условия

        Returns:
            True если тест пройден
        """
        # Проверка отсутствия "провальных" характеристик
        failed_features = [
            'leverage',           # Кредитное плечо
            'prepayment_penalty_excessive',  # Чрезмерные штрафы за досрочное погашение
            'contingent_principal',  # Условный номинал
            'equity_conversion',   # Конвертация в капитал
            'inverse_floating',    # Обратная плавающая ставка
        ]

        for feature in failed_features:
            if terms.get(feature, False):
                return False

        # Проверка benchmark теста для modified time value
        if terms.get('modified_time_value'):
            # Дополнительный benchmark тест per B4.1.9B
            benchmark_diff = terms.get('benchmark_difference', Decimal('0'))
            if benchmark_diff > Decimal('0.10'):  # >10% разница
                return False

        return True

    def business_model_test(
        self,
        collections: Decimal,
        sales: Decimal
    ) -> Tuple[str, str]:
        """
        Тест бизнес-модели

        Per IFRS 9 para B4.1.2-B4.1.6

        Args:
            collections: Объем собранных платежей
            sales: Объем продаж

        Returns:
            (model_type, justification)
        """
        total = collections + sales
        if total == 0:
            return 'undetermined', 'Недостаточно данных для определения бизнес-модели'

        hold_ratio = collections / total

        # Per B4.1.2B: >95% collections = hold-to-collect
        if hold_ratio > Decimal('0.95'):
            return 'hold_to_collect', (
                f"Бизнес-модель 'удержание для получения': доля сборов "
                f"{format_percent(hold_ratio * 100)} > 95%"
            )
        elif hold_ratio > Decimal('0.60'):
            return 'hold_and_sell', (
                f"Бизнес-модель 'удержание и продажа': доля сборов "
                f"{format_percent(hold_ratio * 100)} между 60% и 95%"
            )
        else:
            return 'trading', (
                f"Торговая бизнес-модель: доля сборов "
                f"{format_percent(hold_ratio * 100)} < 60%"
            )

    # =========================================================================
    # ОПРЕДЕЛЕНИЕ СТАДИИ
    # Per IFRS 9 para 5.5.3-5.5.11
    # =========================================================================

    def determine_stage(
        self,
        days_past_due: int,
        pd_current: Decimal,
        pd_at_origination: Decimal,
        qualitative_factors: Dict = None
    ) -> Tuple[int, str]:
        """
        Определение стадии обесценения

        Per IFRS 9 para 5.5.3-5.5.11, АРФР рекомендации:
        - Стадия 1: Низкий кредитный риск, 12-месячный ECL
        - Стадия 2: SICR (Significant Increase in Credit Risk), пожизненный ECL
        - Стадия 3: Кредитно-обесцененные, пожизненный ECL

        Args:
            days_past_due: Дни просрочки
            pd_current: Текущая PD
            pd_at_origination: PD при первоначальном признании
            qualitative_factors: Качественные факторы (реструктуризация, и т.д.)

        Returns:
            (stage, justification)
        """
        thresholds = self.config['STAGE_THRESHOLDS']
        qualitative_factors = qualitative_factors or {}

        # Стадия 3: Кредитно-обесцененные (>90 DPD или дефолт)
        if (days_past_due > thresholds['stage_3_days_past_due'] or
                qualitative_factors.get('default_event', False)):
            return 3, (
                f"Стадия 3 (кредитно-обесцененные): просрочка {days_past_due} дней > 90 дней "
                f"или наличие события дефолта. МСФО 9 para 5.5.3, B5.5.37."
            )

        # Проверка SICR (Significant Increase in Credit Risk)
        sicr_triggered = False
        sicr_reasons = []

        # Количественный критерий: DPD > 30
        if days_past_due > thresholds['stage_2_days_past_due']:
            sicr_triggered = True
            sicr_reasons.append(f"просрочка {days_past_due} дней > 30 дней")

        # Количественный критерий: относительное увеличение PD
        if pd_at_origination > 0:
            pd_ratio = pd_current / pd_at_origination
            if pd_ratio > thresholds['pd_relative_increase']:
                sicr_triggered = True
                sicr_reasons.append(
                    f"PD увеличилась в {float(pd_ratio):.2f}x "
                    f"(порог: {float(thresholds['pd_relative_increase'])}x)"
                )

        # Абсолютное увеличение PD
        pd_increase = pd_current - pd_at_origination
        if pd_increase > thresholds['pd_absolute_increase']:
            sicr_triggered = True
            sicr_reasons.append(
                f"абсолютное увеличение PD на {format_percent(float(pd_increase) * 100)}"
            )

        # Качественные факторы
        if qualitative_factors.get('restructuring'):
            sicr_triggered = True
            sicr_reasons.append("реструктуризация договора")

        if qualitative_factors.get('watchlist'):
            sicr_triggered = True
            sicr_reasons.append("включение в список наблюдения")

        if qualitative_factors.get('covenant_breach'):
            sicr_triggered = True
            sicr_reasons.append("нарушение ковенантов")

        # Стадия 2: SICR
        if sicr_triggered:
            return 2, (
                f"Стадия 2 (SICR): {'; '.join(sicr_reasons)}. "
                f"МСФО 9 para 5.5.3-5.5.11, B5.5.15-B5.5.24."
            )

        # Стадия 1: Низкий кредитный риск
        return 1, (
            f"Стадия 1 (низкий кредитный риск): просрочка {days_past_due} дней ≤ 30 дней, "
            f"отсутствие SICR. МСФО 9 para 5.5.5."
        )

    # =========================================================================
    # РАСЧЕТ PD (Probability of Default)
    # Per IFRS 9 para B5.5.17-B5.5.24
    # =========================================================================

    def calculate_pd_base(
        self,
        historical_pd: Decimal,
        scenario: str = 'weighted'
    ) -> Tuple[Decimal, str]:
        """
        Расчет базовой PD с макро-корректировками

        Формула: PD_adj = PD_base × Σ(w_i × M_i)

        Мультипликаторы НБК Ноябрь 2025:
        - Base: 1.35
        - Adverse: 1.80
        - Severe: 2.40
        - Веса: 55%/35%/10%
        - Итоговый мультипликатор: 1.613

        Args:
            historical_pd: Историческая PD
            scenario: 'base', 'adverse', 'severe', 'weighted'

        Returns:
            (adjusted_pd, formula_display)
        """
        multipliers = self.config['PD_MULTIPLIERS']
        weights = self.config['SCENARIO_WEIGHTS']

        if scenario == 'weighted':
            # Взвешенный мультипликатор
            total_multiplier = (
                multipliers['base'] * weights['base'] +
                multipliers['adverse'] * weights['adverse'] +
                multipliers['severe'] * weights['severe']
            )
            adjusted_pd = historical_pd * total_multiplier

            formula = (
                f"PD_adj = PD_hist × Σ(w_i × M_i)\n"
                f"PD_adj = {float(historical_pd):.4f} × "
                f"({float(multipliers['base'])} × {float(weights['base'])} + "
                f"{float(multipliers['adverse'])} × {float(weights['adverse'])} + "
                f"{float(multipliers['severe'])} × {float(weights['severe'])})\n"
                f"PD_adj = {float(historical_pd):.4f} × {float(total_multiplier):.3f} = "
                f"{float(adjusted_pd):.4f}"
            )
        else:
            multiplier = multipliers[scenario]
            adjusted_pd = historical_pd * multiplier

            formula = (
                f"PD_adj = PD_hist × M_{scenario}\n"
                f"PD_adj = {float(historical_pd):.4f} × {float(multiplier)} = "
                f"{float(adjusted_pd):.4f}"
            )

        return self._round_to_precision(adjusted_pd), formula

    def calculate_pd_bayesian(
        self,
        defaults: int,
        exposures: int,
        prior_alpha: float = 1.0,
        prior_beta: float = 1.0
    ) -> Tuple[Decimal, str]:
        """
        Байесовская оценка PD

        Формула: PD_post = (defaults + α) / (exposures + α + β)
        Beta prior: Beta(α, β)

        Per IFRS 9 para B5.5.17 - использование всей доступной информации

        Args:
            defaults: Количество дефолтов
            exposures: Общее количество экспозиций
            prior_alpha: Параметр α априорного распределения
            prior_beta: Параметр β априорного распределения

        Returns:
            (pd_bayesian, formula_display)
        """
        # Апостериорная оценка из Beta-Binomial модели
        posterior_alpha = defaults + prior_alpha
        posterior_beta = exposures - defaults + prior_beta

        # Математическое ожидание апостериорного распределения
        pd_mean = Decimal(str(posterior_alpha / (posterior_alpha + posterior_beta)))

        # 95% доверительный интервал
        ci_lower = stats.beta.ppf(0.025, posterior_alpha, posterior_beta)
        ci_upper = stats.beta.ppf(0.975, posterior_alpha, posterior_beta)

        formula = (
            f"Байесовская оценка PD (Beta-Binomial):\n"
            f"Prior: Beta({prior_alpha}, {prior_beta})\n"
            f"Posterior: Beta({posterior_alpha:.1f}, {posterior_beta:.1f})\n"
            f"PD_post = E[Beta] = α/(α+β) = {posterior_alpha:.1f}/({posterior_alpha:.1f}+{posterior_beta:.1f})\n"
            f"PD_post = {float(pd_mean):.4f}\n"
            f"95% CI: [{ci_lower:.4f}, {ci_upper:.4f}]"
        )

        return self._round_to_precision(pd_mean), formula

    def calculate_pd_logistic(
        self,
        gdp_growth: Decimal,
        inflation: Decimal,
        coefficients: Dict = None
    ) -> Tuple[Decimal, str]:
        """
        PD через логистическую регрессию

        Формула: logit(PD) = β₀ + β₁×GDP + β₂×Inflation
        PD = 1 / (1 + exp(-logit))

        Args:
            gdp_growth: Рост ВВП, %
            inflation: Инфляция, %
            coefficients: Коэффициенты модели

        Returns:
            (pd_logistic, formula_display)
        """
        # Дефолтные коэффициенты (калиброваны на синтетических данных)
        if coefficients is None:
            coefficients = {
                'intercept': -3.5,
                'gdp': -0.15,
                'inflation': 0.08,
            }

        # Расчет logit
        logit = (
            coefficients['intercept'] +
            coefficients['gdp'] * float(gdp_growth) +
            coefficients['inflation'] * float(inflation)
        )

        # Преобразование в вероятность
        pd_value = Decimal(str(1 / (1 + np.exp(-logit))))

        formula = (
            f"Логистическая регрессия PD:\n"
            f"logit(PD) = β₀ + β₁×GDP + β₂×Inflation\n"
            f"logit(PD) = {coefficients['intercept']:.2f} + "
            f"({coefficients['gdp']:.2f})×{float(gdp_growth):.1f} + "
            f"({coefficients['inflation']:.2f})×{float(inflation):.1f}\n"
            f"logit(PD) = {logit:.4f}\n"
            f"PD = 1/(1 + exp(-{logit:.4f})) = {float(pd_value):.4f}"
        )

        return self._round_to_precision(pd_value), formula

    def calculate_marginal_pd(
        self,
        cumulative_pds: List[Decimal]
    ) -> List[Decimal]:
        """
        Расчет маржинальных PD из кумулятивных

        Формула: PD_marginal_t = PD_cumulative_t - PD_cumulative_{t-1}

        Per IFRS 9 para B5.5.47 - для пожизненных ECL

        Args:
            cumulative_pds: Список кумулятивных PD по годам

        Returns:
            Список маржинальных PD
        """
        marginal = [cumulative_pds[0]]
        for i in range(1, len(cumulative_pds)):
            marginal.append(cumulative_pds[i] - cumulative_pds[i - 1])

        return [self._round_to_precision(pd) for pd in marginal]

    # =========================================================================
    # РАСЧЕТ LGD (Loss Given Default)
    # Per IFRS 9 para B5.5.28-B5.5.30
    # =========================================================================

    def calculate_lgd(
        self,
        base_lgd: Decimal,
        collateral_type: str = 'unsecured',
        collateral_value: Decimal = Decimal('0'),
        ead: Decimal = Decimal('1'),
        apply_macro: bool = True
    ) -> Tuple[Decimal, str]:
        """
        Расчет LGD с макро-корректировками

        Формула: LGD_adj = LGD_hist × (1 + Δ_macro)
        Δ_macro = 0.05×Δinflation + 0.10×Δrate

        Args:
            base_lgd: Базовая LGD или None для дефолта по типу обеспечения
            collateral_type: Тип обеспечения
            collateral_value: Стоимость обеспечения
            ead: EAD для расчета LTV
            apply_macro: Применять ли макро-корректировки

        Returns:
            (adjusted_lgd, formula_display)
        """
        # Базовая LGD по типу обеспечения
        if base_lgd is None or base_lgd == 0:
            base_lgd = self.config['LGD_DEFAULTS'].get(
                collateral_type,
                self.config['LGD_DEFAULTS']['unsecured']
            )

        # Корректировка на стоимость обеспечения (если есть)
        if collateral_value > 0 and ead > 0:
            ltv = (ead - collateral_value) / ead
            ltv = max(Decimal('0'), min(ltv, Decimal('1')))
            # LGD = базовая × LTV (для secured)
            adjusted_lgd = base_lgd * ltv
        else:
            adjusted_lgd = base_lgd

        # Макро-корректировка
        if apply_macro:
            macro_adj = self.config['LGD_MACRO_ADJUSTMENTS']
            # Δinflation от целевого (5%)
            delta_inflation = (self.macro['inflation'] - Decimal('5')) / Decimal('100')
            # Δrate от нормального (10%)
            delta_rate = (self.macro['base_rate'] - Decimal('10')) / Decimal('100')

            macro_factor = (
                Decimal('1') +
                macro_adj['inflation_factor'] * delta_inflation +
                macro_adj['rate_factor'] * delta_rate
            )

            final_lgd = adjusted_lgd * macro_factor
        else:
            macro_factor = Decimal('1')
            final_lgd = adjusted_lgd

        # Ограничение LGD в диапазоне [0, 1]
        final_lgd = max(Decimal('0'), min(final_lgd, Decimal('1')))

        formula = (
            f"Расчет LGD:\n"
            f"Базовая LGD ({collateral_type}): {float(base_lgd):.2%}\n"
        )

        if collateral_value > 0:
            formula += (
                f"LTV = (EAD - Collateral)/EAD = "
                f"({format_currency(ead)} - {format_currency(collateral_value)}) / "
                f"{format_currency(ead)} = {float(ltv):.2%}\n"
                f"LGD после обеспечения: {float(adjusted_lgd):.2%}\n"
            )

        if apply_macro:
            formula += (
                f"Макро-корректировка:\n"
                f"Δ_macro = 0.05×({float(self.macro['inflation'])}-5)% + "
                f"0.10×({float(self.macro['base_rate'])}-10)%\n"
                f"Macro factor = {float(macro_factor):.4f}\n"
            )

        formula += f"LGD итоговая: {float(final_lgd):.2%}"

        return self._round_to_precision(final_lgd), formula

    def calculate_lgd_downturn(
        self,
        average_lgd: Decimal,
        lgd_std: Decimal,
        confidence: float = 0.95
    ) -> Tuple[Decimal, str]:
        """
        Downturn LGD (LGD в период спада)

        Формула: LGD_downturn = LGD_avg + σ × Z
        Z для 95% CL = 1.645

        Per АРФР требования к консервативности

        Args:
            average_lgd: Средняя LGD
            lgd_std: Стандартное отклонение LGD
            confidence: Уровень доверия

        Returns:
            (lgd_downturn, formula_display)
        """
        z_score = Decimal(str(stats.norm.ppf(confidence)))
        lgd_downturn = average_lgd + lgd_std * z_score

        # Ограничение
        lgd_downturn = min(lgd_downturn, Decimal('1'))

        formula = (
            f"Downturn LGD:\n"
            f"LGD_downturn = LGD_avg + σ × Z_{{{confidence*100:.0f}%}}\n"
            f"LGD_downturn = {float(average_lgd):.2%} + "
            f"{float(lgd_std):.2%} × {float(z_score):.3f}\n"
            f"LGD_downturn = {float(lgd_downturn):.2%}"
        )

        return self._round_to_precision(lgd_downturn), formula

    # =========================================================================
    # РАСЧЕТ EAD (Exposure at Default)
    # Per IFRS 9 para B5.5.31-B5.5.33
    # =========================================================================

    def calculate_ead(
        self,
        gross_carrying_amount: Decimal,
        undrawn_amount: Decimal = Decimal('0'),
        facility_type: str = 'credit_lines'
    ) -> Tuple[Decimal, str]:
        """
        Расчет EAD (Exposure at Default)

        Формула: EAD = GCA + Undrawn × CCF

        Args:
            gross_carrying_amount: Валовая балансовая стоимость
            undrawn_amount: Неиспользованная сумма (для внебалансовых)
            facility_type: Тип внебалансового обязательства

        Returns:
            (ead, formula_display)
        """
        ccf = self.config['CCF_FACTORS'].get(facility_type, Decimal('0.50'))

        if undrawn_amount > 0:
            off_balance = undrawn_amount * ccf
            ead = gross_carrying_amount + off_balance

            formula = (
                f"EAD = GCA + Undrawn × CCF\n"
                f"EAD = {format_currency(gross_carrying_amount)} + "
                f"{format_currency(undrawn_amount)} × {float(ccf):.2f}\n"
                f"EAD = {format_currency(gross_carrying_amount)} + "
                f"{format_currency(off_balance)}\n"
                f"EAD = {format_currency(ead)}"
            )
        else:
            ead = gross_carrying_amount
            formula = f"EAD = GCA = {format_currency(ead)}"

        return self._round_to_precision(ead), formula

    # =========================================================================
    # ДИСКОНТИРОВАНИЕ
    # Per IFRS 9 para 5.5.17, B5.5.44-B5.5.46
    # =========================================================================

    def calculate_discount_factor(
        self,
        period: int,
        eir: Decimal,
        method: str = 'discrete'
    ) -> Tuple[Decimal, str]:
        """
        Расчет фактора дисконтирования

        Формулы:
        - Дискретный: DF = 1 / (1 + EIR)^t
        - Непрерывный: DF = exp(-r × t)

        Args:
            period: Период (год)
            eir: Эффективная процентная ставка
            method: 'discrete' или 'continuous'

        Returns:
            (discount_factor, formula_display)
        """
        if method == 'continuous':
            # Непрерывное дисконтирование
            df = Decimal(str(np.exp(-float(eir) * period)))
            formula = (
                f"DF_{period} = exp(-r × t) = exp(-{float(eir):.4f} × {period})\n"
                f"DF_{period} = {float(df):.6f}"
            )
        else:
            # Дискретное дисконтирование
            df = Decimal('1') / ((Decimal('1') + eir) ** period)
            formula = (
                f"DF_{period} = 1 / (1 + EIR)^t = 1 / (1 + {float(eir):.4f})^{period}\n"
                f"DF_{period} = {float(df):.6f}"
            )

        return self._round_to_precision(df), formula

    def interpolate_yield_curve(
        self,
        tenors: List[int],
        rates: List[Decimal],
        target_tenor: int
    ) -> Tuple[Decimal, str]:
        """
        Интерполяция кривой доходности

        Методы: линейная или кубический сплайн

        Args:
            tenors: Сроки в годах
            rates: Ставки
            target_tenor: Целевой срок

        Returns:
            (interpolated_rate, formula_display)
        """
        # Кубический сплайн
        cs = CubicSpline([float(t) for t in tenors],
                        [float(r) for r in rates])
        interpolated = Decimal(str(cs(target_tenor)))

        formula = (
            f"Интерполяция ставки на срок {target_tenor} лет:\n"
            f"Метод: кубический сплайн\n"
            f"Входные данные: {list(zip(tenors, [float(r) for r in rates]))}\n"
            f"Результат: {float(interpolated):.4%}"
        )

        return self._round_to_precision(interpolated), formula

    # =========================================================================
    # РАСЧЕТ ECL (Expected Credit Loss)
    # Per IFRS 9 para 5.5.17-5.5.20, B5.5.28-B5.5.52
    # =========================================================================

    def calculate_ecl(
        self,
        stage: int,
        gross_carrying_amount: Decimal,
        pd_annual: Decimal,
        lgd: Decimal,
        eir: Decimal,
        remaining_term: int,
        undrawn: Decimal = Decimal('0'),
        facility_type: str = 'credit_lines',
        scenario: str = 'weighted',
        collateral_type: str = 'unsecured',
        collateral_value: Decimal = Decimal('0'),
        days_past_due: int = 0
    ) -> ECLResult:
        """
        Полный расчет ECL с аудиторским следом

        Формула: ECL = Σ(PD_t × LGD × EAD_t × DF_t)

        - Стадия 1: t = 1..12 месяцев (или до min(12, term))
        - Стадия 2/3: t = 1..remaining_term

        Args:
            stage: Стадия обесценения (1, 2, 3)
            gross_carrying_amount: Валовая балансовая стоимость
            pd_annual: Годовая PD
            lgd: LGD
            eir: Эффективная процентная ставка (годовая)
            remaining_term: Оставшийся срок в годах
            undrawn: Неиспользованная сумма
            facility_type: Тип внебалансового
            scenario: Сценарий PD
            collateral_type: Тип обеспечения
            collateral_value: Стоимость обеспечения
            days_past_due: Дни просрочки

        Returns:
            ECLResult с полной детализацией
        """
        # EAD
        ead, ead_formula = self.calculate_ead(
            gross_carrying_amount, undrawn, facility_type
        )

        # LGD с корректировками
        adjusted_lgd, lgd_formula = self.calculate_lgd(
            lgd, collateral_type, collateral_value, ead
        )

        # PD с макро-корректировкой
        adjusted_pd, pd_formula = self.calculate_pd_base(pd_annual, scenario)

        # Определение горизонта расчета
        if stage == 1:
            # 12-месячный ECL
            horizon = min(1, remaining_term)
            ecl_type = "12-месячный"
        else:
            # Пожизненный ECL
            horizon = remaining_term
            ecl_type = "пожизненный"

        # Расчет ECL по периодам
        ecl_components = []
        pd_values = []
        ead_values = []
        discount_factors = []

        total_ecl = Decimal('0')

        # Формируем маржинальные PD по годам
        # Простая модель: равномерное распределение годовой PD
        for t in range(1, horizon + 1):
            # PD для года t (маржинальная)
            # Используем формулу выживаемости: PD_marginal_t = PD_annual × (1-PD_annual)^(t-1)
            survival = (Decimal('1') - adjusted_pd) ** (t - 1)
            pd_t = adjusted_pd * survival
            pd_values.append(pd_t)

            # EAD_t (упрощенно: линейная амортизация)
            if remaining_term > 0:
                amortization_factor = Decimal(str(1 - (t - 1) / remaining_term))
            else:
                amortization_factor = Decimal('1')
            ead_t = ead * amortization_factor
            ead_values.append(ead_t)

            # Дисконт-фактор
            df_t, _ = self.calculate_discount_factor(t, eir)
            discount_factors.append(df_t)

            # ECL компонента
            ecl_t = pd_t * adjusted_lgd * ead_t * df_t
            ecl_components.append({
                'period': t,
                'pd': pd_t,
                'lgd': adjusted_lgd,
                'ead': ead_t,
                'df': df_t,
                'ecl': ecl_t
            })
            total_ecl += ecl_t

        # Корректировка для Стадии 3: DoD (Days on Default)
        if stage == 3:
            dod_factor = min(Decimal('1'), Decimal(str(days_past_due / 90)))
            # Увеличиваем LGD пропорционально
            dod_adjustment = Decimal('1') + Decimal('0.20') * dod_factor
            total_ecl *= dod_adjustment

        total_ecl = self._round_to_precision(total_ecl)

        # Формирование отображения формулы
        formula_display = (
            f"{'='*60}\n"
            f"РАСЧЕТ ECL ({ecl_type}) - Стадия {stage}\n"
            f"{'='*60}\n\n"
            f"Основная формула: ECL = Σ(PD_t × LGD × EAD_t × DF_t)\n"
            f"Горизонт расчета: {horizon} {'год' if horizon == 1 else 'лет'}\n\n"
            f"--- Компоненты ---\n\n"
            f"1. {ead_formula}\n\n"
            f"2. {lgd_formula}\n\n"
            f"3. {pd_formula}\n\n"
            f"--- Расчет по периодам ---\n\n"
        )

        for comp in ecl_components:
            formula_display += (
                f"Год {comp['period']}:\n"
                f"  PD_{comp['period']} = {float(comp['pd']):.4f}\n"
                f"  EAD_{comp['period']} = {format_currency(comp['ead'])}\n"
                f"  DF_{comp['period']} = {float(comp['df']):.6f}\n"
                f"  ECL_{comp['period']} = {float(comp['pd']):.4f} × {float(comp['lgd']):.4f} × "
                f"{format_currency(comp['ead'], False)} × {float(comp['df']):.6f}\n"
                f"  ECL_{comp['period']} = {format_currency(comp['ecl'])}\n\n"
            )

        if stage == 3:
            formula_display += (
                f"Корректировка DoD (Стадия 3):\n"
                f"  DoD factor = min(1, {days_past_due}/90) = {float(dod_factor):.2f}\n"
                f"  Adjustment = 1 + 0.20 × {float(dod_factor):.2f} = {float(dod_adjustment):.4f}\n\n"
            )

        formula_display += (
            f"{'='*60}\n"
            f"ИТОГО ECL = {format_currency(total_ecl)}\n"
            f"{'='*60}\n"
        )

        # Обоснование
        justification = (
            f"Расчет ECL выполнен в соответствии с МСФО 9 para 5.5.17-5.5.20, "
            f"B5.5.28-B5.5.52 и АРФР Постановление №269 от 29.12.2017. "
            f"Использованы макроэкономические показатели НБК на {self.macro['date'].strftime('%d.%m.%Y')}: "
            f"ВВП +{self.macro['gdp_growth']}%, инфляция {self.macro['inflation']}%, "
            f"базовая ставка {self.macro['base_rate']}%. "
            f"Мультипликатор PD: {self.config['TOTAL_PD_MULTIPLIER']} (веса сценариев: "
            f"55% базовый, 35% неблагоприятный, 10% стрессовый). "
            f"Точность расчета: до {self.precision} KZT."
        )

        result = ECLResult(
            ecl_amount=total_ecl,
            stage=stage,
            pd_values=pd_values,
            lgd=adjusted_lgd,
            ead_values=ead_values,
            discount_factors=discount_factors,
            formula_display=formula_display,
            justification=justification,
            breakdown={
                'components': ecl_components,
                'ead_total': ead,
                'adjusted_pd': adjusted_pd,
                'scenario': scenario,
                'horizon': horizon,
            },
            calculation_date=datetime.now()
        )

        self._log_audit('Расчет ECL', {
            'stage': stage,
            'ecl_amount': float(total_ecl),
            'gca': float(gross_carrying_amount),
            'scenario': scenario,
        })

        return result

    def calculate_ecl_portfolio(
        self,
        exposures: List[Dict],
        scenario: str = 'weighted'
    ) -> Dict[str, Any]:
        """
        Расчет ECL для портфеля

        Args:
            exposures: Список экспозиций с параметрами
            scenario: Сценарий

        Returns:
            Словарь с результатами по портфелю
        """
        # Демо-ограничение
        if len(exposures) > DEMO_CONFIG['MAX_RECORDS_PER_MODULE']:
            exposures = exposures[:DEMO_CONFIG['MAX_RECORDS_PER_MODULE']]
            logger.warning(
                f"Демо-версия: ограничено до {DEMO_CONFIG['MAX_RECORDS_PER_MODULE']} записей"
            )

        results = {
            'total_ecl': Decimal('0'),
            'total_gca': Decimal('0'),
            'by_stage': {1: Decimal('0'), 2: Decimal('0'), 3: Decimal('0')},
            'count_by_stage': {1: 0, 2: 0, 3: 0},
            'individual_results': [],
            'coverage_ratio': Decimal('0'),
        }

        for exp in exposures:
            # Определение стадии
            stage, _ = self.determine_stage(
                exp.get('days_past_due', 0),
                exp.get('pd_current', Decimal('0.05')),
                exp.get('pd_origination', Decimal('0.03')),
                exp.get('qualitative_factors', {})
            )

            # Расчет ECL
            ecl_result = self.calculate_ecl(
                stage=stage,
                gross_carrying_amount=exp.get('gca', Decimal('0')),
                pd_annual=exp.get('pd_current', Decimal('0.05')),
                lgd=exp.get('lgd', Decimal('0.69')),
                eir=exp.get('eir', Decimal('0.19')),
                remaining_term=exp.get('remaining_term', 3),
                undrawn=exp.get('undrawn', Decimal('0')),
                collateral_type=exp.get('collateral_type', 'unsecured'),
                collateral_value=exp.get('collateral_value', Decimal('0')),
                days_past_due=exp.get('days_past_due', 0),
                scenario=scenario
            )

            results['total_ecl'] += ecl_result.ecl_amount
            results['total_gca'] += exp.get('gca', Decimal('0'))
            results['by_stage'][stage] += ecl_result.ecl_amount
            results['count_by_stage'][stage] += 1
            results['individual_results'].append({
                'id': exp.get('id', 'N/A'),
                'name': exp.get('name', 'N/A'),
                'stage': stage,
                'gca': exp.get('gca'),
                'ecl': ecl_result.ecl_amount,
            })

        # Коэффициент покрытия
        if results['total_gca'] > 0:
            results['coverage_ratio'] = results['total_ecl'] / results['total_gca']

        return results

    # =========================================================================
    # СТРЕСС-ТЕСТИРОВАНИЕ
    # Per IFRS 9 B5.5.15-B5.5.20
    # =========================================================================

    def stress_test_ecl(
        self,
        base_ecl: Decimal,
        scenarios: Dict[str, Decimal] = None
    ) -> Dict[str, Any]:
        """
        Стресс-тестирование ECL

        Args:
            base_ecl: Базовый ECL
            scenarios: Мультипликаторы сценариев

        Returns:
            Результаты стресс-теста
        """
        if scenarios is None:
            scenarios = {
                'base': self.config['PD_MULTIPLIERS']['base'],
                'adverse': self.config['PD_MULTIPLIERS']['adverse'],
                'severe': self.config['PD_MULTIPLIERS']['severe'],
            }

        results = {}
        for name, multiplier in scenarios.items():
            stressed_ecl = base_ecl * multiplier
            results[name] = {
                'ecl': self._round_to_precision(stressed_ecl),
                'multiplier': multiplier,
                'change_pct': (multiplier - Decimal('1')) * Decimal('100'),
            }

        return results

    # =========================================================================
    # ПРОВЕРКА ЛИМИТОВ РЕПО
    # Per АРФР, с 01.07.2025 ≤35%
    # =========================================================================

    def check_repo_limit(
        self,
        repo_amount: Decimal,
        reserves: Decimal,
        check_date: date = None
    ) -> Dict[str, Any]:
        """
        Проверка соблюдения лимита РЕПО

        Per АРФР: ≤50% до 01.07.2025, ≤35% после

        Args:
            repo_amount: Объем РЕПО
            reserves: Технические резервы
            check_date: Дата проверки

        Returns:
            Результат проверки с обоснованием
        """
        if check_date is None:
            check_date = date.today()

        if reserves == 0:
            return {
                'compliant': False,
                'ratio': None,
                'message': 'Ошибка: резервы равны нулю'
            }

        ratio = repo_amount / reserves
        limit_key = 'after_july_2025' if check_date >= date(2025, 7, 1) else 'before_july_2025'
        limit = self.config['REPO_LIMITS'][limit_key]

        compliant = ratio <= limit
        penalty = Decimal('0')

        if not compliant:
            # Штраф: превышение × penalty rate
            excess = ratio - limit
            penalty_rate = Decimal('0.05')  # 5% от превышения
            penalty = excess * reserves * penalty_rate

        return {
            'compliant': compliant,
            'ratio': self._round_to_precision(ratio),
            'limit': limit,
            'penalty': self._round_to_precision(penalty),
            'message': (
                f"Лимит РЕПО {'соблюден' if compliant else 'НАРУШЕН'}: "
                f"коэффициент {float(ratio):.2%} vs лимит {float(limit):.0%}"
            ),
            'reference': f"АРФР, лимит с {'01.07.2025' if limit_key == 'after_july_2025' else 'до 01.07.2025'}"
        }

    # =========================================================================
    # ML МОДЕЛИ ДЛЯ PD/LGD
    # =========================================================================

    def train_pd_model_rf(
        self,
        X: np.ndarray,
        y: np.ndarray,
        n_estimators: int = 100
    ) -> Dict[str, Any]:
        """
        Обучение Random Forest модели для PD

        Args:
            X: Признаки (макропеременные, характеристики заемщика)
            y: Метки дефолтов

        Returns:
            Результаты обучения
        """
        model = RandomForestClassifier(
            n_estimators=n_estimators,
            random_state=42,
            max_depth=5  # Демо: ограничиваем глубину
        )
        model.fit(X, y)

        # Feature importance
        importance = dict(zip(
            [f'feature_{i}' for i in range(X.shape[1])],
            model.feature_importances_
        ))

        return {
            'model': model,
            'feature_importance': importance,
            'accuracy': model.score(X, y),
        }

    def predict_pd_ml(
        self,
        model,
        X: np.ndarray
    ) -> np.ndarray:
        """Предсказание PD через ML модель"""
        return model.predict_proba(X)[:, 1]

    def get_audit_log(self) -> List[Dict]:
        """Получить аудиторский след"""
        return self.audit_log

    def export_audit_trail(self, format: str = 'dict') -> Any:
        """Экспорт аудиторского следа"""
        if format == 'dataframe':
            return pd.DataFrame(self.audit_log)
        return self.audit_log


# =============================================================================
# ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ (для демо)
# =============================================================================

def demo_ecl_calculation():
    """Демонстрация расчета ECL"""
    calc = IFRS9Calculator()

    # Пример: Облигация 500 млн KZT
    result = calc.calculate_ecl(
        stage=2,
        gross_carrying_amount=Decimal('500000000'),
        pd_annual=Decimal('0.095'),  # 9.5% годовая PD
        lgd=Decimal('0.69'),  # 69% без обеспечения
        eir=Decimal('0.19'),  # 19% EIR
        remaining_term=3,  # 3 года
        scenario='weighted'
    )

    print(result.formula_display)
    print(f"\nОбоснование: {result.justification}")

    return result


if __name__ == '__main__':
    demo_ecl_calculation()
