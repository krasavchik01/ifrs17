#!/bin/bash
# KZ-InsurePro Phase 2 Setup Script
# Initializes PostgreSQL + Prisma for production deployment

set -e

echo "=========================================="
echo "KZ-InsurePro Phase 2: Database Setup"
echo "=========================================="
echo ""

# Configuration
DB_NAME=${DB_NAME:-"kz_insurepro_phase2"}
DB_USER=${DB_USER:-"kz_insurepro"}
DB_PASSWORD=${DB_PASSWORD:-"change_me_in_production"}
DB_HOST=${DB_HOST:-"localhost"}
DB_PORT=${DB_PORT:-"5432"}
ENVIRONMENT=${ENVIRONMENT:-"development"}

echo "[1/5] Checking PostgreSQL..."
if ! command -v psql &> /dev/null; then
    echo "ERROR: PostgreSQL is not installed. Please install PostgreSQL 14+"
    exit 1
fi

echo "[2/5] Creating database and user..."
psql -h $DB_HOST -U postgres << EOF
-- Create user
CREATE USER "$DB_USER" WITH PASSWORD '$DB_PASSWORD' CREATEDB;

-- Create database
CREATE DATABASE "$DB_NAME" OWNER "$DB_USER";

-- Enable extensions
\c $DB_NAME
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE "$DB_NAME" TO "$DB_USER";
GRANT ALL PRIVILEGES ON SCHEMA public TO "$DB_USER";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO "$DB_USER";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO "$DB_USER";
EOF

echo "[3/5] Setting environment variables..."
export DATABASE_URL="postgresql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
echo "DATABASE_URL=$DATABASE_URL"

# Create .env file
cat > .env << EOF
# Phase 2 Database Configuration
DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}
ENVIRONMENT=${ENVIRONMENT}
LOG_LEVEL=INFO
EOF

echo "[4/5] Running database migrations..."
psql -h $DB_HOST -U $DB_USER -d $DB_NAME < prisma/migrations/001_initial_schema.sql

echo "[5/5] Seeding demo data..."
psql -h $DB_HOST -U $DB_USER -d $DB_NAME << EOF
-- Demo tenant (Kazakhstan)
INSERT INTO tenants (
    code, name_kz, name_en, currency, regulator,
    nbrb_discount_rate, inflation_rate, data_center_location
) VALUES (
    'demo_tenant_kz',
    'Демо Тенант Казахстан',
    'Demo Tenant Kazakhstan',
    'KZT',
    'ARRF',
    0.05,
    0.085,
    'Astana'
) ON CONFLICT DO NOTHING;

-- Demo user
INSERT INTO users (tenant_id, email, name_kz, name_en, password_hash, role)
SELECT id, 'admin@demo.kz', 'Администратор', 'Administrator',
    'scrypt:\$2b\$12\$hash_placeholder', 'ADMIN'
FROM tenants WHERE code = 'demo_tenant_kz'
ON CONFLICT DO NOTHING;

-- Demo portfolio
INSERT INTO portfolios (tenant_id, name, reporting_date, is_active)
SELECT id, 'Q4 2024 Test Portfolio', NOW(), true
FROM tenants WHERE code = 'demo_tenant_kz'
ON CONFLICT DO NOTHING;
EOF

echo ""
echo "=========================================="
echo "Phase 2 Setup Complete!"
echo "=========================================="
echo ""
echo "Database Configuration:"
echo "  Name: $DB_NAME"
echo "  User: $DB_USER"
echo "  Host: $DB_HOST:$DB_PORT"
echo "  Connection: $DATABASE_URL"
echo ""
echo "Next steps:"
echo "  1. Copy .env to your environment"
echo "  2. Run: python -m pip install -r requirements.txt"
echo "  3. Start Flask: python run.py"
echo "  4. Test API: curl -X POST http://localhost:5000/api/calculate/suite ..."
echo ""
echo "Demo credentials:"
echo "  Email: admin@demo.kz"
echo "  Tenant: demo_tenant_kz"
echo ""
echo "Documentation:"
echo "  See PHASE_2_DATABASE.md for schema details"
echo ""
