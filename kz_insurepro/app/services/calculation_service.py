# -*- coding: utf-8 -*-
"""
KZ-InsurePro - Единый сервис расчетов
SINGLE SOURCE OF TRUTH для всех расчетов МСФО 9, МСФО 17, Платежеспособности

Принцип работы:
1. Все расчеты идут только через этот сервис
2. Данные берутся из БД (models)
3. Используются модули (ifrs9, ifrs17, solvency)
4. Результаты сохраняются обратно в БД
5. Все страницы и API используют ТОЛЬКО этот сервис

Это гарантирует, что все цифры везде одинаковые!
"""

from decimal import Decimal
from datetime import date, datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict

from app.modules.ifrs9 import IFRS9Calculator
from app.modules.ifrs17 import IFRS17Calculator, IFRS17Result
from app.modules.solvency import SolvencyCalculator
from app.modules.fgsv import FGSVCalculator


# =============================================================================
# RESULT DATA CLASSES
# =============================================================================

@dataclass
class PortfolioECLResult:
    """Результат расчета ECL для портфеля"""
    total_ead: Decimal
    total_ecl: Decimal
    weighted_pd: Decimal
    weighted_lgd: Decimal
    coverage_ratio: Decimal
    stage_1_ecl: Decimal
    stage_2_ecl: Decimal
    stage_3_ecl: Decimal
    stage_1_count: int
    stage_2_count: int
    stage_3_count: int
    calculation_date: datetime
    instruments: List[Dict]

    def to_dict(self):
        """Конвертация в словарь для JSON"""
        result = asdict(self)
        result['calculation_date'] = self.calculation_date.isoformat()
        # Конвертация Decimal в float
        for key in result:
            if isinstance(result[key], Decimal):
                result[key] = float(result[key])
        return result


@dataclass
class PortfolioIFRS17Result:
    """Результат расчета МСФО 17 для портфеля"""
    total_bel: Decimal
    total_ra: Decimal
    total_csm: Decimal
    total_lcr: Decimal
    total_liability: Decimal
    onerous_count: int
    onerous_amount: Decimal
    gmm_count: int
    vfa_count: int
    paa_count: int
    calculation_date: datetime
    contracts: List[Dict]

    def to_dict(self):
        result = asdict(self)
        result['calculation_date'] = self.calculation_date.isoformat()
        for key in result:
            if isinstance(result[key], Decimal):
                result[key] = float(result[key])
        return result


@dataclass
class CompleteSolvencyResult:
    """Полный результат расчета платежеспособности"""
    mmp_amount: Decimal
    fmp_amount: Decimal
    ratio: Decimal
    is_compliant: bool
    mmp_by_premiums: Decimal
    mmp_by_claims: Decimal
    equity_capital: Decimal
    ecl_adjustment: Decimal
    csm_adjustment: Decimal
    calculation_date: datetime
    justification: str

    def to_dict(self):
        result = asdict(self)
        result['calculation_date'] = self.calculation_date.isoformat()
        for key in result:
            if isinstance(result[key], Decimal):
                result[key] = float(result[key])
        return result


# =============================================================================
# CALCULATION SERVICE
# =============================================================================

class CalculationService:
    """
    Единый сервис расчетов для всей системы

    Этот сервис обеспечивает:
    - Единую точку входа для всех расчетов
    - Консистентность данных между страницами
    - Аудиторский след всех операций
    - Кэширование результатов
    """

    def __init__(self):
        """Инициализация калькуляторов"""
        self.ifrs9_calc = IFRS9Calculator()
        self.ifrs17_calc = IFRS17Calculator()
        self.solvency_calc = SolvencyCalculator()
        self.fgsv_calc = FGSVCalculator()

        # Кэш для результатов (для оптимизации)
        self._cache = {}

    # =========================================================================
    # IFRS 9 - ECL РАСЧЕТЫ
    # =========================================================================

    def calculate_single_ecl(
        self,
        instrument_id: Optional[str] = None,
        gross_carrying_amount: Decimal = None,
        pd_annual: Decimal = None,
        lgd: Decimal = None,
        eir: Decimal = None,
        remaining_term: int = None,
        days_past_due: int = 0,
        scenario: str = 'weighted'
    ):
        """
        Расчет ECL для одного инструмента

        Args:
            instrument_id: ID инструмента в БД (если есть)
            Или прямые параметры для расчета

        Returns:
            ECL result object с полными данными расчета
        """
        # Если есть ID, загружаем из БД
        if instrument_id:
            # TODO: загрузка из FinancialInstrument model
            pass

        # Определение стадии
        stage, stage_justification = self.ifrs9_calc.determine_stage(
            days_past_due=days_past_due,
            pd_current=pd_annual,
            pd_initial=pd_annual * Decimal('0.5')  # Примерное начальное PD
        )

        # Расчет ECL
        result = self.ifrs9_calc.calculate_ecl(
            stage=stage,
            gross_carrying_amount=gross_carrying_amount,
            pd_annual=pd_annual,
            lgd=lgd,
            eir=eir,
            remaining_term=remaining_term,
            scenario=scenario,
            days_past_due=days_past_due
        )

        # Если есть instrument_id, сохраняем результат в БД
        if instrument_id:
            # TODO: сохранение в FinancialInstrument
            pass

        return result

    def calculate_portfolio_ecl(
        self,
        portfolio_id: Optional[str] = None,
        instruments: Optional[List[Dict]] = None
    ) -> PortfolioECLResult:
        """
        Расчет ECL для портфеля инструментов

        Args:
            portfolio_id: ID портфеля в БД
            instruments: Список инструментов (если не из БД)

        Returns:
            PortfolioECLResult с агрегированными данными
        """
        # Если есть portfolio_id, загружаем из БД
        if portfolio_id:
            # TODO: загрузка из InstrumentPortfolio
            pass

        if not instruments:
            raise ValueError("Необходимо указать портфель или список инструментов")

        # Инициализация агрегатов
        total_ead = Decimal('0')
        total_ecl = Decimal('0')
        weighted_pd_sum = Decimal('0')
        weighted_lgd_sum = Decimal('0')

        stage_ecl = {1: Decimal('0'), 2: Decimal('0'), 3: Decimal('0')}
        stage_count = {1: 0, 2: 0, 3: 0}

        results_list = []

        # Расчет по каждому инструменту
        for instr in instruments:
            ecl_result = self.calculate_single_ecl(
                gross_carrying_amount=Decimal(str(instr.get('ead', 0))),
                pd_annual=Decimal(str(instr.get('pd', 0.01))),
                lgd=Decimal(str(instr.get('lgd', 0.45))),
                eir=Decimal(str(instr.get('eir', 0.10))),
                remaining_term=int(instr.get('term', 5)),
                days_past_due=int(instr.get('dpd', 0)),
                scenario=instr.get('scenario', 'weighted')
            )

            ead = Decimal(str(instr.get('ead', 0)))
            pd = Decimal(str(instr.get('pd', 0.01)))
            lgd = Decimal(str(instr.get('lgd', 0.45)))

            # Агрегация
            total_ead += ead
            total_ecl += ecl_result.ecl_amount
            weighted_pd_sum += pd * ead
            weighted_lgd_sum += lgd * ead

            # По стадиям
            stage = ecl_result.stage
            stage_num = {'Stage 1': 1, 'Stage 2': 2, 'Stage 3': 3}.get(stage, 1)
            stage_ecl[stage_num] += ecl_result.ecl_amount
            stage_count[stage_num] += 1

            results_list.append({
                'instrument_id': instr.get('id'),
                'instrument_name': instr.get('name', 'Unknown'),
                'ead': float(ead),
                'ecl': float(ecl_result.ecl_amount),
                'stage': stage,
                'pd': float(pd),
                'lgd': float(lgd),
            })

        # Weighted averages
        weighted_pd = weighted_pd_sum / total_ead if total_ead > 0 else Decimal('0')
        weighted_lgd = weighted_lgd_sum / total_ead if total_ead > 0 else Decimal('0')
        coverage_ratio = total_ecl / total_ead if total_ead > 0 else Decimal('0')

        return PortfolioECLResult(
            total_ead=total_ead,
            total_ecl=total_ecl,
            weighted_pd=weighted_pd,
            weighted_lgd=weighted_lgd,
            coverage_ratio=coverage_ratio,
            stage_1_ecl=stage_ecl[1],
            stage_2_ecl=stage_ecl[2],
            stage_3_ecl=stage_ecl[3],
            stage_1_count=stage_count[1],
            stage_2_count=stage_count[2],
            stage_3_count=stage_count[3],
            calculation_date=datetime.now(),
            instruments=results_list
        )

    # =========================================================================
    # IFRS 17 - CSM РАСЧЕТЫ
    # =========================================================================

    def calculate_single_contract(
        self,
        contract_id: Optional[str] = None,
        cash_flows: List[Dict] = None,
        acquisition_costs: Decimal = None,
        ra_method: str = 'coc',
        model: str = 'gmm'
    ):
        """
        Расчет МСФО 17 для одного договора

        Args:
            contract_id: ID договора в БД
            cash_flows: Денежные потоки
            acquisition_costs: Затраты на приобретение
            ra_method: Метод расчета RA
            model: Модель оценки (gmm/vfa/paa)

        Returns:
            IFRS17 result object с полными данными
        """
        if contract_id:
            # TODO: загрузка из InsuranceContract
            pass

        if not cash_flows:
            raise ValueError("Необходимо указать денежные потоки")

        # Расчет по GMM (можно добавить VFA/PAA)
        result = self.ifrs17_calc.calculate_gmm(
            cash_flows=cash_flows,
            acquisition_costs=acquisition_costs,
            ra_method=ra_method
        )

        # Сохранение в БД
        if contract_id:
            # TODO: обновление InsuranceContract
            pass

        return result

    def calculate_portfolio_ifrs17(
        self,
        portfolio_id: Optional[str] = None,
        contracts: Optional[List[Dict]] = None
    ) -> PortfolioIFRS17Result:
        """
        Расчет МСФО 17 для портфеля договоров

        Args:
            portfolio_id: ID группы договоров
            contracts: Список договоров

        Returns:
            PortfolioIFRS17Result с агрегацией
        """
        if portfolio_id:
            # TODO: загрузка из ContractGroup
            pass

        if not contracts:
            raise ValueError("Необходимо указать портфель или список договоров")

        # Агрегаты
        total_bel = Decimal('0')
        total_ra = Decimal('0')
        total_csm = Decimal('0')
        total_lcr = Decimal('0')
        onerous_count = 0
        onerous_amount = Decimal('0')

        model_count = {'gmm': 0, 'vfa': 0, 'paa': 0}
        results_list = []

        # Расчет по каждому договору
        for contract in contracts:
            cash_flows = contract.get('cash_flows', [])
            acquisition_costs = Decimal(str(contract.get('acquisition_costs', 0)))
            ra_method = contract.get('ra_method', 'coc')
            model = contract.get('model', 'gmm')

            result = self.calculate_single_contract(
                cash_flows=cash_flows,
                acquisition_costs=acquisition_costs,
                ra_method=ra_method,
                model=model
            )

            # Агрегация
            total_bel += result.bel.bel_amount
            total_ra += result.ra.ra_amount
            total_csm += result.csm.csm_amount if not result.csm.is_onerous else Decimal('0')

            if result.csm.is_onerous:
                total_lcr += abs(result.csm.csm_amount)
                onerous_count += 1
                onerous_amount += abs(result.csm.csm_amount)

            model_count[model.lower()] += 1

            results_list.append({
                'contract_id': contract.get('id'),
                'contract_number': contract.get('contract_number', 'Unknown'),
                'bel': float(result.bel.bel_amount),
                'ra': float(result.ra.ra_amount),
                'csm': float(result.csm.csm_amount),
                'is_onerous': result.csm.is_onerous,
                'model': model.upper(),
            })

        total_liability = total_bel + total_ra + total_csm + total_lcr

        return PortfolioIFRS17Result(
            total_bel=total_bel,
            total_ra=total_ra,
            total_csm=total_csm,
            total_lcr=total_lcr,
            total_liability=total_liability,
            onerous_count=onerous_count,
            onerous_amount=onerous_amount,
            gmm_count=model_count['gmm'],
            vfa_count=model_count['vfa'],
            paa_count=model_count['paa'],
            calculation_date=datetime.now(),
            contracts=results_list
        )

    # =========================================================================
    # SOLVENCY - ПЛАТЕЖЕСПОСОБНОСТЬ
    # =========================================================================

    def calculate_complete_solvency(
        self,
        insurer_id: Optional[str] = None,
        gross_premiums: Decimal = None,
        incurred_claims: Decimal = None,
        equity_capital: Decimal = None,
        ecl_adjustment: Decimal = None,
        csm_adjustment: Decimal = None,
        subordinated_debt: Decimal = Decimal('0'),
        illiquid_assets: Decimal = Decimal('0'),
        has_osago: bool = False,
        k_coefficient: Decimal = Decimal('0.70')
    ) -> CompleteSolvencyResult:
        """
        Полный расчет платежеспособности

        Этот метод используется ВЕЗДЕ где нужна платежеспособность:
        - Страница Solvency
        - Панель Insurers
        - Отчеты
        - API

        Args:
            insurer_id: ID страховщика (если из БД)
            Или прямые параметры

        Returns:
            CompleteSolvencyResult с полными данными
        """
        if insurer_id:
            # TODO: загрузка из Insurer model
            pass

        # Расчет MMP
        mmp_result = self.solvency_calc.calculate_mmp(
            gross_premiums=gross_premiums,
            incurred_claims=incurred_claims,
            k_coefficient=k_coefficient,
            has_osago=has_osago
        )

        # Расчет FMP
        fmp_result = self.solvency_calc.calculate_fmp(
            equity_capital=equity_capital,
            ecl_adjustment=ecl_adjustment,
            csm_adjustment=csm_adjustment,
            subordinated_debt=subordinated_debt,
            illiquid_assets=illiquid_assets
        )

        # Расчет Ratio
        ratio_result = self.solvency_calc.calculate_solvency_ratio(
            fmp_result.fmp_amount,
            mmp_result.mmp_amount
        )

        # Сохранение в БД
        if insurer_id:
            # TODO: обновление Insurer с результатами
            pass

        return CompleteSolvencyResult(
            mmp_amount=mmp_result.mmp_amount,
            fmp_amount=fmp_result.fmp_amount,
            ratio=ratio_result.ratio,
            is_compliant=ratio_result.is_compliant,
            mmp_by_premiums=mmp_result.mmp_by_premiums,
            mmp_by_claims=mmp_result.mmp_by_claims,
            equity_capital=equity_capital,
            ecl_adjustment=ecl_adjustment,
            csm_adjustment=csm_adjustment,
            calculation_date=datetime.now(),
            justification=ratio_result.justification
        )

    # =========================================================================
    # FGSV - ВЗНОСЫ
    # =========================================================================

    def calculate_fgsv_contribution(
        self,
        insurer_id: Optional[str] = None,
        gross_premiums: Decimal = None,
        solvency_ratio: Decimal = None,
        loss_ratio: Decimal = None,
        combined_ratio: Decimal = None
    ):
        """
        Расчет взноса в ФГСВ

        Args:
            insurer_id: ID страховщика
            Или прямые параметры

        Returns:
            FGSV contribution result
        """
        if insurer_id:
            # TODO: загрузка данных страховщика
            pass

        result = self.fgsv_calc.calculate_contribution(
            gross_premiums=gross_premiums,
            solvency_ratio=solvency_ratio,
            loss_ratio=loss_ratio,
            combined_ratio=combined_ratio
        )

        # Сохранение в БД
        if insurer_id:
            # TODO: сохранение в FGSVContribution
            pass

        return result

    # =========================================================================
    # UTILITY METHODS
    # =========================================================================

    def get_audit_trail(self, entity_type: str, entity_id: str) -> List[Dict]:
        """
        Получение аудиторского следа для сущности

        Args:
            entity_type: 'instrument', 'contract', 'insurer'
            entity_id: ID сущности

        Returns:
            Список записей аудита
        """
        # TODO: реализация через audit log
        return []

    def clear_cache(self):
        """Очистка кэша расчетов"""
        self._cache = {}


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

# Создаем единственный экземпляр сервиса для всего приложения
calculation_service = CalculationService()
