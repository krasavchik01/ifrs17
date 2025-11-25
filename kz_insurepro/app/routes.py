# -*- coding: utf-8 -*-
"""
KZ-InsurePro - Главные маршруты Flask
Система с ролями: АРФР, ФГСВ, Страховые компании
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, session
from decimal import Decimal
from datetime import date, datetime
import json

# ВАЖНО: Используем только calculation_service для всех расчетов!
# Это гарантирует что цифры везде одинаковые
from app.services.calculation_service import calculation_service
from config import (
    APP_CONFIG, DEMO_CONFIG, TRANSLATIONS, MACRO_INDICATORS_2025,
    format_currency, format_percent
)

main_bp = Blueprint('main', __name__)


# =============================================================================
# ВЫБОР РОЛИ
# =============================================================================

@main_bp.route('/landing')
def landing():
    """Landing page - Продающая презентация Alliot"""
    return render_template('landing.html',
                          macro=MACRO_INDICATORS_2025,
                          APP_CONFIG=APP_CONFIG)


@main_bp.route('/select-role', methods=['GET', 'POST'])
def select_role():
    """Страница выбора роли"""
    if request.method == 'POST':
        role = request.form.get('role', 'insurer')
        session['role'] = role

        # Перенаправление на соответствующую панель
        if role == 'arfr':
            return redirect(url_for('main.arfr_dashboard'))
        elif role == 'fgsv':
            return redirect(url_for('main.fgsv_dashboard'))
        else:
            return redirect(url_for('main.index'))

    # Если пришли с landing page с параметром role
    if request.args.get('role'):
        role = request.args.get('role')
        session['role'] = role
        if role == 'arfr':
            return redirect(url_for('main.arfr_dashboard'))
        elif role == 'fgsv':
            return redirect(url_for('main.fgsv_dashboard'))
        else:
            return redirect(url_for('main.index'))

    return render_template('select_role.html',
                          macro=MACRO_INDICATORS_2025,
                          APP_CONFIG=APP_CONFIG)


# =============================================================================
# СТРАХОВАЯ КОМПАНИЯ - МАРШРУТЫ
# =============================================================================

@main_bp.route('/')
def index():
    """Главная страница - Панель управления страховой компании"""
    if not session.get('role'):
        session['role'] = 'insurer'

    return render_template('index.html',
                          macro=MACRO_INDICATORS_2025,
                          APP_CONFIG=APP_CONFIG)


@main_bp.route('/help')
def help_guide():
    """Справка и руководство по использованию системы"""
    return render_template('help_guide.html',
                          macro=MACRO_INDICATORS_2025,
                          APP_CONFIG=APP_CONFIG)


# =============================================================================
# ГЛАВНЫЙ РАСЧЕТ - UNIFIED CALCULATION (ECL + IFRS 17 + Solvency)
# =============================================================================

from app.services.unified_calculation_service import unified_calculation_service

@main_bp.route('/calculation', methods=['GET', 'POST'])
def main_calculation():
    """Главный расчет - единая система ECL, МСФО 17 и платежеспособности"""
    result = None
    error = None

    if request.method == 'POST':
        try:
            # Получение параметров из формы
            gca = Decimal(request.form.get('gca', '500000000'))
            pd = Decimal(request.form.get('pd', '0.095'))
            lgd = Decimal(request.form.get('lgd', '0.69'))
            eir = Decimal(request.form.get('eir', '0.19'))
            term = int(request.form.get('term', '3'))
            dpd = int(request.form.get('dpd', '0'))

            premiums = Decimal(request.form.get('premiums', '100000000'))
            claims = Decimal(request.form.get('claims', '80000000'))
            expenses = Decimal(request.form.get('expenses', '5000000'))
            ac = Decimal(request.form.get('ac', '10000000'))
            contract_term = int(request.form.get('contract_term', '10'))
            ra_method = request.form.get('ra_method', 'coc')

            equity = Decimal(request.form.get('equity', '20000000000'))
            subordinated = Decimal(request.form.get('subordinated', '3000000000'))
            illiquid = Decimal(request.form.get('illiquid', '500000000'))
            k_coef = Decimal(request.form.get('k_coef', '0.70'))
            has_osago = request.form.get('osago') == 'on'

            # Выполняем главный расчет
            calc_result = unified_calculation_service.calculate_everything(
                gross_carrying_amount=gca,
                pd_annual=pd,
                lgd=lgd,
                eir=eir,
                remaining_term=term,
                days_past_due=dpd,
                premiums=premiums,
                claims_per_year=claims,
                expenses_per_year=expenses,
                acquisition_costs=ac,
                contract_term=contract_term,
                ra_method=ra_method,
                equity=equity,
                subordinated=subordinated,
                illiquid=illiquid,
                has_osago=has_osago,
                k_coef=k_coef,
            )

            # Форматируем для шаблона
            result = {
                'calculation_date': calc_result.calculation_date.isoformat(),
                'status': calc_result.status,
                'warnings': calc_result.warnings,
                'ecl': calc_result.ecl,
                'ecl_formatted': calc_result.ecl_formatted,
                'ifrs17': calc_result.ifrs17,
                'ifrs17_formatted': calc_result.ifrs17_formatted,
                'solvency': calc_result.solvency,
                'solvency_formatted': calc_result.solvency_formatted,
            }

        except Exception as e:
            error = f"Ошибка расчета: {str(e)}"

    return render_template('main_calculation.html',
                          result=result,
                          error=error,
                          macro=MACRO_INDICATORS_2025,
                          APP_CONFIG=APP_CONFIG)


@main_bp.route('/fgsv', methods=['GET', 'POST'])
def fgsv():
    """Страница ФГСВ - Взносы (для страховой компании)"""
    result = None
    error = None

    if request.method == 'POST':
        try:
            calc = FGSVCalculator()

            # Получение параметров
            premiums = Decimal(request.form.get('premiums', '5000000000'))
            solvency_ratio = Decimal(request.form.get('solvency', '2.50'))
            loss_ratio = Decimal(request.form.get('loss_ratio', '0.55'))
            combined_ratio = Decimal(request.form.get('combined', '0.85'))

            # Расчет взноса
            contribution_result = calc.calculate_contribution(
                gross_premiums=premiums,
                solvency_ratio=solvency_ratio,
                loss_ratio=loss_ratio,
                combined_ratio=combined_ratio,
            )

            result = {
                'contribution': format_currency(contribution_result.contribution_amount),
                'rate': format_percent(float(contribution_result.rate * 100)),
                'risk_class': {
                    'low_risk': 'Низкий',
                    'medium_risk': 'Средний',
                    'high_risk': 'Высокий'
                }.get(contribution_result.risk_class, contribution_result.risk_class),
                'formula_display': contribution_result.formula_display,
                'justification': contribution_result.justification,
            }

        except Exception as e:
            error = f"Ошибка расчета: {str(e)}"

    return render_template('fgsv.html',
                          result=result,
                          error=error,
                          macro=MACRO_INDICATORS_2025,
                          APP_CONFIG=APP_CONFIG)


@main_bp.route('/reports')
def reports():
    """Расширенная система отчетности"""
    return render_template('reports_advanced.html',
                          macro=MACRO_INDICATORS_2025,
                          APP_CONFIG=APP_CONFIG)


@main_bp.route('/audit')
def audit():
    """Аудиторский след"""
    return render_template('audit.html',
                          macro=MACRO_INDICATORS_2025,
                          APP_CONFIG=APP_CONFIG)


# =============================================================================
# АРФР - МАРШРУТЫ РЕГУЛЯТОРА
# =============================================================================

@main_bp.route('/arfr')
@main_bp.route('/arfr/dashboard')
def arfr_dashboard():
    """Панель надзора АРФР"""
    session['role'] = 'arfr'

    # Демо-данные для панели
    stats = {
        'total_insurers': 27,
        'compliant': 24,
        'warnings': 3,
        'violations': 2,
        'total_assets': '2.8 трлн ₸',
        'total_premiums': '890 млрд ₸',
        'avg_solvency': '2.15',
    }

    return render_template('arfr/dashboard.html',
                          stats=stats,
                          macro=MACRO_INDICATORS_2025,
                          APP_CONFIG=APP_CONFIG)


@main_bp.route('/arfr/insurers')
def arfr_insurers():
    """Список страховых компаний для АРФР"""
    # Демо-данные по страховым компаниям
    insurers = [
        {
            'id': 1, 'name': 'СК КазСтрах', 'bin': '123456789012',
            'type': 'Композитная', 'assets': '50.0 млрд', 'solvency': 2.57,
            'status': 'ok', 'ecl': '2.1 млрд', 'csm': '11.8 млрд'
        },
        {
            'id': 2, 'name': 'СК НурПолис', 'bin': '987654321098',
            'type': 'Non-life', 'assets': '25.0 млрд', 'solvency': 1.35,
            'status': 'warning', 'ecl': '0.8 млрд', 'csm': '0'
        },
        {
            'id': 3, 'name': 'СК Евразия', 'bin': '111222333444',
            'type': 'Life', 'assets': '120.0 млрд', 'solvency': 3.21,
            'status': 'ok', 'ecl': '5.2 млрд', 'csm': '35.4 млрд'
        },
        {
            'id': 4, 'name': 'СК Халык', 'bin': '555666777888',
            'type': 'Композитная', 'assets': '85.0 млрд', 'solvency': 2.89,
            'status': 'ok', 'ecl': '3.8 млрд', 'csm': '22.1 млрд'
        },
        {
            'id': 5, 'name': 'СК Виктория', 'bin': '999000111222',
            'type': 'Non-life', 'assets': '18.0 млрд', 'solvency': 1.12,
            'status': 'danger', 'ecl': '1.5 млрд', 'csm': '0'
        },
    ]

    return render_template('arfr/insurers.html',
                          insurers=insurers,
                          macro=MACRO_INDICATORS_2025,
                          APP_CONFIG=APP_CONFIG)


@main_bp.route('/arfr/reports')
def arfr_reports():
    """Проверка отчетности АРФР"""
    # Демо-данные по отчетам на проверке
    reports = [
        {
            'id': 1, 'insurer': 'СК НурПолис', 'type': 'Квартальный',
            'period': 'Q3 2025', 'submitted': '15.10.2025',
            'status': 'review', 'issues': 2
        },
        {
            'id': 2, 'insurer': 'СК Виктория', 'type': 'Ежемесячный',
            'period': 'Октябрь 2025', 'submitted': '05.11.2025',
            'status': 'issues', 'issues': 5
        },
        {
            'id': 3, 'insurer': 'СК КазСтрах', 'type': 'Квартальный',
            'period': 'Q3 2025', 'submitted': '14.10.2025',
            'status': 'pending', 'issues': 0
        },
    ]

    return render_template('arfr/reports.html',
                          reports=reports,
                          macro=MACRO_INDICATORS_2025,
                          APP_CONFIG=APP_CONFIG)


@main_bp.route('/arfr/violations')
def arfr_violations():
    """Нарушения - АРФР"""
    violations = [
        {
            'id': 1, 'insurer': 'СК Виктория', 'type': 'Nmп < 1.0',
            'description': 'Коэффициент платежеспособности ниже минимума',
            'date': '10.11.2025', 'severity': 'critical',
            'status': 'open', 'deadline': '10.12.2025'
        },
        {
            'id': 2, 'insurer': 'СК НурПолис', 'type': 'ECL',
            'description': 'Недостаточный резерв ECL по портфелю облигаций',
            'date': '08.11.2025', 'severity': 'warning',
            'status': 'in_progress', 'deadline': '08.12.2025'
        },
    ]

    return render_template('arfr/violations.html',
                          violations=violations,
                          macro=MACRO_INDICATORS_2025,
                          APP_CONFIG=APP_CONFIG)


@main_bp.route('/arfr/market')
def arfr_market():
    """Аналитика рынка страхования"""
    market_data = {
        'total_premiums': '890 млрд ₸',
        'yoy_growth': '+12.5%',
        'life_share': '35%',
        'nonlife_share': '65%',
        'osago_premiums': '180 млрд ₸',
        'top_5_share': '68%',
    }

    return render_template('arfr/market.html',
                          market_data=market_data,
                          macro=MACRO_INDICATORS_2025,
                          APP_CONFIG=APP_CONFIG)


@main_bp.route('/arfr/stress')
def arfr_stress():
    """Стресс-тесты рынка - АРФР"""
    return render_template('arfr/stress.html',
                          macro=MACRO_INDICATORS_2025,
                          APP_CONFIG=APP_CONFIG)


# =============================================================================
# ФГСВ - МАРШРУТЫ ФОНДА ГАРАНТИРОВАНИЯ
# =============================================================================

@main_bp.route('/fgsv-panel')
@main_bp.route('/fgsv-panel/dashboard')
def fgsv_dashboard():
    """Панель ФГСВ"""
    session['role'] = 'fgsv'

    stats = {
        'fund_balance': '50 млрд ₸',
        'total_contributions': '8.2 млрд ₸',
        'expected_payouts': '2.1 млрд ₸',
        'adequacy_ratio': '2.38',
        'insurers_monitored': 27,
        'high_risk': 3,
    }

    return render_template('fgsv_panel/dashboard.html',
                          stats=stats,
                          macro=MACRO_INDICATORS_2025,
                          APP_CONFIG=APP_CONFIG)


@main_bp.route('/fgsv-panel/contributions')
def fgsv_contributions():
    """Взносы в ФГСВ"""
    contributions = [
        {
            'insurer': 'СК КазСтрах', 'premiums': '35 млрд ₸',
            'rate': '0.5%', 'amount': '175 млн ₸',
            'risk_class': 'low', 'status': 'paid', 'date': '15.10.2025'
        },
        {
            'insurer': 'СК НурПолис', 'premiums': '12 млрд ₸',
            'rate': '1.0%', 'amount': '120 млн ₸',
            'risk_class': 'medium', 'status': 'paid', 'date': '14.10.2025'
        },
        {
            'insurer': 'СК Виктория', 'premiums': '5 млрд ₸',
            'rate': '2.0%', 'amount': '100 млн ₸',
            'risk_class': 'high', 'status': 'pending', 'date': '-'
        },
    ]

    return render_template('fgsv_panel/contributions.html',
                          contributions=contributions,
                          macro=MACRO_INDICATORS_2025,
                          APP_CONFIG=APP_CONFIG)


@main_bp.route('/fgsv-panel/insurers')
def fgsv_insurers():
    """Страховщики - мониторинг ФГСВ"""
    insurers = [
        {
            'name': 'СК КазСтрах', 'solvency': 2.57, 'loss_ratio': 0.55,
            'combined': 0.85, 'pd': 0.02, 'risk_class': 'low'
        },
        {
            'name': 'СК НурПолис', 'solvency': 1.35, 'loss_ratio': 0.71,
            'combined': 0.98, 'pd': 0.08, 'risk_class': 'medium'
        },
        {
            'name': 'СК Виктория', 'solvency': 1.12, 'loss_ratio': 0.82,
            'combined': 1.05, 'pd': 0.15, 'risk_class': 'high'
        },
    ]

    return render_template('fgsv_panel/insurers.html',
                          insurers=insurers,
                          macro=MACRO_INDICATORS_2025,
                          APP_CONFIG=APP_CONFIG)


@main_bp.route('/fgsv-panel/bankruptcy')
def fgsv_bankruptcy():
    """Риск банкротства - ФГСВ"""
    risk_data = {
        'high_risk_count': 3,
        'expected_defaults': 0.8,
        'expected_loss': '1.2 млрд ₸',
        'var_95': '2.5 млрд ₸',
        'var_99': '4.1 млрд ₸',
    }

    return render_template('fgsv_panel/bankruptcy.html',
                          risk_data=risk_data,
                          macro=MACRO_INDICATORS_2025,
                          APP_CONFIG=APP_CONFIG)


@main_bp.route('/fgsv-panel/payouts')
def fgsv_payouts():
    """История выплат ФГСВ"""
    payouts = [
        {
            'year': 2024, 'insurer': 'СК Альянс (ликвидирована)',
            'claims': 1250, 'amount': '1.8 млрд ₸', 'recovery': '720 млн ₸'
        },
        {
            'year': 2023, 'insurer': 'СК Гарант (ликвидирована)',
            'claims': 580, 'amount': '650 млн ₸', 'recovery': '195 млн ₸'
        },
    ]

    return render_template('fgsv_panel/payouts.html',
                          payouts=payouts,
                          macro=MACRO_INDICATORS_2025,
                          APP_CONFIG=APP_CONFIG)


@main_bp.route('/fgsv-panel/simulation')
def fgsv_simulation():
    """Monte Carlo моделирование - ФГСВ"""
    return render_template('fgsv_panel/simulation.html',
                          macro=MACRO_INDICATORS_2025,
                          APP_CONFIG=APP_CONFIG)


# =============================================================================
# РЕЕСТРЫ - ПОРТФЕЛИ ДОГОВОРОВ И ИНСТРУМЕНТОВ
# =============================================================================

@main_bp.route('/contracts-registry')
def contracts_registry():
    """Реестр договоров страхования (МСФО 17)"""
    return render_template('contracts_registry.html',
                          macro=MACRO_INDICATORS_2025,
                          APP_CONFIG=APP_CONFIG)


@main_bp.route('/instruments-registry')
def instruments_registry():
    """Реестр финансовых инструментов (МСФО 9)"""
    return render_template('instruments_registry.html',
                          macro=MACRO_INDICATORS_2025,
                          APP_CONFIG=APP_CONFIG)


# =============================================================================
# ПАКЕТНЫЕ РАСЧЕТЫ (BATCH PROCESSING) - ENTERPRISE FEATURE
# =============================================================================

from app.services.batch_processing_service import batch_processing_service
from app.enterprise_models import CalculationRun, InsuranceType, ContractType


@main_bp.route('/calculations/runs')
def calculation_runs():
    """
    История пакетных расчетов

    КРИТИЧНО: В production системе расчеты НЕ выполняются вручную для каждого договора.
    Пользователь запускает JOB, который обрабатывает весь портфель.
    """
    # Получаем последние 20 расчетов
    runs = batch_processing_service.get_recent_runs(limit=20)

    return render_template('calculations/runs.html',
                          runs=runs,
                          macro=MACRO_INDICATORS_2025,
                          APP_CONFIG=APP_CONFIG)


@main_bp.route('/calculations/new', methods=['GET', 'POST'])
def new_calculation_run():
    """Запуск нового пакетного расчета"""
    if request.method == 'POST':
        try:
            # Параметры расчета
            calculation_type = request.form.get('calculation_type', 'ifrs17')
            reporting_date_str = request.form.get('reporting_date')
            description = request.form.get('description')

            # Фильтры портфеля
            portfolio_filter = {}
            if request.form.get('insurance_type'):
                portfolio_filter['insurance_type'] = InsuranceType(request.form.get('insurance_type'))
            if request.form.get('cohort_year'):
                portfolio_filter['cohort_year'] = int(request.form.get('cohort_year'))
            if request.form.get('contract_type'):
                portfolio_filter['contract_type'] = ContractType(request.form.get('contract_type'))

            # Парсим дату
            if reporting_date_str:
                reporting_date = datetime.strptime(reporting_date_str, '%Y-%m-%d').date()
            else:
                reporting_date = date.today()

            # Создаем расчет
            run = batch_processing_service.create_calculation_run(
                calculation_type=calculation_type,
                reporting_date=reporting_date,
                description=description,
                portfolio_filter=portfolio_filter if portfolio_filter else None
            )

            # Запускаем выполнение в фоне
            # TODO: В production использовать Celery/RQ для асинхронного выполнения
            result = batch_processing_service.execute_calculation_run(
                run_id=run.id,
                portfolio_filter=portfolio_filter if portfolio_filter else None
            )

            if result['status'] == 'success':
                flash(f'Расчет {run.run_code} успешно выполнен! Обработано групп: {result["processed"]}', 'success')
            else:
                flash(f'Ошибка выполнения расчета: {result.get("message")}', 'danger')

            return redirect(url_for('main.calculation_run_detail', run_id=run.id))

        except Exception as e:
            flash(f'Ошибка создания расчета: {str(e)}', 'danger')
            return redirect(url_for('main.calculation_runs'))

    # GET - показываем форму
    return render_template('calculations/new_run.html',
                          macro=MACRO_INDICATORS_2025,
                          APP_CONFIG=APP_CONFIG)


@main_bp.route('/calculations/run/<int:run_id>')
def calculation_run_detail(run_id):
    """Детальная информация по расчету"""
    run = CalculationRun.query.get_or_404(run_id)

    # Получаем результаты по группам
    from app.enterprise_models import GroupCalculationResult
    group_results = GroupCalculationResult.query.filter_by(
        calculation_run_id=run_id
    ).order_by(GroupCalculationResult.total_liability.desc()).limit(50).all()

    # Получаем логи ошибок
    from app.enterprise_models import CalculationLog
    error_logs = CalculationLog.query.filter_by(
        calculation_run_id=run_id,
        calculation_type='ERROR'
    ).all()

    return render_template('calculations/run_detail.html',
                          run=run,
                          group_results=group_results,
                          error_logs=error_logs,
                          macro=MACRO_INDICATORS_2025,
                          APP_CONFIG=APP_CONFIG)


@main_bp.route('/api/calculations/run/<int:run_id>/status')
def api_calculation_status(run_id):
    """
    API для получения статуса расчета (для AJAX polling)

    Используется для обновления прогресс-бара в реальном времени
    """
    status = batch_processing_service.get_run_status(run_id)
    return jsonify(status)


# =============================================================================
# JOURNAL ENTRY GENERATOR - АВТОМАТИЧЕСКОЕ СОЗДАНИЕ ПРОВОДОК
# =============================================================================

from app.services.journal_entry_generator_service import journal_entry_generator_service

@main_bp.route('/api/calculations/run/<int:run_id>/generate-entries', methods=['POST'])
def api_generate_entries(run_id):
    """
    API для генерирования проводок из результатов расчета

    POST /api/calculations/run/123/generate-entries
    Returns: {status, total_entries_created, total_amount, by_event_type}
    """
    try:
        result = journal_entry_generator_service.generate_entries_for_run(run_id=run_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@main_bp.route('/api/calculations/run/<int:run_id>/entries-summary', methods=['GET'])
def api_entries_summary(run_id):
    """
    Получить сводку по созданным проводкам

    GET /api/calculations/run/123/entries-summary
    Returns: {total_entries, posted_entries, pending_entries, by_event_type}
    """
    summary = journal_entry_generator_service.get_entry_summary(run_id)
    return jsonify(summary)


@main_bp.route('/api/calculations/run/<int:run_id>/post-entries', methods=['POST'])
def api_post_entries(run_id):
    """
    Проводить созданные проводки в главную книгу (необратимо!)

    POST /api/calculations/run/123/post-entries
    """
    result = journal_entry_generator_service.post_entries(run_id)
    return jsonify(result)


# =============================================================================
# ACCOUNTING ENGINE - НАСТРОЙКА МАППИНГА
# =============================================================================

from app.enterprise_models import ChartOfAccounts, AccountingRule, AccountingEventType


@main_bp.route('/accounting/chart-of-accounts')
def chart_of_accounts():
    """План счетов (Chart of Accounts)"""
    accounts = ChartOfAccounts.query.order_by(ChartOfAccounts.account_code).all()

    return render_template('accounting/chart_of_accounts.html',
                          accounts=accounts,
                          macro=MACRO_INDICATORS_2025,
                          APP_CONFIG=APP_CONFIG)


@main_bp.route('/accounting/mapping-rules')
def accounting_mapping_rules():
    """
    Правила маппинга событий на счета

    КРИТИЧНО: Это "мозг" Accounting Engine.
    Определяет какие проводки генерировать для каждого события.
    """
    rules = AccountingRule.query.order_by(
        AccountingRule.event_type,
        AccountingRule.priority
    ).all()

    # Группируем правила по типу события
    rules_by_event = {}
    for rule in rules:
        event_name = rule.event_type.value
        if event_name not in rules_by_event:
            rules_by_event[event_name] = []
        rules_by_event[event_name].append(rule)

    # Список всех возможных событий
    all_events = [e for e in AccountingEventType]

    return render_template('accounting/mapping_rules.html',
                          rules=rules,
                          rules_by_event=rules_by_event,
                          all_events=all_events,
                          macro=MACRO_INDICATORS_2025,
                          APP_CONFIG=APP_CONFIG)


@main_bp.route('/accounting/mapping-rules/new', methods=['GET', 'POST'])
def new_accounting_rule():
    """Создание нового правила маппинга"""
    if request.method == 'POST':
        try:
            # Получаем данные из формы
            event_type = AccountingEventType(request.form.get('event_type'))
            debit_account = request.form.get('debit_account')
            credit_account = request.form.get('credit_account')
            description = request.form.get('description')
            priority = int(request.form.get('priority', 100))

            # Фильтры (опционально)
            insurance_type_str = request.form.get('insurance_type')
            contract_type_str = request.form.get('contract_type')
            measurement_model_str = request.form.get('measurement_model')

            # Создаем правило
            rule = AccountingRule(
                event_type=event_type,
                debit_account_code=debit_account,
                credit_account_code=credit_account,
                description=description,
                priority=priority,
                is_active=True
            )

            # Добавляем фильтры если указаны
            if insurance_type_str:
                rule.insurance_type = InsuranceType(insurance_type_str)
            if contract_type_str:
                rule.contract_type = ContractType(contract_type_str)
            if measurement_model_str:
                rule.measurement_model = MeasurementModel(measurement_model_str)

            db.session.add(rule)
            db.session.commit()

            flash(f'Правило маппинга успешно создано!', 'success')
            return redirect(url_for('main.accounting_mapping_rules'))

        except Exception as e:
            flash(f'Ошибка создания правила: {str(e)}', 'danger')
            return redirect(url_for('main.new_accounting_rule'))

    # GET - показываем форму
    accounts = ChartOfAccounts.query.filter_by(is_active=True).order_by(ChartOfAccounts.account_code).all()
    all_events = [e for e in AccountingEventType]

    return render_template('accounting/new_rule.html',
                          accounts=accounts,
                          all_events=all_events,
                          macro=MACRO_INDICATORS_2025,
                          APP_CONFIG=APP_CONFIG)


@main_bp.route('/accounting/journal-entries')
def journal_entries():
    """Журнал проводок (Sub-ledger)"""
    from app.enterprise_models import JournalEntry
    from app import db
    from sqlalchemy import func

    # Получаем последние 100 проводок
    entries = JournalEntry.query.order_by(
        JournalEntry.posting_date.desc(),
        JournalEntry.entry_number.desc()
    ).limit(100).all()

    # Статистика
    total_entries = JournalEntry.query.count()
    posted_entries = JournalEntry.query.filter_by(is_posted=True).count()
    total_amount = db.session.query(func.sum(JournalEntry.amount)).scalar() or 0

    stats = {
        'total_entries': total_entries,
        'posted_entries': posted_entries,
        'pending_entries': total_entries - posted_entries,
        'total_amount': total_amount
    }

    return render_template('accounting/journal_entries.html',
                          entries=entries,
                          stats=stats,
                          macro=MACRO_INDICATORS_2025,
                          APP_CONFIG=APP_CONFIG)


# =============================================================================
# REINSURANCE ANALYSIS - АНАЛИЗ ПЕРЕСТРАХОВАНИЯ
# =============================================================================

from app.services.reinsurance_service import reinsurance_service

@main_bp.route('/api/calculations/run/<int:run_id>/reinsurance/portfolio', methods=['GET'])
def api_portfolio_net_gross(run_id):
    """
    Получить анализ портфеля: нетто/брутто разбор по типам договоров

    GET /api/calculations/run/123/reinsurance/portfolio
    """
    result = reinsurance_service.calculate_portfolio_net_gross(run_id)
    return jsonify(result)


@main_bp.route('/api/calculations/run/<int:run_id>/reinsurance/metrics', methods=['GET'])
def api_reinsurance_metrics(run_id):
    """
    Получить ключевые метрики перестрахования

    GET /api/calculations/run/123/reinsurance/metrics
    Returns: {cession_ratio, net_gross_ratio, relief_ratio, direct_ratio}
    """
    result = reinsurance_service.get_reinsurance_metrics(run_id)
    return jsonify(result)


@main_bp.route('/api/group-result/<int:result_id>/net-gross', methods=['GET'])
def api_group_net_gross(result_id):
    """
    Получить нетто/брутто разбор для конкретной группы

    GET /api/group-result/456/net-gross
    """
    result = reinsurance_service.get_group_net_gross(result_id)
    return jsonify(result)


@main_bp.route('/analytics/reinsurance', methods=['GET'])
def reinsurance_analysis():
    """Страница анализа перестрахования с Net/Gross разбором"""
    return render_template('analytics/reinsurance_analysis.html',
                          macro=MACRO_INDICATORS_2025,
                          APP_CONFIG=APP_CONFIG)


# =============================================================================
# YIELD CURVE MANAGEMENT - УПРАВЛЕНИЕ КРИВЫМИ ДОХОДНОСТИ
# =============================================================================

from app.services.yield_curve_service import yield_curve_service

@main_bp.route('/yield-curves', methods=['GET'])
def yield_curves_list():
    """Страница со списком всех кривых доходности"""
    result = yield_curve_service.list_curves()
    curves = result.get('curves', [])
    return render_template('analytics/yield_curves.html',
                          curves=curves,
                          macro=MACRO_INDICATORS_2025,
                          APP_CONFIG=APP_CONFIG)


@main_bp.route('/api/yield-curves', methods=['GET'])
def api_list_yield_curves():
    """
    Получить список всех кривых

    GET /api/yield-curves?type=risk_free&active=true
    """
    curve_type = request.args.get('type')
    active_only = request.args.get('active', 'true').lower() == 'true'
    
    result = yield_curve_service.list_curves(
        curve_type=curve_type,
        active_only=active_only
    )
    return jsonify(result)


@main_bp.route('/api/yield-curves', methods=['POST'])
def api_create_yield_curve():
    """
    Создать новую кривую доходности

    POST /api/yield-curves
    {
        "curve_name": "RFR_KZT_2025Q4",
        "curve_type": "risk_free",
        "reference_date": "2025-12-31",
        "curve_points": [
            {"term": 1, "rate": 0.05},
            {"term": 5, "rate": 0.06},
            {"term": 10, "rate": 0.065}
        ]
    }
    """
    try:
        data = request.get_json()
        result = yield_curve_service.create_yield_curve(
            curve_name=data.get('curve_name'),
            curve_type=data.get('curve_type'),
            reference_date=datetime.strptime(data.get('reference_date'), '%Y-%m-%d').date(),
            description=data.get('description'),
            curve_points=data.get('curve_points', [])
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400


@main_bp.route('/api/yield-curves/<int:curve_id>', methods=['GET'])
def api_get_yield_curve(curve_id):
    """
    Получить полные данные кривой (с интерполированными точками)

    GET /api/yield-curves/123
    """
    result = yield_curve_service.get_curve_data(curve_id)
    return jsonify(result)


@main_bp.route('/api/yield-curves/<int:curve_id>/points', methods=['PUT'])
def api_update_curve_points(curve_id):
    """
    Обновить точки кривой

    PUT /api/yield-curves/123/points
    {
        "curve_points": [
            {"term": 1, "rate": 0.05},
            {"term": 5, "rate": 0.06}
        ]
    }
    """
    try:
        data = request.get_json()
        result = yield_curve_service.update_curve_points(
            curve_id=curve_id,
            curve_points=data.get('curve_points', [])
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400


@main_bp.route('/api/yield-curves/<int:curve_id>/rate', methods=['GET'])
def api_get_rate_for_term(curve_id):
    """
    Получить ставку для конкретного срока

    GET /api/yield-curves/123/rate?term=5.5
    """
    try:
        term = float(request.args.get('term', 0))
        result = yield_curve_service.get_rate_for_term(curve_id, term)
        return jsonify(result)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400


@main_bp.route('/api/yield-curves/<int:curve_id>/discount-factor', methods=['GET'])
def api_calculate_discount_factor(curve_id):
    """
    Вычислить дисконт-фактор

    GET /api/yield-curves/123/discount-factor?term=5&compounding=annual
    """
    try:
        term = float(request.args.get('term', 0))
        compounding = request.args.get('compounding', 'annual')
        
        result = yield_curve_service.calculate_discount_factor(
            curve_id=curve_id,
            term_years=term,
            compounding=compounding
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400


@main_bp.route('/api/yield-curves/<int:curve_id>/set-active', methods=['POST'])
def api_set_active_curve(curve_id):
    """
    Установить кривую как активную для типа

    POST /api/yield-curves/123/set-active
    {"curve_type": "risk_free"}
    """
    try:
        data = request.get_json()
        result = yield_curve_service.set_active_curve(
            curve_id=curve_id,
            curve_type=data.get('curve_type')
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400
