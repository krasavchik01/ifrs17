# -*- coding: utf-8 -*-
"""
Alliot - Reinsurance Service
Разделение расчетов на нетто (net) и брутто (gross) показатели

КРИТИЧНО: В страховании важно разделять прямые договоры, входящее и исходящее перестрахование:
- NET (Нетто): После вычета перестраховочного возмещения
- GROSS (Брутто): До учета перестрахования
- REINSURANCE RELIEF (Облегчение): Эффект перестрахования на расчеты

Основной флоу:
1. Беру GroupCalculationResult для всех трех типов договоров
2. Для DIRECT - это и нетто, и брутто одновременно
3. Для REINSURANCE_HELD - это входящее перестрахование (уменьшает нетто)
4. Для REINSURANCE_ISSUED - это исходящее перестрахование (увеличивает нетто)
5. Вычисляю чистые эффекты и relief эффекты
"""

from decimal import Decimal
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple
from sqlalchemy import func

from app import db
from app.enterprise_models import (
    GroupCalculationResult, ContractGroup, CalculationRun,
    ContractType, InsuranceType, MeasurementModel
)


class ReinsuranceService:
    """
    Сервис для анализа и разделения перестраховки (net/gross)

    Компоненты:
    1. Net/Gross calculation - расчет нетто и брутто показателей
    2. Relief calculation - вычисление эффекта перестрахования
    3. Portfolio analysis - анализ портфеля по типам договоров
    4. Reporting - отчеты и аналитика по перестрахованию
    """

    def __init__(self):
        pass

    def calculate_portfolio_net_gross(
        self,
        run_id: int
    ) -> Dict[str, any]:
        """
        Расчет нетто и брутто для всего портфеля в run

        Returns:
            {
                'portfolio_gross': { BEL, RA, CSM, ... },
                'portfolio_net': { BEL, RA, CSM, ... },
                'reinsurance_relief': { BEL, RA, CSM, ... },
                'by_contract_type': {
                    'DIRECT': { gross, net, ... },
                    'REINSURANCE_HELD': { ... },
                    'REINSURANCE_ISSUED': { ... }
                }
            }
        """

        run = CalculationRun.query.get(run_id)
        if not run:
            return {'status': 'error', 'message': 'CalculationRun not found'}

        try:
            # Получаем результаты по контрактному типу
            direct_results = self._get_results_by_contract_type(
                run_id=run_id,
                contract_type=ContractType.DIRECT
            )

            held_results = self._get_results_by_contract_type(
                run_id=run_id,
                contract_type=ContractType.REINSURANCE_HELD
            )

            issued_results = self._get_results_by_contract_type(
                run_id=run_id,
                contract_type=ContractType.REINSURANCE_ISSUED
            )

            # Вычисляем показатели по каждому типу
            direct_calc = self._aggregate_results(direct_results)
            held_calc = self._aggregate_results(held_results)
            issued_calc = self._aggregate_results(issued_results)

            # Брутто = DIRECT + HELD (входящее перестрахование добавляет брутто риск)
            portfolio_gross = self._combine_calculations(direct_calc, held_calc)

            # Нетто = DIRECT + ISSUED - HELD
            # (исходящее уменьшает нетто, входящее увеличивает брутто но уменьшает нетто)
            portfolio_net = self._combine_calculations(
                self._combine_calculations(direct_calc, issued_calc),
                held_calc,
                subtract=True
            )

            # Relief = Gross - Net (эффект перестрахования)
            reinsurance_relief = self._calculate_relief(
                portfolio_gross, portfolio_net
            )

            return {
                'status': 'success',
                'run_id': run_id,
                'reporting_date': run.reporting_date.isoformat(),
                'portfolio_gross': portfolio_gross,
                'portfolio_net': portfolio_net,
                'reinsurance_relief': reinsurance_relief,
                'by_contract_type': {
                    'DIRECT': {
                        **direct_calc,
                        'count': len(direct_results),
                        'contract_count': sum(r.contract_group.total_contracts for r in direct_results)
                    },
                    'REINSURANCE_HELD': {
                        **held_calc,
                        'count': len(held_results),
                        'contract_count': sum(r.contract_group.total_contracts for r in held_results)
                    },
                    'REINSURANCE_ISSUED': {
                        **issued_calc,
                        'count': len(issued_results),
                        'contract_count': sum(r.contract_group.total_contracts for r in issued_results)
                    }
                }
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': str(e),
                'run_id': run_id
            }

    def get_group_net_gross(
        self,
        result_id: int
    ) -> Dict[str, any]:
        """
        Получить нетто/брутто разбор для конкретной GroupCalculationResult

        Args:
            result_id: ID GroupCalculationResult

        Returns:
            {
                'group_code': str,
                'contract_type': str,
                'gross': { BEL, RA, CSM, total },
                'net': { BEL, RA, CSM, total },
                'relief': { BEL, RA, CSM, total }
            }
        """

        result = GroupCalculationResult.query.get(result_id)
        if not result:
            return {'status': 'error', 'message': 'GroupCalculationResult not found'}

        group = result.contract_group
        contract_type = group.contract_type

        # Для DIRECT - gross = net
        if contract_type == ContractType.DIRECT:
            gross = {
                'bel': float(result.bel_amount or 0),
                'ra': float(result.ra_amount or 0),
                'csm': float(result.csm_amount or 0),
                'total_liability': float(result.total_liability or 0)
            }
            net = gross.copy()
            relief = {
                'bel': 0.0,
                'ra': 0.0,
                'csm': 0.0,
                'total_liability': 0.0
            }

        # Для REINSURANCE_HELD - входящее перестрахование
        # Gross = это значения в результате
        # Net = Gross - Relief (relief - положительное число, уменьшает net)
        elif contract_type == ContractType.REINSURANCE_HELD:
            gross = {
                'bel': float(result.bel_amount or 0),
                'ra': float(result.ra_amount or 0),
                'csm': float(result.csm_amount or 0),
                'total_liability': float(result.total_liability or 0)
            }

            # Relief от входящего перестрахования (уменьшает нетто)
            # Обычно 30-50% в зависимости от договора
            relief_percentage = Decimal('0.40')  # 40% по умолчанию (настраивается)
            relief = {
                'bel': float(result.bel_amount * relief_percentage if result.bel_amount else 0),
                'ra': float(result.ra_amount * relief_percentage if result.ra_amount else 0),
                'csm': float(result.csm_amount * relief_percentage if result.csm_amount else 0),
                'total_liability': float(result.total_liability * relief_percentage if result.total_liability else 0)
            }

            net = {
                'bel': gross['bel'] - relief['bel'],
                'ra': gross['ra'] - relief['ra'],
                'csm': gross['csm'] - relief['csm'],
                'total_liability': gross['total_liability'] - relief['total_liability']
            }

        # Для REINSURANCE_ISSUED - исходящее перестрахование
        # Net = результат (то что остается нам)
        # Gross = Net + Relief (relief - положительное число, то что передали)
        else:  # REINSURANCE_ISSUED
            net = {
                'bel': float(result.bel_amount or 0),
                'ra': float(result.ra_amount or 0),
                'csm': float(result.csm_amount or 0),
                'total_liability': float(result.total_liability or 0)
            }

            # Relief от исходящего перестрахования (это то что передали)
            relief_percentage = Decimal('0.25')  # 25% по умолчанию
            relief = {
                'bel': float(result.bel_amount * relief_percentage if result.bel_amount else 0),
                'ra': float(result.ra_amount * relief_percentage if result.ra_amount else 0),
                'csm': float(result.csm_amount * relief_percentage if result.csm_amount else 0),
                'total_liability': float(result.total_liability * relief_percentage if result.total_liability else 0)
            }

            gross = {
                'bel': net['bel'] + relief['bel'],
                'ra': net['ra'] + relief['ra'],
                'csm': net['csm'] + relief['csm'],
                'total_liability': net['total_liability'] + relief['total_liability']
            }

        return {
            'status': 'success',
            'group_code': group.group_code,
            'contract_type': contract_type.value,
            'insurance_type': group.insurance_type.value if group.insurance_type else None,
            'gross': gross,
            'net': net,
            'relief': relief,
            'relief_percentage': float(relief_percentage) if 'relief_percentage' in locals() else 0.0
        }

    def _get_results_by_contract_type(
        self,
        run_id: int,
        contract_type: ContractType
    ) -> List[GroupCalculationResult]:
        """Получить результаты расчетов для конкретного типа договора"""

        return db.session.query(GroupCalculationResult).join(
            ContractGroup
        ).filter(
            GroupCalculationResult.calculation_run_id == run_id,
            ContractGroup.contract_type == contract_type
        ).all()

    def _aggregate_results(
        self,
        results: List[GroupCalculationResult]
    ) -> Dict[str, float]:
        """Агрегировать результаты (просуммировать)"""

        if not results:
            return {
                'bel': 0.0,
                'ra': 0.0,
                'csm': 0.0,
                'loss_component': 0.0,
                'total_liability': 0.0,
                'premium': 0.0
            }

        return {
            'bel': float(sum(r.bel_amount or 0 for r in results)),
            'ra': float(sum(r.ra_amount or 0 for r in results)),
            'csm': float(sum(r.csm_amount or 0 for r in results)),
            'loss_component': float(sum(r.loss_component or 0 for r in results)),
            'total_liability': float(sum(r.total_liability or 0 for r in results)),
            'premium': float(sum(
                r.contract_group.total_premium_received or 0
                for r in results if r.contract_group
            ))
        }

    def _combine_calculations(
        self,
        calc1: Dict[str, float],
        calc2: Dict[str, float],
        subtract: bool = False
    ) -> Dict[str, float]:
        """Объединить два расчета (сложить или вычесть)"""

        operation = (lambda a, b: a - b) if subtract else (lambda a, b: a + b)

        return {
            'bel': operation(calc1['bel'], calc2['bel']),
            'ra': operation(calc1['ra'], calc2['ra']),
            'csm': operation(calc1['csm'], calc2['csm']),
            'loss_component': operation(calc1['loss_component'], calc2['loss_component']),
            'total_liability': operation(calc1['total_liability'], calc2['total_liability']),
            'premium': operation(calc1['premium'], calc2['premium'])
        }

    def _calculate_relief(
        self,
        gross: Dict[str, float],
        net: Dict[str, float]
    ) -> Dict[str, float]:
        """Вычислить relief (эффект перестрахования) = Gross - Net"""

        return {
            'bel': gross['bel'] - net['bel'],
            'ra': gross['ra'] - net['ra'],
            'csm': gross['csm'] - net['csm'],
            'loss_component': gross['loss_component'] - net['loss_component'],
            'total_liability': gross['total_liability'] - net['total_liability'],
            'premium': gross['premium'] - net['premium']
        }

    def get_reinsurance_metrics(
        self,
        run_id: int
    ) -> Dict[str, any]:
        """
        Получить ключевые метрики перестрахования

        Returns:
            {
                'cession_ratio': % передано в перестрахование,
                'net_gross_ratio': нетто/брутто соотношение,
                'relief_ratio': облегчение/брутто,
                'direct_ratio': % прямого бизнеса
            }
        """

        portfolio = self.calculate_portfolio_net_gross(run_id)

        if portfolio.get('status') != 'success':
            return portfolio

        gross_liability = portfolio['portfolio_gross']['total_liability']
        net_liability = portfolio['portfolio_net']['total_liability']
        relief_liability = portfolio['reinsurance_relief']['total_liability']

        if gross_liability == 0:
            return {
                'status': 'error',
                'message': 'No gross liability to calculate metrics'
            }

        direct_liability = portfolio['by_contract_type']['DIRECT']['total_liability']

        return {
            'status': 'success',
            'cession_ratio': float((relief_liability / gross_liability * 100) if gross_liability > 0 else 0),
            'net_gross_ratio': float((net_liability / gross_liability * 100) if gross_liability > 0 else 0),
            'relief_ratio': float((relief_liability / gross_liability * 100) if gross_liability > 0 else 0),
            'direct_ratio': float((direct_liability / gross_liability * 100) if gross_liability > 0 else 0),
            'direct_liability': direct_liability,
            'held_liability': portfolio['by_contract_type']['REINSURANCE_HELD']['total_liability'],
            'issued_liability': portfolio['by_contract_type']['REINSURANCE_ISSUED']['total_liability']
        }


# Singleton instance
reinsurance_service = ReinsuranceService()
