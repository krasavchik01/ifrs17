#!/bin/bash

# IFRS 17 Pro - Quick Deploy Script
# This script deploys your app to Vercel in one command

echo "🚀 IFRS 17 Pro - Deploying to Vercel..."
echo ""

# Check if vercel is installed
if ! command -v vercel &> /dev/null
then
    echo "📦 Installing Vercel CLI..."
    npm install -g vercel
fi

# Deploy to Vercel
echo "🌐 Deploying to production..."
vercel --prod --yes

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📝 Next steps:"
echo "1. Set environment variables in Vercel Dashboard"
echo "2. Add your database URL"
echo "3. Configure Stripe keys"
echo "4. Run migrations: vercel env pull && npx prisma migrate deploy"
echo ""
echo "🎉 Your IFRS 17 Pro is live!"
