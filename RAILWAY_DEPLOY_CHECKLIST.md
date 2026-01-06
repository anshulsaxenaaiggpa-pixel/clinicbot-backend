# Railway Deployment Checklist - CuraSlot

## Required Environment Variables

Set these in Railway dashboard or via CLI:

```bash
# Core Configuration
ENVIRONMENT=production
DEBUG=false

# Security (CRITICAL)
SESSION_SECRET_KEY=<64+ character random string>
SECRET_KEY=<32+ character random string>

# Database (Auto-set by Railway when PostgreSQL added)
DATABASE_URL=<automatically set by Railway>

# Admin UI
ADMIN_UI_ENABLED=true
ADMIN_UI_HTTPS_ONLY=false  # Railway proxy terminates HTTPS

# Optional but Recommended
REDIS_URL=<set if Redis plugin added>
PASSWORD_HASH_ROUNDS=12
```

## Quick Setup Commands

### Generate Secrets (Run locally, then paste to Railway)

```powershell
# Generate SESSION_SECRET_KEY (64 chars)
python -c "import secrets; print('SESSION_SECRET_KEY=' + secrets.token_urlsafe(64))"

# Generate SECRET_KEY (32 chars)
python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))"
```

### Set Railway Variables (if Railway CLI installed)

```bash
# Set all required variables
railway variables set ENVIRONMENT=production
railway variables set DEBUG=false
railway variables set ADMIN_UI_ENABLED=true
railway variables set ADMIN_UI_HTTPS_ONLY=false
railway variables set SESSION_SECRET_KEY="<paste generated secret>"
railway variables set SECRET_KEY="<paste generated secret>"
railway variables set PASSWORD_HASH_ROUNDS=12
```

## Post-Deploy Verification

### 1. Check Deployment Logs

```bash
railway logs --tail 50
```

**Expected output:**
```
✅ All configuration checks passed
✅ SECURITY VALIDATION PASSED - Application starting
✅ Database migrations completed successfully
✅ All routers registered successfully
```

### 2. Test Health Endpoint

```bash
curl https://clinicbot-whatsapp-production.up.railway.app/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "service": "CuraSlot",
  "environment": "production",
  "database": "connected",
  "redis": "not configured" // or "connected" if Redis added
}
```

### 3. Test Admin Login

1. Navigate to: `https://clinicbot-whatsapp-production.up.railway.app/admin/login`
2. Should show login page (not 500 error)
3. Try logging in with admin credentials
4. Dashboard should load

## Troubleshooting

### If you see: `CRITICAL: DEBUG=True in production`

```bash
railway variables set DEBUG=false
```

### If you see: `CRITICAL: SESSION_SECRET_KEY too short`

```bash
# Generate a new 64+ char secret
python -c "import secrets; print(secrets.token_urlsafe(64))"

# Set it in Railway
railway variables set SESSION_SECRET_KEY="<paste here>"
```

### If you see: `WARNING: ADMIN_UI_HTTPS_ONLY=False in production`

This is expected for Railway (proxy mode). Ignore it.

### If you see: `WARNING: REDIS_URL not configured`

Sessions will use in-memory storage. For production persistence, add Redis:
```bash
railway add
# Select Redis from the list
```

## Current Fixes Applied

✅ Removed duplicate DEBUG setting in config.py
✅ Set DEBUG default to False (production-safe)
✅ Enhanced startup validator with detailed error reporting
✅ Downgraded Redis from CRITICAL to WARNING (not required for startup)
✅ Added error handling to show exact validation failures

## Migration Status

Auto-migrations run on startup. No manual `alembic upgrade head` needed.
