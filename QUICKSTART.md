# ⚡ Quick Start Guide - IFRS 17 Pro

Get your IFRS 17 automation system up and running in 5 minutes!

## 🚀 1-Minute Setup (Local Development)

```bash
# Clone and navigate


# Install dependencies
npm install

# Set up environment
cp .env.example .env

# Update .env with your database URL:
# DATABASE_URL="postgresql://user:pass@localhost:5432/ifrs17"

# Run database migrations
npx prisma migrate dev

# Start development server
npm run dev
```

Visit http://localhost:3000 🎉

## 📦 What's Included

### ✅ Complete IFRS 17 Implementation
- CSM (Contractual Service Margin) calculations
- Risk Adjustment (Insurance, Financial, Operational)
- Fulfilment Cash Flows with PV calculations
- GMM, PAA, VFA measurement models

### ✅ SaaS Features
- Multi-tenant architecture
- User authentication & RBAC
- Stripe subscription management
- Real-time analytics dashboard

### ✅ Enterprise-Grade
- Audit logging
- Regulatory compliance
- Data export (Excel, PDF)
- API-first design

## 🎯 First Steps

### 1. Create Your Organization

```typescript
// Demo account is pre-configured
Email: demo@ifrs17pro.com
Password: demo123
```

### 2. Add Your First Contract

Navigate to **Dashboard → New Contract**

```javascript
Contract Number: POL-2024-001
Type: Life Insurance
Product Line: Life
Measurement Model: GMM
Inception Date: 2024-01-01
Coverage Period: 20 years
Sum Insured: 1,000,000 KZT
```

### 3. Calculate CSM

Go to **CSM → Calculate**

```javascript
Contract: POL-2024-001
Reporting Date: 2024-12-31
Discount Rate: 5%
Coverage Units: 20,000,000
Units Released: 1,000,000
```

### 4. Generate Report

Navigate to **Reports → Generate**

```javascript
Report Type: CSM Roll-Forward
Period: Q4 2024
Format: Excel / PDF
```

## 🌐 Deploy to Vercel in 2 Minutes

### Option 1: One-Click Deploy

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/krasavchik01/ifrs17)

### Option 2: Vercel CLI

```bash
# Install Vercel CLI
npm i -g vercel

# Login to Vercel
vercel login

# Deploy to production

vercel --prod
```

Add environment variables in Vercel Dashboard:
- `DATABASE_URL`
- `NEXTAUTH_SECRET`
- `NEXTAUTH_URL`
- `STRIPE_SECRET_KEY`
- `STRIPE_PUBLISHABLE_KEY`

## 📊 Sample Data

### Create Sample Contracts

```bash
# We'll add a seed script
npx prisma db seed
```

This creates:
- 10 sample insurance contracts
- 5 cohorts (by product line and year)
- Historical CSM calculations
- Sample claims data

## 🎓 Learn by Example

### Example 1: Calculate Initial CSM

```typescript
import { calculateInitialCSM } from '@/lib/ifrs17/csm';

const csm = calculateInitialCSM(
  1_200_000, // PV of inflows (premiums)
  1_000_000, // PV of outflows (claims + expenses)
  50_000     // Risk adjustment
);

console.log(csm); // 150,000
```

### Example 2: Project Cash Flows

```typescript
import { projectPremiumCashFlows } from '@/lib/ifrs17/cash-flows';

const cashFlows = projectPremiumCashFlows(
  120_000,              // Annual premium
  20,                   // Contract duration (years)
  'monthly',            // Payment frequency
  new Date('2024-01-01') // Inception date
);

console.log(cashFlows.length); // 240 payments (20 years × 12 months)
```

### Example 3: Calculate Risk Adjustment

```typescript
import { calculateRiskAdjustmentConfidenceLevel } from '@/lib/ifrs17/risk-adjustment';

const riskAdj = calculateRiskAdjustmentConfidenceLevel(
  0,         // Expected value (mean)
  100_000,   // Standard deviation
  0.75       // 75% confidence level
);

console.log(riskAdj); // ~67,400
```

## 🔑 API Examples

### Authentication

```bash
curl -X POST http://localhost:3000/api/auth/signin \
  -H "Content-Type: application/json" \
  -d '{
    "email": "demo@ifrs17pro.com",
    "password": "demo123"
  }'
```

### Create Contract

```bash
curl -X POST http://localhost:3000/api/contracts \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "contractNumber": "POL-2024-001",
    "contractType": "life",
    "productLine": "life",
    "measurementModel": "GMM",
    "profitability": "profitable",
    "inceptionDate": "2024-01-01",
    "coverageStartDate": "2024-01-01",
    "coverageEndDate": "2044-01-01",
    "nominalAmount": 1000000,
    "currency": "KZT"
  }'
```

### Calculate CSM

```bash
curl -X POST http://localhost:3000/api/csm/calculate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "contractId": "contract-id",
    "reportingDate": "2024-12-31",
    "periodStart": "2024-01-01",
    "periodEnd": "2024-12-31",
    "discountRate": 0.05,
    "totalCoverageUnits": 20000000,
    "coverageUnitsReleased": 1000000
  }'
```

## 📱 Mobile Testing

Test on mobile devices using ngrok:

```bash
# Install ngrok
npm install -g ngrok

# Start your dev server
npm run dev

# In another terminal, expose it
ngrok http 3000
```

Share the ngrok URL with your team!

## 🐳 Docker Setup (Optional)

```bash
# Build Docker image
docker build -t ifrs17-saas .

# Run with Docker Compose
docker-compose up

# Includes PostgreSQL and app
```

## 🔧 Common Issues

### Issue: Prisma Client not generated

```bash
npx prisma generate
```

### Issue: Database connection fails

Check your `DATABASE_URL` format:
```
postgresql://USER:PASSWORD@HOST:PORT/DATABASE?schema=public
```

### Issue: Module not found

```bash
rm -rf node_modules package-lock.json
npm install
```

### Issue: TypeScript errors

```bash
npm run build
```

## 📚 Next Steps

1. **Read the Docs**: [Full documentation](./README.md)
2. **Deploy**: [Deployment guide](./DEPLOYMENT.md)
3. **Contribute**: [Contributing guide](./CONTRIBUTING.md)
4. **Architecture**: [Technical details](./ARCHITECTURE.md)

## 💬 Get Help

- **GitHub Issues**: Report bugs
- **Discussions**: Ask questions
- **Discord**: Join community
- **Email**: support@ifrs17pro.com

## 🎯 Checklist for Production

- [ ] Database is on managed PostgreSQL
- [ ] Environment variables are set
- [ ] Stripe is in live mode
- [ ] Custom domain configured
- [ ] SSL certificate active
- [ ] Error monitoring enabled
- [ ] Backups configured
- [ ] Team members invited
- [ ] First contract created
- [ ] First calculation run
- [ ] First report generated

## 🌟 Features Roadmap

### Coming Soon
- [ ] Batch import from Excel
- [ ] Custom report templates
- [ ] Email notifications
- [ ] API rate limiting
- [ ] Webhook integrations

### Future
- [ ] Machine learning predictions
- [ ] Mobile apps
- [ ] Real-time collaboration
- [ ] Advanced scenario analysis

---

**Ready to automate IFRS 17? Let's go! 🚀**

Questions? Open an issue or join our [Discord](https://discord.gg/ifrs17pro)
