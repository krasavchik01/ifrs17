# -*- coding: utf-8 -*-
"""
KZ-InsurePro - Модуль ФГСВ: Фонд гарантирования страховых выплат
Расчет взносов и моделирование сценариев банкротства

Соответствие:
- Закон РК №423-II от 03.06.2003 "О Фонде гарантирования страховых выплат"
- Универсальное покрытие с 2023

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
    FGSV_CONFIG, MACRO_INDICATORS_2025, LOCALE_CONFIG,
    format_currency, format_percent, DEMO_CONFIG
)

logger = logging.getLogger(__name__)


@dataclass
class ContributionResult:
    """Результат расчета взносов в ФГСВ"""
    contribution_amount: Decimal
    rate: Decimal
    premium_base: Decimal
    risk_class: str
    formula_display: str
    justification: str


@dataclass
class BankruptcySimulationResult:
    """Результат моделирования банкротства"""
    expected_claims: Decimal
    fund_adequacy: Decimal
    probability_of_shortfall: Decimal
    var_95: Decimal
    simulations: int
    formula_display: str
    justification: str


@dataclass
class FGSVAssessmentResult:
    """Полная оценка для ФГСВ"""
    contributions: List[ContributionResult]
    total_contributions: Decimal
    fund_balance: Decimal
    adequacy_ratio: Decimal
    is_adequate: bool
    bankruptcy_simulation: BankruptcySimulationResult
    formula_display: str
    justification: str


class FGSVCalculator:
    """
    Калькулятор для Фонда гарантирования страховых выплат

    Реализует:
    - Расчет взносов по классам риска
    - Моделирование сценариев банкротства (Monte Carlo)
    - Оценка достаточности фонда
    - Прогнозирование выплат
    """

    def __init__(self):
        self.config = FGSV_CONFIG
        self.macro = MACRO_INDICATORS_2025
        self.precision = Decimal('0.001')

        # Аудиторский след
        self.audit_log = []

        # Seed для воспроизводимости
        np.random.seed(42)

        logger.info("FGSVCalculator инициализирован")

    def _round_to_precision(self, value: Decimal) -> Decimal:
        """Округление до точности 0.001 KZT"""
        return value.quantize(self.precision, rounding=ROUND_HALF_UP)

    def _log_audit(self, operation: str, details: Dict[str, Any]):
        """Запись в аудиторский след"""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'operation': operation,
            'details': details,
            'reference': 'Закон РК №423-II'
        }
        self.audit_log.append(entry)
        logger.info(f"Аудит: {operation}")

    # =========================================================================
    # ОПРЕДЕЛЕНИЕ КЛАССА РИСКА
    # =========================================================================

    def determine_risk_class(
        self,
        solvency_ratio: Decimal,
        loss_ratio: Decimal,
        combined_ratio: Decimal,
        years_in_market: int
    ) -> Tuple[str, str]:
        """
        Определение класса риска страховщика

        Критерии:
        - Low risk: Nmп ≥ 200%, loss ratio < 60%, combined ratio < 90%
        - Medium risk: 150% ≤ Nmп < 200%
        - High risk: Nmп < 150% или убыточность высокая

        Args:
            solvency_ratio: Коэффициент платежеспособности
            loss_ratio: Коэффициент убыточности
            combined_ratio: Комбинированный коэффициент
            years_in_market: Лет на рынке

        Returns:
            (risk_class, justification)
        """
        # Оценка по критериям
        score = 0

        # Платежеспособность
        if solvency_ratio >= Decimal('2.0'):
            score += 3
        elif solvency_ratio >= Decimal('1.5'):
            score += 2
        elif solvency_ratio >= Decimal('1.0'):
            score += 1

        # Убыточность
        if loss_ratio < Decimal('0.60'):
            score += 2
        elif loss_ratio < Decimal('0.75'):
            score += 1

        # Комбинированный
        if combined_ratio < Decimal('0.90'):
            score += 2
        elif combined_ratio < Decimal('1.0'):
            score += 1

        # Опыт
        if years_in_market >= 10:
            score += 1

        # Определение класса
        if score >= 7:
            risk_class = 'low_risk'
            description = 'Низкий риск'
        elif score >= 4:
            risk_class = 'medium_risk'
            description = 'Средний риск'
        else:
            risk_class = 'high_risk'
            description = 'Высокий риск'

        justification = (
            f"Класс риска: {description} (score={score}). "
            f"Nmп={float(solvency_ratio):.0%}, Loss ratio={float(loss_ratio):.0%}, "
            f"Combined ratio={float(combined_ratio):.0%}, "
            f"Лет на рынке: {years_in_market}."
        )

        return risk_class, justification

    # =========================================================================
    # РАСЧЕТ ВЗНОСОВ
    # =========================================================================

    def calculate_contribution(
        self,
        gross_premiums: Decimal,
        risk_class: str = None,
        solvency_ratio: Decimal = None,
        loss_ratio: Decimal = None,
        combined_ratio: Decimal = None,
        years_in_market: int = 5
    ) -> ContributionResult:
        """
        Расчет взноса в ФГСВ

        Формула: Contribution = rate × Gross_Premiums

        Per Закон №423-II: ставка 0.5-2% от премий

        Args:
            gross_premiums: Валовые премии за период
            risk_class: Класс риска (или определяется автоматически)
            solvency_ratio: Для автоматического определения класса
            loss_ratio: Для автоматического определения класса
            combined_ratio: Для автоматического определения класса
            years_in_market: Лет на рынке

        Returns:
            ContributionResult
        """
        # Определение класса риска
        if risk_class is None:
            if solvency_ratio is not None:
                risk_class, class_justification = self.determine_risk_class(
                    solvency_ratio,
                    loss_ratio or Decimal('0.70'),
                    combined_ratio or Decimal('0.95'),
                    years_in_market
                )
            else:
                risk_class = 'medium_risk'
                class_justification = "Класс риска не указан, применен средний"
        else:
            class_justification = f"Класс риска указан явно: {risk_class}"

        # Ставка по классу риска
        rate = self.config['CONTRIBUTION_RATES'].get(risk_class, Decimal('0.01'))

        # Расчет взноса
        contribution = gross_premiums * rate
        contribution = self._round_to_precision(contribution)

        # Перевод класса на русский
        risk_class_ru = {
            'low_risk': 'Низкий',
            'medium_risk': 'Средний',
            'high_risk': 'Высокий'
        }.get(risk_class, risk_class)

        formula_display = (
            f"{'='*60}\n"
            f"РАСЧЕТ ВЗНОСА В ФГСВ\n"
            f"{'='*60}\n\n"
            f"Формула: Взнос = Ставка × Премии\n\n"
            f"Валовые премии: {format_currency(gross_premiums)}\n"
            f"Класс риска: {risk_class_ru}\n"
            f"Ставка: {float(rate):.1%}\n\n"
            f"Взнос = {float(rate):.1%} × {format_currency(gross_premiums)}\n"
            f"Взнос = {format_currency(contribution)}\n"
            f"{'='*60}\n"
        )

        justification = (
            f"Взнос в ФГСВ рассчитан в соответствии с Законом РК №423-II. "
            f"{class_justification} "
            f"Ставка {float(rate):.1%} применена к валовым премиям "
            f"{format_currency(gross_premiums)}. "
            f"Итоговый взнос = {format_currency(contribution)}."
        )

        result = ContributionResult(
            contribution_amount=contribution,
            rate=rate,
            premium_base=gross_premiums,
            risk_class=risk_class,
            formula_display=formula_display,
            justification=justification
        )

        self._log_audit('Расчет взноса ФГСВ', {
            'contribution': float(contribution),
            'rate': float(rate),
            'risk_class': risk_class,
            'premiums': float(gross_premiums),
        })

        return result

    # =========================================================================
    # МОДЕЛИРОВАНИЕ БАНКРОТСТВА
    # =========================================================================

    def simulate_bankruptcy(
        self,
        insurer_data: List[Dict],
        num_simulations: int = None,
        correlation: float = 0.3
    ) -> BankruptcySimulationResult:
        """
        Monte Carlo моделирование сценариев банкротства

        Модель: Коррелированные дефолты с Gaussian copula

        Args:
            insurer_data: Список страховщиков
                [{'name': str, 'premiums': Decimal, 'reserves': Decimal,
                  'pd': Decimal, 'recovery': Decimal}, ...]
            num_simulations: Количество симуляций
            correlation: Корреляция между дефолтами

        Returns:
            BankruptcySimulationResult
        """
        if num_simulations is None:
            num_simulations = self.config['BANKRUPTCY_SIMULATIONS']

        # Демо-ограничение
        num_simulations = min(num_simulations, 1000)

        n_insurers = len(insurer_data)
        if n_insurers == 0:
            return BankruptcySimulationResult(
                expected_claims=Decimal('0'),
                fund_adequacy=Decimal('1'),
                probability_of_shortfall=Decimal('0'),
                var_95=Decimal('0'),
                simulations=0,
                formula_display="Нет данных страховщиков",
                justification="Нет данных"
            )

        # Извлечение параметров
        pds = np.array([float(ins.get('pd', 0.05)) for ins in insurer_data])
        reserves = np.array([float(ins.get('reserves', 0)) for ins in insurer_data])
        recoveries = np.array([float(ins.get('recovery', 0.3)) for ins in insurer_data])

        # Лимиты выплат
        limits = []
        for ins in insurer_data:
            ins_type = ins.get('type', 'voluntary')
            limit = self.config['PAYOUT_LIMITS'].get(ins_type, Decimal('500000'))
            limits.append(float(limit))
        limits = np.array(limits)

        # Генерация коррелированных дефолтов (Gaussian copula)
        # Ковариационная матрица
        cov_matrix = np.full((n_insurers, n_insurers), correlation)
        np.fill_diagonal(cov_matrix, 1.0)

        # Генерация нормальных величин
        normal_samples = np.random.multivariate_normal(
            np.zeros(n_insurers),
            cov_matrix,
            num_simulations
        )

        # Преобразование в вероятности дефолта через CDF
        uniform_samples = stats.norm.cdf(normal_samples)

        # Определение дефолтов
        defaults = uniform_samples < pds  # Shape: (num_simulations, n_insurers)

        # Расчет убытков для фонда
        # Loss = (Reserves - Recovery × Reserves) × Default
        lgd_rates = 1 - recoveries
        potential_losses = reserves * lgd_rates

        # Применение лимитов выплат (упрощенно: как множитель)
        # Реально нужно знать количество полисов и суммы выплат
        losses_per_sim = defaults * potential_losses  # Shape: (num_simulations, n_insurers)
        total_losses = np.sum(losses_per_sim, axis=1)  # Shape: (num_simulations,)

        # Статистики
        expected_claims = Decimal(str(np.mean(total_losses)))
        var_95 = Decimal(str(np.percentile(total_losses, 95)))
        var_99 = Decimal(str(np.percentile(total_losses, 99)))

        # Вероятность дефицита (предполагаем фонд = 10% от суммарных резервов)
        total_reserves = sum(float(ins.get('reserves', 0)) for ins in insurer_data)
        assumed_fund = total_reserves * 0.10  # 10% от резервов
        probability_of_shortfall = Decimal(str(np.mean(total_losses > assumed_fund)))

        # Достаточность фонда
        fund_adequacy = Decimal(str(assumed_fund / float(expected_claims))) if expected_claims > 0 else Decimal('10')

        formula_display = (
            f"{'='*60}\n"
            f"МОДЕЛИРОВАНИЕ БАНКРОТСТВА (Monte Carlo)\n"
            f"{'='*60}\n\n"
            f"Параметры:\n"
            f"  Страховщиков: {n_insurers}\n"
            f"  Симуляций: {num_simulations}\n"
            f"  Корреляция дефолтов: {correlation}\n\n"
            f"Результаты:\n"
            f"  Ожидаемые выплаты: {format_currency(expected_claims)}\n"
            f"  VaR 95%: {format_currency(var_95)}\n"
            f"  VaR 99%: {format_currency(var_99)}\n"
            f"  P(дефицит): {float(probability_of_shortfall):.1%}\n\n"
            f"Предполагаемый фонд: {format_currency(Decimal(str(assumed_fund)))}\n"
            f"Достаточность: {float(fund_adequacy):.2f}x\n"
            f"{'='*60}\n"
        )

        justification = (
            f"Monte Carlo моделирование ({num_simulations} симуляций) "
            f"с коррелированными дефолтами (ρ={correlation}). "
            f"Ожидаемые выплаты ФГСВ = {format_currency(expected_claims)}, "
            f"VaR 95% = {format_currency(var_95)}. "
            f"Вероятность дефицита фонда = {float(probability_of_shortfall):.1%}."
        )

        result = BankruptcySimulationResult(
            expected_claims=self._round_to_precision(expected_claims),
            fund_adequacy=self._round_to_precision(fund_adequacy),
            probability_of_shortfall=self._round_to_precision(probability_of_shortfall),
            var_95=self._round_to_precision(var_95),
            simulations=num_simulations,
            formula_display=formula_display,
            justification=justification
        )

        self._log_audit('Моделирование банкротства', {
            'expected_claims': float(expected_claims),
            'var_95': float(var_95),
            'p_shortfall': float(probability_of_shortfall),
            'simulations': num_simulations,
        })

        return result

    # =========================================================================
    # ОЦЕНКА ДОСТАТОЧНОСТИ ФОНДА
    # =========================================================================

    def assess_fund_adequacy(
        self,
        fund_balance: Decimal,
        expected_claims: Decimal,
        contributions_pipeline: Decimal = Decimal('0')
    ) -> Dict[str, Any]:
        """
        Оценка достаточности фонда

        Требование: Fund / Expected_Claims > 1.2

        Args:
            fund_balance: Текущий баланс фонда
            expected_claims: Ожидаемые выплаты
            contributions_pipeline: Ожидаемые поступления взносов

        Returns:
            Результат оценки
        """
        total_resources = fund_balance + contributions_pipeline
        required_ratio = self.config['ADEQUACY_RATIO']

        if expected_claims > 0:
            current_ratio = fund_balance / expected_claims
            projected_ratio = total_resources / expected_claims
        else:
            current_ratio = Decimal('100')
            projected_ratio = Decimal('100')

        is_adequate = current_ratio >= required_ratio
        will_be_adequate = projected_ratio >= required_ratio

        # Дефицит/профицит
        shortfall = max(Decimal('0'), expected_claims * required_ratio - fund_balance)
        surplus = max(Decimal('0'), fund_balance - expected_claims * required_ratio)

        return {
            'fund_balance': fund_balance,
            'expected_claims': expected_claims,
            'current_ratio': self._round_to_precision(current_ratio),
            'projected_ratio': self._round_to_precision(projected_ratio),
            'required_ratio': required_ratio,
            'is_adequate': is_adequate,
            'will_be_adequate': will_be_adequate,
            'shortfall': self._round_to_precision(shortfall),
            'surplus': self._round_to_precision(surplus),
        }

    # =========================================================================
    # ПОЛНАЯ ОЦЕНКА ФГСВ
    # =========================================================================

    def full_assessment(
        self,
        insurers: List[Dict],
        fund_balance: Decimal
    ) -> FGSVAssessmentResult:
        """
        Полная оценка для ФГСВ

        Args:
            insurers: Список страховщиков с данными
            fund_balance: Текущий баланс фонда

        Returns:
            FGSVAssessmentResult
        """
        # Демо-ограничение
        if len(insurers) > DEMO_CONFIG['MAX_RECORDS_PER_MODULE']:
            insurers = insurers[:DEMO_CONFIG['MAX_RECORDS_PER_MODULE']]
            logger.warning(f"Демо: ограничено до {DEMO_CONFIG['MAX_RECORDS_PER_MODULE']} страховщиков")

        # Расчет взносов
        contributions = []
        total_contributions = Decimal('0')

        for ins in insurers:
            result = self.calculate_contribution(
                gross_premiums=ins.get('premiums', Decimal('0')),
                solvency_ratio=ins.get('solvency_ratio'),
                loss_ratio=ins.get('loss_ratio'),
                combined_ratio=ins.get('combined_ratio'),
                years_in_market=ins.get('years_in_market', 5)
            )
            contributions.append(result)
            total_contributions += result.contribution_amount

        # Моделирование банкротства
        bankruptcy_sim = self.simulate_bankruptcy(insurers)

        # Оценка достаточности
        adequacy = self.assess_fund_adequacy(
            fund_balance,
            bankruptcy_sim.expected_claims,
            total_contributions
        )

        formula_display = (
            f"{'='*60}\n"
            f"ПОЛНАЯ ОЦЕНКА ФГСВ\n"
            f"{'='*60}\n\n"
            f"Страховщиков: {len(insurers)}\n"
            f"Всего взносов: {format_currency(total_contributions)}\n\n"
            f"Баланс фонда: {format_currency(fund_balance)}\n"
            f"Ожидаемые выплаты: {format_currency(bankruptcy_sim.expected_claims)}\n"
            f"Коэффициент достаточности: {float(adequacy['current_ratio']):.2f}x "
            f"(требуется ≥ {float(adequacy['required_ratio'])})\n\n"
            f"Статус: {'ДОСТАТОЧНО ✓' if adequacy['is_adequate'] else 'НЕДОСТАТОЧНО ✗'}\n"
            f"{'='*60}\n"
        )

        justification = (
            f"Полная оценка ФГСВ для {len(insurers)} страховщиков. "
            f"Суммарные взносы = {format_currency(total_contributions)}. "
            f"При ожидаемых выплатах {format_currency(bankruptcy_sim.expected_claims)} "
            f"коэффициент достаточности = {float(adequacy['current_ratio']):.2f}x. "
            f"Фонд {'достаточен' if adequacy['is_adequate'] else 'НЕДОСТАТОЧЕН'}."
        )

        result = FGSVAssessmentResult(
            contributions=contributions,
            total_contributions=total_contributions,
            fund_balance=fund_balance,
            adequacy_ratio=adequacy['current_ratio'],
            is_adequate=adequacy['is_adequate'],
            bankruptcy_simulation=bankruptcy_sim,
            formula_display=formula_display,
            justification=justification
        )

        self._log_audit('Полная оценка ФГСВ', {
            'insurers': len(insurers),
            'total_contributions': float(total_contributions),
            'adequacy_ratio': float(adequacy['current_ratio']),
            'is_adequate': adequacy['is_adequate'],
        })

        return result

    # =========================================================================
    # РАННЕЕ ПРЕДУПРЕЖДЕНИЕ
    # =========================================================================

    def early_warning_indicators(
        self,
        insurer: Dict
    ) -> Dict[str, Any]:
        """
        Индикаторы раннего предупреждения

        Args:
            insurer: Данные страховщика

        Returns:
            Словарь с индикаторами и флагами
        """
        warnings = []
        risk_score = 0

        # Платежеспособность
        solvency = insurer.get('solvency_ratio', Decimal('1.5'))
        if solvency < Decimal('1.0'):
            warnings.append('КРИТИЧНО: Nmп < 100%')
            risk_score += 5
        elif solvency < Decimal('1.2'):
            warnings.append('ВНИМАНИЕ: Nmп < 120%')
            risk_score += 3
        elif solvency < Decimal('1.5'):
            warnings.append('Наблюдение: Nmп < 150%')
            risk_score += 1

        # Убыточность
        loss_ratio = insurer.get('loss_ratio', Decimal('0.70'))
        if loss_ratio > Decimal('0.90'):
            warnings.append('КРИТИЧНО: Loss ratio > 90%')
            risk_score += 4
        elif loss_ratio > Decimal('0.80'):
            warnings.append('ВНИМАНИЕ: Loss ratio > 80%')
            risk_score += 2

        # Combined ratio
        combined = insurer.get('combined_ratio', Decimal('0.95'))
        if combined > Decimal('1.10'):
            warnings.append('КРИТИЧНО: Combined ratio > 110%')
            risk_score += 4
        elif combined > Decimal('1.00'):
            warnings.append('ВНИМАНИЕ: Combined ratio > 100%')
            risk_score += 2

        # Рост премий (аномальный)
        premium_growth = insurer.get('premium_growth', Decimal('0'))
        if premium_growth > Decimal('0.50'):
            warnings.append('Наблюдение: Рост премий > 50%')
            risk_score += 1
        elif premium_growth < Decimal('-0.20'):
            warnings.append('ВНИМАНИЕ: Падение премий > 20%')
            risk_score += 2

        # Определение уровня риска
        if risk_score >= 8:
            risk_level = 'КРИТИЧЕСКИЙ'
            action = 'Немедленное вмешательство АРФР'
        elif risk_score >= 5:
            risk_level = 'ВЫСОКИЙ'
            action = 'Усиленный мониторинг'
        elif risk_score >= 2:
            risk_level = 'ПОВЫШЕННЫЙ'
            action = 'Регулярный мониторинг'
        else:
            risk_level = 'НОРМАЛЬНЫЙ'
            action = 'Стандартный мониторинг'

        return {
            'insurer_name': insurer.get('name', 'N/A'),
            'risk_score': risk_score,
            'risk_level': risk_level,
            'warnings': warnings,
            'recommended_action': action,
            'indicators': {
                'solvency_ratio': float(solvency),
                'loss_ratio': float(loss_ratio),
                'combined_ratio': float(combined),
            }
        }

    def get_audit_log(self) -> List[Dict]:
        """Получить аудиторский след"""
        return self.audit_log


# =============================================================================
# ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ
# =============================================================================

def demo_fgsv_assessment():
    """Демонстрация оценки ФГСВ"""
    calc = FGSVCalculator()

    # Пример страховщиков
    insurers = [
        {
            'name': 'Страховая компания А',
            'premiums': Decimal('5000000000'),  # 5 млрд
            'reserves': Decimal('3000000000'),  # 3 млрд
            'solvency_ratio': Decimal('2.50'),
            'loss_ratio': Decimal('0.55'),
            'combined_ratio': Decimal('0.85'),
            'pd': Decimal('0.02'),
            'recovery': Decimal('0.40'),
            'years_in_market': 15,
            'type': 'compulsory',
        },
        {
            'name': 'Страховая компания Б',
            'premiums': Decimal('3000000000'),  # 3 млрд
            'reserves': Decimal('2000000000'),  # 2 млрд
            'solvency_ratio': Decimal('1.30'),
            'loss_ratio': Decimal('0.75'),
            'combined_ratio': Decimal('1.02'),
            'pd': Decimal('0.08'),
            'recovery': Decimal('0.30'),
            'years_in_market': 7,
            'type': 'voluntary',
        },
    ]

    # Баланс фонда
    fund_balance = Decimal('50000000000')  # 50 млрд

    # Полная оценка
    result = calc.full_assessment(insurers, fund_balance)

    print(result.formula_display)
    print(f"\nОбоснование: {result.justification}")

    # Раннее предупреждение
    for ins in insurers:
        warnings = calc.early_warning_indicators(ins)
        print(f"\nИндикаторы для {warnings['insurer_name']}:")
        print(f"  Уровень риска: {warnings['risk_level']}")
        if warnings['warnings']:
            for w in warnings['warnings']:
                print(f"  - {w}")

    return result


if __name__ == '__main__':
    demo_fgsv_assessment()
