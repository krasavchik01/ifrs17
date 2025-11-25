# -*- coding: utf-8 -*-
"""
KZ-InsurePro - Модули расчетов
"""

from app.modules.ifrs9 import IFRS9Calculator
from app.modules.ifrs17 import IFRS17Calculator
from app.modules.solvency import SolvencyCalculator
from app.modules.fgsv import FGSVCalculator

__all__ = [
    'IFRS9Calculator',
    'IFRS17Calculator',
    'SolvencyCalculator',
    'FGSVCalculator',
]
