# IFRS 17 Pro - Enterprise Insurance Automation System

🇰🇿 **Professional IFRS 17 automation platform for Kazakhstan insurance market**

Built with enterprise-grade architecture following Big Four quality standards.

## 🚀 Features

### Core IFRS 17 Capabilities

- **Insurance Contract Management**
  - Complete lifecycle tracking
  - Automatic contract grouping and cohort management
  - Support for GMM, PAA, and VFA measurement models

- **CSM (Contractual Service Margin)**
  - Automated CSM roll-forward calculations
  - Interest accretion and release for service
  - Experience adjustments and estimate changes
  - Coverage units calculation

- **Risk Adjustment**
  - Confidence level approach (50%-99%)
  - Cost of capital methodology
  - Quantile-based calculations
  - Insurance, financial, and operational risk components

- **Fulfilment Cash Flows**
  - Present value calculations with discount curves
  - Premium, claim, and expense projections
  - Duration and convexity analysis
  - Reinsurance adjustments

- **Reporting & Analytics**
  - IFRS 17 compliant financial statements
  - CSM roll-forward reports
  - Interactive dashboards with real-time KPIs
  - Export to Excel, PDF formats

### SaaS Platform Features

- **Multi-tenant Architecture**
  - Complete data isolation per organization
  - Role-based access control (Admin, Manager, Actuary, User, Auditor)
  - Subscription management with Stripe

- **Security & Compliance**
  - Complete audit trail for all operations
  - MFA support
  - Enterprise-grade authentication with NextAuth.js
  - Data encryption at rest and in transit

- **Developer-Friendly**
  - RESTful API with TypeScript types
  - PostgreSQL with Prisma ORM
  - Comprehensive validation with Zod
  - Modern Next.js 14 App Router

## 🛠️ Tech Stack

- **Frontend**: Next.js 14, React 18, TypeScript, Tailwind CSS
- **Backend**: Next.js API Routes, Prisma ORM
- **Database**: PostgreSQL
- **Authentication**: NextAuth.js
- **Payments**: Stripe
- **Deployment**: Vercel
- **Analytics**: Recharts

## 📋 Prerequisites

- Node.js 18.x or higher
- PostgreSQL 14.x or higher
- npm or yarn

## 🚀 Quick Start

### 1. Clone and Install

\`\`\`bash

npm install
\`\`\`

### 2. Environment Setup

Create a \`.env\` file:

\`\`\`env
# Database
DATABASE_URL="postgresql://user:password@localhost:5432/ifrs17_saas"

# NextAuth
NEXTAUTH_URL="http://localhost:3000"
NEXTAUTH_SECRET="your-secret-key-generate-with-openssl"

# Stripe (get from stripe.com)
STRIPE_SECRET_KEY="sk_test_..."
STRIPE_PUBLISHABLE_KEY="pk_test_..."
STRIPE_WEBHOOK_SECRET="whsec_..."
\`\`\`

### 3. Database Setup

\`\`\`bash
# Generate Prisma Client
npx prisma generate

# Run migrations
npx prisma migrate dev

# (Optional) Seed demo data
npx prisma db seed
\`\`\`

### 4. Run Development Server

\`\`\`bash
npm run dev
\`\`\`

Visit http://localhost:3000

## 🌐 Deploying to Vercel

### One-Click Deploy

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/krasavchik01/ifrs17)

### Manual Deploy

1. **Install Vercel CLI**

\`\`\`bash
npm i -g vercel
\`\`\`

2. **Login to Vercel**

\`\`\`bash
vercel login
\`\`\`

3. **Deploy**

\`\`\`bash
vercel --prod
\`\`\`

4. **Set Environment Variables**

In Vercel Dashboard:
- Go to Settings → Environment Variables
- Add all variables from \`.env.example\`
- Redeploy

### Database Setup for Production

Use managed PostgreSQL:
- [Supabase](https://supabase.com)
- [Neon](https://neon.tech)
- [Railway](https://railway.app)
- [Vercel Postgres](https://vercel.com/storage/postgres)

## 📊 API Documentation

### Authentication

\`\`\`typescript
POST /api/auth/signin
POST /api/auth/signup
POST /api/auth/signout
\`\`\`

### Contracts

\`\`\`typescript
GET    /api/contracts          // List contracts
POST   /api/contracts          // Create contract
GET    /api/contracts/:id      // Get contract
PUT    /api/contracts/:id      // Update contract
DELETE /api/contracts/:id      // Delete contract
\`\`\`

### CSM Calculations

\`\`\`typescript
POST /api/csm/calculate         // Calculate CSM
GET  /api/csm/:contractId       // Get CSM history
\`\`\`

### Reports

\`\`\`typescript
GET  /api/reports               // List reports
POST /api/reports/generate      // Generate report
GET  /api/reports/:id/download  // Download report
\`\`\`

## 🏗️ Project Structure

\`\`\`
.
├── prisma/
│   └── schema.prisma          # Database schema
├── src/
│   ├── app/                   # Next.js 14 App Router
│   │   ├── api/              # API routes
│   │   ├── dashboard/        # Dashboard pages
│   │   ├── contracts/        # Contract management
│   │   └── reports/          # Reporting
│   ├── components/           # React components
│   │   └── ui/              # Reusable UI components
│   ├── lib/                 # Utilities
│   │   ├── ifrs17/          # IFRS 17 calculation engines
│   │   │   ├── csm.ts       # CSM calculations
│   │   │   ├── risk-adjustment.ts
│   │   │   └── cash-flows.ts
│   │   ├── auth.ts          # Authentication config
│   │   └── prisma.ts        # Database client
│   └── types/               # TypeScript types
└── package.json
\`\`\`

## 💡 Usage Examples

### Creating a Contract

\`\`\`typescript
const contract = await fetch('/api/contracts', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    contractNumber: 'POL-2024-001',
    contractType: 'life',
    productLine: 'life',
    measurementModel: 'GMM',
    profitability: 'profitable',
    inceptionDate: '2024-01-01',
    coverageStartDate: '2024-01-01',
    coverageEndDate: '2044-01-01',
    nominalAmount: 1000000,
  }),
});
\`\`\`

### Calculating CSM

\`\`\`typescript
const csm = await fetch('/api/csm/calculate', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    contractId: 'contract-id',
    reportingDate: '2024-12-31',
    periodStart: '2024-01-01',
    periodEnd: '2024-12-31',
    discountRate: 0.05,
    totalCoverageUnits: 20000000,
    coverageUnitsReleased: 1000000,
  }),
});
\`\`\`

## 🔐 Security

- All passwords are hashed with bcrypt
- JWT-based session management
- RBAC (Role-Based Access Control)
- Complete audit logging
- SQL injection protection via Prisma
- XSS protection
- CSRF tokens

## 📈 Performance

- Server-side rendering with Next.js 14
- Optimistic updates
- Database query optimization
- Edge-ready deployment
- CDN for static assets

## 🧪 Testing

\`\`\`bash
npm run test           # Unit tests
npm run test:e2e       # E2E tests
npm run test:coverage  # Coverage report
\`\`\`

## 📝 License

Proprietary - All Rights Reserved

## 🤝 Support

- Documentation: [https://docs.ifrs17pro.com](https://docs.ifrs17pro.com)
- Email: support@ifrs17pro.com
- Slack: [Join our community](https://slack.ifrs17pro.com)

## 🎯 Roadmap

- [ ] Machine learning for claims prediction
- [ ] Real-time collaboration
- [ ] Mobile applications
- [ ] Advanced scenario analysis
- [ ] Reinsurance module expansion
- [ ] Integration with core insurance systems

---

Built with ❤️ for Kazakhstan Insurance Market

**Enterprise IFRS 17 Automation - Big Four Quality**
# Force rebuild
