# 🚀 Deployment Guide - IFRS 17 Pro

Complete guide for deploying your IFRS 17 SaaS application to Vercel.

## Prerequisites

- GitHub account
- Vercel account (free tier works!)
- PostgreSQL database (we recommend Supabase or Neon)
- Stripe account for payments

## Step 1: Database Setup

### Option A: Supabase (Recommended)

1. Go to [supabase.com](https://supabase.com)
2. Create a new project
3. Get your connection string from Settings → Database
4. Connection string format:
   ```
   postgresql://postgres:[YOUR-PASSWORD]@[HOST]:5432/postgres
   ```

### Option B: Neon

1. Go to [neon.tech](https://neon.tech)
2. Create a new project
3. Copy the connection string from the dashboard

### Option C: Railway

1. Go to [railway.app](https://railway.app)
2. Create new → PostgreSQL
3. Copy the DATABASE_URL from Variables tab

## Step 2: Push to GitHub

```bash
# Navigate to your project
cd ifrs17-saas

# Initialize git (if not already)
git init

# Add all files
git add .

# Commit
git commit -m "Initial commit - IFRS 17 Pro SaaS"

# Create a new repository on GitHub, then:
git remote add origin https://github.com/YOUR_USERNAME/ifrs17-saas.git
git branch -M main
git push -u origin main
```

## Step 3: Deploy to Vercel

### Method 1: Vercel Dashboard (Easy)

1. Go to [vercel.com](https://vercel.com)
2. Click "New Project"
3. Import your GitHub repository
4. Configure project:
   - Framework Preset: Next.js
   - Root Directory: `./ifrs17-saas`
   - Build Command: `npm run build`
   - Output Directory: `.next`

### Method 2: Vercel CLI

```bash
# Install Vercel CLI globally
npm i -g vercel

# Login
vercel login

# Deploy
cd ifrs17-saas
vercel

# For production
vercel --prod
```

## Step 4: Environment Variables

In Vercel Dashboard → Settings → Environment Variables, add:

### Required Variables

```env
# Database
DATABASE_URL="postgresql://..."

# NextAuth
NEXTAUTH_URL="https://your-app.vercel.app"
NEXTAUTH_SECRET="generate-with-openssl-rand-base64-32"

# Stripe
STRIPE_SECRET_KEY="sk_live_..."
STRIPE_PUBLISHABLE_KEY="pk_live_..."
STRIPE_WEBHOOK_SECRET="whsec_..."

# Application
NODE_ENV="production"
```

### Generate NEXTAUTH_SECRET

```bash
openssl rand -base64 32
```

## Step 5: Database Migration

After deployment, run migrations:

```bash
# Install Vercel CLI
npm i -g vercel

# Pull environment variables
vercel env pull

# Run migrations
npx prisma migrate deploy

# Generate Prisma Client
npx prisma generate
```

Or use Vercel's deployment hooks to automate this.

## Step 6: Stripe Configuration

### 1. Create Products and Prices

```bash
# Set your Stripe secret key
export STRIPE_SECRET_KEY=sk_test_...

# Create product
stripe products create \
  --name "IFRS 17 Pro Subscription" \
  --description "Professional IFRS 17 automation"

# Create prices for each plan
# Starter - $499/month
stripe prices create \
  --product prod_XXX \
  --unit-amount 49900 \
  --currency usd \
  --recurring interval=month \
  --metadata plan=starter

# Professional - $1,499/month
stripe prices create \
  --product prod_XXX \
  --unit-amount 149900 \
  --currency usd \
  --recurring interval=month \
  --metadata plan=professional
```

### 2. Configure Webhook

1. Go to Stripe Dashboard → Developers → Webhooks
2. Add endpoint: `https://your-app.vercel.app/api/stripe/webhook`
3. Select events:
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`
4. Copy webhook secret to `STRIPE_WEBHOOK_SECRET`

## Step 7: Custom Domain (Optional)

1. In Vercel Dashboard → Settings → Domains
2. Add your domain (e.g., `ifrs17pro.com`)
3. Follow DNS configuration instructions
4. Update `NEXTAUTH_URL` to your custom domain

## Step 8: Preview Deployments

Every branch and PR automatically gets a preview URL!

### Branch Deployments

```bash
# Create a feature branch
git checkout -b feature/new-reports

# Make changes and commit
git add .
git commit -m "Add new reports"

# Push to GitHub
git push origin feature/new-reports
```

Vercel will automatically deploy to a preview URL like:
`https://ifrs17-saas-feature-new-reports.vercel.app`

### Sharing Preview Links

When you create a PR, Vercel bot comments with the preview URL.
Share this URL with stakeholders for review!

## Step 9: Monitoring & Analytics

### Vercel Analytics (Built-in)

1. In Vercel Dashboard → Analytics
2. View real-time traffic, performance metrics
3. Free tier includes basic analytics

### Application Monitoring

Consider adding:

- **Sentry** for error tracking
- **LogRocket** for session replay
- **PostHog** for product analytics

```bash
npm install @sentry/nextjs
npx @sentry/wizard@latest -i nextjs
```

## Step 10: Production Checklist

Before going live, ensure:

- [ ] All environment variables are set (production)
- [ ] Database migrations are applied
- [ ] Stripe is in live mode (not test)
- [ ] Custom domain is configured
- [ ] SSL certificate is active (automatic with Vercel)
- [ ] Email notifications are configured
- [ ] Backup strategy is in place for database
- [ ] Error monitoring is active
- [ ] Rate limiting is configured
- [ ] CORS settings are correct
- [ ] Security headers are set

## Common Issues & Solutions

### Issue 1: Database Connection Fails

**Solution**: Ensure your DATABASE_URL includes `?schema=public` at the end

```
postgresql://user:pass@host:5432/db?schema=public
```

### Issue 2: NextAuth Redirect Error

**Solution**: Make sure NEXTAUTH_URL matches your deployment URL exactly (no trailing slash)

### Issue 3: Stripe Webhook Failing

**Solution**:
1. Check webhook secret is correct
2. Ensure webhook endpoint is publicly accessible
3. Verify event types are selected

### Issue 4: Build Fails on Vercel

**Solution**: Check build logs. Common causes:
- TypeScript errors
- Missing environment variables during build
- Prisma client not generated

Add to vercel.json:
```json
{
  "build": {
    "env": {
      "DATABASE_URL": "@database_url"
    }
  }
}
```

## Scaling Considerations

### For High Traffic

1. **Database Connection Pooling**
   - Use PgBouncer
   - Or switch to Supabase with built-in pooling

2. **Caching**
   - Add Redis for session storage
   - Use Vercel Edge Caching

3. **CDN**
   - Static assets automatically cached by Vercel
   - Use `next/image` for optimized images

4. **Monitoring**
   - Set up alerts for high error rates
   - Monitor database query performance
   - Track API response times

## Backup & Recovery

### Database Backups

For Supabase:
- Daily automatic backups included
- Point-in-time recovery available

For self-hosted:
```bash
# Automated daily backup script
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql
```

### Application Backups

- Git repository is your code backup
- Vercel keeps deployment history
- Export data regularly via API

## Cost Optimization

### Vercel Costs (Estimated)

- **Hobby** (Free): 100 GB bandwidth, perfect for getting started
- **Pro** ($20/month): 1TB bandwidth, custom domains
- **Enterprise** (Custom): Unlimited, dedicated support

### Database Costs

- **Supabase**: $25/month (8GB database, 100GB bandwidth)
- **Neon**: $19/month (3GB storage, 10M requests)
- **Railway**: ~$5/month (small database)

### Total Monthly Cost (Starter Setup)

- Vercel Hobby: $0
- Supabase: $25
- **Total: ~$25/month** 🎉

## Support & Resources

- **Documentation**: https://docs.ifrs17pro.com
- **GitHub Issues**: https://github.com/yourusername/ifrs17-saas/issues
- **Discord Community**: https://discord.gg/ifrs17pro
- **Email Support**: support@ifrs17pro.com

## Next Steps

After successful deployment:

1. ✅ Create your first organization
2. ✅ Add test insurance contracts
3. ✅ Run CSM calculations
4. ✅ Generate reports
5. ✅ Invite team members
6. ✅ Configure subscription plans
7. ✅ Set up custom branding

---

**Congratulations! Your IFRS 17 Pro SaaS is now live! 🎉**

Share your preview links with stakeholders and start automating IFRS 17 compliance!
