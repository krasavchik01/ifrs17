# -*- coding: utf-8 -*-
"""
Unified Calculation Service - Главный расчет IFRS 9 + IFRS 17 + Solvency

Одна функция для всех расчетов:
- ECL (МСФО 9) - Expected Credit Loss
- BEL/RA/CSM (МСФО 17) - Insurance Liability
- Solvency (Платежеспособность) - Nmp coefficient

КРИТИЧНО: Это ЕДИНСТВЕННЫЙ источник истины для всех трех расчетов.
Все остальные сервисы используют эту функцию.
"""

from decimal import Decimal
from datetime import date, datetime
from dataclasses import dataclass
from typing import Dict, Optional, Any

from app.services.calculation_service import calculation_service
from app.modules.solvency import SolvencyCalculator
from config import format_currency, format_percent


@dataclass
class ECLResult:
    """Результаты расчета ECL (МСФО 9)"""
    ecl_amount: Decimal
    stage: str  # Stage 1, 2, or 3
    pd_12m: Decimal  # 12-month PD
    pd_lifetime: Decimal  # Lifetime PD
    formula_display: str
    justification: str


@dataclass
class IFRS17Result:
    """Результаты расчета МСФО 17"""
    bel: Decimal  # Best Estimate Liability
    ra: Decimal   # Risk Adjustment
    csm: Decimal  # Contractual Service Margin
    fcf: Decimal  # Fulfilment Cash Flows
    total_liability: Decimal
    is_onerous: bool
    formula_display: str
    justification: str


@dataclass
class SolvencyResult:
    """Результаты расчета платежеспособности"""
    mmp: Decimal  # Minimum Capital Requirement
    fmp: Decimal  # Own Funds
    ratio: Decimal  # Nmp = FMP / MMP
    is_compliant: bool
    stress_adverse: Decimal
    stress_severe: Decimal
    var_99_5: Decimal
    formula_display: str
    justification: str


@dataclass
class UnifiedCalculationResult:
    """Главный результат всех трех расчетов"""
    calculation_date: date

    # ECL (МСФО 9)
    ecl: ECLResult
    ecl_formatted: Dict[str, str]

    # МСФО 17
    ifrs17: IFRS17Result
    ifrs17_formatted: Dict[str, str]

    # Платежеспособность
    solvency: SolvencyResult
    solvency_formatted: Dict[str, str]

    # Статус
    status: str  # 'compliant' or 'warning' or 'critical'
    warnings: list  # Список предупреждений

    def to_dict(self) -> Dict[str, Any]:
        """Преобразовать результат в словарь"""
        return {
            'calculation_date': self.calculation_date.isoformat(),
            'ecl': {
                'amount': str(self.ecl.ecl_amount),
                'stage': self.ecl.stage,
                'formatted': self.ecl_formatted,
                'formula': self.ecl.formula_display,
                'justification': self.ecl.justification,
            },
            'ifrs17': {
                'bel': str(self.ifrs17.bel),
                'ra': str(self.ifrs17.ra),
                'csm': str(self.ifrs17.csm),
                'total_liability': str(self.ifrs17.total_liability),
                'is_onerous': self.ifrs17.is_onerous,
                'formatted': self.ifrs17_formatted,
                'formula': self.ifrs17.formula_display,
                'justification': self.ifrs17.justification,
            },
            'solvency': {
                'mmp': str(self.solvency.mmp),
                'fmp': str(self.solvency.fmp),
                'ratio': float(self.solvency.ratio),
                'is_compliant': self.solvency.is_compliant,
                'stress_adverse': float(self.solvency.stress_adverse),
                'stress_severe': float(self.solvency.stress_severe),
                'var_99_5': float(self.solvency.var_99_5),
                'formatted': self.solvency_formatted,
                'formula': self.solvency.formula_display,
                'justification': self.solvency.justification,
            },
            'status': self.status,
            'warnings': self.warnings,
        }


class UnifiedCalculationService:
    """
    Главный сервис расчетов

    Вычисляет ECL, МСФО 17 и платежеспособность в одном месте.
    Гарантирует консистентность данных между тремя расчетами.
    """

    def calculate_everything(
        self,
        # ECL параметры
        gross_carrying_amount: Decimal = Decimal('500000000'),
        pd_annual: Decimal = Decimal('0.095'),
        lgd: Decimal = Decimal('0.69'),
        eir: Decimal = Decimal('0.19'),
        remaining_term: int = 3,
        days_past_due: int = 0,

        # МСФО 17 параметры
        premiums: Decimal = Decimal('100000000'),
        claims_per_year: Decimal = Decimal('80000000'),
        expenses_per_year: Decimal = Decimal('5000000'),
        acquisition_costs: Decimal = Decimal('10000000'),
        contract_term: int = 10,
        ra_method: str = 'coc',

        # Платежеспособность параметры
        gross_premiums: Optional[Decimal] = None,
        incurred_claims: Optional[Decimal] = None,
        equity: Decimal = Decimal('20000000000'),
        csm_adj: Optional[Decimal] = None,
        subordinated: Decimal = Decimal('3000000000'),
        illiquid: Decimal = Decimal('500000000'),
        has_osago: bool = False,
        k_coef: Decimal = Decimal('0.70'),
    ) -> UnifiedCalculationResult:
        """
        Главная функция расчета.

        Вычисляет все три показателя в одном месте:
        1. ECL (МСФО 9)
        2. BEL/RA/CSM (МСФО 17)
        3. MMP/FMP/Nmp (Платежеспособность)

        Returns: UnifiedCalculationResult с полными результатами
        """

        warnings = []

        # ========================================================================
        # 1. РАСЧЕТ ECL (МСФО 9)
        # ========================================================================

        try:
            ecl_calc_result = calculation_service.calculate_single_ecl(
                gross_carrying_amount=gross_carrying_amount,
                pd_annual=pd_annual,
                lgd=lgd,
                eir=eir,
                remaining_term=remaining_term,
                days_past_due=days_past_due,
                scenario='weighted'
            )

            ecl_result = ECLResult(
                ecl_amount=ecl_calc_result.ecl_amount,
                stage=ecl_calc_result.stage,
                pd_12m=pd_annual,
                pd_lifetime=pd_annual * Decimal(remaining_term),
                formula_display=ecl_calc_result.formula_display,
                justification=ecl_calc_result.justification
            )

            ecl_formatted = {
                'ecl_amount': format_currency(ecl_result.ecl_amount),
                'stage': ecl_result.stage,
                'net_value': format_currency(gross_carrying_amount - ecl_result.ecl_amount),
                'coverage_ratio': format_percent(float(ecl_result.ecl_amount / gross_carrying_amount * 100)),
            }

        except Exception as e:
            warnings.append(f'Ошибка расчета ECL: {str(e)}')
            ecl_result = ECLResult(
                ecl_amount=Decimal('0'),
                stage='ERROR',
                pd_12m=Decimal('0'),
                pd_lifetime=Decimal('0'),
                formula_display='',
                justification=f'Ошибка: {str(e)}'
            )
            ecl_formatted = {}

        # ========================================================================
        # 2. РАСЧЕТ МСФО 17 (BEL/RA/CSM)
        # ========================================================================

        try:
            # Формируем денежные потоки
            cash_flows = []
            for year in range(1, contract_term + 1):
                cf = {
                    'period': year,
                    'premiums': float(premiums) if year == 1 else 0,
                    'claims': float(claims_per_year) * (1 + 0.02 * year),
                    'expenses': float(expenses_per_year),
                    'acquisition_costs': float(acquisition_costs) if year == 1 else 0,
                }
                cash_flows.append(cf)

            # Используем IFRS17Calculator из modules
            from app.modules.ifrs17 import IFRS17Calculator
            calc = IFRS17Calculator()

            gmm_result = calc.calculate_gmm(
                cash_flows=cash_flows,
                acquisition_costs=acquisition_costs,
                ra_method=ra_method,
            )

            ifrs17_result = IFRS17Result(
                bel=gmm_result.bel.bel_amount,
                ra=gmm_result.ra.ra_amount,
                csm=gmm_result.csm.csm_amount,
                fcf=gmm_result.fcf,
                total_liability=gmm_result.total_liability,
                is_onerous=gmm_result.csm.is_onerous,
                formula_display=gmm_result.formula_display,
                justification=gmm_result.justification
            )

            ifrs17_formatted = {
                'bel': format_currency(ifrs17_result.bel),
                'ra': format_currency(ifrs17_result.ra),
                'csm': format_currency(ifrs17_result.csm),
                'total_liability': format_currency(ifrs17_result.total_liability),
                'is_onerous': 'Да' if ifrs17_result.is_onerous else 'Нет',
            }

        except Exception as e:
            warnings.append(f'Ошибка расчета МСФО 17: {str(e)}')
            ifrs17_result = IFRS17Result(
                bel=Decimal('0'),
                ra=Decimal('0'),
                csm=Decimal('0'),
                fcf=Decimal('0'),
                total_liability=Decimal('0'),
                is_onerous=False,
                formula_display='',
                justification=f'Ошибка: {str(e)}'
            )
            ifrs17_formatted = {}

        # ========================================================================
        # 3. РАСЧЕТ ПЛАТЕЖЕСПОСОБНОСТИ (MMP/FMP/Nmp)
        # ========================================================================

        # Если параметры не передали, используем значения по умолчанию
        if gross_premiums is None:
            gross_premiums = premiums * Decimal('350')  # Масштабирование до размера портфеля
        if incurred_claims is None:
            incurred_claims = gross_premiums * Decimal('0.55')  # Loss ratio 55%
        if csm_adj is None:
            csm_adj = ifrs17_result.csm  # Используем CSM из МСФО 17

        try:
            calc = SolvencyCalculator()

            # MMP
            mmp_calc_result = calc.calculate_mmp(
                gross_premiums=gross_premiums,
                incurred_claims=incurred_claims,
                k_coefficient=k_coef,
                has_osago=has_osago
            )

            # FMP
            ecl_adj = ecl_result.ecl_amount
            fmp_calc_result = calc.calculate_fmp(
                equity_capital=equity,
                ecl_adjustment=ecl_adj,
                csm_adjustment=csm_adj,
                subordinated_debt=subordinated,
                illiquid_assets=illiquid,
            )

            # Ratio
            ratio_calc_result = calc.calculate_solvency_ratio(
                fmp_calc_result.fmp_amount,
                mmp_calc_result.mmp_amount
            )

            # Stress test
            stress_calc_result = calc.stress_test(
                fmp_calc_result.fmp_amount,
                mmp_calc_result.mmp_amount
            )

            solvency_result = SolvencyResult(
                mmp=mmp_calc_result.mmp_amount,
                fmp=fmp_calc_result.fmp_amount,
                ratio=ratio_calc_result.ratio,
                is_compliant=ratio_calc_result.is_compliant,
                stress_adverse=stress_calc_result.stressed_ratios.get('adverse', Decimal('0')),
                stress_severe=stress_calc_result.stressed_ratios.get('severe', Decimal('0')),
                var_99_5=stress_calc_result.var_99_5,
                formula_display=mmp_calc_result.formula_display + '\n\n' + fmp_calc_result.formula_display + '\n\n' + ratio_calc_result.formula_display,
                justification=ratio_calc_result.justification
            )

            solvency_formatted = {
                'mmp': format_currency(solvency_result.mmp),
                'fmp': format_currency(solvency_result.fmp),
                'ratio': format_percent(float(solvency_result.ratio * 100)),
                'is_compliant': 'Да' if solvency_result.is_compliant else 'Нет',
                'stress_adverse': format_percent(float(solvency_result.stress_adverse * 100)),
                'stress_severe': format_percent(float(solvency_result.stress_severe * 100)),
                'var_99_5': format_percent(float(solvency_result.var_99_5 * 100)),
            }

        except Exception as e:
            warnings.append(f'Ошибка расчета платежеспособности: {str(e)}')
            solvency_result = SolvencyResult(
                mmp=Decimal('0'),
                fmp=Decimal('0'),
                ratio=Decimal('0'),
                is_compliant=False,
                stress_adverse=Decimal('0'),
                stress_severe=Decimal('0'),
                var_99_5=Decimal('0'),
                formula_display='',
                justification=f'Ошибка: {str(e)}'
            )
            solvency_formatted = {}

        # ========================================================================
        # ОПРЕДЕЛЕНИЕ ОБЩЕГО СТАТУСА
        # ========================================================================

        status = 'compliant'

        # Проверка ECL
        if ecl_result.stage == 'Stage 3':
            status = 'critical'
        elif ecl_result.stage == 'Stage 2':
            status = 'warning'

        # Проверка МСФО 17
        if ifrs17_result.is_onerous:
            if status != 'critical':
                status = 'warning'

        # Проверка платежеспособности
        if not solvency_result.is_compliant:
            status = 'critical'
        elif solvency_result.ratio < Decimal('1.5'):
            if status != 'critical':
                status = 'warning'

        # ========================================================================
        # СБОРКА РЕЗУЛЬТАТА
        # ========================================================================

        return UnifiedCalculationResult(
            calculation_date=date.today(),
            ecl=ecl_result,
            ecl_formatted=ecl_formatted,
            ifrs17=ifrs17_result,
            ifrs17_formatted=ifrs17_formatted,
            solvency=solvency_result,
            solvency_formatted=solvency_formatted,
            status=status,
            warnings=warnings
        )


# Глобальный экземпляр сервиса
unified_calculation_service = UnifiedCalculationService()
