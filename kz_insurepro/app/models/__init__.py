# -*- coding: utf-8 -*-
"""
KZ-InsurePro - Модели данных
"""

# Re-export everything from both model modules
from app.models.database import (
    Insurer, FinancialData, Portfolio, Exposure,
    InsuranceContract, ECLCalculation, IFRS17Calculation,
    SolvencyCalculation, FGSVContribution, AuditLog, Report
)

__all__ = [
    'Insurer', 'FinancialData', 'Portfolio', 'Exposure',
    'InsuranceContract', 'ECLCalculation', 'IFRS17Calculation',
    'SolvencyCalculation', 'FGSVContribution', 'AuditLog', 'Report'
]
