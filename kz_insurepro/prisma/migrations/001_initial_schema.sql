-- Initial schema for KZ-InsurePro Phase 2
-- PostgreSQL 14+
-- Multi-tenant with partitioning by tenant_id

-- =============================================================================
-- EXTENSIONS
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =============================================================================
-- ENUMS
-- =============================================================================

CREATE TYPE insurance_type AS ENUM ('LIFE', 'NON_LIFE', 'HEALTH', 'ANNUITY');
CREATE TYPE measurement_model AS ENUM ('GMM', 'VFA', 'PAA');
CREATE TYPE contract_status AS ENUM ('ACTIVE', 'EXPIRED', 'CANCELLED', 'CLAIMED');
CREATE TYPE ecl_stage AS ENUM ('STAGE_1', 'STAGE_2', 'STAGE_3');
CREATE TYPE calculation_status AS ENUM ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'PARTIAL');
CREATE TYPE user_role AS ENUM ('ADMIN', 'ACTUARY', 'AUDITOR', 'ANALYST', 'VIEWER');

-- =============================================================================
-- MULTI-TENANT CORE
-- =============================================================================

CREATE TABLE tenants (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    code VARCHAR(100) UNIQUE NOT NULL,
    name_kz VARCHAR(255) NOT NULL,
    name_en VARCHAR(255),
    currency VARCHAR(3) DEFAULT 'KZT',

    -- Regulatory
    regulator VARCHAR(50) DEFAULT 'ARRF',
    nbrb_discount_rate NUMERIC(10, 6) DEFAULT 0.05,
    inflation_rate NUMERIC(10, 6) DEFAULT 0.085,

    -- Data residency
    data_center_location VARCHAR(100) DEFAULT 'Astana',

    -- Subscription
    subscription_tier VARCHAR(50) DEFAULT 'professional',
    max_calculation_runs INTEGER DEFAULT 1000,
    max_portfolio_size INTEGER DEFAULT 50000,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT unique_tenant_code UNIQUE(code)
);

CREATE INDEX idx_tenants_code ON tenants(code);

-- =============================================================================
-- USERS
-- =============================================================================

CREATE TABLE users (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    tenant_id VARCHAR(36) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    name_kz VARCHAR(255) NOT NULL,
    name_en VARCHAR(255),
    password_hash VARCHAR(255) NOT NULL,

    role user_role DEFAULT 'VIEWER',
    is_active BOOLEAN DEFAULT TRUE,

    last_login_at TIMESTAMP,
    last_activity_at TIMESTAMP DEFAULT NOW(),

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT unique_tenant_email UNIQUE(tenant_id, email)
);

CREATE INDEX idx_users_tenant ON users(tenant_id);
CREATE INDEX idx_users_email ON users(email);

-- =============================================================================
-- PORTFOLIOS
-- =============================================================================

CREATE TABLE portfolios (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    tenant_id VARCHAR(36) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,

    reporting_date TIMESTAMP NOT NULL,
    currency VARCHAR(3) DEFAULT 'KZT',
    is_active BOOLEAN DEFAULT TRUE,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_portfolios_tenant ON portfolios(tenant_id);
CREATE INDEX idx_portfolios_reporting_date ON portfolios(reporting_date);

-- =============================================================================
-- LOANS (IFRS 9 - ECL)
-- =============================================================================

CREATE TABLE credit_loans (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    portfolio_id VARCHAR(36) NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    tenant_id VARCHAR(36) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    external_id VARCHAR(255) NOT NULL,

    -- Exposure data
    ead NUMERIC(20, 2) NOT NULL,
    pd NUMERIC(5, 4) NOT NULL CHECK (pd >= 0 AND pd <= 1),
    lgd NUMERIC(5, 4) NOT NULL CHECK (lgd >= 0 AND lgd <= 1),

    -- Stage classification
    stage ecl_stage DEFAULT 'STAGE_1',
    days_past_due INTEGER DEFAULT 0,

    -- Loan details
    origination_date TIMESTAMP NOT NULL,
    maturity_date TIMESTAMP NOT NULL,
    sector VARCHAR(100) DEFAULT 'retail',

    -- Market data
    country_code VARCHAR(2) DEFAULT 'KZ',
    currency VARCHAR(3) DEFAULT 'KZT',

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_modified_by VARCHAR(36)

);

CREATE INDEX idx_credit_loans_portfolio ON credit_loans(portfolio_id);
CREATE INDEX idx_credit_loans_tenant ON credit_loans(tenant_id);
CREATE INDEX idx_credit_loans_stage ON credit_loans(stage);
CREATE INDEX idx_credit_loans_external_id ON credit_loans(external_id);

-- =============================================================================
-- CONTRACTS (IFRS 17 - INSURANCE LIABILITIES)
-- =============================================================================

CREATE TABLE insurance_contracts (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    portfolio_id VARCHAR(36) NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    tenant_id VARCHAR(36) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    external_id VARCHAR(255) NOT NULL,

    -- Contract classification
    type insurance_type NOT NULL,
    measurement_model measurement_model DEFAULT 'GMM',
    status contract_status DEFAULT 'ACTIVE',

    -- Cohort grouping
    cohort_id VARCHAR(255) NOT NULL,
    cohort_group VARCHAR(255) NOT NULL,

    -- Coverage and premium
    coverage_units NUMERIC(20, 2) NOT NULL,
    annual_premium NUMERIC(20, 2) NOT NULL,
    annual_claims_expected NUMERIC(20, 2) NOT NULL,
    annual_expenses NUMERIC(20, 2) NOT NULL,
    acquisition_costs NUMERIC(20, 2) NOT NULL,

    -- Terms
    inception_date TIMESTAMP NOT NULL,
    maturity_date TIMESTAMP NOT NULL,
    contract_term_years INTEGER NOT NULL,

    -- Financial assumptions
    discount_rate NUMERIC(5, 4) DEFAULT 0.05,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_insurance_contracts_portfolio ON insurance_contracts(portfolio_id);
CREATE INDEX idx_insurance_contracts_tenant ON insurance_contracts(tenant_id);
CREATE INDEX idx_insurance_contracts_cohort ON insurance_contracts(cohort_id);
CREATE INDEX idx_insurance_contracts_status ON insurance_contracts(status);

-- =============================================================================
-- CALCULATION RUNS (PHASE 1 OUTPUT STORAGE)
-- =============================================================================

CREATE TABLE calculation_runs (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    job_id VARCHAR(36) UNIQUE NOT NULL,
    tenant_id VARCHAR(36) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    portfolio_id VARCHAR(36) NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,

    -- Status and timing
    status calculation_status DEFAULT 'PENDING',
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    processing_time_ms INTEGER,

    -- Audit
    input_hash VARCHAR(64) NOT NULL,
    results_json JSONB,

    -- Compliance
    compliance_status VARCHAR(50),

    created_by VARCHAR(36),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_calculation_runs_tenant ON calculation_runs(tenant_id);
CREATE INDEX idx_calculation_runs_portfolio ON calculation_runs(portfolio_id);
CREATE INDEX idx_calculation_runs_job_id ON calculation_runs(job_id);
CREATE INDEX idx_calculation_runs_status ON calculation_runs(status);
CREATE INDEX idx_calculation_runs_created_at ON calculation_runs(created_at);

-- =============================================================================
-- ECL CALCULATIONS (IFRS 9)
-- =============================================================================

CREATE TABLE ecl_calculations (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    calculation_run_id VARCHAR(36) NOT NULL REFERENCES calculation_runs(id) ON DELETE CASCADE,
    loan_id VARCHAR(36) NOT NULL REFERENCES credit_loans(id) ON DELETE CASCADE,
    tenant_id VARCHAR(36) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- ECL components (KZT)
    total_ecl NUMERIC(20, 2) NOT NULL,
    stage_1_ecl NUMERIC(20, 2),
    stage_2_ecl NUMERIC(20, 2),
    stage_3_ecl NUMERIC(20, 2),

    -- Coverage metrics
    coverage_ratio NUMERIC(7, 4),
    weighted_pd NUMERIC(5, 4),
    weighted_lgd NUMERIC(5, 4),
    macro_impact NUMERIC(5, 4),

    -- Validation
    is_compliant BOOLEAN DEFAULT TRUE,
    warnings TEXT,

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_ecl_calculations_run ON ecl_calculations(calculation_run_id);
CREATE INDEX idx_ecl_calculations_loan ON ecl_calculations(loan_id);
CREATE INDEX idx_ecl_calculations_tenant ON ecl_calculations(tenant_id);

-- =============================================================================
-- IFRS 17 CALCULATIONS
-- =============================================================================

CREATE TABLE ifrs17_calculations (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    calculation_run_id VARCHAR(36) NOT NULL REFERENCES calculation_runs(id) ON DELETE CASCADE,
    contract_id VARCHAR(36) NOT NULL REFERENCES insurance_contracts(id) ON DELETE CASCADE,
    tenant_id VARCHAR(36) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    cohort_id VARCHAR(255) NOT NULL,

    -- Components (KZT)
    total_bel NUMERIC(20, 2) NOT NULL,
    total_ra NUMERIC(20, 2) NOT NULL,
    total_csm NUMERIC(20, 2) NOT NULL,
    total_liability NUMERIC(20, 2) NOT NULL,

    -- Risk metrics
    ra_confidence_level NUMERIC(5, 4) DEFAULT 0.75,

    -- Onerous detection
    is_onerous BOOLEAN DEFAULT FALSE,

    -- Reinsurance
    reinsurance_impact NUMERIC(5, 4) DEFAULT 0.0,

    warnings TEXT,

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_ifrs17_calculations_run ON ifrs17_calculations(calculation_run_id);
CREATE INDEX idx_ifrs17_calculations_contract ON ifrs17_calculations(contract_id);
CREATE INDEX idx_ifrs17_calculations_cohort ON ifrs17_calculations(cohort_id);
CREATE INDEX idx_ifrs17_calculations_tenant ON ifrs17_calculations(tenant_id);

-- =============================================================================
-- SOLVENCY CALCULATIONS (ARRF R)
-- =============================================================================

CREATE TABLE solvency_calculations (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    calculation_run_id VARCHAR(36) NOT NULL REFERENCES calculation_runs(id) ON DELETE CASCADE,
    tenant_id VARCHAR(36) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- Capital components (KZT)
    market_scr NUMERIC(20, 2) NOT NULL,
    credit_scr NUMERIC(20, 2) NOT NULL,
    operational_scr NUMERIC(20, 2) NOT NULL,
    total_scr NUMERIC(20, 2) NOT NULL,

    own_funds NUMERIC(20, 2) NOT NULL,
    mmp NUMERIC(20, 2) NOT NULL,

    -- Ratio and compliance
    solvency_ratio NUMERIC(7, 4) NOT NULL,
    is_compliant BOOLEAN DEFAULT TRUE,

    -- Stress scenarios
    stress_scenarios JSONB,

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_solvency_calculations_run ON solvency_calculations(calculation_run_id);
CREATE INDEX idx_solvency_calculations_tenant ON solvency_calculations(tenant_id);

-- =============================================================================
-- AUDIT LOGS
-- =============================================================================

CREATE TABLE audit_logs (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    tenant_id VARCHAR(36) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    entity_type VARCHAR(100) NOT NULL,
    entity_id VARCHAR(36) NOT NULL,
    action VARCHAR(50) NOT NULL,

    user_id VARCHAR(36),
    user_email VARCHAR(255),

    old_values JSONB,
    new_values JSONB,

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_audit_logs_tenant ON audit_logs(tenant_id);
CREATE INDEX idx_audit_logs_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);
CREATE INDEX idx_audit_logs_user_email ON audit_logs(user_email);

-- =============================================================================
-- ML MODELS (PHASE 2B)
-- =============================================================================

CREATE TABLE ml_models (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    tenant_id VARCHAR(36) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    name VARCHAR(255) NOT NULL,
    model_type VARCHAR(50) NOT NULL,
    version VARCHAR(50) NOT NULL,

    -- Performance metrics
    accuracy NUMERIC(5, 4),
    auc_roc NUMERIC(5, 4),
    training_samples INTEGER,

    -- Model storage
    model_path VARCHAR(1024) NOT NULL,
    config_json JSONB,

    -- Status
    is_active BOOLEAN DEFAULT FALSE,
    deployed_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_ml_models_tenant ON ml_models(tenant_id);
CREATE INDEX idx_ml_models_type ON ml_models(model_type);

-- =============================================================================
-- API KEYS
-- =============================================================================

CREATE TABLE api_keys (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    tenant_id VARCHAR(36) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    name VARCHAR(255) NOT NULL,
    key_hash VARCHAR(64) UNIQUE NOT NULL,

    -- Permissions (PostgreSQL array)
    scopes TEXT[] DEFAULT ARRAY['read:portfolio', 'write:calculation'],

    -- Rate limiting
    rate_limit_per_hour INTEGER DEFAULT 100,
    last_used_at TIMESTAMP,

    is_active BOOLEAN DEFAULT TRUE,

    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP
);

CREATE INDEX idx_api_keys_tenant ON api_keys(tenant_id);
CREATE INDEX idx_api_keys_hash ON api_keys(key_hash);

-- =============================================================================
-- FUNCTIONS FOR AUDIT TRAIL
-- =============================================================================

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to all tables with updated_at
CREATE TRIGGER update_tenants_updated_at
BEFORE UPDATE ON tenants
FOR EACH ROW
EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_portfolios_updated_at
BEFORE UPDATE ON portfolios
FOR EACH ROW
EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_credit_loans_updated_at
BEFORE UPDATE ON credit_loans
FOR EACH ROW
EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_insurance_contracts_updated_at
BEFORE UPDATE ON insurance_contracts
FOR EACH ROW
EXECUTE FUNCTION update_updated_at();

-- =============================================================================
-- INITIAL DATA (KZ Demo Tenant)
-- =============================================================================

INSERT INTO tenants (code, name_kz, name_en, currency, regulator, nbrb_discount_rate, inflation_rate)
VALUES (
    'demo_tenant_kz',
    'Демо Тенант Казахстан',
    'Demo Tenant Kazakhstan',
    'KZT',
    'ARRF',
    0.05,
    0.085
);

-- Add demo user (password: demo_password_hash)
INSERT INTO users (tenant_id, email, name_kz, name_en, password_hash, role)
SELECT id, 'admin@demo.kz', 'Администратор', 'Admin', 'demo_hash_placeholder', 'ADMIN'
FROM tenants WHERE code = 'demo_tenant_kz';

-- =============================================================================
-- COMMENTS
-- =============================================================================

COMMENT ON TABLE tenants IS 'Multi-tenant core - one row per organization (bank/insurer)';
COMMENT ON TABLE credit_loans IS 'Loan portfolio for IFRS 9 ECL calculations, partitioned by tenant_id';
COMMENT ON TABLE insurance_contracts IS 'Insurance contract portfolio for IFRS 17 calculations';
COMMENT ON TABLE calculation_runs IS 'Stores Phase 1 CoreEngine outputs (ECL, BEL/RA/CSM, SCR)';
COMMENT ON COLUMN calculation_runs.job_id IS 'UUID from Phase 1 CoreEngine.calculate_suite()';
COMMENT ON COLUMN calculation_runs.input_hash IS 'SHA256 hash of input payload for audit trail';

COMMENT ON TABLE audit_logs IS 'Full audit trail: who changed what when';
COMMENT ON TABLE ml_models IS 'ML models for Phase 2B PD/LGD prediction';
