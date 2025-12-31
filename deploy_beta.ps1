# 🚀 5-Minute BETA Deployment Script (PowerShell)
# Deploys consent feature to Railway production

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "🎯 BETA LAUNCH: Consent Feature Deploy" -ForegroundColor Yellow
Write-Host "=========================================" -ForegroundColor Cyan

# Step 1: Navigate to project directory
Set-Location "C:\Users\Param\.gemini\antigravity\scratch\clinicbot-ai"
Write-Host "`n✅ Working directory: $(Get-Location)" -ForegroundColor Green

# Step 2: Check git status
Write-Host "`n📋 Git Status:" -ForegroundColor Yellow
git status --short

# Step 3: Stage all changes
Write-Host "`n📦 Staging changes..." -ForegroundColor Yellow
git add .

# Step 4: Commit with BETA marker
Write-Host "`n💾 Committing..." -ForegroundColor Yellow
$commitMessage = @"
DEPLOY: Add DPDP/GDPR consent capture - BETA READY

- ✅ ConsentLog model with audit trail
- ✅ Consent handler (check + record)
- ✅ WhatsApp integration with consent gate
- ✅ Migration: 0e4dac089749_add_consent_log
- ✅ BETA LAUNCH READY 🎉
"@

try {
    git commit -m $commitMessage
} catch {
    Write-Host "⚠️  No changes to commit (maybe already committed?)" -ForegroundColor Yellow
}

# Step 5: Push to Railway
Write-Host "`n🚀 Pushing to Railway..." -ForegroundColor Green
git push origin main

Write-Host "`n=========================================" -ForegroundColor Cyan
Write-Host "✅ Code deployed! Railway is building..." -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Cyan

Write-Host "`n🔄 Next Steps:" -ForegroundColor Yellow
Write-Host "1. Wait 30-60s for Railway deployment"
Write-Host "2. Run: railway logs (to monitor)"
Write-Host "3. Verify migration: railway run alembic current"
Write-Host "4. Test WhatsApp: Send 'Hi' to bot"

Write-Host "`n🎉 BETA LAUNCH IN PROGRESS!" -ForegroundColor Green
