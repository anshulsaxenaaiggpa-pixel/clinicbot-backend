# Railway Deployment Debug Guide

## Error: "Application failed to respond"

### Immediate Actions:

#### 1. Check Railway Environment Variables

Verify these envvars are set on Railway:

```bash
# Required for startup
DATABASE_URL=postgresql://...
SESSION_SECRET_KEY=<at least 32 characters>
SECRET_KEY=<at least 32 characters>

# Environment settings
ENVIRONMENT=production
DEBUG=false
ADMIN_UI_ENABLED=true
ADMIN_UI_HTTPS_ONLY=false  # IMPORTANT: Railway proxy mode

# API Keys
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...

# WhatsApp Provider
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
TWILIO_WHATSAPP_NUMBER=...
```

#### 2. Get Railway Logs

```bash
# In Railway Dashboard:
1. Click on your deployment
2. Go to "Deployments" tab
3. Click on the latest deployment
4. Copy and share the full logs from the "Logs" section
```

#### 3. Potential Issues & Fixes

**Issue A: Startup Validation Failing**

If logs show "STARTUP ABORTED DUE TO VALIDATION FAILURE":

```bash
# Fix in Railway environment variables:
DEBUG=false  # Must be false in production
ADMIN_UI_HTTPS_ONLY=false  # Railway uses proxy, set to false
SESSION_SECRET_KEY=<generate new 32+ char secret>
```

**Issue B: Database Migration Timeout**

If logs show migration hanging or timeout:

```bash
# The app tries to run migrations on startup (main.py line 122-137)
# This might timeout. Disable auto-migrations temporarily:

# Comment out lines 122-137 in main.py and deploy
```

**Issue C: Model/Database Column Mismatch**

If logs show `UndefinedColumn` or `ProgrammingError`:

```bash
# The startup includes auto-fix for doctor columns (main.py lines 81-120)
# But PostgreSQL syntax might differ from SQLite

# Check if migrations completed successfully in logs
```

### Debugging Steps:

1. **Get the exact error from Railway logs** - This is critical!

2. **Test health endpoint**:
   ```bash
   curl https://your-app.railway.app/health
   ```

3. **Test root endpoint**:
   ```bash
   curl https://your-app.railway.app/
   ```

4. **Check if it's just admin routes or entire app**:
   ```bash
   curl https://your-app.railway.app/api/v1/debug
   ```

### Quick Fixes to Deploy:

Based on common issues from conversation history:

**FIX 1: Disable Auto-Migrations (if they're timing out)**

Comment out the auto-migration block in `app/main.py` lines 122-137.

**FIX 2: Fix PostgreSQL Column Syntax**

The `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` syntax in main.py (lines 88-115) might fail on some PostgreSQL versions.

**FIX 3: Simplify Startup**

Remove the doctor column checks temporarily to isolate the issue.

### What I Need from You:

**Please share the Railway deployment logs!** Look for:
- Any Python errors or tracebacks
- Database connection errors
- Migration failures
- Validation failures (with "❌" or "CRITICAL")

The logs will tell us exactly what's failing.

### Expected Log Output (Success):

```
🚀 MAIN.PY LOADING - CuraSlot Admin API
🔒 RUNNING STARTUP SECURITY VALIDATION
✅ SECURITY VALIDATION PASSED
🔧 Ensuring doctor table has required columns...
✅ Ensured upi_id column exists
✅ Ensured status column exists
✅ Ensured consultation_fee column exists
🔄 RUNNING DATABASE MIGRATIONS
✅ Database migrations completed successfully
🗄️ Ensuring consent_log table exists...
✅ consent_log and audit_log tables ready!
📝 Registering admin routers...
✅ All admin routers registered successfully!
✅ All routers registered successfully
🌐 Total routes: <number>
```

If you see anything different, that's where the problem is!
