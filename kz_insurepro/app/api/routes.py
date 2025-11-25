# -*- coding: utf-8 -*-
"""
KZ-InsurePro - API маршруты
RESTful API для интеграции с внешними системами (1С, SAP)

ВАЖНО: Все расчеты идут через calculation_service!
Это гарантирует единые цифры везде в системе.
"""

from flask import Blueprint, request, jsonify
from decimal import Decimal
from datetime import datetime

from app.services.calculation_service import calculation_service
from config import DEMO_CONFIG, MACRO_INDICATORS_2025

api_bp = Blueprint('api', __name__)


def decimal_to_float(obj):
    """Конвертация Decimal в float для JSON"""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: decimal_to_float(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [decimal_to_float(i) for i in obj]
    return obj


@api_bp.route('/health', methods=['GET'])
def health():
    """Проверка состояния API"""
    return jsonify({
        'status': 'ok',
        'version': DEMO_CONFIG['VERSION'],
        'demo': True,
        'timestamp': datetime.now().isoformat(),
    })


@api_bp.route('/macro', methods=['GET'])
def get_macro():
    """Получение макроэкономических показателей"""
    return jsonify({
        'status': 'ok',
        'data': decimal_to_float({
            'gdp_growth': MACRO_INDICATORS_2025['gdp_growth'],
            'inflation': MACRO_INDICATORS_2025['inflation'],
            'base_rate': MACRO_INDICATORS_2025['base_rate'],
            'usd_kzt': MACRO_INDICATORS_2025['usd_kzt'],
            'brent_usd': MACRO_INDICATORS_2025['brent_usd'],
            'mrp': MACRO_INDICATORS_2025['mrp'],
            'date': str(MACRO_INDICATORS_2025['date']),
        }),
        'source': 'НБК Ноябрь 2025',
    })


@api_bp.route('/ifrs9/ecl', methods=['POST'])
def calculate_ecl():
    """
    Расчет ECL по МСФО 9 - ЕДИНЫЙ расчет через сервис

    Request JSON:
    {
        "gca": 500000000,
        "pd": 0.095,
        "lgd": 0.69,
        "eir": 0.19,
        "term": 3,
        "dpd": 0,
        "scenario": "weighted"
    }
    """
    try:
        data = request.get_json()

        # ВСЕ расчеты идут через calculation_service!
        result = calculation_service.calculate_single_ecl(
            gross_carrying_amount=Decimal(str(data.get('gca', 500000000))),
            pd_annual=Decimal(str(data.get('pd', 0.095))),
            lgd=Decimal(str(data.get('lgd', 0.69))),
            eir=Decimal(str(data.get('eir', 0.19))),
            remaining_term=int(data.get('term', 3)),
            days_past_due=int(data.get('dpd', 0)),
            scenario=data.get('scenario', 'weighted')
        )

        gca = Decimal(str(data.get('gca', 500000000)))

        return jsonify({
            'status': 'ok',
            'result': {
                'ecl_amount': float(result.ecl_amount),
                'stage': result.stage,
                'net_value': float(gca - result.ecl_amount),
                'coverage_ratio': float(result.ecl_amount / gca),
                'calculation_date': result.calculation_date.isoformat(),
            },
            'audit': {
                'justification': result.justification,
            },
            'watermark': DEMO_CONFIG['WATERMARK_TEXT'],
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
        }), 400


@api_bp.route('/ifrs17/gmm', methods=['POST'])
def calculate_gmm():
    """
    Расчет по GMM (МСФО 17) - ЕДИНЫЙ расчет через сервис

    Request JSON:
    {
        "premiums": 100000000,
        "claims_per_year": 80000000,
        "expenses_per_year": 5000000,
        "acquisition_costs": 10000000,
        "term": 10,
        "ra_method": "coc"
    }
    """
    try:
        data = request.get_json()

        premiums = Decimal(str(data.get('premiums', 100000000)))
        claims_per_year = Decimal(str(data.get('claims_per_year', 80000000)))
        expenses_per_year = Decimal(str(data.get('expenses_per_year', 5000000)))
        acquisition_costs = Decimal(str(data.get('acquisition_costs', 10000000)))
        term = int(data.get('term', 10))
        ra_method = data.get('ra_method', 'coc')

        # Формирование CF
        cash_flows = []
        for year in range(1, term + 1):
            cf = {
                'period': year,
                'premiums': float(premiums) if year == 1 else 0,
                'claims': float(claims_per_year) * (1 + 0.02 * year),
                'expenses': float(expenses_per_year),
                'acquisition_costs': float(acquisition_costs) if year == 1 else 0,
            }
            cash_flows.append(cf)

        # ВСЕ расчеты идут через calculation_service!
        result = calculation_service.calculate_single_contract(
            cash_flows=cash_flows,
            acquisition_costs=acquisition_costs,
            ra_method=ra_method,
            model='gmm'
        )

        return jsonify({
            'status': 'ok',
            'result': {
                'bel': float(result.bel.bel_amount),
                'ra': float(result.ra.ra_amount),
                'csm': float(result.csm.csm_amount),
                'fcf': float(result.fcf),
                'total_liability': float(result.total_liability),
                'is_onerous': result.csm.is_onerous,
                'measurement_model': result.measurement_model,
            },
            'audit': {
                'justification': result.justification,
            },
            'watermark': DEMO_CONFIG['WATERMARK_TEXT'],
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
        }), 400


@api_bp.route('/solvency/calculate', methods=['POST'])
def calculate_solvency():
    """
    Расчет платежеспособности - ЕДИНЫЙ расчет через сервис

    Request JSON:
    {
        "gross_premiums": 35000000000,
        "incurred_claims": 18000000000,
        "equity": 20000000000,
        "ecl_adjustment": 2100000000,
        "csm_adjustment": 11800000000,
        "subordinated": 3000000000,
        "illiquid": 500000000,
        "has_osago": true,
        "k": 0.70
    }
    """
    try:
        data = request.get_json()

        # ВСЕ расчеты идут через calculation_service!
        result = calculation_service.calculate_complete_solvency(
            gross_premiums=Decimal(str(data.get('gross_premiums', 35000000000))),
            incurred_claims=Decimal(str(data.get('incurred_claims', 18000000000))),
            equity_capital=Decimal(str(data.get('equity', 20000000000))),
            ecl_adjustment=Decimal(str(data.get('ecl_adjustment', 2100000000))),
            csm_adjustment=Decimal(str(data.get('csm_adjustment', 11800000000))),
            subordinated_debt=Decimal(str(data.get('subordinated', 3000000000))),
            illiquid_assets=Decimal(str(data.get('illiquid', 500000000))),
            has_osago=data.get('has_osago', False),
            k_coefficient=Decimal(str(data.get('k', 0.70)))
        )

        return jsonify({
            'status': 'ok',
            'result': {
                'mmp': float(result.mmp_amount),
                'fmp': float(result.fmp_amount),
                'ratio': float(result.ratio),
                'is_compliant': result.is_compliant,
                'mmp_by_premiums': float(result.mmp_by_premiums),
                'mmp_by_claims': float(result.mmp_by_claims),
            },
            'audit': {
                'justification': result.justification,
            },
            'watermark': DEMO_CONFIG['WATERMARK_TEXT'],
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
        }), 400


@api_bp.route('/fgsv/contribution', methods=['POST'])
def calculate_fgsv_contribution():
    """
    Расчет взноса в ФГСВ - ЕДИНЫЙ расчет через сервис

    Request JSON:
    {
        "premiums": 5000000000,
        "solvency_ratio": 2.50,
        "loss_ratio": 0.55,
        "combined_ratio": 0.85
    }
    """
    try:
        data = request.get_json()

        # ВСЕ расчеты идут через calculation_service!
        result = calculation_service.calculate_fgsv_contribution(
            gross_premiums=Decimal(str(data.get('premiums', 5000000000))),
            solvency_ratio=Decimal(str(data.get('solvency_ratio', 2.50))),
            loss_ratio=Decimal(str(data.get('loss_ratio', 0.55))),
            combined_ratio=Decimal(str(data.get('combined_ratio', 0.85)))
        )

        return jsonify({
            'status': 'ok',
            'result': {
                'contribution': float(result.contribution_amount),
                'rate': float(result.rate),
                'risk_class': result.risk_class,
            },
            'audit': {
                'justification': result.justification,
            },
            'watermark': DEMO_CONFIG['WATERMARK_TEXT'],
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
        }), 400


@api_bp.route('/ifrs9/portfolio', methods=['POST'])
def calculate_portfolio_ecl():
    """
    Расчет ECL для портфеля инструментов

    Request JSON:
    {
        "instruments": [
            {
                "id": "INS-001",
                "name": "Облигация А",
                "ead": 100000000,
                "pd": 0.05,
                "lgd": 0.45,
                "eir": 0.10,
                "term": 5,
                "dpd": 0
            },
            ...
        ]
    }
    """
    try:
        data = request.get_json()
        instruments = data.get('instruments', [])

        if not instruments:
            return jsonify({
                'status': 'error',
                'message': 'Необходимо предоставить список инструментов'
            }), 400

        # Расчет через сервис
        result = calculation_service.calculate_portfolio_ecl(instruments=instruments)

        return jsonify({
            'status': 'ok',
            'result': result.to_dict(),
            'watermark': DEMO_CONFIG['WATERMARK_TEXT'],
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
        }), 400


@api_bp.route('/ifrs17/portfolio', methods=['POST'])
def calculate_portfolio_ifrs17():
    """
    Расчет МСФО 17 для портфеля договоров

    Request JSON:
    {
        "contracts": [
            {
                "id": "CNT-001",
                "contract_number": "POL-2025-001",
                "cash_flows": [...],
                "acquisition_costs": 1000000,
                "ra_method": "coc",
                "model": "gmm"
            },
            ...
        ]
    }
    """
    try:
        data = request.get_json()
        contracts = data.get('contracts', [])

        if not contracts:
            return jsonify({
                'status': 'error',
                'message': 'Необходимо предоставить список договоров'
            }), 400

        # Расчет через сервис
        result = calculation_service.calculate_portfolio_ifrs17(contracts=contracts)

        return jsonify({
            'status': 'ok',
            'result': result.to_dict(),
            'watermark': DEMO_CONFIG['WATERMARK_TEXT'],
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
        }), 400


# Mock endpoints для интеграций
@api_bp.route('/integration/1c', methods=['POST'])
def mock_1c_integration():
    """Mock endpoint для интеграции с 1С"""
    return jsonify({
        'status': 'mock',
        'message': 'Интеграция с 1С доступна в полной версии',
        'watermark': DEMO_CONFIG['WATERMARK_TEXT'],
    })


@api_bp.route('/integration/sap', methods=['POST'])
def mock_sap_integration():
    """Mock endpoint для интеграции с SAP"""
    return jsonify({
        'status': 'mock',
        'message': 'Интеграция с SAP доступна в полной версии',
        'watermark': DEMO_CONFIG['WATERMARK_TEXT'],
    })
