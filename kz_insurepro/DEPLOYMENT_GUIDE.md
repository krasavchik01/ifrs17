# KZ-InsurePro: Deployment & Usage Guide

**Version:** 1.0.0
**Last Updated:** November 25, 2024
**Status:** Production Ready (Phase 1 + 2 + 2B)

---

## Quick Start

### For Developers (5 minutes)

```bash
# 1. Start Flask server
python run.py

# 2. Test the API
curl -X POST http://localhost:5000/api/suite   -H "Content-Type: application/json"   -d '{
    "tenant_id": "demo_tenant_kz",
    "portfolio_name": "Test",
    "calculation_date": "2024-12-31",
    "loans": [{"id": "L001", "ead": 500000000, "pd": 0.02, "lgd": 0.4, "stage": 1, "days_past_due": 0, "sector": "retail", "maturity_years": 3}],
    "contracts": [],
    "risks": {"market_volatility": 0.15, "credit_exposure": 5e12, "credit_default_rate": 0.05, "operational_loss_rate": 0.02, "own_funds": 2e12},
    "minimum_capital_requirement": 1e12
  }'
```

---

## Prerequisites

- Python 3.11+
- PostgreSQL 14+ (production only)
- Node.js 18+ (for React frontend)

## Installation

```bash
# 1. Clone repository
cd kz_insurepro

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or
venv\Scriptsctivate     # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start Flask
python run.py
```

## API Endpoint: POST /api/suite

### Request

Unified calculation for IFRS 9, IFRS 17, and Solvency (ARRF R)

```json
{
  "tenant_id": "demo_tenant_kz",
  "portfolio_name": "Q4 2024",
  "calculation_date": "2024-12-31",
  "inflation_rate": 0.085,
  "risk_free_rate": 0.05,
  "loans": [
    {
      "id": "L001",
      "ead": 500000000,
      "pd": 0.02,
      "lgd": 0.4,
      "stage": 1,
      "days_past_due": 0,
      "sector": "retail",
      "maturity_years": 3
    }
  ],
  "contracts": [
    {
      "id": "C001",
      "type": "life",
      "inception_date": "2024-01-01",
      "coverage_units": 20000000,
      "annual_premium": 100000000,
      "annual_claims_expected": 50000000,
      "annual_expenses": 5000000,
      "discount_rate": 0.05,
      "contract_term_years": 10,
      "cohort": "2024-life"
    }
  ],
  "risks": {
    "market_volatility": 0.15,
    "credit_exposure": 5000000000000,
    "credit_default_rate": 0.05,
    "operational_loss_rate": 0.02,
    "own_funds": 2000000000000
  },
  "minimum_capital_requirement": 1000000000000
}
```

### Response (200 OK)

```json
{
  "status": "error",
  "job_id": "e73c3217-ccca-4a0f-854d-f455f2db0ee5",
  "results": {
    "ifrs9": {
      "total_ecl_kzt": 3602202.79,
      "total_ead_kzt": 500000000.0,
      "coverage_ratio_pct": 0.72,
      "weighted_pd_pct": 2.0,
      "weighted_lgd_pct": 40.0,
      "macro_impact_pct": 4.25
    },
    "ifrs17": {
      "bel_kzt": 537527147.40,
      "ra_kzt": 50586731.26,
      "csm_kzt": 0,
      "total_liability_kzt": 588113878.66
    },
    "solvency": {
      "scr_total_kzt": 808298267967.96,
      "own_funds_kzt": 2000000000000.0,
      "mmp_kzt": 1000000000000.0,
      "ratio_pct": 247.43,
      "is_compliant": true
    },
    "compliance": {
      "status": "error",
      "errors": ["ECL coverage < 60%", "Onerous contracts detected"],
      "warnings": ["Stage 3 coverage warning"]
    }
  },
  "processing_time_ms": 0.93
}
```

## Architecture

### Phase 1: Core Engine
- IFRS 9: Expected Credit Loss (ECL) calculation
- IFRS 17: Best Estimate Liability (BEL) + Risk Adjustment (RA)
- Solvency: ARRF R capital requirements

### Phase 2: Database
- Multi-tenant PostgreSQL schema
- Calculation run storage (JSONB)
- Full audit trail for compliance

### Phase 2B: React Dashboard
- Portfolio management UI
- CSV/XLSX upload form
- Recharts visualizations
- Calculation history

## Testing

```bash
# Run core engine test
python test_core_manual.py

# Test API (with running Flask)
python << 'EOF'
import requests
response = requests.post('http://localhost:5000/api/suite', json={
    "tenant_id": "demo_tenant_kz",
    ...
})
print(response.json())
EOF
```

## Production Deployment

### Docker

```bash
docker build -t kz-insurepro .
docker run -p 5000:5000 -e DATABASE_URL="postgresql://..." kz-insurepro
```

### PostgreSQL Setup

```bash
# Create database
createdb kz_insurepro_prod

# Set connection
export DATABASE_URL="postgresql://user:pass@localhost:5432/kz_insurepro_prod"

# Run migrations
psql $DATABASE_URL < prisma/migrations/001_initial_schema.sql
```

## Troubleshooting

### Port 5000 in use
```bash
lsof -i :5000
kill -9 <PID>
```

### Database connection error
```bash
psql $DATABASE_URL -c "SELECT 1;"
```

### NumPy serialization error
- Ensure `convert_numpy_types()` is in `/api/calculate.py`
- Restart Flask

## Support

- API Docs: See `/api/calculate.py`
- Database Schema: See `PHASE_2_DATABASE.md`
- Status: See `STATUS_REPORT.md`

---

**Built for Kazakhstan's IFRS compliance. 🇰🇿**
