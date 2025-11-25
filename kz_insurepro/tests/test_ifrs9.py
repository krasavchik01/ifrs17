# -*- coding: utf-8 -*-
"""
KZ-InsurePro - Unit тесты для модуля МСФО 9
"""

import pytest
import sys
import os
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.modules.ifrs9 import IFRS9Calculator


class TestIFRS9Calculator:
    """Тесты калькулятора МСФО 9"""

    def setup_method(self):
        """Инициализация перед каждым тестом"""
        self.calc = IFRS9Calculator()

    def test_initialization(self):
        """Тест инициализации калькулятора"""
        assert self.calc is not None
        assert self.calc.config is not None
        assert self.calc.macro is not None

    def test_determine_stage_1(self):
        """Тест определения стадии 1 (низкий риск)"""
        stage, _ = self.calc.determine_stage(
            days_past_due=0,
            pd_current=Decimal('0.05'),
            pd_at_origination=Decimal('0.05'),
        )
        assert stage == 1

    def test_determine_stage_2_dpd(self):
        """Тест определения стадии 2 по дням просрочки"""
        stage, _ = self.calc.determine_stage(
            days_past_due=45,  # >30 дней
            pd_current=Decimal('0.05'),
            pd_at_origination=Decimal('0.05'),
        )
        assert stage == 2

    def test_determine_stage_2_pd_increase(self):
        """Тест определения стадии 2 по увеличению PD"""
        stage, _ = self.calc.determine_stage(
            days_past_due=0,
            pd_current=Decimal('0.15'),  # 3x увеличение
            pd_at_origination=Decimal('0.05'),
        )
        assert stage == 2

    def test_determine_stage_3(self):
        """Тест определения стадии 3 (дефолт)"""
        stage, _ = self.calc.determine_stage(
            days_past_due=100,  # >90 дней
            pd_current=Decimal('0.10'),
            pd_at_origination=Decimal('0.05'),
        )
        assert stage == 3

    def test_calculate_pd_base_weighted(self):
        """Тест расчета взвешенной PD"""
        pd_adj, formula = self.calc.calculate_pd_base(
            historical_pd=Decimal('0.05'),
            scenario='weighted'
        )
        # Ожидаемый результат: 0.05 × 1.613 = 0.08065
        assert pd_adj > Decimal('0.08')
        assert pd_adj < Decimal('0.09')

    def test_calculate_pd_bayesian(self):
        """Тест байесовской оценки PD"""
        pd_bayes, formula = self.calc.calculate_pd_bayesian(
            defaults=10,
            exposures=1000,
        )
        # Ожидаемый результат: около 1%
        assert pd_bayes > Decimal('0.005')
        assert pd_bayes < Decimal('0.02')

    def test_calculate_lgd(self):
        """Тест расчета LGD"""
        lgd, formula = self.calc.calculate_lgd(
            base_lgd=Decimal('0.69'),
            collateral_type='unsecured',
        )
        assert lgd > Decimal('0')
        assert lgd <= Decimal('1')

    def test_calculate_ead(self):
        """Тест расчета EAD"""
        ead, formula = self.calc.calculate_ead(
            gross_carrying_amount=Decimal('100000000'),
            undrawn_amount=Decimal('20000000'),
            facility_type='credit_lines',
        )
        # EAD = 100M + 20M × 0.5 = 110M
        assert ead == Decimal('110000000')

    def test_calculate_discount_factor(self):
        """Тест расчета дисконт-фактора"""
        df, formula = self.calc.calculate_discount_factor(
            period=1,
            eir=Decimal('0.19'),
            method='discrete'
        )
        # DF = 1 / (1 + 0.19) ≈ 0.8403
        assert df > Decimal('0.84')
        assert df < Decimal('0.85')

    def test_calculate_ecl_stage_1(self):
        """Тест расчета ECL для стадии 1"""
        result = self.calc.calculate_ecl(
            stage=1,
            gross_carrying_amount=Decimal('500000000'),
            pd_annual=Decimal('0.032'),  # 3.2%
            lgd=Decimal('0.69'),
            eir=Decimal('0.19'),
            remaining_term=3,
            scenario='weighted'
        )
        assert result.ecl_amount > Decimal('0')
        assert result.ecl_amount < Decimal('500000000')
        assert result.stage == 1
        assert result.formula_display is not None
        assert result.justification is not None

    def test_calculate_ecl_stage_2(self):
        """Тест расчета ECL для стадии 2"""
        result = self.calc.calculate_ecl(
            stage=2,
            gross_carrying_amount=Decimal('500000000'),
            pd_annual=Decimal('0.095'),  # 9.5%
            lgd=Decimal('0.69'),
            eir=Decimal('0.19'),
            remaining_term=3,
            scenario='weighted'
        )
        assert result.ecl_amount > Decimal('0')
        assert result.stage == 2
        # ECL стадии 2 должен быть больше стадии 1

    def test_calculate_ecl_portfolio(self):
        """Тест расчета ECL для портфеля"""
        exposures = [
            {
                'id': '1',
                'name': 'Bond A',
                'gca': Decimal('100000000'),
                'pd_current': Decimal('0.03'),
                'lgd': Decimal('0.69'),
                'eir': Decimal('0.19'),
                'remaining_term': 3,
                'days_past_due': 0,
            },
            {
                'id': '2',
                'name': 'Bond B',
                'gca': Decimal('200000000'),
                'pd_current': Decimal('0.08'),
                'lgd': Decimal('0.69'),
                'eir': Decimal('0.19'),
                'remaining_term': 5,
                'days_past_due': 45,
            },
        ]

        results = self.calc.calculate_ecl_portfolio(exposures)
        assert results['total_ecl'] > Decimal('0')
        assert results['total_gca'] == Decimal('300000000')
        assert len(results['individual_results']) == 2

    def test_check_repo_limit_compliant(self):
        """Тест проверки лимита РЕПО (соблюден)"""
        result = self.calc.check_repo_limit(
            repo_amount=Decimal('3000000000'),  # 3B
            reserves=Decimal('10000000000'),   # 10B (30%)
        )
        assert result['compliant'] is True

    def test_check_repo_limit_violated(self):
        """Тест проверки лимита РЕПО (нарушен)"""
        result = self.calc.check_repo_limit(
            repo_amount=Decimal('5000000000'),  # 5B
            reserves=Decimal('10000000000'),   # 10B (50%)
        )
        # После 01.07.2025 лимит 35%
        assert result['compliant'] is False

    def test_stress_test_ecl(self):
        """Тест стресс-тестирования ECL"""
        results = self.calc.stress_test_ecl(
            base_ecl=Decimal('100000000'),
        )
        assert 'base' in results
        assert 'adverse' in results
        assert 'severe' in results
        assert results['severe']['ecl'] > results['base']['ecl']

    def test_classify_asset_ac(self):
        """Тест классификации актива (AC)"""
        result = self.calc.classify_asset(
            cash_flows=[],
            business_model='hold_to_collect',
            contractual_terms={'prepayment_penalty_excessive': False}
        )
        assert result.category == 'AC'
        assert result.sppi_passed is True

    def test_classify_asset_fvtpl(self):
        """Тест классификации актива (FVTPL)"""
        result = self.calc.classify_asset(
            cash_flows=[],
            business_model='trading',
            contractual_terms={}
        )
        assert result.category == 'FVTPL'

    def test_precision(self):
        """Тест точности расчетов (0.001 KZT)"""
        result = self.calc.calculate_ecl(
            stage=1,
            gross_carrying_amount=Decimal('500000000.123'),
            pd_annual=Decimal('0.0321'),
            lgd=Decimal('0.691'),
            eir=Decimal('0.191'),
            remaining_term=3,
        )
        # Проверяем, что результат округлен до 3 знаков
        assert str(result.ecl_amount).find('.') != -1
        decimal_places = len(str(result.ecl_amount).split('.')[1])
        assert decimal_places <= 3

    def test_audit_log(self):
        """Тест аудиторского следа"""
        _ = self.calc.calculate_ecl(
            stage=1,
            gross_carrying_amount=Decimal('100000000'),
            pd_annual=Decimal('0.05'),
            lgd=Decimal('0.69'),
            eir=Decimal('0.19'),
            remaining_term=1,
        )
        audit_log = self.calc.get_audit_log()
        assert len(audit_log) > 0
        assert 'operation' in audit_log[-1]


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
