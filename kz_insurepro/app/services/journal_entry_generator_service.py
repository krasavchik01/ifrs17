# -*- coding: utf-8 -*-
"""
Alliot - Journal Entry Generator Service
Автоматическое создание проводок (JournalEntry) на основе результатов расчетов

КРИТИЧНО: Это "финальный компилятор" системы.
Берет результаты расчетов (BEL, CSM, RA) и конвертирует их в бухгалтерские проводки.

Основной флоу:
1. Берется GroupCalculationResult из completed CalculationRun
2. Для каждого события (CSM_RELEASE, BEL_CHANGE, и т.д.) подбираются AccountingRule
3. Правила фильтруются по: insurance_type, contract_type, measurement_model
4. При совпадении нескольких правил - берется с наименьшим priority
5. Создается JournalEntry с полным audit trail
6. Все записи связываются с CalculationRun для трейсируемости
"""

from decimal import Decimal
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple
from sqlalchemy import func

from app import db
from app.enterprise_models import (
    CalculationRun, GroupCalculationResult, JournalEntry, AccountingRule,
    AccountingEventType, ContractGroup, ChartOfAccounts, CalculationLog,
    InsuranceType, ContractType, MeasurementModel
)


class JournalEntryGeneratorService:
    """
    Сервис для автоматического генерирования проводок из результатов расчетов

    Компоненты:
    1. Rule matching - выбор применимых правил для события
    2. Entry creation - создание проводок с аудит-информацией
    3. Bulk generation - пакетное создание всех проводок для расчета
    4. Reversal handling - обработка сторнирующих проводок
    """

    def __init__(self):
        pass

    def generate_entries_for_run(
        self,
        run_id: int,
        dry_run: bool = False
    ) -> Dict[str, any]:
        """
        Основной метод: создать все проводки для CalculationRun

        Args:
            run_id: ID расчета (CalculationRun)
            dry_run: Если True - только подсчитать, не сохранять

        Returns:
            Статистика генерации:
            {
                'status': 'success'|'error',
                'run_id': int,
                'total_entries_created': int,
                'total_amount': float,
                'by_event_type': {event: count, ...},
                'errors': [list of error messages]
            }
        """
        run = CalculationRun.query.get(run_id)
        if not run:
            return {'status': 'error', 'message': 'CalculationRun not found'}

        try:
            # Получаем все результаты расчетов для этого run
            group_results = GroupCalculationResult.query.filter_by(
                calculation_run_id=run_id
            ).all()

            if not group_results:
                return {
                    'status': 'error',
                    'message': 'No calculation results found for this run'
                }

            # Счетчики
            total_entries = 0
            total_amount = Decimal('0')
            entries_by_event = {}
            errors = []
            entries_to_create = []

            # Обрабатываем каждый результат
            for result in group_results:
                group = result.contract_group

                try:
                    # 1. CSM Release - если есть releasable CSM
                    if result.csm_expected_release and result.csm_expected_release > 0:
                        entry = self._create_csm_release_entry(
                            run=run,
                            result=result,
                            group=group
                        )
                        if entry:
                            entries_to_create.append(entry)
                            entries_by_event.setdefault(AccountingEventType.CSM_RELEASE.value, 0)
                            entries_by_event[AccountingEventType.CSM_RELEASE.value] += 1
                            total_amount += entry.amount

                    # 2. Loss Component - если есть убыток
                    if result.loss_component and result.loss_component > 0:
                        entry = self._create_loss_component_entry(
                            run=run,
                            result=result,
                            group=group
                        )
                        if entry:
                            entries_to_create.append(entry)
                            entries_by_event.setdefault(AccountingEventType.LOSS_COMPONENT.value, 0)
                            entries_by_event[AccountingEventType.LOSS_COMPONENT.value] += 1
                            total_amount += entry.amount

                    # 3. RA Update - изменение Risk Adjustment
                    if result.ra_amount and result.ra_amount > 0:
                        entry = self._create_ra_adjustment_entry(
                            run=run,
                            result=result,
                            group=group
                        )
                        if entry:
                            entries_to_create.append(entry)
                            entries_by_event.setdefault(AccountingEventType.RA_ADJUSTMENT.value, 0)
                            entries_by_event[AccountingEventType.RA_ADJUSTMENT.value] += 1
                            total_amount += entry.amount

                except Exception as e:
                    errors.append(f"Error processing group {group.group_code}: {str(e)}")
                    self._log_error(run, group, f"Journal entry generation failed: {str(e)}")

            # Сохраняем созданные проводки (если не dry_run)
            if not dry_run and entries_to_create:
                for entry in entries_to_create:
                    db.session.add(entry)
                    total_entries += 1

                db.session.commit()

            return {
                'status': 'success',
                'run_id': run_id,
                'total_entries_created': len(entries_to_create) if not dry_run else total_entries,
                'total_amount': float(total_amount),
                'by_event_type': entries_by_event,
                'errors': errors if errors else None
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': str(e),
                'run_id': run_id
            }

    def _create_csm_release_entry(
        self,
        run: CalculationRun,
        result: GroupCalculationResult,
        group: ContractGroup
    ) -> Optional[JournalEntry]:
        """Создать проводку для CSM Release (доход от страховой деятельности)"""

        # Ищем применимое правило для CSM_RELEASE
        rule = self._find_matching_rule(
            event_type=AccountingEventType.CSM_RELEASE,
            group=group
        )

        if not rule:
            return None

        # Генерируем номер проводки
        entry_number = self._generate_entry_number(run, AccountingEventType.CSM_RELEASE)

        # Создаем проводку
        entry = JournalEntry(
            calculation_run_id=run.id,
            entry_number=entry_number,
            posting_date=run.reporting_date,
            debit_account=rule.debit_account_code,
            credit_account=rule.credit_account_code,
            amount=result.csm_expected_release,
            currency='KZT',
            event_type=AccountingEventType.CSM_RELEASE,
            source_type='contract_group',
            source_id=group.id,
            source_reference=group.group_code,
            contract_group_id=group.id,
            description=f'CSM Release for group {group.group_code}',
            narrative=f'CSM expected release: {float(result.csm_expected_release):,.2f} KZT',
            formula_reference=f'CSM_Release = {float(result.csm_expected_release):,.2f}',
            assumptions_used=result.assumptions_snapshot,
            is_posted=False
        )

        return entry

    def _create_loss_component_entry(
        self,
        run: CalculationRun,
        result: GroupCalculationResult,
        group: ContractGroup
    ) -> Optional[JournalEntry]:
        """Создать проводку для Loss Component (убыток по группе)"""

        rule = self._find_matching_rule(
            event_type=AccountingEventType.LOSS_COMPONENT,
            group=group
        )

        if not rule:
            return None

        entry_number = self._generate_entry_number(run, AccountingEventType.LOSS_COMPONENT)

        entry = JournalEntry(
            calculation_run_id=run.id,
            entry_number=entry_number,
            posting_date=run.reporting_date,
            debit_account=rule.debit_account_code,
            credit_account=rule.credit_account_code,
            amount=result.loss_component,
            currency='KZT',
            event_type=AccountingEventType.LOSS_COMPONENT,
            source_type='contract_group',
            source_id=group.id,
            source_reference=group.group_code,
            contract_group_id=group.id,
            description=f'Loss Component for group {group.group_code}',
            narrative=f'Loss component: {float(result.loss_component):,.2f} KZT',
            formula_reference=f'Loss_Component = FCF - Premium = {float(result.loss_component):,.2f}',
            assumptions_used=result.assumptions_snapshot,
            is_posted=False
        )

        return entry

    def _create_ra_adjustment_entry(
        self,
        run: CalculationRun,
        result: GroupCalculationResult,
        group: ContractGroup
    ) -> Optional[JournalEntry]:
        """Создать проводку для Risk Adjustment (корректировка риска)"""

        rule = self._find_matching_rule(
            event_type=AccountingEventType.RA_ADJUSTMENT,
            group=group
        )

        if not rule:
            return None

        entry_number = self._generate_entry_number(run, AccountingEventType.RA_ADJUSTMENT)

        entry = JournalEntry(
            calculation_run_id=run.id,
            entry_number=entry_number,
            posting_date=run.reporting_date,
            debit_account=rule.debit_account_code,
            credit_account=rule.credit_account_code,
            amount=result.ra_amount,
            currency='KZT',
            event_type=AccountingEventType.RA_ADJUSTMENT,
            source_type='contract_group',
            source_id=group.id,
            source_reference=group.group_code,
            contract_group_id=group.id,
            description=f'Risk Adjustment for group {group.group_code}',
            narrative=f'RA amount: {float(result.ra_amount):,.2f} KZT',
            formula_reference=f'RA = 10% × BEL = {float(result.ra_amount):,.2f}',
            assumptions_used=result.assumptions_snapshot,
            is_posted=False
        )

        return entry

    def _find_matching_rule(
        self,
        event_type: AccountingEventType,
        group: ContractGroup
    ) -> Optional[AccountingRule]:
        """
        Найти применимое правило маппинга для события

        Логика подбора:
        1. Все активные правила для этого события
        2. Фильтруем по insurance_type, contract_type, measurement_model
        3. Берем правило с наименьшим priority
        4. Если нет точного совпадения - ищем общее правило (без фильтров)
        """

        # Все активные правила для этого события, отсортированные по приоритету
        all_rules = AccountingRule.query.filter_by(
            event_type=event_type,
            is_active=True
        ).order_by(AccountingRule.priority).all()

        if not all_rules:
            return None

        # Пытаемся найти точное совпадение с фильтрами
        for rule in all_rules:
            if self._rule_matches(rule, group):
                return rule

        # Если точного совпадения нет - ищем общее правило (без фильтров)
        for rule in all_rules:
            if not rule.insurance_type and not rule.contract_type and not rule.measurement_model:
                return rule

        return None

    def _rule_matches(self, rule: AccountingRule, group: ContractGroup) -> bool:
        """Проверить, применимо ли правило к группе"""

        # Проверяем insurance_type фильтр
        if rule.insurance_type:
            if rule.insurance_type != group.insurance_type:
                return False

        # Проверяем contract_type фильтр
        if rule.contract_type:
            if rule.contract_type != group.contract_type:
                return False

        # Проверяем measurement_model фильтр
        if rule.measurement_model:
            if rule.measurement_model != group.measurement_model:
                return False

        return True

    def _generate_entry_number(
        self,
        run: CalculationRun,
        event_type: AccountingEventType
    ) -> str:
        """Генерировать уникальный номер проводки"""

        # Находим максимальный номер для этого типа события в этом run
        max_entry = JournalEntry.query.filter(
            JournalEntry.calculation_run_id == run.id,
            JournalEntry.event_type == event_type
        ).order_by(
            JournalEntry.entry_number.desc()
        ).first()

        # Формат: RUN_CODE-EVENT_TYPE-SEQ
        # Пример: IFRS-20251231-CSM_RELEASE-001
        if max_entry:
            # Извлекаем последний номер
            parts = max_entry.entry_number.split('-')
            seq = int(parts[-1]) + 1
        else:
            seq = 1

        date_str = run.reporting_date.strftime('%Y%m%d')
        event_str = event_type.value.upper()[:8]  # Первые 8 символов типа события

        return f"{date_str}-{event_str}-{seq:04d}"

    def _log_error(
        self,
        run: CalculationRun,
        group: ContractGroup,
        error_message: str
    ):
        """Логировать ошибку в CalculationLog"""

        log = CalculationLog(
            calculation_run_id=run.id,
            entity_type='contract_group',
            entity_id=group.id,
            entity_reference=group.group_code,
            calculation_type='JOURNAL_ENTRY_GENERATION_ERROR',
            calculation_date=run.reporting_date,
            input_data={'error': error_message},
            formula_display='Error during journal entry generation',
            result_value=Decimal('0')
        )
        db.session.add(log)

    def post_entries(self, run_id: int) -> Dict[str, any]:
        """
        Проводить (post) созданные проводки в главную книгу

        ВНИМАНИЕ: Эта операция необратима!
        """

        entries = JournalEntry.query.filter_by(
            calculation_run_id=run_id,
            is_posted=False
        ).all()

        if not entries:
            return {
                'status': 'info',
                'message': 'No entries to post',
                'count': 0
            }

        try:
            for entry in entries:
                entry.is_posted = True
                entry.posted_at = datetime.utcnow()

            db.session.commit()

            return {
                'status': 'success',
                'message': f'Posted {len(entries)} entries',
                'count': len(entries)
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }

    def get_entry_summary(self, run_id: int) -> Dict[str, any]:
        """Получить сводку по проводкам для run"""

        run = CalculationRun.query.get(run_id)
        if not run:
            return {'status': 'error', 'message': 'Run not found'}

        # Статистика по типам событий
        event_counts = db.session.query(
            JournalEntry.event_type,
            func.count(JournalEntry.id).label('count'),
            func.sum(JournalEntry.amount).label('total_amount')
        ).filter_by(calculation_run_id=run_id).group_by(JournalEntry.event_type).all()

        summary = {
            'run_id': run_id,
            'run_code': run.run_code,
            'reporting_date': run.reporting_date.isoformat(),
            'total_entries': JournalEntry.query.filter_by(calculation_run_id=run_id).count(),
            'posted_entries': JournalEntry.query.filter_by(calculation_run_id=run_id, is_posted=True).count(),
            'pending_entries': JournalEntry.query.filter_by(calculation_run_id=run_id, is_posted=False).count(),
            'total_amount': float(
                db.session.query(func.sum(JournalEntry.amount)).filter_by(calculation_run_id=run_id).scalar() or 0
            ),
            'by_event_type': [
                {
                    'event_type': str(row[0].value) if row[0] else 'unknown',
                    'count': row[1],
                    'total_amount': float(row[2] or 0)
                }
                for row in event_counts
            ]
        }

        return summary


# Singleton instance
journal_entry_generator_service = JournalEntryGeneratorService()
