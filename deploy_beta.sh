#!/bin/bash
# 🚀 5-Minute BETA Deployment Script
# Deploys consent feature to Railway production

set -e  # Exit on error

echo "========================================="
echo "🎯 BETA LAUNCH: Consent Feature Deploy"
echo "========================================="

# Step 1: Verify we're in the right directory
cd "$(dirname "$0")"
echo "✅ Working directory: $(pwd)"

# Step 2: Check git status
echo ""
echo "📋 Git Status:"
git status --short

# Step 3: Stage all changes
echo ""
echo "📦 Staging changes..."
git add .

# Step 4: Commit with BETA marker
echo ""
echo "💾 Committing..."
git commit -m "DEPLOY: Add DPDP/GDPR consent capture - BETA READY

- ✅ ConsentLog model with audit trail
- ✅ Consent handler (check + record)
- ✅ WhatsApp integration with consent gate
- ✅ Migration: 0e4dac089749_add_consent_log
- ✅ BETA LAUNCH READY 🎉
" || echo "⚠️  No changes to commit (maybe already committed?)"

# Step 5: Push to Railway
echo ""
echo "🚀 Pushing to Railway..."
git push origin main

echo ""
echo "========================================="
echo "✅ Code deployed! Railway is building..."
echo "========================================="
echo ""
echo "🔄 Next Steps:"
echo "1. Wait 30-60s for Railway deployment"
echo "2. Run: railway logs (to monitor)"
echo "3. Verify migration: railway run alembic current"
echo "4. Test WhatsApp: Send 'Hi' to bot"
echo ""
echo "🎉 BETA LAUNCH IN PROGRESS!"
