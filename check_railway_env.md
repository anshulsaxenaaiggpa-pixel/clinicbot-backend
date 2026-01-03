# Railway Environment Variables Check Guide

## How to Access Railway Dashboard

1. Go to [https://railway.app/](https://railway.app/)
2. Sign in to your account
3. Click on your **clinicbot-ai** project

## Checking Environment Variables

1. In your project, click on your **FastAPI service**
2. Go to the **Variables** tab
3. You should see all your environment variables listed

### Required Variables Checklist

Make sure these variables are set in Railway:

#### ✅ **Security** (Critical - App Won't Start Without These)
- [ ] `SECRET_KEY` - Must be set (minimum 32 characters)
- [ ] `SESSION_SECRET_KEY` - Must be at least 32 characters

#### ✅ **Database**
- [ ] `DATABASE_URL` - Should auto-populate from Railway Postgres service
- [ ] `REDIS_URL` - Should auto-populate from Railway Redis service (optional but recommended)

#### ✅ **Twilio WhatsApp** (Required for Bot to Send Messages)
- [ ] `TWILIO_ACCOUNT_SID` - Your Twilio account SID (starts with "AC")
- [ ] `TWILIO_AUTH_TOKEN` - Your Twilio auth token
- [ ] `TWILIO_WHATSAPP_NUMBER` - Format: `whatsapp:+14155238886` (with "whatsapp:" prefix)

#### ⚠️ **Optional**
- [ ] `OPENAI_API_KEY` - For intent classification (optional)
- [ ] `WHATSAPP_PROVIDER` - Set to "twilio" (default)
- [ ] `ENVIRONMENT` - Set to "production"

## How to Add/Update Variables

1. In the **Variables** tab, click **+ New Variable**
2. Enter the **Variable Name** (e.g., `TWILIO_ACCOUNT_SID`)
3. Enter the **Value**
4. Click **Add**
5. Railway will automatically redeploy your app

## Viewing Deployment Logs

1. In your project, click on your **FastAPI service**
2. Go to the **Deployments** tab
3. Click on the **latest deployment**
4. You'll see real-time logs

### What to Look For in Logs

#### ✅ **Good Signs**
```
INFO:     Started server process
INFO:     Waiting for application startup.
✅ [Redis Connected] Successfully connected to Redis
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

#### ❌ **Error Signs**
```
ValueError: SESSION_SECRET_KEY must be at least 32 characters
sqlalchemy.exc.OperationalError: could not connect to database
ERROR: Error handling message from +1234567890
❌ Twilio send FAILED
```

## Testing the Webhook

### Step 1: Get Your Railway URL
Your Railway app URL should be: `https://<your-app-name>.up.railway.app`

You can find this in:
- Railway dashboard → Your service → **Settings** tab → **Domains** section

### Step 2: Configure Twilio Webhook

1. Go to [Twilio Console](https://console.twilio.com/)
2. Navigate to **Messaging** → **Try it out** → **Send a WhatsApp message**
3. Click on **Sandbox settings**
4. Under "When a message comes in":
   - URL: `https://<your-railway-app>.up.railway.app/api/v1/webhooks/whatsapp`
   - Method: **POST**
5. Click **Save**

### Step 3: Test the Flow

1. Send a WhatsApp message to your Twilio sandbox number
2. Type: `Hi`
3. Check Railway logs immediately (keep logs open in another tab)

#### Expected Log Flow:
```
INFO:     Received WhatsApp message: {'From': 'whatsapp:+1234567890', 'Body': 'Hi', ...}
INFO:     Found clinic: Test Clinic (ID: abc123) for number +14155238886
📋 Sending consent prompt to +1234567890
📤 Attempting to send WhatsApp message via twilio to +1234567890
INFO:     Sent Twilio message to +1234567890
```

## Common Issues and Fixes

### Issue 1: App Crashes on Startup
**Symptoms**: Logs show "Error" and app keeps restarting

**Causes**:
- Missing `SECRET_KEY` or `SESSION_SECRET_KEY`
- `SESSION_SECRET_KEY` too short (< 32 chars)

**Fix**:
```bash
# Generate a secure secret key
# In your local terminal:
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Copy the output and set it as SECRET_KEY and SESSION_SECRET_KEY in Railway
```

### Issue 2: No Clinic Found Error
**Symptoms**: Logs show "No clinic found for WhatsApp number"

**Fix**:
You need to create a clinic in the database with the correct WhatsApp number.

1. Option A: Use the admin UI (if enabled)
2. Option B: Run this script locally and then seed to production:
   ```bash
   cd C:\Users\Param\.gemini\antigravity\scratch\clinicbot-ai
   python seed_test_data.py
   ```

### Issue 3: Twilio Send Failed
**Symptoms**: Message received but no reply, logs show "❌ Twilio send FAILED"

**Causes**:
- Wrong Twilio credentials
- Phone number not in sandbox
- Network issue

**Fix**:
1. Verify credentials in Twilio Console → Account → API credentials
2. Ensure test phone number joined sandbox (send "join <sandbox-word>" to sandbox number)
3. Check Railway can make outbound HTTPS requests

## Quick Diagnostic Command

Run this locally to check your configuration:
```bash
cd C:\Users\Param\.gemini\antigravity\scratch\clinicbot-ai
python diagnostic_script.py
```

This will check:
- Environment variables
- Database connection
- Clinic configuration  
- Twilio connectivity
- Redis connection
