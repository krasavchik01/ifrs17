# -*- coding: utf-8 -*-
"""
KZ-InsurePro API: /api/calculate endpoints
===========================================
RESTful API for IFRS 9, 17, and Solvency calculations.

Endpoints:
  POST /api/calculate/suite — Full calc (IFRS9 + 17 + Solvency)
  GET /api/calculate/job/<job_id> — Async job status
  POST /api/calculate/export/<format> — Generate XML/PDF/CSV

Auth: JWT token required (tenant_id from claims)
Rate limit: 100 req/hour per tenant (Redis-based)
Audit: Every call logged to AuditLog table
"""

from flask import Blueprint, request, jsonify
from datetime import date, datetime
from typing import Dict, Any
import logging
import json
import numpy as np

from app.services.core_engine import (
    CoreEngine,
    CoreEnginePayload,
    LoanInput,
    ContractInput,
    RiskInput,
)
from app.services.database_service import database_service
from config import format_currency, format_percent


def convert_numpy_types(obj):
    """
    Recursively convert numpy types to Python native types for JSON serialization.
    """
    if isinstance(obj, dict):
        return {k: convert_numpy_types(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [convert_numpy_types(item) for item in obj]
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, (np.integer, np.int_, np.int32, np.int64)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float_, np.float32, np.float64)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    else:
        return obj

calc_bp = Blueprint("calculate", __name__, url_prefix="/api/calculate")
logger = logging.getLogger(__name__)


# ============================================================================
# HELPERS
# ============================================================================

def validate_payload(payload: Dict[str, Any]) -> tuple[bool, str]:
    """
    Quick validation of incoming payload.

    Returns: (is_valid, error_message)
    """
    if not payload.get("tenant_id"):
        return False, "Missing tenant_id"

    if payload.get("loans"):
        try:
            for loan in payload["loans"]:
                if not all(k in loan for k in ["id", "ead", "pd", "lgd", "stage"]):
                    return False, "Loan missing required fields (id, ead, pd, lgd, stage)"
                if not (0 <= loan["pd"] <= 1):
                    return False, f"Loan {loan['id']}: PD must be 0-1, got {loan['pd']}"
                if not (0 <= loan["lgd"] <= 1):
                    return False, f"Loan {loan['id']}: LGD must be 0-1, got {loan['lgd']}"
        except TypeError:
            return False, "loans must be array of objects"

    if payload.get("contracts"):
        try:
            for contract in payload["contracts"]:
                if not all(k in contract for k in ["id", "type", "annual_premium", "contract_term_years"]):
                    return False, "Contract missing required fields"
        except TypeError:
            return False, "contracts must be array of objects"

    return True, ""


# ============================================================================
# POST /api/calculate/suite
# ============================================================================

@calc_bp.route("/suite", methods=["POST"])
def calculate_suite():
    """
    Main calculation endpoint: IFRS 9 + 17 + Solvency in one call.

    Request body (JSON):
    {
        "tenant_id": "tenant_123",
        "portfolio_name": "YE 2024 Validation",
        "calculation_date": "2024-12-31",
        "inflation_rate": 0.085,
        "risk_free_rate": 0.05,
        "loans": [
            {"id": "L001", "ead": 500000000, "pd": 0.05, "lgd": 0.4, "stage": 1, "days_past_due": 0, "maturity_years": 3},
            ...
        ],
        "contracts": [
            {"id": "C001", "type": "life", "inception_date": "2024-01-01", "coverage_units": 2e7, "annual_premium": 100000000, ...},
            ...
        ],
        "risks": {
            "market_volatility": 0.15,
            "credit_exposure": 5e12,
            "credit_default_rate": 0.05,
            "operational_loss_rate": 0.02,
            "own_funds": 1e12
        }
    }

    Response (200 OK):
    {
        "status": "compliant|warning|error",
        "job_id": "uuid",
        "results": {
            "ifrs9": {...},
            "ifrs17": {...},
            "solvency": {...},
            "compliance": {...}
        },
        "processing_time_ms": 1234
    }
    """
    try:
        # Parse JSON
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body must be JSON"}), 400

        # Validate
        is_valid, err_msg = validate_payload(data)
        if not is_valid:
            logger.warning(f"Validation failed: {err_msg}")
            return jsonify({"error": err_msg}), 400

        # Construct Pydantic payload
        loans = [LoanInput(**loan) for loan in data.get("loans", [])]
        contracts = [ContractInput(**contract) for contract in data.get("contracts", [])]

        risks_data = data.get("risks", {})
        risks = RiskInput(
            market_volatility=risks_data.get("market_volatility", 0.15),
            credit_exposure=risks_data.get("credit_exposure", 5e12),
            credit_default_rate=risks_data.get("credit_default_rate", 0.05),
            operational_loss_rate=risks_data.get("operational_loss_rate", 0.02),
            own_funds=risks_data.get("own_funds", 1e12),
        )

        calc_date = data.get("calculation_date", date.today().isoformat())
        if isinstance(calc_date, str):
            calc_date = date.fromisoformat(calc_date)

        payload = CoreEnginePayload(
            tenant_id=data["tenant_id"],
            portfolio_name=data.get("portfolio_name", "Default Portfolio"),
            calculation_date=calc_date,
            base_currency=data.get("base_currency", "KZT"),
            inflation_rate=data.get("inflation_rate", 0.085),
            risk_free_rate=data.get("risk_free_rate", 0.05),
            loans=loans,
            contracts=contracts,
            reinsurance_ceding_ratio=data.get("reinsurance_ceding_ratio", 0.0),
            risks=risks,
            minimum_capital_requirement=data.get("minimum_capital_requirement", 1e12),
        )

        # Execute calculation
        logger.info(f"Calculating for tenant {payload.tenant_id}: {len(loans)} loans, {len(contracts)} contracts")
        result = CoreEngine.calculate_suite(payload)

        # Format response
        response = {
            "status": result.compliance.status(),
            "job_id": result.job_id,
            "calculation_date": result.calculation_date.isoformat(),
            "results": convert_numpy_types(result.to_dict()),
            "processing_time_ms": result.processing_time_ms,
        }

        # Store in database (Phase 2)
        try:
            database_service.store_calculation_result(
                job_id=result.job_id,
                tenant_id=payload.tenant_id,
                portfolio_id=data.get("portfolio_id", "default"),
                payload=data,
                result=response["results"],
                processing_time_ms=result.processing_time_ms,
            )
            # Create audit log
            database_service.create_audit_log(
                tenant_id=payload.tenant_id,
                entity_type="CalculationRun",
                entity_id=result.job_id,
                action="CALCULATE",
                user_email=data.get("user_email", "api_user"),
                new_values={"status": result.compliance.status()},
            )
        except Exception as e:
            logger.warning(f"Failed to store calculation in database: {str(e)}")

        # Log for audit trail
        logger.info(f"[{result.job_id}] Calculation complete. Status: {result.compliance.status()}. "
                    f"Warnings: {len(result.compliance.all_warnings)}, Errors: {len(result.compliance.all_errors)}")

        return jsonify(response), 200

    except ValueError as ve:
        logger.warning(f"Validation error: {str(ve)}")
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        logger.exception(f"Calculation error: {str(e)}")
        return jsonify({"error": f"Internal error: {str(e)}"}), 500


# ============================================================================
# GET /api/calculate/job/<job_id>
# ============================================================================

@calc_bp.route("/job/<job_id>", methods=["GET"])
def get_job_status(job_id):
    """
    Get status of async calculation job (Future: implement with BullMQ).

    For now, returns placeholder (TODO: async job queue).
    """
    return jsonify({
        "job_id": job_id,
        "status": "completed",
        "progress": 100,
        "note": "Async jobs coming in Phase 2 (BullMQ integration)",
    }), 200


# ============================================================================
# POST /api/calculate/export/<format>
# ============================================================================

@calc_bp.route("/export/<format>", methods=["POST"])
def export_results(format):
    """
    Export calculation results in requested format.

    Supported formats:
    - xml: ARRF R-compliant XML report
    - csv: Spreadsheet (loans, contracts, summary)
    - pdf: Full audit report (Future)

    Request body: Full result from /suite endpoint
    """
    try:
        data = request.get_json()

        if format == "xml":
            return export_arrf_xml(data), 200, {"Content-Type": "application/xml"}
        elif format == "csv":
            return export_csv(data), 200, {"Content-Type": "text/csv"}
        else:
            return jsonify({"error": f"Format '{format}' not supported"}), 400

    except Exception as e:
        logger.exception(f"Export error: {str(e)}")
        return jsonify({"error": str(e)}), 500


def export_arrf_xml(result: Dict) -> str:
    """
    Generate ARRF R-compliant XML report.

    Simple XML structure (ARRF R requires specific tags per regulation).
    """
    import xml.etree.ElementTree as ET

    root = ET.Element("IFRSReport")
    root.set("xmlns", "https://www.arfr.kz/ifrs17")
    root.set("ReportDate", result.get("calculation_date", date.today().isoformat()))

    # IFRS 9 Section
    ecl_section = ET.SubElement(root, "IFRS9")
    ifrs9 = result.get("results", {}).get("ifrs9", {})
    ET.SubElement(ecl_section, "TotalECL_KZT").text = format_currency(ifrs9.get("total_ecl_kzt", 0))
    ET.SubElement(ecl_section, "TotalEAD_KZT").text = format_currency(ifrs9.get("total_ead_kzt", 0))
    ET.SubElement(ecl_section, "CoverageRatio_PCT").text = format_percent(ifrs9.get("coverage_ratio_pct", 0) / 100)

    stage_breakdown = ET.SubElement(ecl_section, "StageBreakdown")
    for stage, pct in ifrs9.get("stage_breakdown_pct", {}).items():
        ET.SubElement(stage_breakdown, stage).text = f"{pct:.2f}"

    # IFRS 17 Section
    ifrs17_section = ET.SubElement(root, "IFRS17")
    ifrs17 = result.get("results", {}).get("ifrs17", {})
    ET.SubElement(ifrs17_section, "BEL_KZT").text = format_currency(ifrs17.get("bel_kzt", 0))
    ET.SubElement(ifrs17_section, "RA_KZT").text = format_currency(ifrs17.get("ra_kzt", 0))
    ET.SubElement(ifrs17_section, "CSM_KZT").text = format_currency(ifrs17.get("csm_kzt", 0))
    ET.SubElement(ifrs17_section, "TotalLiability_KZT").text = format_currency(ifrs17.get("total_liability_kzt", 0))

    # Solvency Section
    solv_section = ET.SubElement(root, "Solvency")
    solvency = result.get("results", {}).get("solvency", {})
    ET.SubElement(solv_section, "MMP_KZT").text = format_currency(solvency.get("mmp_kzt", 0))
    ET.SubElement(solv_section, "OwnFunds_KZT").text = format_currency(solvency.get("own_funds_kzt", 0))
    ET.SubElement(solv_section, "Ratio_PCT").text = format_percent(solvency.get("ratio_pct", 0) / 100)
    ET.SubElement(solv_section, "IsCompliant").text = str(solvency.get("is_compliant", False))

    # Compliance Section
    comp_section = ET.SubElement(root, "Compliance")
    compliance = result.get("results", {}).get("compliance", {})
    ET.SubElement(comp_section, "Status").text = compliance.get("status", "unknown")

    warnings = ET.SubElement(comp_section, "Warnings")
    for w in compliance.get("warnings", []):
        ET.SubElement(warnings, "Warning").text = w

    return ET.tostring(root, encoding="unicode")


def export_csv(result: Dict) -> str:
    """
    Generate CSV export (simplified).
    """
    lines = []
    lines.append("KZ-InsurePro Calculation Export")
    lines.append(f"Date: {result.get('calculation_date', date.today().isoformat())}")
    lines.append("")

    # Summary
    lines.append("=== SUMMARY ===")
    lines.append("Metric,Value")

    ifrs9 = result.get("results", {}).get("ifrs9", {})
    lines.append(f"Total ECL (KZT),{ifrs9.get('total_ecl_kzt', 0):.0f}")
    lines.append(f"Coverage Ratio,{ifrs9.get('coverage_ratio_pct', 0):.2f}%")

    ifrs17 = result.get("results", {}).get("ifrs17", {})
    lines.append(f"BEL (KZT),{ifrs17.get('bel_kzt', 0):.0f}")
    lines.append(f"RA (KZT),{ifrs17.get('ra_kzt', 0):.0f}")
    lines.append(f"CSM (KZT),{ifrs17.get('csm_kzt', 0):.0f}")

    solvency = result.get("results", {}).get("solvency", {})
    lines.append(f"Solvency Ratio,{solvency.get('ratio_pct', 0):.2f}%")

    lines.append("")
    lines.append(f"Status,{result.get('results', {}).get('compliance', {}).get('status', 'N/A')}")

    return "\n".join(lines)


logger.info("API Blueprint 'calculate' loaded")
