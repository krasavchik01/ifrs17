# -*- coding: utf-8 -*-
"""
Alliot - Модели данных
Enterprise-система для МСФО 17, МСФО 9, Платежеспособности
Включает: Cohort Grouping, Batch Processing, Accounting Engine
"""

from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import Enum
import enum

from app import db


# =============================================================================
# ENUMS
# =============================================================================

class InsuranceType(enum.Enum):
    LIFE = 'life'
    NON_LIFE = 'non_life'
    HEALTH = 'health'
    ANNUITY = 'annuity'


class MeasurementModel(enum.Enum):
    GMM = 'gmm'  # General Measurement Model
    VFA = 'vfa'  # Variable Fee Approach
    PAA = 'paa'  # Premium Allocation Approach


class ContractStatus(enum.Enum):
    ACTIVE = 'active'
    EXPIRED = 'expired'
    CANCELLED = 'cancelled'
    CLAIMED = 'claimed'


class InstrumentType(enum.Enum):
    BOND = 'bond'
    DEPOSIT = 'deposit'
    LOAN = 'loan'
    EQUITY = 'equity'
    DERIVATIVE = 'derivative'
    REAL_ESTATE = 'real_estate'


class InstrumentClassification(enum.Enum):
    AC = 'ac'        # Amortized Cost
    FVOCI = 'fvoci'  # Fair Value through OCI
    FVTPL = 'fvtpl'  # Fair Value through P&L


class ECLStage(enum.Enum):
    STAGE_1 = 1  # 12-month ECL
    STAGE_2 = 2  # Lifetime ECL (SICR)
    STAGE_3 = 3  # Credit-impaired


class ProfitabilityGroup(enum.Enum):
    """Группы прибыльности для МСФО 17"""
    ONEROUS = 'onerous'  # Убыточные при признании
    NO_SIGNIFICANT_LOSS = 'no_significant_loss'  # Нет значительного риска убытка
    PROFITABLE = 'profitable'  # Прибыльные


class ContractType(enum.Enum):
    """Тип договора: прямой или перестрахование"""
    DIRECT = 'direct'  # Прямой договор
    REINSURANCE_HELD = 'reinsurance_held'  # Входящее перестрахование
    REINSURANCE_ISSUED = 'reinsurance_issued'  # Исходящее перестрахование


class CalculationRunStatus(enum.Enum):
    """Статус пакетного расчета"""
    PENDING = 'pending'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'
    PARTIAL = 'partial'  # Частично завершен с ошибками


class AccountingEventType(enum.Enum):
    """Типы бухгалтерских событий"""
    INITIAL_RECOGNITION = 'initial_recognition'
    PREMIUM_RECEIVED = 'premium_received'
    UNWINDING_DISCOUNT = 'unwinding_discount'
    CSM_RELEASE = 'csm_release'
    CLAIMS_INCURRED = 'claims_incurred'
    CLAIMS_PAID = 'claims_paid'
    EXPENSES_INCURRED = 'expenses_incurred'
    RA_ADJUSTMENT = 'ra_adjustment'
    LOSS_REVERSAL = 'loss_reversal'
    ECL_PROVISION = 'ecl_provision'
    ECL_WRITEOFF = 'ecl_writeoff'
    ECL_RECOVERY = 'ecl_recovery'


# =============================================================================
# МСФО 17 - РЕЕСТР ДОГОВОРОВ СТРАХОВАНИЯ
# =============================================================================

class InsuranceContract(db.Model):
    """Договор страхования для расчета по МСФО 17"""
    __tablename__ = 'insurance_contracts'

    id = db.Column(db.Integer, primary_key=True)

    # Идентификация
    contract_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    policyholder_name = db.Column(db.String(200), nullable=False)
    policyholder_bin = db.Column(db.String(12))

    # Классификация
    insurance_type = db.Column(db.Enum(InsuranceType), nullable=False)
    contract_type = db.Column(db.Enum(ContractType), nullable=False, default=ContractType.DIRECT)
    product_name = db.Column(db.String(100))
    measurement_model = db.Column(db.Enum(MeasurementModel), nullable=False, default=MeasurementModel.GMM)

    # Перестрахование (если contract_type = REINSURANCE_*)
    reinsurer_name = db.Column(db.String(200))  # Перестраховщик
    reinsurance_treaty_id = db.Column(db.String(50))  # ID договора перестрахования
    ceded_percentage = db.Column(db.Numeric(5, 4))  # % переданного риска (0-1)

    # Даты
    inception_date = db.Column(db.Date, nullable=False)
    expiry_date = db.Column(db.Date, nullable=False)
    cohort_year = db.Column(db.Integer, nullable=False)  # Год когорты для группировки

    # Суммы (в KZT)
    sum_insured = db.Column(db.Numeric(20, 2), nullable=False)
    premium_amount = db.Column(db.Numeric(20, 2), nullable=False)
    acquisition_costs = db.Column(db.Numeric(20, 2), default=0)

    # Расчетные параметры
    expected_claims = db.Column(db.Numeric(20, 2))
    expected_expenses = db.Column(db.Numeric(20, 2))
    discount_rate = db.Column(db.Numeric(10, 6))
    lapse_rate = db.Column(db.Numeric(10, 6))

    # Результаты расчета МСФО 17
    bel_amount = db.Column(db.Numeric(20, 2))
    ra_amount = db.Column(db.Numeric(20, 2))
    csm_amount = db.Column(db.Numeric(20, 2))
    loss_component = db.Column(db.Numeric(20, 2), default=0)
    is_onerous = db.Column(db.Boolean, default=False)

    # Статус
    status = db.Column(db.Enum(ContractStatus), default=ContractStatus.ACTIVE)

    # Метаданные
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    calculated_at = db.Column(db.DateTime)

    # Группировка
    group_id = db.Column(db.Integer, db.ForeignKey('contract_groups.id'))

    def __repr__(self):
        return f'<InsuranceContract {self.contract_number}>'

    @property
    def fcf(self):
        """Fulfillment Cash Flows = BEL + RA"""
        if self.bel_amount and self.ra_amount:
            return self.bel_amount + self.ra_amount
        return None

    @property
    def total_liability(self):
        """Общее обязательство = FCF + CSM или Loss Component"""
        if self.fcf:
            if self.is_onerous:
                return self.fcf + (self.loss_component or 0)
            return self.fcf + (self.csm_amount or 0)
        return None

    @property
    def coverage_units_remaining(self):
        """Оставшиеся единицы покрытия (для амортизации CSM)"""
        if self.expiry_date and self.inception_date:
            total_days = (self.expiry_date - self.inception_date).days
            elapsed_days = (date.today() - self.inception_date).days
            remaining = max(0, total_days - elapsed_days)
            return remaining / total_days if total_days > 0 else 0
        return 0


class ContractGroup(db.Model):
    """
    Группа договоров для МСФО 17 (Unit of Account)

    КРИТИЧНО: МСФО 17 запрещает агрегацию договоров разных лет!
    Группировка по 3 признакам:
    1. Портфель (Insurance Type) - схожие риски
    2. Когорта (Cohort Year) - год выпуска
    3. Группа прибыльности (Profitability) - onerous/profitable/no_significant_loss
    """
    __tablename__ = 'contract_groups'

    id = db.Column(db.Integer, primary_key=True)

    # Уникальный идентификатор группы (например: "LIFE_2025_PROFITABLE")
    group_code = db.Column(db.String(100), unique=True, nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)

    # === КРИТЕРИИ ГРУППИРОВКИ (IFRS 17 Level of Aggregation) ===

    # 1. Портфель (Portfolio)
    insurance_type = db.Column(db.Enum(InsuranceType), nullable=False)
    product_name = db.Column(db.String(100))  # Дополнительная детализация

    # 2. Когорта (Annual Cohort)
    cohort_year = db.Column(db.Integer, nullable=False, index=True)

    # 3. Группа прибыльности (Profitability Group)
    profitability_group = db.Column(db.Enum(ProfitabilityGroup), nullable=False)

    # Модель оценки
    measurement_model = db.Column(db.Enum(MeasurementModel), nullable=False)

    # Тип договоров (прямые/перестрахование)
    contract_type = db.Column(db.Enum(ContractType), nullable=False, default=ContractType.DIRECT)

    # === АГРЕГИРОВАННЫЕ РЕЗУЛЬТАТЫ (GROUP LEVEL) ===

    # Счетчики
    total_contracts = db.Column(db.Integer, default=0)
    active_contracts = db.Column(db.Integer, default=0)

    # Суммы
    total_premium = db.Column(db.Numeric(20, 2), default=0)
    total_sum_insured = db.Column(db.Numeric(20, 2), default=0)

    # МСФО 17 компоненты (на уровне группы!)
    total_bel = db.Column(db.Numeric(20, 2), default=0)
    total_ra = db.Column(db.Numeric(20, 2), default=0)
    total_csm = db.Column(db.Numeric(20, 2), default=0)
    total_loss_component = db.Column(db.Numeric(20, 2), default=0)
    total_fcf = db.Column(db.Numeric(20, 2), default=0)  # FCF = BEL + RA
    total_liability = db.Column(db.Numeric(20, 2), default=0)  # Общее обязательство

    # Средневзвешенные параметры
    weighted_avg_discount_rate = db.Column(db.Numeric(10, 6))
    weighted_avg_lapse_rate = db.Column(db.Numeric(10, 6))

    # Coverage Units (для Release CSM)
    total_coverage_units_initial = db.Column(db.Numeric(20, 2))
    total_coverage_units_remaining = db.Column(db.Numeric(20, 2))

    # === СВЯЗИ ===
    contracts = db.relationship('InsuranceContract', backref='group', lazy='dynamic')

    # === МЕТАДАННЫЕ ===
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_calculated_at = db.Column(db.DateTime)

    def __repr__(self):
        return f'<ContractGroup {self.group_code}>'

    @property
    def is_onerous(self):
        """Группа обременительная если CSM = 0 и есть Loss Component"""
        return self.profitability_group == ProfitabilityGroup.ONEROUS or \
               (self.total_csm == 0 and self.total_loss_component > 0)

    @property
    def csm_coverage_ratio(self):
        """Коэффициент покрытия CSM = Remaining / Initial coverage units"""
        if self.total_coverage_units_initial and self.total_coverage_units_initial > 0:
            return float(self.total_coverage_units_remaining / self.total_coverage_units_initial)
        return 0


# =============================================================================
# МСФО 9 - РЕЕСТР ФИНАНСОВЫХ ИНСТРУМЕНТОВ
# =============================================================================

class FinancialInstrument(db.Model):
    """Финансовый инструмент для расчета ECL по МСФО 9"""
    __tablename__ = 'financial_instruments'

    id = db.Column(db.Integer, primary_key=True)

    # Идентификация
    instrument_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    instrument_name = db.Column(db.String(200), nullable=False)
    issuer_name = db.Column(db.String(200))
    issuer_bin = db.Column(db.String(12))
    isin = db.Column(db.String(12))  # ISIN код

    # Классификация
    instrument_type = db.Column(db.Enum(InstrumentType), nullable=False)
    classification = db.Column(db.Enum(InstrumentClassification), nullable=False)

    # Даты
    acquisition_date = db.Column(db.Date, nullable=False)
    maturity_date = db.Column(db.Date)

    # Суммы (в KZT)
    nominal_value = db.Column(db.Numeric(20, 2), nullable=False)  # Номинал / Основная сумма
    acquisition_cost = db.Column(db.Numeric(20, 2), nullable=False)  # Стоимость приобретения
    amortized_cost = db.Column(db.Numeric(20, 2))  # Амортизированная стоимость
    fair_value = db.Column(db.Numeric(20, 2))  # Справедливая стоимость

    # Процентные ставки
    coupon_rate = db.Column(db.Numeric(10, 6))  # Купонная ставка
    effective_rate = db.Column(db.Numeric(10, 6))  # Эффективная ставка

    # Обеспечение
    collateral_type = db.Column(db.String(50))  # Тип обеспечения
    collateral_value = db.Column(db.Numeric(20, 2))  # Стоимость обеспечения

    # Параметры ECL
    days_past_due = db.Column(db.Integer, default=0)
    ecl_stage = db.Column(db.Enum(ECLStage), default=ECLStage.STAGE_1)

    # PD параметры
    pd_at_origination = db.Column(db.Numeric(10, 6))  # PD при выдаче
    pd_current = db.Column(db.Numeric(10, 6))  # Текущий PD
    pd_lifetime = db.Column(db.Numeric(10, 6))  # Lifetime PD

    # LGD параметры
    lgd = db.Column(db.Numeric(10, 6))

    # EAD
    ead = db.Column(db.Numeric(20, 2))  # Exposure at Default

    # Результаты расчета ECL
    ecl_12_month = db.Column(db.Numeric(20, 2))  # 12-месячный ECL
    ecl_lifetime = db.Column(db.Numeric(20, 2))  # Lifetime ECL
    ecl_amount = db.Column(db.Numeric(20, 2))  # Признанный ECL

    # Рейтинг
    credit_rating = db.Column(db.String(10))  # S&P/Moody's рейтинг
    internal_rating = db.Column(db.String(10))  # Внутренний рейтинг

    # Метаданные
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    calculated_at = db.Column(db.DateTime)

    # Группировка
    portfolio_id = db.Column(db.Integer, db.ForeignKey('instrument_portfolios.id'))

    def __repr__(self):
        return f'<FinancialInstrument {self.instrument_id}>'

    @property
    def carrying_amount(self):
        """Балансовая стоимость = Амортизированная стоимость - ECL"""
        if self.amortized_cost and self.ecl_amount:
            return self.amortized_cost - self.ecl_amount
        return self.amortized_cost

    @property
    def coverage_ratio(self):
        """Коэффициент покрытия ECL = ECL / EAD"""
        if self.ecl_amount and self.ead and self.ead > 0:
            return float(self.ecl_amount / self.ead)
        return 0


class InstrumentPortfolio(db.Model):
    """Портфель финансовых инструментов"""
    __tablename__ = 'instrument_portfolios'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

    # Тип портфеля
    instrument_type = db.Column(db.Enum(InstrumentType))
    classification = db.Column(db.Enum(InstrumentClassification))

    # Агрегированные результаты
    total_instruments = db.Column(db.Integer, default=0)
    total_nominal = db.Column(db.Numeric(20, 2), default=0)
    total_ead = db.Column(db.Numeric(20, 2), default=0)
    total_ecl = db.Column(db.Numeric(20, 2), default=0)

    # По стадиям
    stage_1_count = db.Column(db.Integer, default=0)
    stage_1_ead = db.Column(db.Numeric(20, 2), default=0)
    stage_1_ecl = db.Column(db.Numeric(20, 2), default=0)

    stage_2_count = db.Column(db.Integer, default=0)
    stage_2_ead = db.Column(db.Numeric(20, 2), default=0)
    stage_2_ecl = db.Column(db.Numeric(20, 2), default=0)

    stage_3_count = db.Column(db.Integer, default=0)
    stage_3_ead = db.Column(db.Numeric(20, 2), default=0)
    stage_3_ecl = db.Column(db.Numeric(20, 2), default=0)

    # Связи
    instruments = db.relationship('FinancialInstrument', backref='portfolio', lazy='dynamic')

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def weighted_avg_pd(self):
        """Средневзвешенный PD по портфелю"""
        total_weighted = sum(
            float(i.pd_current or 0) * float(i.ead or 0)
            for i in self.instruments
        )
        total_ead = sum(float(i.ead or 0) for i in self.instruments)
        return total_weighted / total_ead if total_ead > 0 else 0

    @property
    def coverage_ratio(self):
        """Коэффициент покрытия портфеля = Total ECL / Total EAD"""
        if self.total_ecl and self.total_ead and self.total_ead > 0:
            return float(self.total_ecl / self.total_ead)
        return 0


# =============================================================================
# ИСТОРИЯ МИГРАЦИИ СТАДИЙ ECL
# =============================================================================

class StageTransition(db.Model):
    """История переходов между стадиями ECL"""
    __tablename__ = 'stage_transitions'

    id = db.Column(db.Integer, primary_key=True)
    instrument_id = db.Column(db.Integer, db.ForeignKey('financial_instruments.id'), nullable=False)

    transition_date = db.Column(db.Date, nullable=False)
    from_stage = db.Column(db.Enum(ECLStage))
    to_stage = db.Column(db.Enum(ECLStage), nullable=False)

    # Причина перехода
    reason = db.Column(db.String(200))
    days_past_due = db.Column(db.Integer)
    pd_change = db.Column(db.Numeric(10, 6))

    # ECL до и после
    ecl_before = db.Column(db.Numeric(20, 2))
    ecl_after = db.Column(db.Numeric(20, 2))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# =============================================================================
# ЗАГРУЗКА ДАННЫХ
# =============================================================================

class DataUpload(db.Model):
    """Журнал загрузок данных"""
    __tablename__ = 'data_uploads'

    id = db.Column(db.Integer, primary_key=True)

    upload_type = db.Column(db.String(50), nullable=False)  # 'contracts', 'instruments'
    filename = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer)

    # Статистика
    total_rows = db.Column(db.Integer)
    successful_rows = db.Column(db.Integer)
    failed_rows = db.Column(db.Integer)

    # Статус
    status = db.Column(db.String(20), default='pending')  # pending, processing, completed, failed
    error_message = db.Column(db.Text)

    # Метаданные
    uploaded_by = db.Column(db.String(100))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)


# =============================================================================
# ОТЧЕТЫ И РАСКРЫТИЯ
# =============================================================================

class ReportingPeriod(db.Model):
    """Отчетный период"""
    __tablename__ = 'reporting_periods'

    id = db.Column(db.Integer, primary_key=True)

    period_name = db.Column(db.String(50), nullable=False)  # 'Q1 2025', '2024'
    period_type = db.Column(db.String(20), nullable=False)  # 'quarterly', 'annual'
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)

    # МСФО 17 агрегаты
    ifrs17_total_liability = db.Column(db.Numeric(20, 2))
    ifrs17_total_bel = db.Column(db.Numeric(20, 2))
    ifrs17_total_ra = db.Column(db.Numeric(20, 2))
    ifrs17_total_csm = db.Column(db.Numeric(20, 2))
    ifrs17_insurance_revenue = db.Column(db.Numeric(20, 2))
    ifrs17_insurance_expense = db.Column(db.Numeric(20, 2))

    # МСФО 9 агрегаты
    ifrs9_total_ecl = db.Column(db.Numeric(20, 2))
    ifrs9_stage_1_ecl = db.Column(db.Numeric(20, 2))
    ifrs9_stage_2_ecl = db.Column(db.Numeric(20, 2))
    ifrs9_stage_3_ecl = db.Column(db.Numeric(20, 2))

    # Платежеспособность
    solvency_fmp = db.Column(db.Numeric(20, 2))
    solvency_mmp = db.Column(db.Numeric(20, 2))
    solvency_ratio = db.Column(db.Numeric(10, 4))

    is_final = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# =============================================================================
# BATCH PROCESSING - ПАКЕТНЫЕ РАСЧЕТЫ
# =============================================================================

class CalculationRun(db.Model):
    """
    Пакетный расчет (Calculation Job)

    КРИТИЧНО: В production системе пользователь не нажимает "Рассчитать"
    для каждого договора. Он запускает JOB, который обрабатывает
    весь портфель (100K+ договоров) асинхронно.
    """
    __tablename__ = 'calculation_runs'

    id = db.Column(db.Integer, primary_key=True)

    # === ПАРАМЕТРЫ ЗАПУСКА ===
    run_code = db.Column(db.String(50), unique=True, nullable=False, index=True)  # "RUN_2025Q1_001"
    run_name = db.Column(db.String(200), nullable=False)

    # Тип расчета
    calculation_type = db.Column(db.String(50), nullable=False)  # 'ifrs17', 'ifrs9', 'solvency', 'all'

    # Дата отчета (Reporting Date) - критично для Point-in-Time
    reporting_date = db.Column(db.Date, nullable=False, index=True)

    # Фильтры портфеля
    insurance_type_filter = db.Column(db.String(50))  # 'life', 'non_life', 'all'
    contract_type_filter = db.Column(db.String(50))  # 'direct', 'reinsurance', 'all'

    # === СТАТУС И ПРОГРЕСС ===
    status = db.Column(db.Enum(CalculationRunStatus), nullable=False, default=CalculationRunStatus.PENDING)

    # Прогресс (для UI progress bar)
    total_items = db.Column(db.Integer, default=0)  # Всего к обработке
    processed_items = db.Column(db.Integer, default=0)  # Обработано
    successful_items = db.Column(db.Integer, default=0)  # Успешно
    failed_items = db.Column(db.Integer, default=0)  # С ошибками

    progress_percentage = db.Column(db.Numeric(5, 2), default=0)  # 0-100%

    # === РЕЗУЛЬТАТЫ ===

    # МСФО 17
    ifrs17_groups_calculated = db.Column(db.Integer, default=0)
    ifrs17_total_liability = db.Column(db.Numeric(20, 2))
    ifrs17_total_csm = db.Column(db.Numeric(20, 2))

    # МСФО 9
    ifrs9_instruments_calculated = db.Column(db.Integer, default=0)
    ifrs9_total_ecl = db.Column(db.Numeric(20, 2))

    # Платежеспособность
    solvency_ratio = db.Column(db.Numeric(10, 4))
    solvency_fmp = db.Column(db.Numeric(20, 2))
    solvency_mmp = db.Column(db.Numeric(20, 2))

    # === ПРОИЗВОДИТЕЛЬНОСТЬ ===
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    duration_seconds = db.Column(db.Integer)  # Длительность в секундах

    # === ЛОГИ И ОШИБКИ ===
    error_log = db.Column(db.Text)  # Лог ошибок
    warning_count = db.Column(db.Integer, default=0)

    # === СВЯЗИ ===
    # Связь с результатами расчетов (one-to-many)
    # group_results backref from GroupCalculationResult
    # journal_entries backref from JournalEntry

    # === МЕТАДАННЫЕ ===
    created_by = db.Column(db.String(100))  # Пользователь запустивший
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<CalculationRun {self.run_code}>'

    @property
    def is_running(self):
        return self.status == CalculationRunStatus.RUNNING

    @property
    def is_completed(self):
        return self.status == CalculationRunStatus.COMPLETED


class GroupCalculationResult(db.Model):
    """
    Результаты расчета для группы договоров (снапшот)

    КРИТИЧНО: Результаты хранятся отдельно от самой группы!
    Это позволяет сравнивать результаты разных периодов.
    """
    __tablename__ = 'group_calculation_results'

    id = db.Column(db.Integer, primary_key=True)

    # Связи
    calculation_run_id = db.Column(db.Integer, db.ForeignKey('calculation_runs.id'), nullable=False)
    contract_group_id = db.Column(db.Integer, db.ForeignKey('contract_groups.id'), nullable=False)

    # Дата расчета (Point-in-Time)
    calculation_date = db.Column(db.Date, nullable=False, index=True)

    # === РЕЗУЛЬТАТЫ НА МОМЕНТ РАСЧЕТА ===

    # Компоненты МСФО 17
    bel_amount = db.Column(db.Numeric(20, 2), nullable=False)
    ra_amount = db.Column(db.Numeric(20, 2), nullable=False)
    csm_amount = db.Column(db.Numeric(20, 2), nullable=False)
    loss_component = db.Column(db.Numeric(20, 2), default=0)
    fcf_amount = db.Column(db.Numeric(20, 2), nullable=False)
    total_liability = db.Column(db.Numeric(20, 2), nullable=False)

    # Счетчики
    contracts_count = db.Column(db.Integer, nullable=False)

    # Средневзвешенные параметры на момент расчета
    avg_discount_rate = db.Column(db.Numeric(10, 6))
    avg_lapse_rate = db.Column(db.Numeric(10, 6))

    # Coverage Units (для CSM release)
    coverage_units_remaining = db.Column(db.Numeric(20, 2))
    coverage_units_consumed = db.Column(db.Numeric(20, 2))

    # === ДВИЖЕНИЕ CSM (CSM Roll-forward) ===
    csm_opening_balance = db.Column(db.Numeric(20, 2))
    csm_new_business = db.Column(db.Numeric(20, 2))
    csm_expected_release = db.Column(db.Numeric(20, 2))
    csm_experience_adjustments = db.Column(db.Numeric(20, 2))
    csm_assumption_changes = db.Column(db.Numeric(20, 2))
    csm_closing_balance = db.Column(db.Numeric(20, 2))

    # === AUDIT TRAIL ===
    calculation_method = db.Column(db.String(50))  # 'gmm', 'vfa', 'paa'
    formula_used = db.Column(db.Text)
    assumptions_snapshot = db.Column(db.JSON)  # Снапшот всех допущений

    # Связи
    calculation_run = db.relationship('CalculationRun', backref='group_results')
    contract_group = db.relationship('ContractGroup', backref='calculation_results')

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<GroupCalculationResult Run:{self.calculation_run_id} Group:{self.contract_group_id}>'


# =============================================================================
# ACCOUNTING ENGINE - ГЕНЕРАТОР ПРОВОДОК
# =============================================================================

class ChartOfAccounts(db.Model):
    """
    План счетов (Chart of Accounts)

    КРИТИЧНО: Каждый клиент использует свой план счетов из 1С/SAP.
    Система должна позволить загрузить их план и настроить маппинг.
    """
    __tablename__ = 'chart_of_accounts'

    id = db.Column(db.Integer, primary_key=True)

    # Счет
    account_code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    account_name = db.Column(db.String(200), nullable=False)
    account_name_en = db.Column(db.String(200))

    # Тип счета
    account_type = db.Column(db.String(50), nullable=False)  # 'asset', 'liability', 'equity', 'revenue', 'expense'
    account_subtype = db.Column(db.String(50))  # 'insurance_liability', 'investment', etc.

    # Классификация для отчетности
    balance_sheet_category = db.Column(db.String(100))  # Категория в балансе
    pnl_category = db.Column(db.String(100))  # Категория в P&L

    # Флаги
    is_active = db.Column(db.Boolean, default=True)
    requires_analytical = db.Column(db.Boolean, default=False)  # Требует аналитики

    # Метаданные
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Account {self.account_code} - {self.account_name}>'


class AccountingRule(db.Model):
    """
    Правила маппинга событий на счета (Accounting Mapping Rules)

    КРИТИЧНО: Это "мозг" Accounting Engine.
    Определяет какие проводки генерировать для каждого события.

    Пример: Если событие = CSM_RELEASE для Life insurance:
        Дт 3310 (Обязательства по страхованию)
        Кт 6010 (Доходы от страхования)
    """
    __tablename__ = 'accounting_rules'

    id = db.Column(db.Integer, primary_key=True)

    # === УСЛОВИЯ ПРИМЕНЕНИЯ ПРАВИЛА ===

    # Тип события
    event_type = db.Column(db.Enum(AccountingEventType), nullable=False, index=True)

    # Фильтры (опционально - если None, применяется ко всем)
    insurance_type = db.Column(db.Enum(InsuranceType))  # Только для конкретного типа
    contract_type = db.Column(db.Enum(ContractType))  # Direct/Reinsurance
    measurement_model = db.Column(db.Enum(MeasurementModel))  # GMM/VFA/PAA

    # Приоритет (если несколько правил подходят)
    priority = db.Column(db.Integer, default=100)

    # === ПРОВОДКИ ===

    # Дебет
    debit_account_code = db.Column(db.String(20), db.ForeignKey('chart_of_accounts.account_code'), nullable=False)
    debit_account_name = db.Column(db.String(200))

    # Кредит
    credit_account_code = db.Column(db.String(20), db.ForeignKey('chart_of_accounts.account_code'), nullable=False)
    credit_account_name = db.Column(db.String(200))

    # Описание
    description = db.Column(db.Text)

    # Активность
    is_active = db.Column(db.Boolean, default=True)

    # Связи
    debit_account = db.relationship('ChartOfAccounts', foreign_keys=[debit_account_code])
    credit_account = db.relationship('ChartOfAccounts', foreign_keys=[credit_account_code])

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<AccountingRule {self.event_type.value}: Дт{self.debit_account_code} Кт{self.credit_account_code}>'


class JournalEntry(db.Model):
    """
    Проводка (Journal Entry / Sub-ledger)

    КРИТИЧНО: Это конечный output Accounting Engine.
    Эта таблица выгружается в 1С/SAP как Журнал проводок.

    Каждый расчет генерирует тысячи проводок.
    """
    __tablename__ = 'journal_entries'

    id = db.Column(db.Integer, primary_key=True)

    # Связь с расчетом
    calculation_run_id = db.Column(db.Integer, db.ForeignKey('calculation_runs.id'), nullable=False, index=True)

    # === ОСНОВНЫЕ ПОЛЯ ПРОВОДКИ ===

    # Номер проводки
    entry_number = db.Column(db.String(50), unique=True, nullable=False, index=True)

    # Дата проводки
    posting_date = db.Column(db.Date, nullable=False, index=True)
    value_date = db.Column(db.Date)  # Дата валютирования

    # Счета
    debit_account = db.Column(db.String(20), db.ForeignKey('chart_of_accounts.account_code'), nullable=False)
    credit_account = db.Column(db.String(20), db.ForeignKey('chart_of_accounts.account_code'), nullable=False)

    # Сумма
    amount = db.Column(db.Numeric(20, 2), nullable=False)
    currency = db.Column(db.String(3), default='KZT')

    # === АНАЛИТИКА (для drill-down) ===

    # Событие, которое создало проводку
    event_type = db.Column(db.Enum(AccountingEventType), nullable=False, index=True)

    # Источник
    source_type = db.Column(db.String(50))  # 'contract_group', 'instrument', 'portfolio'
    source_id = db.Column(db.Integer)  # ID группы/инструмента
    source_reference = db.Column(db.String(100))  # Номер договора/инструмента

    # Группа/Портфель
    contract_group_id = db.Column(db.Integer, db.ForeignKey('contract_groups.id'))
    instrument_portfolio_id = db.Column(db.Integer, db.ForeignKey('instrument_portfolios.id'))

    # === ОПИСАНИЕ ===
    description = db.Column(db.Text, nullable=False)
    narrative = db.Column(db.Text)  # Дополнительные пояснения

    # === AUDIT TRAIL ===
    formula_reference = db.Column(db.Text)  # Формула, которая привела к проводке
    assumptions_used = db.Column(db.JSON)  # Допущения на момент расчета

    # === СТАТУС ===
    is_posted = db.Column(db.Boolean, default=False)  # Проведена в главную книгу?
    is_reversed = db.Column(db.Boolean, default=False)  # Сторнирована?
    reversal_entry_id = db.Column(db.Integer, db.ForeignKey('journal_entries.id'))  # Ссылка на сторно

    # Связи
    calculation_run = db.relationship('CalculationRun', backref='journal_entries')
    contract_group = db.relationship('ContractGroup', backref='journal_entries')
    instrument_portfolio = db.relationship('InstrumentPortfolio', backref='journal_entries')

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<JournalEntry {self.entry_number}: {self.amount} KZT>'


# =============================================================================
# DATA LINEAGE - ПРОСЛЕЖИВАЕМОСТЬ ДАННЫХ
# =============================================================================

class CalculationLog(db.Model):
    """
    Детальный лог расчетов (для drill-down и аудита)

    КРИТИЧНО: Аудитор должен иметь возможность проследить
    любую цифру в отчете до исходного CSV файла.

    Схема: Итоговая цифра → Группа → Договор → Исходный файл → Строка CSV
    """
    __tablename__ = 'calculation_logs'

    id = db.Column(db.Integer, primary_key=True)

    # Связи
    calculation_run_id = db.Column(db.Integer, db.ForeignKey('calculation_runs.id'), nullable=False, index=True)

    # Объект расчета
    entity_type = db.Column(db.String(50), nullable=False)  # 'contract', 'group', 'instrument'
    entity_id = db.Column(db.Integer, nullable=False)
    entity_reference = db.Column(db.String(100))  # Номер договора/инструмента

    # === РАСЧЕТ ===

    # Что считалось
    calculation_type = db.Column(db.String(50), nullable=False)  # 'bel', 'ra', 'csm', 'ecl'

    # Входные данные (snapshot)
    input_data = db.Column(db.JSON, nullable=False)

    # Формула
    formula_display = db.Column(db.Text)
    formula_latex = db.Column(db.Text)

    # Результат
    result_value = db.Column(db.Numeric(20, 2), nullable=False)

    # Обоснование
    justification = db.Column(db.Text)

    # === TRACEABILITY (Data Lineage) ===

    # Исходные данные
    source_file_id = db.Column(db.Integer, db.ForeignKey('data_uploads.id'))
    source_file_name = db.Column(db.String(255))
    source_row_number = db.Column(db.Integer)  # Строка в CSV

    # Предыдущий расчет (если есть)
    previous_calculation_id = db.Column(db.Integer, db.ForeignKey('calculation_logs.id'))

    # Связи
    calculation_run = db.relationship('CalculationRun', backref='calculation_logs')
    source_file = db.relationship('DataUpload', backref='calculation_logs')

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<CalculationLog {self.entity_reference}: {self.calculation_type} = {self.result_value}>'


# =============================================================================
# YIELD CURVE - КРИВАЯ ДОХОДНОСТИ
# =============================================================================

class YieldCurve(db.Model):
    """
    Кривая доходности (Discount Rate Curve)

    КРИТИЧНО: Вместо одной ставки (18%) нужна полная кривая
    по срокам (1Y, 2Y, 3Y... 30Y).

    Используется для дисконтирования денежных потоков МСФО 17.
    """
    __tablename__ = 'yield_curves'

    id = db.Column(db.Integer, primary_key=True)

    # Идентификация кривой
    curve_name = db.Column(db.String(100), nullable=False)  # "KZT_RFR_2025Q1"
    curve_type = db.Column(db.String(50), nullable=False)  # 'risk_free', 'swap', 'corporate'
    currency = db.Column(db.String(3), nullable=False, default='KZT')

    # Дата кривой
    curve_date = db.Column(db.Date, nullable=False, index=True)

    # Источник данных
    source = db.Column(db.String(100))  # 'KASE', 'Bloomberg', 'Manual'

    # Методология построения
    construction_method = db.Column(db.String(50))  # 'bootstrap', 'smith_wilson', 'nelson_siegel'

    # === ТОЧКИ КРИВОЙ (Term Structure) ===
    # Хранятся как JSON массив: [{"term": 1, "rate": 0.10}, {"term": 2, "rate": 0.105}, ...]
    curve_points = db.Column(db.JSON, nullable=False)

    # Параметры экстраполяции
    extrapolation_method = db.Column(db.String(50))  # Для сроков > max term
    ultimate_forward_rate = db.Column(db.Numeric(10, 6))  # UFR для Smith-Wilson

    # Корректировки
    illiquidity_premium = db.Column(db.Numeric(10, 6), default=0)  # Премия за неликвидность
    credit_adjustment = db.Column(db.Numeric(10, 6), default=0)  # Кредитная корректировка

    # Метаданные
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<YieldCurve {self.curve_name} on {self.curve_date}>'

    def get_rate(self, term_years):
        """Получить ставку для конкретного срока (с интерполяцией)"""
        if not self.curve_points:
            return None

        # TODO: Реализовать линейную/кубическую интерполяцию
        points = sorted(self.curve_points, key=lambda x: x['term'])

        # Простая линейная интерполяция
        for i in range(len(points) - 1):
            if points[i]['term'] <= term_years <= points[i+1]['term']:
                t1, r1 = points[i]['term'], points[i]['rate']
                t2, r2 = points[i+1]['term'], points[i+1]['rate']
                # Линейная интерполяция
                rate = r1 + (r2 - r1) * (term_years - t1) / (t2 - t1)
                return Decimal(str(rate))

        # Если срок больше максимального - возвращаем UFR
        if term_years > points[-1]['term'] and self.ultimate_forward_rate:
            return self.ultimate_forward_rate

        # Если срок меньше минимального
        if term_years < points[0]['term']:
            return Decimal(str(points[0]['rate']))

        return Decimal(str(points[-1]['rate']))
