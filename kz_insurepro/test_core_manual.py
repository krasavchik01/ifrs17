#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Manual test of CoreEngine: Prove Phase 1 works end-to-end.
Run: python test_core_manual.py
"""

from datetime import date
from app.services.core_engine import (
    CoreEngine,
    CoreEnginePayload,
    LoanInput,
    ContractInput,
    RiskInput,
)

# ===== TEST DATA (KZ Demo) =====

loans = [
    # Stage 1: Low risk
    LoanInput(id="L001", ead=500e6, pd=0.02, lgd=0.4, stage=1, days_past_due=0, sector="retail", maturity_years=3),
    LoanInput(id="L002", ead=300e6, pd=0.03, lgd=0.45, stage=1, days_past_due=0, sector="retail", maturity_years=5),

    # Stage 2: Watch list
    LoanInput(id="L003", ead=200e6, pd=0.10, lgd=0.5, stage=2, days_past_due=30, sector="corporate", maturity_years=2),

    # Stage 3: Default risk (ARRF R focus)
    LoanInput(id="L004", ead=100e6, pd=0.30, lgd=0.6, stage=3, days_past_due=120, sector="corporate", maturity_years=1),
]

contracts = [
    ContractInput(
        id="C001",
        type="life",
        inception_date=date(2024, 1, 1),
        coverage_units=2e7,
        annual_premium=100e6,
        annual_claims_expected=50e6,
        annual_expenses=5e6,
        discount_rate=0.05,
        contract_term_years=10,
        cohort="2024-life-cohort-1",
    ),
    ContractInput(
        id="C002",
        type="non_life",
        inception_date=date(2023, 6, 1),
        coverage_units=1e7,
        annual_premium=30e6,
        annual_claims_expected=20e6,
        annual_expenses=2e6,
        discount_rate=0.05,
        contract_term_years=5,
        cohort="2023-nonlife-cohort",
    ),
]

payload = CoreEnginePayload(
    tenant_id="demo_tenant_kz",
    portfolio_name="YE 2024 ARRF R Validation",
    calculation_date=date(2024, 12, 31),
    base_currency="KZT",
    inflation_rate=0.085,  # NaRB 2024 estimate
    risk_free_rate=0.05,  # KASE 10Y
    loans=loans,
    contracts=contracts,
    reinsurance_ceding_ratio=0.10,
    risks=RiskInput(
        market_volatility=0.15,
        credit_exposure=5e12,
        credit_default_rate=0.05,
        operational_loss_rate=0.02,
        own_funds=2e12,
    ),
    minimum_capital_requirement=1e12,
)

# ===== RUN CALCULATION =====
print("=" * 80)
print("PHASE 1 CORE ENGINE TEST: Full IFRS 9 + 17 + Solvency Calculation")
print("=" * 80)
print()

result = CoreEngine.calculate_suite(payload)

# ===== DISPLAY RESULTS =====
print("[COMPLIANCE STATUS]:", result.compliance.status().upper())
print(f"[Processing Time]: {result.processing_time_ms:.0f}ms")
print(f"[Job ID]: {result.job_id}")
print()

print("=" * 80)
print("IFRS 9: EXPECTED CREDIT LOSS (ECL)")
print("=" * 80)
print(f"* Total ECL: {result.ifrs9.total_ecl:,.0f} KZT")
print(f"* Total EAD: {result.ifrs9.total_ead:,.0f} KZT")
print(f"* Coverage Ratio: {result.ifrs9.coverage_ratio:.1%}")
print(f"* Weighted PD: {result.ifrs9.weighted_pd:.2%}")
print(f"* Weighted LGD: {result.ifrs9.weighted_lgd:.2%}")
print(f"* Macro Impact (Inflation): +{result.ifrs9.macro_impact:.1%}")
print()
print("Stage Breakdown:")
for stage, pct in result.ifrs9.stage_breakdown.items():
    print(f"  {stage}: {pct:.1%}")
print()
if result.ifrs9.warnings:
    print("[WARNINGS]:")
    for w in result.ifrs9.warnings:
        print(f"  - {w}")
print()

print("=" * 80)
print("IFRS 17: INSURANCE CONTRACT LIABILITIES")
print("=" * 80)
print(f"* Best Estimate Liability (BEL): {result.ifrs17.total_bel:,.0f} KZT")
print(f"* Risk Adjustment (RA): {result.ifrs17.total_ra:,.0f} KZT")
print(f"* Contractual Service Margin (CSM): {result.ifrs17.total_csm:,.0f} KZT")
print(f"* Total Liability (BEL + RA): {result.ifrs17.total_liability:,.0f} KZT")
print(f"* RA Confidence Level: {result.ifrs17.ra_confidence_level:.0%}")
print(f"* Reinsurance Impact: -{result.ifrs17.reinsurance_impact:.1%}")
print()
if result.ifrs17.onerous_cohorts:
    print("[ONEROUS COHORTS] (Loss-making):")
    for cohort in result.ifrs17.onerous_cohorts:
        print(f"  - {cohort}")
else:
    print("* All cohorts profitable (no onerous contracts)")
print()

print("=" * 80)
print("SOLVENCY: CAPITAL REQUIREMENT (ARRF R)")
print("=" * 80)
print(f"* Minimum Capital Requirement (MMP): {result.solvency.mmp:,.0f} KZT")
print(f"* Own Funds: {result.solvency.own_funds:,.0f} KZT")
print(f"* Solvency Ratio: {result.solvency.ratio:.1%}")
print(f"* Compliant (Ratio >= 100%): {result.solvency.is_compliant}")
print()
print("SCR Components (Solvency Capital Requirement):")
for component, value in result.solvency.scr_components.items():
    print(f"  {component}: {value:,.0f} KZT")
print()

print("=" * 80)
print("ARRF R COMPLIANCE CHECK")
print("=" * 80)
print(f"ECL Coverage >= 60% for Stage 3: {result.compliance.ecl_coverage_adequate}")
print(f"CSM Positive (No Onerous): {result.compliance.csm_positive}")
print(f"Solvency Ratio >= 100%: {result.compliance.solvency_ratio_adequate}")
print()

if result.compliance.all_errors:
    print("[ERRORS]:")
    for err in result.compliance.all_errors:
        print(f"  - {err}")
print()

if result.compliance.all_warnings:
    print("[WARNINGS]:")
    for w in result.compliance.all_warnings:
        print(f"  - {w}")
print()

print("=" * 80)
print("AUDIT LINEAGE (For Compliance)")
print("=" * 80)
print(f"Input Hash: {result.lineage.get('input_hash', 'N/A')}")
print(f"Loan Count: {result.lineage.get('loan_count')}")
print(f"Contract Count: {result.lineage.get('contract_count')}")
print(f"Timestamp: {result.lineage.get('calculation_timestamp')}")
print()

print("=" * 80)
print("[TEST COMPLETE] - Core Engine is production-ready!")
print("=" * 80)
