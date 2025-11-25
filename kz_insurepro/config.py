# -*- coding: utf-8 -*-
"""
KZ-InsurePro - Конфигурация системы
Демо-версия для страховых компаний Казахстана

Все настройки соответствуют требованиям АРФР и международным стандартам.
"""

import os
from decimal import Decimal
from datetime import date

# Базовые пути
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
SAMPLE_DATA_DIR = os.path.join(DATA_DIR, 'sample')
EXPORTS_DIR = os.path.join(DATA_DIR, 'exports')
ML_MODELS_DIR = os.path.join(BASE_DIR, 'ml_models')

# =============================================================================
# КОНФИГУРАЦИЯ ПРИЛОЖЕНИЯ
# =============================================================================
APP_CONFIG = {
    'VERSION': '3.0.0',
    'RELEASE_DATE': '25.11.2025',
    'APP_NAME': 'Alliot',
    'APP_SUBTITLE': 'Комплексная Регуляторная Система для Страхового Рынка',
    'COMPANY': 'Alliot Systems',
    'TAGLINE': 'Автоматизация МСФО 17, МСФО 9 и платежеспособности',
}

# Для обратной совместимости
DEMO_CONFIG = APP_CONFIG

# =============================================================================
# БАЗА ДАННЫХ
# =============================================================================
class Config:
    """Базовая конфигурация Flask"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'kz-insurepro-demo-secret-key-2025'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        f'sqlite:///{os.path.join(BASE_DIR, "kz_insurepro_demo.db")}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Настройки для продакшн (заглушки)
    POSTGRESQL_URI_PLACEHOLDER = 'postgresql://user:password@localhost:5432/kz_insurepro'


# =============================================================================
# МАКРОЭКОНОМИЧЕСКИЕ ПОКАЗАТЕЛИ КАЗАХСТАНА (Ноябрь 2025)
# Источник: Национальный Банк Казахстана (НБК)
# =============================================================================
MACRO_INDICATORS_2025 = {
    'gdp_growth': Decimal('5.6'),  # Рост ВВП, %
    'inflation': Decimal('12.9'),  # Инфляция, %
    'base_rate': Decimal('18.0'),  # Базовая ставка НБК, %
    'usd_kzt': Decimal('560'),  # Курс USD/KZT
    'eur_kzt': Decimal('590'),  # Курс EUR/KZT
    'brent_usd': Decimal('80.7'),  # Цена Brent, USD/баррель
    'mrp': Decimal('3932'),  # МРП (Месячный расчетный показатель) 2025, KZT
    'date': date(2025, 11, 1),
}

# =============================================================================
# МСФО 9 - КОНФИГУРАЦИЯ ECL
# Per IFRS 9 para B5.5.17, ARFR No. 269 от 29.12.2017
# =============================================================================
IFRS9_CONFIG = {
    # Мультипликаторы PD по сценариям (НБК Ноябрь 2025)
    'PD_MULTIPLIERS': {
        'base': Decimal('1.35'),      # Базовый сценарий
        'adverse': Decimal('1.80'),   # Неблагоприятный сценарий
        'severe': Decimal('2.40'),    # Стрессовый сценарий
    },

    # Веса сценариев для взвешенного ECL
    'SCENARIO_WEIGHTS': {
        'base': Decimal('0.55'),      # 55%
        'adverse': Decimal('0.35'),   # 35%
        'severe': Decimal('0.10'),    # 10%
    },

    # Итоговый мультипликатор: 1.35*0.55 + 1.80*0.35 + 2.40*0.10 = 1.613
    'TOTAL_PD_MULTIPLIER': Decimal('1.613'),

    # Базовые LGD по типам обеспечения (АРФР рекомендации)
    'LGD_DEFAULTS': {
        'unsecured': Decimal('0.69'),        # Без обеспечения - 69%
        'secured_real_estate': Decimal('0.35'),  # Недвижимость - 35%
        'secured_vehicles': Decimal('0.50'),     # Автотранспорт - 50%
        'secured_deposits': Decimal('0.15'),     # Депозиты - 15%
        'sovereign': Decimal('0.45'),            # Государственные - 45%
    },

    # CCF (Credit Conversion Factors) для EAD
    'CCF_FACTORS': {
        'credit_lines': Decimal('0.50'),      # Кредитные линии - 50%
        'guarantees': Decimal('0.75'),        # Гарантии - 75%
        'letters_of_credit': Decimal('0.60'), # Аккредитивы - 60%
        'unused_limits': Decimal('0.40'),     # Неиспользованные лимиты - 40%
    },

    # Пороги для перехода между стадиями
    'STAGE_THRESHOLDS': {
        'stage_2_days_past_due': 30,   # >30 дней - Стадия 2
        'stage_3_days_past_due': 90,   # >90 дней - Стадия 3
        'pd_relative_increase': Decimal('2.0'),  # 2x увеличение PD
        'pd_absolute_increase': Decimal('0.005'), # +0.5% абсолютный порог
    },

    # Лимиты РЕПО (АРФР, с 01.07.2025)
    'REPO_LIMITS': {
        'before_july_2025': Decimal('0.50'),  # ≤50% до июля 2025
        'after_july_2025': Decimal('0.35'),   # ≤35% после
    },

    # Макро-корректировки для LGD
    'LGD_MACRO_ADJUSTMENTS': {
        'inflation_factor': Decimal('0.05'),  # 5% на каждый % инфляции
        'rate_factor': Decimal('0.10'),       # 10% на каждый % ставки
    },

    # Точность вычислений (до 0.001 KZT)
    'PRECISION': Decimal('0.001'),
}

# =============================================================================
# МСФО 17 - КОНФИГУРАЦИЯ СТРАХОВЫХ КОНТРАКТОВ
# Per IFRS 17 para 32-52, ARFR адаптации
# =============================================================================
IFRS17_CONFIG = {
    # Ставка дисконтирования (базовая + премия за неликвидность)
    'DISCOUNT_RATES': {
        'base_rate': Decimal('18.0'),         # Базовая ставка НБК
        'illiquidity_premium': Decimal('0.50'), # Премия за неликвидность
        'total_rate': Decimal('18.50'),        # Итоговая ставка
    },

    # Премия за неликвидность по годам (CIA 2025 updates)
    'ILLIQUIDITY_PREMIUM_BY_YEAR': {
        1: Decimal('0.80'),  # 80% spread years 1-3
        2: Decimal('0.80'),
        3: Decimal('0.80'),
        4: Decimal('0.75'),  # 75% year 4
        5: Decimal('0.70'),  # 70% years 5+
    },

    # Risk Adjustment методы
    'RA_METHODS': {
        'var': {
            'confidence_level': Decimal('0.95'),  # VaR 95%
            'description': 'Value at Risk на уровне доверия 95%',
        },
        'tvar': {
            'confidence_level': Decimal('0.90'),  # TVaR 90%
            'description': 'Tail VaR (условное хвостовое ожидание)',
        },
        'coc': {
            'rate': Decimal('0.065'),  # 6.5% Cost of Capital
            'description': 'Метод стоимости капитала',
        },
        'cte': {
            'confidence_level': Decimal('0.90'),  # CTE 90%
            'description': 'Conditional Tail Expectation',
        },
    },

    # Monte Carlo параметры (демо)
    'MONTE_CARLO': {
        'simulations': 1000,  # Количество симуляций (демо)
        'simulations_full': 10000,  # Полная версия
        'seed': 42,  # Для воспроизводимости
    },

    # Корреляции рисков
    'RISK_CORRELATIONS': {
        'mortality_lapse': Decimal('0.50'),
        'mortality_morbidity': Decimal('0.25'),
        'lapse_expense': Decimal('0.30'),
    },

    # Уровни доверия для RA
    'CONFIDENCE_LEVELS': {
        'non_life': Decimal('0.75'),  # 75th percentile
        'life': Decimal('0.80'),       # 80th percentile
        'gross': Decimal('0.812'),     # 81.2% с диверсификацией
    },

    # Ставки аннуляции (lapse rates)
    'LAPSE_RATES': {
        'life_baseline': Decimal('0.05'),   # 5% базовый
        'non_life_baseline': Decimal('0.10'), # 10% базовый
        'stress_multiplier': Decimal('1.50'), # x1.5 при стрессе
    },

    # Coverage Units методы
    'COVERAGE_UNIT_METHODS': [
        'sum_assured',
        'account_value',
        'expected_premiums',
        'number_of_contracts',
    ],

    # OSAGO корректировки (АРФР)
    'OSAGO_ADJUSTMENT': Decimal('1.50'),  # +50% MMP для ОСАГО

    # Стабилизационный резерв (non-life)
    'STABILIZATION_RESERVE_MAX': Decimal('0.10'),  # ≤10%
}

# =============================================================================
# SOLVENCY - КОНФИГУРАЦИЯ ПЛАТЕЖЕСПОСОБНОСТИ
# Per ARFR Постановление №304 от 26.12.2016, изменения 2024-2025
# Адаптация Solvency II (EU 2025/2, EIOPA updates Nov 2025)
# =============================================================================
SOLVENCY_CONFIG = {
    # МГФ (Минимальный гарантийный фонд) в МРП
    'MGF_MRP': {
        'life_non_life': 500000,      # 500,000 МРП для life/non-life
        'reinsurance': 3500000,       # 3,500,000 МРП для перестрахования
    },

    # МГФ в KZT (2025)
    'MGF_KZT': {
        'life_non_life': Decimal('1966000000'),  # 1.966 млрд KZT
        'reinsurance': Decimal('13762000000'),   # 13.762 млрд KZT
    },

    # Коэффициенты MMP по премиям
    'MMP_PREMIUM_COEFFICIENTS': {
        'tier_1_rate': Decimal('0.18'),    # 18% до 3.5 млрд
        'tier_1_threshold': Decimal('3500000000'),  # 3.5 млрд KZT
        'tier_2_rate': Decimal('0.16'),    # 16% свыше 3.5 млрд
    },

    # Коэффициенты MMP по убыткам
    'MMP_CLAIMS_COEFFICIENTS': {
        'tier_1_rate': Decimal('0.26'),    # 26% до 2.5 млрд
        'tier_1_threshold': Decimal('2500000000'),  # 2.5 млрд KZT
        'tier_2_rate': Decimal('0.23'),    # 23% свыше 2.5 млрд
    },

    # Поправочный коэффициент K
    'K_COEFFICIENT': {
        'min': Decimal('0.50'),
        'max': Decimal('0.85'),
        'default': Decimal('0.70'),
    },

    # Life страхование: коэффициенты для резервов
    'LIFE_COEFFICIENTS': {
        'annuity_rate': Decimal('0.08'),  # 8% от резервов аннуитетов
        'math_reserve_addon': Decimal('0.03'),  # +3% мат. резервов
    },

    # Субординированный долг
    'SUBORDINATED_DEBT_LIMIT': Decimal('0.50'),  # ≤50% FMP

    # Solvency II SCR шоки (EIOPA 2025)
    'SCR_SHOCKS': {
        'equity_type1': Decimal('0.39'),  # 39% акции развитых рынков
        'equity_type2': Decimal('0.49'),  # 49% акции развивающихся
        'property': Decimal('0.25'),       # 25% недвижимость
        'interest_up': Decimal('0.20'),    # +20% процентные ставки
        'interest_down': Decimal('0.20'),  # -20% процентные ставки
        'spread': Decimal('0.10'),         # 10% кредитные спреды
        'pandemic': Decimal('2.00'),       # 200% шок для пандемий
    },

    # Операционный риск
    'OPERATIONAL_RISK': {
        'bscr_cap': Decimal('0.30'),  # Макс. 30% от BSCR
        'premium_rate': Decimal('0.03'),  # 3% от премий
        'tp_rate': Decimal('0.03'),  # 3% от техн. резервов
    },

    # ORSA параметры
    'ORSA': {
        'forward_years': 3,  # Горизонт планирования
        'stress_scenarios': ['base', 'adverse', 'severe', 'reverse'],
    },

    # Диверсификация (EIOPA 2025)
    'BOARD_DIVERSITY': {
        'min_underrepresented': Decimal('0.40'),  # ≥40%
    },

    # Лимиты диверсификации активов
    'ASSET_DIVERSIFICATION_LIMITS': {
        'single_issuer': Decimal('0.10'),  # ≤10%
        'group': Decimal('0.30'),  # ≤30%
    },

    # Высоколиквидные активы
    'HIGH_LIQUID_ASSETS_RATIO': Decimal('1.0'),  # ≥1.0

    # Минимальный уставный капитал (Постановление НБ РК)
    # Per adilet.zan.kz/rus/docs/V010001513_
    'MINIMUM_CHARTER_CAPITAL': {
        'general_insurance': Decimal('130000000'),    # 130 млн KZT - общее страхование
        'life_insurance': Decimal('150000000'),       # 150 млн KZT - страхование жизни
        'general_reinsurance': Decimal('150000000'),  # 150 млн KZT - общее + перестрахование
        'life_reinsurance': Decimal('170000000'),     # 170 млн KZT - жизнь + перестрахование
        'reinsurance_only': Decimal('230000000'),     # 230 млн KZT - только перестрахование
    },

    # Дополнительные требования по классам страхования
    'ADDITIONAL_CAPITAL_BY_CLASS': {
        'life': Decimal('15000000'),              # +15 млн - страхование жизни
        'annuity': Decimal('20000000'),           # +20 млн - аннуитетное
        'accident_health': Decimal('5000000'),    # +5 млн - НС и болезни
        'medical': Decimal('10000000'),           # +10 млн - медицинское
        'auto': Decimal('5000000'),               # +5 млн - автотранспорт
        'aviation': Decimal('10000000'),          # +10 млн - воздушный транспорт
        'cargo': Decimal('7000000'),              # +7 млн - грузы
    },
}

# =============================================================================
# ФГСВ - ФОНД ГАРАНТИРОВАНИЯ СТРАХОВЫХ ВЫПЛАТ
# Per Закон РК №423-II от 03.06.2003
# =============================================================================
FGSV_CONFIG = {
    # Ставки взносов по классам риска
    'CONTRIBUTION_RATES': {
        'low_risk': Decimal('0.005'),     # 0.5%
        'medium_risk': Decimal('0.010'),  # 1.0%
        'high_risk': Decimal('0.020'),    # 2.0%
    },

    # Лимиты выплат
    'PAYOUT_LIMITS': {
        'compulsory': Decimal('1000000'),  # 1 млн KZT для обязательного
        'voluntary': Decimal('500000'),    # 500 тыс KZT для добровольного
    },

    # Достаточность фонда
    'ADEQUACY_RATIO': Decimal('1.20'),  # Фонд/Ожидаемые выплаты > 1.2

    # Monte Carlo для банкротств
    'BANKRUPTCY_SIMULATIONS': 1000,  # Демо
}

# =============================================================================
# ЛОКАЛИЗАЦИЯ (Русский язык)
# =============================================================================
LOCALE_CONFIG = {
    'language': 'ru',
    'currency_symbol': '₸',
    'currency_code': 'KZT',
    'date_format': '%d.%m.%Y',
    'datetime_format': '%d.%m.%Y %H:%M:%S',
    'decimal_separator': ',',
    'thousands_separator': ' ',
}

# =============================================================================
# СЛОВАРЬ ПЕРЕВОДОВ (i18n)
# =============================================================================
TRANSLATIONS = {
    # Общие
    'app_name': 'KZ-InsurePro',
    'app_subtitle': 'Автоматизация МСФО и платежеспособности для страховых компаний Казахстана',
    'demo_version': 'Демонстрационная версия',
    'full_version': 'Полная версия',

    # Навигация
    'nav_dashboard': 'Панель управления',
    'nav_ifrs9': 'МСФО 9',
    'nav_ifrs17': 'МСФО 17',
    'nav_solvency': 'Платежеспособность',
    'nav_fgsv': 'ФГСВ',
    'nav_reports': 'Отчеты',
    'nav_settings': 'Настройки',

    # МСФО 9
    'ifrs9_title': 'МСФО 9: Финансовые инструменты',
    'ifrs9_ecl': 'Расчет ECL (Ожидаемые кредитные убытки)',
    'ifrs9_classification': 'Классификация и оценка',
    'ifrs9_impairment': 'Обесценение',
    'ifrs9_stage_1': 'Стадия 1 (12-месячные ECL)',
    'ifrs9_stage_2': 'Стадия 2 (Пожизненные ECL)',
    'ifrs9_stage_3': 'Стадия 3 (Кредитно-обесцененные)',

    # МСФО 17
    'ifrs17_title': 'МСФО 17: Договоры страхования',
    'ifrs17_bel': 'Наилучшая оценка обязательств (BEL)',
    'ifrs17_ra': 'Корректировка на риск (RA)',
    'ifrs17_csm': 'Контрактная маржа обслуживания (CSM)',
    'ifrs17_gmm': 'Общая модель оценки (GMM)',
    'ifrs17_vfa': 'Подход переменного вознаграждения (VFA)',
    'ifrs17_paa': 'Подход распределения премий (PAA)',

    # Solvency
    'solvency_title': 'Платежеспособность (АРФР)',
    'solvency_mmp': 'Минимальная маржа платежеспособности (MMP)',
    'solvency_mgf': 'Минимальный гарантийный фонд (MGF)',
    'solvency_fmp': 'Фактическая маржа платежеспособности (FMP)',
    'solvency_ratio': 'Коэффициент платежеспособности (Nmп)',
    'solvency_stress': 'Стресс-тестирование',

    # ФГСВ
    'fgsv_title': 'ФГСВ: Фонд гарантирования страховых выплат',
    'fgsv_contributions': 'Расчет взносов',
    'fgsv_simulations': 'Моделирование банкротств',

    # Формы
    'form_submit': 'Рассчитать',
    'form_reset': 'Сбросить',
    'form_export': 'Экспорт',
    'form_import': 'Импорт данных',

    # Отчеты
    'report_generate': 'Сформировать отчет',
    'report_download': 'Скачать',
    'report_xbrl': 'Экспорт XBRL',
    'report_audit_trail': 'Аудиторский след',

    # Сообщения
    'msg_success': 'Операция выполнена успешно',
    'msg_error': 'Ошибка при выполнении операции',
    'msg_validation_error': 'Ошибка валидации данных',
    'msg_demo_limit': 'Достигнут лимит демо-версии',

    # Единицы измерения
    'unit_kzt': 'тенге',
    'unit_percent': '%',
    'unit_days': 'дней',
    'unit_years': 'лет',

    # Таблицы
    'table_total': 'Итого',
    'table_average': 'Среднее',
    'table_min': 'Минимум',
    'table_max': 'Максимум',
}

# =============================================================================
# API КОНФИГУРАЦИЯ (Заглушки для интеграций)
# =============================================================================
API_CONFIG = {
    # 1C интеграция (mock)
    '1c': {
        'enabled': False,
        'endpoint': 'http://mock-1c-api.local/api',
        'placeholder': 'Интеграция с 1С доступна в полной версии',
    },

    # SAP интеграция (mock)
    'sap': {
        'enabled': False,
        'endpoint': 'http://mock-sap-api.local/api',
        'placeholder': 'Интеграция с SAP доступна в полной версии',
    },

    # НБК API (mock)
    'nbk': {
        'enabled': False,
        'endpoint': 'https://nationalbank.kz/api',
        'placeholder': 'Данные НБК загружены статически (Ноябрь 2025)',
    },

    # adilet.zan.kz (mock для парсинга законодательства)
    'adilet': {
        'enabled': False,
        'endpoint': 'https://adilet.zan.kz',
        'placeholder': 'Парсинг законодательства доступен в полной версии',
    },
}

# =============================================================================
# ЛОГИРОВАНИЕ
# =============================================================================
LOGGING_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'date_format': '%Y-%m-%d %H:%M:%S',
    'file': os.path.join(BASE_DIR, 'logs', 'kz_insurepro.log'),
    'max_bytes': 10485760,  # 10 MB
    'backup_count': 5,
}

# =============================================================================
# РЕГУЛЯТОРНЫЕ ССЫЛКИ
# =============================================================================
REGULATORY_REFERENCES = {
    'ifrs9': {
        'standard': 'МСФО 9 "Финансовые инструменты"',
        'arfr_resolution': 'Постановление АРФР №269 от 29.12.2017',
        'amendments': ['№83 от 21.10.2024', '№92 от 27.12.2024'],
    },
    'ifrs17': {
        'standard': 'МСФО 17 "Договоры страхования"',
        'effective_date': '01.01.2023',
        'updates': 'Технические обновления МСФО Декабрь 2025',
    },
    'solvency': {
        'resolution': 'Постановление АРФР №304 от 26.12.2016',
        'amendments': ['№95 от 22.12.2023', '№3 от 20.02.2023', '№14 от 16.05.2025'],
        'internal_audit': 'Изменения по внутреннему аудиту от 08.10.2025',
        'eiopa_updates': 'EIOPA 2025: макропруденциальные требования, диверсификация советов',
    },
    'fgsv': {
        'law': 'Закон РК №423-II от 03.06.2003 "О Фонде гарантирования страховых выплат"',
        'universal_coverage': 'Универсальное покрытие с 2023',
    },
}


def get_translation(key: str) -> str:
    """Получить перевод по ключу"""
    return TRANSLATIONS.get(key, key)


def format_currency(amount, include_symbol: bool = True) -> str:
    """Форматировать сумму в KZT"""
    if isinstance(amount, (int, float)):
        amount = Decimal(str(amount))

    # Форматирование с разделителями тысяч
    formatted = f"{amount:,.3f}".replace(',', ' ').replace('.', ',')

    if include_symbol:
        return f"{formatted} {LOCALE_CONFIG['currency_symbol']}"
    return formatted


def format_date(date_obj) -> str:
    """Форматировать дату в русском формате"""
    return date_obj.strftime(LOCALE_CONFIG['date_format'])


def format_percent(value) -> str:
    """Форматировать процент"""
    if isinstance(value, (int, float)):
        value = Decimal(str(value))
    return f"{value:.2f}%".replace('.', ',')
