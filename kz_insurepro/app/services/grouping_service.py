# -*- coding: utf-8 -*-
"""
Alliot - Auto-Grouping Service
Автоматическая группировка договоров по требованиям МСФО 17

КРИТИЧНО: МСФО 17 требует группировки (Unit of Account) по 3 уровням:
1. Portfolio (схожие риски + управляются вместе)
2. Annual Cohort (год выпуска - НЕЛЬЗЯ смешивать разные годы!)
3. Profitability Group (onerous/profitable/no_significant_loss)

Этот сервис автоматически создает группы при импорте договоров.
"""

from decimal import Decimal
from datetime import datetime
from typing import List, Dict, Tuple
from sqlalchemy import func

from app import db
from app.enterprise_models import (
    InsuranceContract, ContractGroup,
    InsuranceType, MeasurementModel, ContractType, ProfitabilityGroup
)


class GroupingService:
    """
    Сервис автоматической группировки договоров

    Используется:
    1. При импорте CSV - автоматически распределяет договоры по группам
    2. При пересчете - может перегруппировать если изменились параметры
    """

    def __init__(self):
        pass

    def auto_group_contracts(
        self,
        contracts: List[InsuranceContract] = None,
        recreate_groups: bool = False
    ) -> Dict[str, any]:
        """
        Автоматическая группировка договоров

        Args:
            contracts: Список договоров (если None - берем все активные)
            recreate_groups: Пересоздать группы заново?

        Returns:
            Статистика группировки
        """
        if contracts is None:
            # Берем все активные договоры без группы
            contracts = InsuranceContract.query.filter_by(group_id=None).all()

        if not contracts:
            return {
                'status': 'no_contracts',
                'groups_created': 0,
                'contracts_grouped': 0
            }

        groups_created = 0
        contracts_grouped = 0

        # Группируем по критериям МСФО 17
        grouped_contracts = self._group_by_criteria(contracts)

        for group_key, contract_list in grouped_contracts.items():
            # Создаем или находим группу
            group = self._get_or_create_group(group_key, contract_list[0])

            # Присваиваем договоры группе
            for contract in contract_list:
                contract.group_id = group.id
                contracts_grouped += 1

            # Обновляем агрегаты группы
            self._update_group_aggregates(group)

            if group.id is None:  # Новая группа
                groups_created += 1

        db.session.commit()

        return {
            'status': 'success',
            'groups_created': groups_created,
            'contracts_grouped': contracts_grouped,
            'total_groups': len(grouped_contracts)
        }

    def _group_by_criteria(self, contracts: List[InsuranceContract]) -> Dict[str, List]:
        """
        Группировка договоров по 3 критериям МСФО 17

        Returns:
            Dict где ключ = "LIFE_2025_PROFITABLE_GMM_DIRECT"
        """
        grouped = {}

        for contract in contracts:
            # Определяем группу прибыльности
            profitability = self._determine_profitability(contract)

            # Формируем ключ группы
            group_key = self._build_group_key(
                insurance_type=contract.insurance_type,
                cohort_year=contract.cohort_year,
                profitability=profitability,
                measurement_model=contract.measurement_model,
                contract_type=contract.contract_type
            )

            if group_key not in grouped:
                grouped[group_key] = []

            grouped[group_key].append(contract)

        return grouped

    def _determine_profitability(self, contract: InsuranceContract) -> ProfitabilityGroup:
        """
        Определение группы прибыльности при признании

        МСФО 17 требует тест на обременительность (Onerous Test):
        - Если FCF < 0 при признании → Onerous (убыточный)
        - Если нет значительного риска убытка → No Significant Loss
        - Иначе → Profitable
        """
        # Если уже помечен как onerous
        if contract.is_onerous:
            return ProfitabilityGroup.ONEROUS

        # Простая логика (в реальности нужен более сложный тест):
        # Если ожидаемые убытки > 90% премии - риск убытка
        if contract.expected_claims and contract.premium_amount:
            loss_ratio = float(contract.expected_claims / contract.premium_amount)
            if loss_ratio > 1.0:
                return ProfitabilityGroup.ONEROUS
            elif loss_ratio > 0.9:
                return ProfitabilityGroup.NO_SIGNIFICANT_LOSS
            else:
                return ProfitabilityGroup.PROFITABLE

        # По умолчанию - нет значительного риска
        return ProfitabilityGroup.NO_SIGNIFICANT_LOSS

    def _build_group_key(
        self,
        insurance_type: InsuranceType,
        cohort_year: int,
        profitability: ProfitabilityGroup,
        measurement_model: MeasurementModel,
        contract_type: ContractType
    ) -> str:
        """
        Построение уникального ключа группы

        Format: "{INSURANCE_TYPE}_{YEAR}_{PROFITABILITY}_{MODEL}_{TYPE}"
        Example: "LIFE_2025_PROFITABLE_GMM_DIRECT"
        """
        parts = [
            insurance_type.value.upper(),
            str(cohort_year),
            profitability.value.upper(),
            measurement_model.value.upper(),
            contract_type.value.upper()
        ]
        return "_".join(parts)

    def _get_or_create_group(
        self,
        group_key: str,
        sample_contract: InsuranceContract
    ) -> ContractGroup:
        """
        Найти существующую группу или создать новую
        """
        group = ContractGroup.query.filter_by(group_code=group_key).first()

        if not group:
            # Определяем группу прибыльности
            profitability = self._determine_profitability(sample_contract)

            # Создаем новую группу
            group = ContractGroup(
                group_code=group_key,
                name=self._generate_group_name(sample_contract, profitability),
                description=self._generate_group_description(sample_contract, profitability),
                insurance_type=sample_contract.insurance_type,
                cohort_year=sample_contract.cohort_year,
                profitability_group=profitability,
                measurement_model=sample_contract.measurement_model,
                contract_type=sample_contract.contract_type,
                product_name=sample_contract.product_name
            )
            db.session.add(group)
            db.session.flush()  # Получаем ID

        return group

    def _generate_group_name(
        self,
        contract: InsuranceContract,
        profitability: ProfitabilityGroup
    ) -> str:
        """Генерация читаемого имени группы"""
        type_names = {
            InsuranceType.LIFE: 'Жизнь',
            InsuranceType.NON_LIFE: 'Не-жизнь',
            InsuranceType.HEALTH: 'Здоровье',
            InsuranceType.ANNUITY: 'Аннуитет'
        }

        profit_names = {
            ProfitabilityGroup.ONEROUS: 'Убыточные',
            ProfitabilityGroup.PROFITABLE: 'Прибыльные',
            ProfitabilityGroup.NO_SIGNIFICANT_LOSS: 'Без значительного риска'
        }

        contract_type_names = {
            ContractType.DIRECT: 'Прямые',
            ContractType.REINSURANCE_HELD: 'Входящее перестрах.',
            ContractType.REINSURANCE_ISSUED: 'Исходящее перестрах.'
        }

        return f"{type_names.get(contract.insurance_type)} {contract.cohort_year} - " \
               f"{profit_names.get(profitability)} ({contract_type_names.get(contract.contract_type)})"

    def _generate_group_description(
        self,
        contract: InsuranceContract,
        profitability: ProfitabilityGroup
    ) -> str:
        """Генерация описания группы"""
        return f"Группа договоров {contract.insurance_type.value} " \
               f"когорты {contract.cohort_year}, " \
               f"классификация: {profitability.value}, " \
               f"модель оценки: {contract.measurement_model.value.upper()}"

    def _update_group_aggregates(self, group: ContractGroup):
        """
        Обновление агрегированных показателей группы

        КРИТИЧНО: После присвоения договоров группе нужно
        пересчитать все агрегаты на уровне группы
        """
        contracts = group.contracts.all()

        if not contracts:
            return

        # Счетчики
        group.total_contracts = len(contracts)
        group.active_contracts = sum(1 for c in contracts if c.status.value == 'active')

        # Суммы
        group.total_premium = sum(c.premium_amount or 0 for c in contracts)
        group.total_sum_insured = sum(c.sum_insured or 0 for c in contracts)

        # МСФО 17 компоненты (если уже рассчитаны)
        group.total_bel = sum(c.bel_amount or 0 for c in contracts)
        group.total_ra = sum(c.ra_amount or 0 for c in contracts)
        group.total_csm = sum(c.csm_amount or 0 for c in contracts)
        group.total_loss_component = sum(c.loss_component or 0 for c in contracts)

        group.total_fcf = group.total_bel + group.total_ra
        group.total_liability = group.total_fcf + group.total_csm + group.total_loss_component

        # Средневзвешенные параметры
        total_premium = group.total_premium
        if total_premium > 0:
            group.weighted_avg_discount_rate = sum(
                float(c.discount_rate or 0) * float(c.premium_amount or 0)
                for c in contracts
            ) / float(total_premium)

            group.weighted_avg_lapse_rate = sum(
                float(c.lapse_rate or 0) * float(c.premium_amount or 0)
                for c in contracts
            ) / float(total_premium)

        # Coverage Units
        total_initial_coverage = sum(
            float(c.premium_amount or 0) *
            max(1, (c.expiry_date - c.inception_date).days / 365)
            for c in contracts
        )
        group.total_coverage_units_initial = Decimal(str(total_initial_coverage))

        # Remaining coverage units
        total_remaining_coverage = sum(
            float(c.premium_amount or 0) * c.coverage_units_remaining
            for c in contracts
        )
        group.total_coverage_units_remaining = Decimal(str(total_remaining_coverage))

        group.updated_at = datetime.utcnow()

    def regroup_all_contracts(self) -> Dict[str, any]:
        """
        Полная перегруппировка всех договоров

        ВНИМАНИЕ: Используется только при изменении логики группировки!
        """
        # Очищаем все связи
        InsuranceContract.query.update({'group_id': None})
        db.session.commit()

        # Удаляем старые пустые группы
        ContractGroup.query.delete()
        db.session.commit()

        # Заново группируем
        all_contracts = InsuranceContract.query.all()
        return self.auto_group_contracts(contracts=all_contracts)


# Singleton instance
grouping_service = GroupingService()
