# -*- coding: utf-8 -*-
"""
Alliot - Batch Processing Service
Пакетная обработка расчетов для всего портфеля

КРИТИЧНО: В production системе расчеты выполняются не по одному договору,
а пакетно для всего портфеля (100K+ договоров). Это:
1. Быстрее (параллельная обработка)
2. Надежнее (один договор упал - остальные продолжают)
3. Аудируемо (вся история расчетов с логами)
"""

from decimal import Decimal
from datetime import datetime, date
from typing import Dict, List, Optional
from sqlalchemy import func

from app import db
from app.enterprise_models import (
    CalculationRun, CalculationRunStatus, ContractGroup,
    GroupCalculationResult, InsuranceContract, CalculationLog,
    JournalEntry, AccountingEventType, AccountingRule
)
from app.services.calculation_service import calculation_service


class BatchProcessingService:
    """
    Сервис пакетной обработки расчетов

    Основной флоу:
    1. Пользователь нажимает "Запустить расчет" → создается CalculationRun
    2. Система берет все группы договоров (не договоры!)
    3. Для каждой группы вызывается calculation_service
    4. Результаты сохраняются в GroupCalculationResult
    5. Генерируются проводки (JournalEntry)
    6. Обновляется статус и прогресс
    """

    def __init__(self):
        pass

    def create_calculation_run(
        self,
        calculation_type: str,
        reporting_date: date,
        description: str = None,
        portfolio_filter: Dict = None
    ) -> CalculationRun:
        """
        Создать новый расчет (Job)

        Args:
            calculation_type: 'ifrs17', 'ifrs9', 'solvency', 'all'
            reporting_date: Дата отчетности
            description: Описание расчета
            portfolio_filter: Фильтры (insurance_type, cohort_year, etc.)

        Returns:
            CalculationRun объект
        """
        # Генерируем уникальный код
        run_code = self._generate_run_code(calculation_type, reporting_date)

        # Определяем какие группы будут рассчитаны
        query = ContractGroup.query

        if portfolio_filter:
            if 'insurance_type' in portfolio_filter:
                query = query.filter_by(insurance_type=portfolio_filter['insurance_type'])
            if 'cohort_year' in portfolio_filter:
                query = query.filter_by(cohort_year=portfolio_filter['cohort_year'])
            if 'contract_type' in portfolio_filter:
                query = query.filter_by(contract_type=portfolio_filter['contract_type'])

        total_groups = query.count()

        # Создаем запись
        run = CalculationRun(
            run_code=run_code,
            run_name=description or f"{calculation_type.upper()} расчет на {reporting_date}",
            description=description,
            calculation_type=calculation_type,
            reporting_date=reporting_date,
            status=CalculationRunStatus.PENDING,
            total_items=total_groups,
            processed_items=0,
            progress_percentage=Decimal('0.00'),
            created_by='system',  # TODO: использовать текущего пользователя
            created_at=datetime.utcnow()
        )

        db.session.add(run)
        db.session.commit()

        return run

    def execute_calculation_run(
        self,
        run_id: int,
        portfolio_filter: Dict = None
    ) -> Dict[str, any]:
        """
        Выполнить расчет (основной метод)

        Args:
            run_id: ID расчета
            portfolio_filter: Фильтры портфеля

        Returns:
            Статистика выполнения
        """
        run = CalculationRun.query.get(run_id)
        if not run:
            return {'status': 'error', 'message': 'Run not found'}

        # Начинаем расчет
        run.status = CalculationRunStatus.RUNNING
        run.started_at = datetime.utcnow()
        db.session.commit()

        try:
            # Получаем группы для расчета
            groups = self._get_groups_for_calculation(run, portfolio_filter)

            total_groups = len(groups)
            run.total_items = total_groups
            db.session.commit()

            # Счетчики
            processed = 0
            failed = 0
            ifrs17_groups_calculated = 0
            total_csm = Decimal('0')
            total_bel = Decimal('0')
            total_ecl = Decimal('0')

            # Обрабатываем каждую группу
            for group in groups:
                try:
                    # Выполняем расчет в зависимости от типа
                    if run.calculation_type in ['ifrs17', 'all']:
                        result = self._calculate_ifrs17_for_group(run, group)
                        if result:
                            ifrs17_groups_calculated += 1
                            total_csm += result.csm_amount or 0
                            total_bel += result.bel_amount or 0

                    if run.calculation_type in ['ifrs9', 'all']:
                        ecl_result = self._calculate_ifrs9_for_group(run, group)
                        if ecl_result:
                            total_ecl += ecl_result

                    processed += 1

                except Exception as e:
                    # Логируем ошибку, но продолжаем
                    self._log_error(run, group, str(e))
                    failed += 1
                    processed += 1

                # Обновляем прогресс
                run.processed_items = processed
                run.progress_percentage = Decimal(str((processed / total_groups) * 100))
                db.session.commit()

            # Завершаем расчет
            run.ended_at = datetime.utcnow()
            run.duration_seconds = int((run.ended_at - run.started_at).total_seconds())

            # Сохраняем результаты
            run.ifrs17_groups_calculated = ifrs17_groups_calculated
            run.ifrs17_total_csm = total_csm
            run.ifrs17_total_bel = total_bel
            run.ifrs17_total_liability = total_bel + total_csm
            run.ifrs9_total_ecl = total_ecl

            # Определяем финальный статус
            if failed == 0:
                run.status = CalculationRunStatus.COMPLETED
            elif failed < total_groups:
                run.status = CalculationRunStatus.PARTIAL
            else:
                run.status = CalculationRunStatus.FAILED

            run.errors_count = failed
            db.session.commit()

            return {
                'status': 'success',
                'run_id': run.id,
                'total_groups': total_groups,
                'processed': processed,
                'failed': failed,
                'ifrs17_csm': float(total_csm),
                'ifrs17_bel': float(total_bel),
                'ifrs9_ecl': float(total_ecl),
                'duration': run.duration_seconds
            }

        except Exception as e:
            run.status = CalculationRunStatus.FAILED
            run.ended_at = datetime.utcnow()
            run.error_message = str(e)
            db.session.commit()

            return {
                'status': 'error',
                'message': str(e)
            }

    def _get_groups_for_calculation(
        self,
        run: CalculationRun,
        portfolio_filter: Dict = None
    ) -> List[ContractGroup]:
        """Получить список групп для расчета"""
        query = ContractGroup.query.filter(ContractGroup.total_contracts > 0)

        if portfolio_filter:
            if 'insurance_type' in portfolio_filter:
                query = query.filter_by(insurance_type=portfolio_filter['insurance_type'])
            if 'cohort_year' in portfolio_filter:
                query = query.filter_by(cohort_year=portfolio_filter['cohort_year'])
            if 'contract_type' in portfolio_filter:
                query = query.filter_by(contract_type=portfolio_filter['contract_type'])

        return query.all()

    def _calculate_ifrs17_for_group(
        self,
        run: CalculationRun,
        group: ContractGroup
    ) -> Optional[GroupCalculationResult]:
        """
        Расчет МСФО 17 для группы

        КРИТИЧНО: Расчет выполняется на уровне ГРУППЫ, не договора!
        """
        # Получаем договоры группы
        contracts = group.contracts.all()

        if not contracts:
            return None

        # Агрегируем входные данные
        total_premium = sum(float(c.premium_amount or 0) for c in contracts)
        total_sum_insured = sum(float(c.sum_insured or 0) for c in contracts)

        # Используем средневзвешенные параметры группы
        discount_rate = float(group.weighted_avg_discount_rate or 0.18)

        # Рассчитываем BEL на уровне группы
        # Упрощенная формула: PV(Expected Claims + Expenses)
        expected_claims = sum(float(c.expected_claims or c.premium_amount * Decimal('0.70')) for c in contracts)
        expected_expenses = sum(float(c.expected_expenses or c.premium_amount * Decimal('0.15')) for c in contracts)

        # Средний срок (в годах)
        avg_duration = sum(
            (c.expiry_date - run.reporting_date).days / 365.25
            for c in contracts if c.expiry_date > run.reporting_date
        ) / len(contracts) if contracts else 1

        discount_factor = 1 / ((1 + discount_rate) ** avg_duration)
        bel_amount = Decimal(str((expected_claims + expected_expenses) * discount_factor))

        # Рассчитываем RA (упрощенно - 10% от BEL)
        ra_amount = bel_amount * Decimal('0.10')

        # FCF (Fulfillment Cash Flows)
        fcf_amount = bel_amount + ra_amount

        # CSM расчет
        # CSM = Премии - FCF (если положительное)
        # Loss Component = FCF - Премии (если отрицательное)
        margin = Decimal(str(total_premium)) - fcf_amount

        if margin >= 0:
            csm_amount = margin
            loss_component = Decimal('0')
        else:
            csm_amount = Decimal('0')
            loss_component = abs(margin)

        # Создаем результат
        result = GroupCalculationResult(
            calculation_run_id=run.id,
            contract_group_id=group.id,
            calculation_date=run.reporting_date,

            # Компоненты
            bel_amount=bel_amount,
            ra_amount=ra_amount,
            csm_amount=csm_amount,
            loss_component=loss_component,
            total_liability=bel_amount + ra_amount + csm_amount + loss_component,

            # CSM Roll-forward (упрощенно)
            csm_opening_balance=group.total_csm or Decimal('0'),
            csm_new_business=csm_amount,
            csm_expected_release=Decimal('0'),  # TODO: рассчитать на основе coverage units
            csm_closing_balance=csm_amount,

            # Снапшот параметров
            assumptions_snapshot={
                'discount_rate': discount_rate,
                'avg_duration': avg_duration,
                'expected_claims': expected_claims,
                'expected_expenses': expected_expenses,
                'total_premium': total_premium,
                'contract_count': len(contracts)
            }
        )

        db.session.add(result)

        # Обновляем агрегаты группы
        group.total_bel = bel_amount
        group.total_ra = ra_amount
        group.total_csm = csm_amount
        group.total_loss_component = loss_component
        group.total_fcf = fcf_amount
        group.total_liability = result.total_liability
        group.updated_at = datetime.utcnow()

        # Логируем расчет
        self._log_calculation(run, group, 'IFRS17', result.assumptions_snapshot, float(result.total_liability))

        return result

    def _calculate_ifrs9_for_group(
        self,
        run: CalculationRun,
        group: ContractGroup
    ) -> Decimal:
        """
        Расчет МСФО 9 ECL для группы
        (Упрощенная версия)
        """
        contracts = group.contracts.all()

        if not contracts:
            return Decimal('0')

        total_ecl = Decimal('0')

        for contract in contracts:
            # Используем calculation_service для ECL
            if contract.premium_amount:
                # Упрощенно: ECL = Exposure * PD * LGD
                exposure = float(contract.premium_amount)
                pd = 0.05  # 5% вероятность дефолта
                lgd = 0.45  # 45% потери при дефолте

                ecl = Decimal(str(exposure * pd * lgd))
                total_ecl += ecl

        return total_ecl

    def _generate_run_code(self, calculation_type: str, reporting_date: date) -> str:
        """Генерация уникального кода расчета"""
        date_str = reporting_date.strftime('%Y%m%d')
        type_prefix = calculation_type[:4].upper()

        # Находим последний номер за день
        existing = CalculationRun.query.filter(
            CalculationRun.run_code.like(f'{type_prefix}-{date_str}-%')
        ).count()

        seq = existing + 1
        return f"{type_prefix}-{date_str}-{seq:04d}"

    def _log_calculation(
        self,
        run: CalculationRun,
        group: ContractGroup,
        calc_type: str,
        input_data: Dict,
        result_value: float
    ):
        """Логирование расчета для аудита"""
        log = CalculationLog(
            calculation_run_id=run.id,
            entity_type='contract_group',
            entity_id=group.id,
            entity_reference=group.group_code,
            calculation_type=calc_type,
            calculation_date=run.reporting_date,
            input_data=input_data,
            formula_display=f"{calc_type} calculation for group {group.group_code}",
            result_value=Decimal(str(result_value)),
            created_at=datetime.utcnow()
        )
        db.session.add(log)

    def _log_error(self, run: CalculationRun, group: ContractGroup, error_message: str):
        """Логирование ошибки"""
        log = CalculationLog(
            calculation_run_id=run.id,
            entity_type='contract_group',
            entity_id=group.id,
            entity_reference=group.group_code,
            calculation_type='ERROR',
            calculation_date=run.reporting_date,
            input_data={'error': error_message},
            formula_display='Error during calculation',
            result_value=Decimal('0'),
            created_at=datetime.utcnow()
        )
        db.session.add(log)

    def get_run_status(self, run_id: int) -> Dict[str, any]:
        """
        Получить статус расчета (для AJAX polling)
        """
        run = CalculationRun.query.get(run_id)
        if not run:
            return {'status': 'not_found'}

        return {
            'run_id': run.id,
            'run_code': run.run_code,
            'status': run.status.value,
            'progress': float(run.progress_percentage or 0),
            'total_items': run.total_items,
            'processed_items': run.processed_items,
            'duration': run.duration_seconds,
            'results': {
                'ifrs17_csm': float(run.ifrs17_total_csm or 0),
                'ifrs17_bel': float(run.ifrs17_total_bel or 0),
                'ifrs9_ecl': float(run.ifrs9_total_ecl or 0)
            } if run.status == CalculationRunStatus.COMPLETED else None
        }

    def get_recent_runs(self, limit: int = 10) -> List[CalculationRun]:
        """Получить последние расчеты"""
        return CalculationRun.query.order_by(
            CalculationRun.created_at.desc()
        ).limit(limit).all()


# Singleton instance
batch_processing_service = BatchProcessingService()
