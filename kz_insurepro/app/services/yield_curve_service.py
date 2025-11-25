# -*- coding: utf-8 -*-
"""
Alliot - Yield Curve Service
Управление кривыми доходности и дисконтными ставками

КРИТИЧНО: В МСФО 17 для расчета BEL используются дисконт-ставки.
Эти ставки загружаются из кривых доходности (yield curves).

Основные кривые:
1. Risk-Free Curve - безрисковая кривая (берется из правительственных облигаций)
2. Basic Curves - базовые кривые для каждого вида риска
3. Ultimate Forward Rate (UFR) - долгосрочная форвард-ставка

Основной флоу:
1. Загружаем/создаем кривую доходности с точками по срокам
2. Используем интерполяцию для сроков, не указанных явно
3. Вычисляем дисконт-факторы: DF = 1 / (1 + rate)^term
4. Применяем в расчетах BEL
"""

from decimal import Decimal
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple
import json
import numpy as np
from scipy import interpolate

from app import db
from app.enterprise_models import YieldCurve


class YieldCurveService:
    """
    Сервис для управления кривыми доходности

    Компоненты:
    1. Curve management - создание и обновление кривых
    2. Interpolation - интерполяция ставок для произвольных сроков
    3. Discount factor calculation - расчет дисконт-факторов
    4. Curve analysis - анализ и визуализация кривых
    """

    # Константы интерполяции
    INTERPOLATION_METHOD = 'cubic'  # linear, cubic
    MIN_POINTS_FOR_SPLINE = 4  # Минимум точек для cubic spline

    def __init__(self):
        pass

    def create_yield_curve(
        self,
        curve_name: str,
        curve_type: str,
        reference_date: date,
        description: str = None,
        curve_points: List[Dict[str, float]] = None
    ) -> Dict[str, any]:
        """
        Создать новую кривую доходности

        Args:
            curve_name: Название кривой (e.g., 'RFR_KZT_2025Q4')
            curve_type: Тип ('risk_free', 'basic', 'corporate')
            reference_date: Дата публикации кривой
            description: Описание
            curve_points: Список точек [{term: float, rate: float}, ...]

        Returns:
            Статус и ID новой кривой
        """

        try:
            # Проверяем не существует ли уже такая кривая на эту дату
            existing = YieldCurve.query.filter_by(
                curve_name=curve_name,
                reference_date=reference_date
            ).first()

            if existing:
                return {
                    'status': 'error',
                    'message': f'Curve {curve_name} already exists for {reference_date}'
                }

            # Создаем кривую
            curve = YieldCurve(
                curve_name=curve_name,
                curve_type=curve_type,
                reference_date=reference_date,
                description=description,
                curve_points=curve_points or []
            )

            db.session.add(curve)
            db.session.commit()

            return {
                'status': 'success',
                'curve_id': curve.id,
                'curve_name': curve.curve_name,
                'message': f'Curve {curve_name} created successfully'
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }

    def update_curve_points(
        self,
        curve_id: int,
        curve_points: List[Dict[str, float]]
    ) -> Dict[str, any]:
        """
        Обновить точки кривой

        Args:
            curve_id: ID кривой
            curve_points: Список точек [{term: float, rate: float}, ...]

        Returns:
            Статус обновления
        """

        curve = YieldCurve.query.get(curve_id)
        if not curve:
            return {'status': 'error', 'message': 'Curve not found'}

        try:
            # Валидируем точки
            if not self._validate_curve_points(curve_points):
                return {
                    'status': 'error',
                    'message': 'Invalid curve points. Must have term (0-50) and rate (0-1)'
                }

            curve.curve_points = curve_points
            db.session.commit()

            return {
                'status': 'success',
                'curve_id': curve_id,
                'points_count': len(curve_points)
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }

    def get_rate_for_term(
        self,
        curve_id: int,
        term_years: float
    ) -> Dict[str, any]:
        """
        Получить ставку для конкретного срока (с интерполяцией)

        Args:
            curve_id: ID кривой
            term_years: Срок в годах

        Returns:
            {rate: float, interpolated: bool, method: str}
        """

        curve = YieldCurve.query.get(curve_id)
        if not curve:
            return {'status': 'error', 'message': 'Curve not found'}

        try:
            rate = curve.get_rate_for_term(term_years)

            return {
                'status': 'success',
                'curve_id': curve_id,
                'term_years': term_years,
                'rate': float(rate),
                'currency': curve.currency or 'KZT'
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }

    def calculate_discount_factor(
        self,
        curve_id: int,
        term_years: float,
        compounding: str = 'annual'
    ) -> Dict[str, any]:
        """
        Вычислить дисконт-фактор для срока

        Formula:
        - Annual: DF = 1 / (1 + rate)^term
        - Continuous: DF = e^(-rate * term)

        Args:
            curve_id: ID кривой
            term_years: Срок в годах
            compounding: 'annual' или 'continuous'

        Returns:
            {discount_factor: float, rate: float}
        """

        rate_result = self.get_rate_for_term(curve_id, term_years)

        if rate_result.get('status') != 'success':
            return rate_result

        rate = Decimal(str(rate_result['rate']))
        term = Decimal(str(term_years))

        try:
            if compounding == 'continuous':
                # DF = e^(-rate * term)
                import math
                df = math.exp(-float(rate) * float(term))
            else:  # annual
                # DF = 1 / (1 + rate)^term
                df = 1 / pow(1 + rate, term)

            return {
                'status': 'success',
                'discount_factor': float(df),
                'rate': float(rate),
                'term_years': term_years,
                'compounding': compounding
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }

    def list_curves(
        self,
        curve_type: str = None,
        active_only: bool = True
    ) -> Dict[str, any]:
        """
        Получить список кривых

        Args:
            curve_type: Фильтр по типу ('risk_free', 'basic', 'corporate')
            active_only: Только активные кривые

        Returns:
            Список кривых с их параметрами
        """

        query = YieldCurve.query

        if curve_type:
            query = query.filter_by(curve_type=curve_type)

        if active_only:
            query = query.filter_by(is_active=True)

        curves = query.order_by(YieldCurve.reference_date.desc()).all()

        return {
            'status': 'success',
            'total': len(curves),
            'curves': [
                {
                    'id': c.id,
                    'curve_name': c.curve_name,
                    'curve_type': c.curve_type,
                    'reference_date': c.reference_date.isoformat(),
                    'currency': c.currency,
                    'points_count': len(c.curve_points) if c.curve_points else 0,
                    'is_active': c.is_active,
                    'created_at': c.created_at.isoformat() if c.created_at else None
                }
                for c in curves
            ]
        }

    def set_active_curve(
        self,
        curve_id: int,
        curve_type: str
    ) -> Dict[str, any]:
        """
        Установить активную кривую для типа

        Args:
            curve_id: ID кривой
            curve_type: Тип кривой ('risk_free', 'basic', etc.)

        Returns:
            Статус обновления
        """

        curve = YieldCurve.query.get(curve_id)
        if not curve:
            return {'status': 'error', 'message': 'Curve not found'}

        try:
            # Деактивируем все кривые этого типа
            YieldCurve.query.filter_by(
                curve_type=curve_type,
                currency=curve.currency
            ).update({'is_active': False})

            # Активируем выбранную
            curve.is_active = True
            db.session.commit()

            return {
                'status': 'success',
                'curve_id': curve_id,
                'message': f'Curve {curve.curve_name} set as active'
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }

    def get_curve_data(self, curve_id: int) -> Dict[str, any]:
        """
        Получить полные данные кривой для визуализации

        Returns:
            {
                curve_name, reference_date, points: [{term, rate}, ...],
                extended_points: для графика (интерполированные точки)
            }
        """

        curve = YieldCurve.query.get(curve_id)
        if not curve:
            return {'status': 'error', 'message': 'Curve not found'}

        try:
            # Базовые точки
            base_points = curve.curve_points or []

            # Генерируем интерполированные точки для графика (каждые 0.25 года)
            extended_points = []
            if base_points and len(base_points) >= 2:
                terms = [p['term'] for p in base_points]
                rates = [p['rate'] for p in base_points]

                # Интерполируем
                min_term = min(terms)
                max_term = max(terms)

                extended_terms = np.arange(min_term, max_term + 0.25, 0.25)

                for t in extended_terms:
                    rate = curve.get_rate_for_term(t)
                    extended_points.append({
                        'term': float(t),
                        'rate': float(rate)
                    })

            return {
                'status': 'success',
                'id': curve.id,
                'curve_name': curve.curve_name,
                'curve_type': curve.curve_type,
                'reference_date': curve.reference_date.isoformat(),
                'currency': curve.currency or 'KZT',
                'base_points': base_points,
                'extended_points': extended_points,
                'ultimate_forward_rate': float(curve.ultimate_forward_rate) if curve.ultimate_forward_rate else None
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }

    def _validate_curve_points(
        self,
        points: List[Dict[str, float]]
    ) -> bool:
        """Валидировать формат точек кривой"""

        if not points or not isinstance(points, list):
            return False

        for p in points:
            if not isinstance(p, dict):
                return False
            if 'term' not in p or 'rate' not in p:
                return False
            if not isinstance(p['term'], (int, float)) or not isinstance(p['rate'], (int, float)):
                return False
            if p['term'] < 0 or p['term'] > 50:  # Срок 0-50 лет
                return False
            if p['rate'] < 0 or p['rate'] > 1:  # Ставка 0-100%
                return False

        return True


# Singleton instance
yield_curve_service = YieldCurveService()
