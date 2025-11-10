# 🚀 Deploy IFRS 17 Pro to Vercel RIGHT NOW!

## ⚡ Option 1: One-Click Deploy (Fastest - 2 minutes)

### Step 1: Click this button

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/krasavchik01/ifrs17)

### Step 2: Configure

1. **Fork & Import**: Vercel will ask you to fork the repo
2. **Root Directory**: Set to `ifrs17-saas`
3. **Framework**: Should auto-detect as Next.js
4. **Click Deploy**

### Step 3: Add Environment Variables (After First Deploy)

Go to your project in Vercel → Settings → Environment Variables:

```bash
# Required
DATABASE_URL=postgresql://user:pass@host:5432/db?schema=public
NEXTAUTH_SECRET=your-secret-here
NEXTAUTH_URL=https://your-app.vercel.app

# Optional (for payments)
STRIPE_SECRET_KEY=sk_live_xxx
STRIPE_PUBLISHABLE_KEY=pk_live_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
```

### Step 4: Redeploy

After adding env vars, click "Redeploy" to rebuild with environment variables.

**🎉 Done! Your app is live!**

---

## 🔧 Option 2: Vercel CLI (Terminal - 3 minutes)

### Quick Deploy Commands:

```bash
# 1. Navigate to project
cd ifrs17-saas

# 2. Login to Vercel
vercel login

# 3. Deploy to production
vercel --prod

# Follow the prompts:
# - Set up and deploy? Yes
# - Which scope? Your account
# - Link to existing project? No
# - Project name? ifrs17-pro (or whatever you want)
# - Directory? ./ (current)
# - Override settings? No
```

**That's it!** 🎊

---

## 🔗 Option 3: Connect GitHub Repository (Best for Teams)

### Step 1: Import Project

1. Go to [vercel.com/new](https://vercel.com/new)
2. Click "Import Git Repository"
3. Select `krasavchik01/ifrs17`
4. Configure:
   - **Root Directory**: `ifrs17-saas`
   - **Framework Preset**: Next.js (auto-detected)
   - **Build Command**: `npm run build`
   - **Output Directory**: `.next`

### Step 2: Configure Environment Variables

Click "Environment Variables" and add:

```env
DATABASE_URL=postgresql://...
NEXTAUTH_SECRET=generate-with-openssl-rand-base64-32
NEXTAUTH_URL=https://your-app.vercel.app
```

To generate NEXTAUTH_SECRET:
```bash
openssl rand -base64 32
```

### Step 3: Deploy

Click "Deploy" button!

**Benefits:**
- ✅ Auto-deploy on every push
- ✅ Preview URLs for every PR
- ✅ Easy rollbacks
- ✅ Team collaboration

---

## 📊 Setting Up Database (5 minutes)

### Recommended: Supabase (Free Tier Available)

1. Go to [supabase.com](https://supabase.com)
2. Create new project
3. Wait 2 minutes for setup
4. Get connection string:
   - Go to Settings → Database
   - Copy "Connection string" (URI)
   - Replace `[YOUR-PASSWORD]` with your password

Example:
```
postgresql://postgres:[PASSWORD]@db.xxx.supabase.co:5432/postgres
```

5. Add to Vercel environment variables as `DATABASE_URL`

### Alternative: Neon (Super Fast)

1. Go to [neon.tech](https://neon.tech)
2. Create project
3. Copy connection string
4. Add to Vercel

### Alternative: Railway (Easy Setup)

1. Go to [railway.app](https://railway.app)
2. New Project → PostgreSQL
3. Copy DATABASE_URL from Variables tab
4. Add to Vercel

---

## 🔐 Setting Up Stripe (Optional - for Payments)

### Step 1: Create Stripe Account

1. Go to [stripe.com](https://stripe.com)
2. Sign up / Login
3. Activate your account

### Step 2: Get API Keys

1. Dashboard → Developers → API Keys
2. Copy **Publishable key** and **Secret key**
3. Add to Vercel environment variables:
   - `STRIPE_PUBLISHABLE_KEY`
   - `STRIPE_SECRET_KEY`

### Step 3: Create Products & Prices

```bash
# Using Stripe CLI
stripe products create \
  --name "IFRS 17 Pro Subscription" \
  --description "Professional IFRS 17 automation"

# Get product ID, then create prices
stripe prices create \
  --product prod_XXX \
  --unit-amount 49900 \
  --currency usd \
  --recurring interval=month
```

### Step 4: Configure Webhook

1. Stripe Dashboard → Developers → Webhooks
2. Add endpoint: `https://your-app.vercel.app/api/stripe/webhook`
3. Select events:
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`
4. Copy webhook secret → Add to Vercel as `STRIPE_WEBHOOK_SECRET`

---

## 🗄️ Running Database Migrations

After deployment:

```bash
# Pull environment variables from Vercel
vercel env pull

# Run migrations
npx prisma migrate deploy

# Generate Prisma Client
npx prisma generate
```

Or use Vercel's build command (recommended):

```bash
# package.json already has this
"postinstall": "prisma generate"
```

---

## ✅ Deployment Checklist

Before going live:

- [ ] Database is set up (Supabase/Neon/Railway)
- [ ] `DATABASE_URL` added to Vercel
- [ ] `NEXTAUTH_SECRET` generated and added
- [ ] `NEXTAUTH_URL` points to your domain
- [ ] Stripe keys added (if using payments)
- [ ] Stripe webhook configured
- [ ] Database migrations run
- [ ] First test account created
- [ ] Custom domain configured (optional)

---

## 🎯 Quick Troubleshooting

### Build fails on Vercel?

1. Check build logs in Vercel dashboard
2. Ensure all environment variables are set
3. Make sure `DATABASE_URL` is accessible from Vercel

### Database connection error?

1. Check `DATABASE_URL` format:
   ```
   postgresql://USER:PASSWORD@HOST:PORT/DATABASE?schema=public
   ```
2. Ensure database accepts connections from `0.0.0.0/0`
3. Check if password has special characters (URL encode them)

### NextAuth error?

1. Ensure `NEXTAUTH_URL` matches your deployment URL exactly
2. Generate new `NEXTAUTH_SECRET`: `openssl rand -base64 32`
3. Check that it's set in Environment Variables

---

## 🌟 After Deployment

### Get Your Preview Link

Every deployment gets a unique URL:
- **Production**: `https://your-app.vercel.app`
- **Branch Previews**: `https://your-app-git-branch-name.vercel.app`
- **Commit Previews**: `https://your-app-git-commit-hash.vercel.app`

### Share with Team

```
Share this link:
https://your-app.vercel.app

Or custom domain:
https://ifrs17pro.com
```

### Monitor Deployment

- **Dashboard**: [vercel.com/dashboard](https://vercel.com/dashboard)
- **Logs**: Real-time function logs
- **Analytics**: Built-in Web Analytics

---

## 🚀 You're Live!

Your IFRS 17 Pro SaaS is now deployed and ready to use!

### Next Steps:

1. ✅ Visit your deployment URL
2. ✅ Create your first organization
3. ✅ Add test insurance contracts
4. ✅ Run CSM calculations
5. ✅ Generate reports
6. ✅ Share preview link with stakeholders

---

## 💬 Need Help?

- **GitHub Issues**: [Report bugs](https://github.com/krasavchik01/ifrs17/issues)
- **Vercel Docs**: [vercel.com/docs](https://vercel.com/docs)
- **Supabase Docs**: [supabase.com/docs](https://supabase.com/docs)

---

**🎉 Happy Deploying!**

Built with ❤️ for Kazakhstan Insurance Market 🇰🇿
