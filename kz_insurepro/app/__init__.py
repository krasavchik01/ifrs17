# -*- coding: utf-8 -*-
"""
KZ-InsurePro - Инициализация приложения
Демо-версия для страховых компаний Казахстана
"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os
import sys

# Добавляем корневую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config, APP_CONFIG, DEMO_CONFIG, TRANSLATIONS, MACRO_INDICATORS_2025

db = SQLAlchemy()


def create_app(config_class=Config):
    """Фабрика приложения Flask"""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Инициализация расширений
    db.init_app(app)

    # Контекстные процессоры для шаблонов
    @app.context_processor
    def inject_globals():
        return {
            'APP_CONFIG': APP_CONFIG,
            'DEMO_CONFIG': DEMO_CONFIG,
            'TRANSLATIONS': TRANSLATIONS,
            'macro': MACRO_INDICATORS_2025,
            't': lambda key: TRANSLATIONS.get(key, key),
        }

    # Импортируем модели для регистрации с db
    # Важно: делаем это ПОСЛЕ db.init_app() но ДО db.create_all()
    from app import enterprise_models  # новые enterprise модели (содержат все нужные модели)

    # Регистрация blueprints
    from app.api.routes import api_bp
    app.register_blueprint(api_bp, url_prefix='/api')

    # Phase 1: New calculation API
    from app.api.calculate import calc_bp
    app.register_blueprint(calc_bp, url_prefix='/api')

    # Главные маршруты
    from app.routes import main_bp
    app.register_blueprint(main_bp)

    # Создание таблиц БД
    with app.app_context():
        db.create_all()

    return app
