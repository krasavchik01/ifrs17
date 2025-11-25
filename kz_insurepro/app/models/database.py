# -*- coding: utf-8 -*-
"""
KZ-InsurePro - Модели базы данных
SQLAlchemy модели для хранения данных страховщиков и расчетов
"""

from datetime import datetime
from decimal import Decimal
from app import db


class Insurer(db.Model):
    """Страховая компания"""
    __tablename__ = 'insurers'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    bin = db.Column(db.String(12), unique=True)  # БИН
    license_number = db.Column(db.String(50))
    license_date = db.Column(db.Date)
    insurer_type = db.Column(db.String(50))  # life, non_life, composite, reinsurance
    years_in_market = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    financial_data = db.relationship('FinancialData', backref='insurer', lazy=True)
    ecl_calculations = db.relationship('ECLCalculation', backref='insurer', lazy=True)
    ifrs17_calculations = db.relationship('IFRS17Calculation', backref='insurer', lazy=True)
    solvency_calculations = db.relationship('SolvencyCalculation', backref='insurer', lazy=True)

    def __repr__(self):
        return f'<Insurer {self.name}>'


class FinancialData(db.Model):
    """Финансовые данные страховщика"""
    __tablename__ = 'financial_data'

    id = db.Column(db.Integer, primary_key=True)
    insurer_id = db.Column(db.Integer, db.ForeignKey('insurers.id'), nullable=False)
    report_date = db.Column(db.Date, nullable=False)

    # Баланс
    total_assets = db.Column(db.Numeric(20, 3))
    equity_capital = db.Column(db.Numeric(20, 3))
    technical_reserves = db.Column(db.Numeric(20, 3))
    subordinated_debt = db.Column(db.Numeric(20, 3))
    illiquid_assets = db.Column(db.Numeric(20, 3))
    intangible_assets = db.Column(db.Numeric(20, 3))

    # Премии и убытки
    gross_premiums = db.Column(db.Numeric(20, 3))
    net_premiums = db.Column(db.Numeric(20, 3))
    incurred_claims = db.Column(db.Numeric(20, 3))
    paid_claims = db.Column(db.Numeric(20, 3))

    # Резервы МСФО 17
    bel = db.Column(db.Numeric(20, 3))
    ra = db.Column(db.Numeric(20, 3))
    csm = db.Column(db.Numeric(20, 3))
    lrc = db.Column(db.Numeric(20, 3))  # Liability for Remaining Coverage
    lic = db.Column(db.Numeric(20, 3))  # Liability for Incurred Claims

    # Life специфика
    annuity_reserves = db.Column(db.Numeric(20, 3))
    math_reserves = db.Column(db.Numeric(20, 3))

    # Коэффициенты
    loss_ratio = db.Column(db.Numeric(10, 4))
    expense_ratio = db.Column(db.Numeric(10, 4))
    combined_ratio = db.Column(db.Numeric(10, 4))

    # РЕПО
    repo_amount = db.Column(db.Numeric(20, 3))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<FinancialData {self.insurer_id} @ {self.report_date}>'


class Portfolio(db.Model):
    """Портфель финансовых инструментов для МСФО 9"""
    __tablename__ = 'portfolios'

    id = db.Column(db.Integer, primary_key=True)
    insurer_id = db.Column(db.Integer, db.ForeignKey('insurers.id'), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    portfolio_type = db.Column(db.String(50))  # bonds, loans, deposits, etc.

    # Relationships
    exposures = db.relationship('Exposure', backref='portfolio', lazy=True)

    def __repr__(self):
        return f'<Portfolio {self.name}>'


class Exposure(db.Model):
    """Экспозиция (отдельный финансовый инструмент)"""
    __tablename__ = 'exposures'

    id = db.Column(db.Integer, primary_key=True)
    portfolio_id = db.Column(db.Integer, db.ForeignKey('portfolios.id'), nullable=False)
    instrument_id = db.Column(db.String(50))  # Внутренний ID инструмента
    instrument_name = db.Column(db.String(255))
    instrument_type = db.Column(db.String(50))  # bond, loan, deposit, etc.

    # Классификация МСФО 9
    classification = db.Column(db.String(20))  # AC, FVOCI, FVTPL
    business_model = db.Column(db.String(50))

    # Параметры
    gross_carrying_amount = db.Column(db.Numeric(20, 3))
    fair_value = db.Column(db.Numeric(20, 3))
    eir = db.Column(db.Numeric(10, 6))  # Эффективная процентная ставка
    remaining_term = db.Column(db.Integer)  # В месяцах
    origination_date = db.Column(db.Date)
    maturity_date = db.Column(db.Date)

    # Обеспечение
    collateral_type = db.Column(db.String(50))
    collateral_value = db.Column(db.Numeric(20, 3))

    # Кредитный риск
    days_past_due = db.Column(db.Integer, default=0)
    pd_at_origination = db.Column(db.Numeric(10, 6))
    pd_current = db.Column(db.Numeric(10, 6))
    lgd = db.Column(db.Numeric(10, 6))
    stage = db.Column(db.Integer)  # 1, 2, 3

    # Внебалансовые
    undrawn_amount = db.Column(db.Numeric(20, 3))
    facility_type = db.Column(db.String(50))

    # ECL
    ecl_amount = db.Column(db.Numeric(20, 3))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Exposure {self.instrument_name}>'


class InsuranceContract(db.Model):
    """Договор страхования для МСФО 17"""
    __tablename__ = 'insurance_contracts'

    id = db.Column(db.Integer, primary_key=True)
    insurer_id = db.Column(db.Integer, db.ForeignKey('insurers.id'), nullable=False)
    contract_number = db.Column(db.String(50))
    product_type = db.Column(db.String(100))  # life, non_life, osago, kazko, etc.

    # Группировка
    portfolio_name = db.Column(db.String(100))
    cohort_year = db.Column(db.Integer)
    profitability_group = db.Column(db.String(50))  # onerous, remaining, etc.

    # Модель измерения
    measurement_model = db.Column(db.String(10))  # GMM, VFA, PAA

    # Параметры
    inception_date = db.Column(db.Date)
    coverage_period = db.Column(db.Integer)  # В месяцах
    premium_amount = db.Column(db.Numeric(20, 3))
    sum_insured = db.Column(db.Numeric(20, 3))

    # МСФО 17 компоненты
    bel = db.Column(db.Numeric(20, 3))
    ra = db.Column(db.Numeric(20, 3))
    csm = db.Column(db.Numeric(20, 3))
    is_onerous = db.Column(db.Boolean, default=False)
    loss_component = db.Column(db.Numeric(20, 3))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<InsuranceContract {self.contract_number}>'


class ECLCalculation(db.Model):
    """Результаты расчета ECL"""
    __tablename__ = 'ecl_calculations'

    id = db.Column(db.Integer, primary_key=True)
    insurer_id = db.Column(db.Integer, db.ForeignKey('insurers.id'), nullable=False)
    calculation_date = db.Column(db.DateTime, default=datetime.utcnow)
    scenario = db.Column(db.String(50))  # base, adverse, severe, weighted

    # Результаты по стадиям
    stage_1_ecl = db.Column(db.Numeric(20, 3))
    stage_2_ecl = db.Column(db.Numeric(20, 3))
    stage_3_ecl = db.Column(db.Numeric(20, 3))
    total_ecl = db.Column(db.Numeric(20, 3))

    # Покрытие
    total_gca = db.Column(db.Numeric(20, 3))
    coverage_ratio = db.Column(db.Numeric(10, 6))

    # Аудит
    justification = db.Column(db.Text)
    formula_log = db.Column(db.Text)

    def __repr__(self):
        return f'<ECLCalculation {self.id} @ {self.calculation_date}>'


class IFRS17Calculation(db.Model):
    """Результаты расчета по МСФО 17"""
    __tablename__ = 'ifrs17_calculations'

    id = db.Column(db.Integer, primary_key=True)
    insurer_id = db.Column(db.Integer, db.ForeignKey('insurers.id'), nullable=False)
    calculation_date = db.Column(db.DateTime, default=datetime.utcnow)
    measurement_model = db.Column(db.String(10))  # GMM, VFA, PAA

    # Компоненты
    total_bel = db.Column(db.Numeric(20, 3))
    total_ra = db.Column(db.Numeric(20, 3))
    total_csm = db.Column(db.Numeric(20, 3))
    total_fcf = db.Column(db.Numeric(20, 3))
    total_liability = db.Column(db.Numeric(20, 3))

    # Обременительные
    onerous_contracts_count = db.Column(db.Integer)
    total_loss_component = db.Column(db.Numeric(20, 3))

    # Аудит
    justification = db.Column(db.Text)
    formula_log = db.Column(db.Text)

    def __repr__(self):
        return f'<IFRS17Calculation {self.id} @ {self.calculation_date}>'


class SolvencyCalculation(db.Model):
    """Результаты расчета платежеспособности"""
    __tablename__ = 'solvency_calculations'

    id = db.Column(db.Integer, primary_key=True)
    insurer_id = db.Column(db.Integer, db.ForeignKey('insurers.id'), nullable=False)
    calculation_date = db.Column(db.DateTime, default=datetime.utcnow)

    # MMP
    mmp_by_premiums = db.Column(db.Numeric(20, 3))
    mmp_by_claims = db.Column(db.Numeric(20, 3))
    total_mmp = db.Column(db.Numeric(20, 3))
    k_coefficient = db.Column(db.Numeric(10, 4))

    # FMP
    fmp_before_adjustments = db.Column(db.Numeric(20, 3))
    ecl_adjustment = db.Column(db.Numeric(20, 3))
    csm_adjustment = db.Column(db.Numeric(20, 3))
    total_fmp = db.Column(db.Numeric(20, 3))

    # Ratio
    solvency_ratio = db.Column(db.Numeric(10, 4))
    is_compliant = db.Column(db.Boolean)

    # Стресс-тест
    stressed_ratio_adverse = db.Column(db.Numeric(10, 4))
    stressed_ratio_severe = db.Column(db.Numeric(10, 4))
    var_99_5 = db.Column(db.Numeric(10, 4))

    # Аудит
    justification = db.Column(db.Text)
    formula_log = db.Column(db.Text)

    def __repr__(self):
        return f'<SolvencyCalculation {self.id} @ {self.calculation_date}>'


class FGSVContribution(db.Model):
    """Взносы в ФГСВ"""
    __tablename__ = 'fgsv_contributions'

    id = db.Column(db.Integer, primary_key=True)
    insurer_id = db.Column(db.Integer, db.ForeignKey('insurers.id'), nullable=False)
    period_start = db.Column(db.Date, nullable=False)
    period_end = db.Column(db.Date, nullable=False)

    # Расчет
    premium_base = db.Column(db.Numeric(20, 3))
    risk_class = db.Column(db.String(20))
    rate = db.Column(db.Numeric(10, 6))
    contribution_amount = db.Column(db.Numeric(20, 3))

    # Статус
    is_paid = db.Column(db.Boolean, default=False)
    payment_date = db.Column(db.Date)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<FGSVContribution {self.insurer_id} {self.period_start}-{self.period_end}>'


class AuditLog(db.Model):
    """Аудиторский след"""
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.String(50))  # Для демо - пустой
    operation = db.Column(db.String(100))
    module = db.Column(db.String(50))  # ifrs9, ifrs17, solvency, fgsv
    insurer_id = db.Column(db.Integer)

    # Детали
    input_parameters = db.Column(db.Text)  # JSON
    output_summary = db.Column(db.Text)  # JSON
    formula_display = db.Column(db.Text)
    justification = db.Column(db.Text)
    reference = db.Column(db.String(255))

    def __repr__(self):
        return f'<AuditLog {self.operation} @ {self.timestamp}>'


class Report(db.Model):
    """Сгенерированные отчеты"""
    __tablename__ = 'reports'

    id = db.Column(db.Integer, primary_key=True)
    insurer_id = db.Column(db.Integer, db.ForeignKey('insurers.id'))
    report_type = db.Column(db.String(50))  # ecl, ifrs17, solvency, fgsv, xbrl
    report_date = db.Column(db.Date)
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Файл
    file_name = db.Column(db.String(255))
    file_path = db.Column(db.String(500))
    file_format = db.Column(db.String(20))  # pdf, xlsx, xml

    # Метаданные
    parameters = db.Column(db.Text)  # JSON
    watermark = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f'<Report {self.report_type} {self.report_date}>'
