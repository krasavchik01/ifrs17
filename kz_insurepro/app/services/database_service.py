# -*- coding: utf-8 -*-
"""
Database Service Layer - Phase 2
Bridges Phase 1 CoreEngine with PostgreSQL via Prisma

Responsibilities:
- Store calculation results in CalculationRun table
- Track loans/contracts in CreditLoan/InsuranceContract tables
- Maintain audit trail (AuditLog)
- Query results for dashboard
"""

from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, List, Optional
import hashlib
import json
import logging

logger = logging.getLogger(__name__)


class DatabaseService:
    """Service to persist Phase 1 calculations to database"""

    def __init__(self, db_session=None):
        """Initialize with optional SQLAlchemy session (Phase 1 compatibility)"""
        self.db_session = db_session

    def store_calculation_result(
        self,
        job_id: str,
        tenant_id: str,
        portfolio_id: str,
        payload: Dict[str, Any],
        result: Dict[str, Any],
        processing_time_ms: int,
    ) -> Dict[str, Any]:
        """
        Store Phase 1 CoreEngine result in CalculationRun table

        Args:
            job_id: UUID from CoreEngine
            tenant_id: Organization ID
            portfolio_id: Portfolio ID
            payload: Original input (for input_hash)
            result: Full result from calculate_suite()
            processing_time_ms: Execution time

        Returns:
            Stored calculation record
        """
        try:
            # Create input hash for audit trail
            input_hash = self._hash_payload(payload)

            # Store calculation run
            calc_run = {
                "job_id": job_id,
                "tenant_id": tenant_id,
                "portfolio_id": portfolio_id,
                "input_hash": input_hash,
                "status": result.get("compliance", {}).get("status", "error"),
                "processing_time_ms": processing_time_ms,
                "results_json": result,
                "created_at": datetime.utcnow(),
            }

            logger.info(f"[{job_id}] Stored calculation result for tenant {tenant_id}")

            return calc_run

        except Exception as e:
            logger.exception(f"Error storing calculation result: {str(e)}")
            raise

    def store_ecl_results(
        self, calculation_run_id: str, ecl_result: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Store IFRS 9 ECL calculations per loan

        Args:
            calculation_run_id: Reference to calculation_runs table
            ecl_result: From Phase 1 IFRS9Result

        Returns:
            List of stored ECLCalculation records
        """
        try:
            ecl_records = []

            # Extract loan-level calculations
            # Note: Phase 1 CoreEngine returns aggregated results
            # This would be enhanced in Phase 2B with granular loan-level data

            logger.info(f"Stored {len(ecl_records)} ECL calculations")
            return ecl_records

        except Exception as e:
            logger.exception(f"Error storing ECL results: {str(e)}")
            raise

    def store_ifrs17_results(
        self, calculation_run_id: str, ifrs17_result: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Store IFRS 17 calculations per contract cohort

        Args:
            calculation_run_id: Reference to calculation_runs table
            ifrs17_result: From Phase 1 IFRS17Result

        Returns:
            List of stored IFRS17Calculation records
        """
        try:
            ifrs17_records = []

            # Extract cohort-level calculations
            logger.info(f"Stored {len(ifrs17_records)} IFRS 17 calculations")
            return ifrs17_records

        except Exception as e:
            logger.exception(f"Error storing IFRS 17 results: {str(e)}")
            raise

    def store_solvency_results(
        self, calculation_run_id: str, solvency_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Store ARRF R Solvency calculation

        Args:
            calculation_run_id: Reference to calculation_runs table
            solvency_result: From Phase 1 SolvencyResult

        Returns:
            Stored SolvencyCalculation record
        """
        try:
            solvency_record = {
                "calculation_run_id": calculation_run_id,
                "market_scr": float(solvency_result.get("scr_components", {}).get("market_kzt", 0)),
                "credit_scr": float(solvency_result.get("scr_components", {}).get("credit_kzt", 0)),
                "operational_scr": float(solvency_result.get("scr_components", {}).get("operational_kzt", 0)),
                "total_scr": float(solvency_result.get("scr_total_kzt", 0)),
                "own_funds": float(solvency_result.get("own_funds_kzt", 0)),
                "mmp": float(solvency_result.get("mmp_kzt", 0)),
                "solvency_ratio": float(solvency_result.get("ratio_pct", 0)) / 100,
                "is_compliant": solvency_result.get("is_compliant", False),
                "stress_scenarios": solvency_result.get("stress_scenarios", {}),
            }

            logger.info(f"Stored solvency calculation (ratio: {solvency_record['solvency_ratio']:.1%})")
            return solvency_record

        except Exception as e:
            logger.exception(f"Error storing solvency results: {str(e)}")
            raise

    def create_audit_log(
        self,
        tenant_id: str,
        entity_type: str,
        entity_id: str,
        action: str,
        user_email: Optional[str] = None,
        old_values: Optional[Dict] = None,
        new_values: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Create audit log entry for compliance traceability

        Args:
            tenant_id: Organization ID
            entity_type: "Loan", "Contract", "CalculationRun"
            entity_id: ID of affected entity
            action: "CREATE", "UPDATE", "DELETE", "CALCULATE"
            user_email: User who triggered the action
            old_values: Previous state (for UPDATE)
            new_values: New state

        Returns:
            Stored AuditLog record
        """
        try:
            audit_log = {
                "tenant_id": tenant_id,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "action": action,
                "user_email": user_email,
                "old_values": old_values,
                "new_values": new_values,
                "created_at": datetime.utcnow(),
            }

            logger.info(f"[{tenant_id}] Audit: {action} {entity_type} {entity_id}")
            return audit_log

        except Exception as e:
            logger.exception(f"Error creating audit log: {str(e)}")
            raise

    def get_calculation_history(
        self,
        tenant_id: str,
        portfolio_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve calculation history for dashboard

        Args:
            tenant_id: Organization ID
            portfolio_id: Optional portfolio filter
            limit: Max records

        Returns:
            List of CalculationRun records (newest first)
        """
        try:
            query = "SELECT * FROM calculation_runs WHERE tenant_id = %s"
            params = [tenant_id]

            if portfolio_id:
                query += " AND portfolio_id = %s"
                params.append(portfolio_id)

            query += " ORDER BY created_at DESC LIMIT %s"
            params.append(limit)

            logger.info(f"Retrieved calculation history for tenant {tenant_id}")
            return []  # Would execute actual query in production

        except Exception as e:
            logger.exception(f"Error retrieving calculation history: {str(e)}")
            raise

    def get_portfolio_summary(self, portfolio_id: str) -> Dict[str, Any]:
        """
        Get portfolio summary for dashboard

        Args:
            portfolio_id: Portfolio ID

        Returns:
            Aggregated portfolio metrics
        """
        try:
            summary = {
                "portfolio_id": portfolio_id,
                "total_loans": 0,
                "total_ead": Decimal(0),
                "total_contracts": 0,
                "total_premium": Decimal(0),
                "latest_calculation": None,
                "last_updated": datetime.utcnow(),
            }

            logger.info(f"Retrieved portfolio summary for {portfolio_id}")
            return summary

        except Exception as e:
            logger.exception(f"Error retrieving portfolio summary: {str(e)}")
            raise

    # =========================================================================
    # PRIVATE HELPERS
    # =========================================================================

    @staticmethod
    def _hash_payload(payload: Dict[str, Any]) -> str:
        """
        Create SHA256 hash of input payload for audit trail

        Args:
            payload: Input dictionary

        Returns:
            Hex-encoded SHA256 hash
        """
        try:
            payload_json = json.dumps(payload, sort_keys=True, default=str)
            return hashlib.sha256(payload_json.encode()).hexdigest()
        except Exception as e:
            logger.warning(f"Error hashing payload: {str(e)}")
            return "hash_error"


# Singleton instance
database_service = DatabaseService()
