# -*- coding: utf-8 -*-
"""
KZ-InsurePro - Главный файл запуска
Демо-версия для страховых компаний Казахстана
"""

import os
import sys

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app

app = create_app()

if __name__ == '__main__':
    print("=" * 60)
    print("KZ-InsurePro - Демо-версия")
    print("Автоматизация МСФО и платежеспособности")
    print("для страховых компаний Казахстана")
    print("=" * 60)
    print()
    print("Запуск на http://127.0.0.1:5000")
    print()
    print("ДЕМОНСТРАЦИОННАЯ ВЕРСИЯ - НЕ ДЛЯ ПРОИЗВОДСТВЕННОГО ИСПОЛЬЗОВАНИЯ")
    print("=" * 60)

    app.run(debug=True, host='127.0.0.1', port=5000)
