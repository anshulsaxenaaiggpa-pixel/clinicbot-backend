# Deploy Booking Flow Fix to Railway

## Changes Made

Fixed database schema mismatch causing booking flow to fail:

1. **Removed Non-Existent Columns from Doctor Model** ([`doctor.py`](file:///C:/Users/Param/.gemini/antigravity/scratch/clinicbot-ai/app/models/doctor.py))
   - Removed `whatsapp_number`, `city`, `is_searchable` fields
   - These were v1.1 features not yet in production database
   - **Error**: `column doctors.whatsapp_number does not exist`

2. **Session Missing `user_phone`** ([`whatsapp_handler.py`](file:///C:/Users/Param/.gemini/antigravity/scratch/clinicbot-ai/app/services/whatsapp_handler.py#L185))
   - Added `session["user_phone"] = user_phone` before passing session to conversation manager

3. **Context Dict Not Initialized** ([`conversation_manager.py`](file:///C:/Users/Param/.gemini/antigravity/scratch/clinicbot-ai/app/services/conversation_manager.py#L123-L125))
   - Added check to ensure `session["context"]` dict exists

## How to Deploy

### Option 1: Auto-Deploy (If GitHub connected to Railway)

```bash
# In your project directory
git add .
git commit -m "Fix: Add user_phone to session and ensure context dict exists"
git push
```

Railway will automatically detect the push and redeploy within 2-3 minutes.

### Option 2: Manual Railway CLI Deploy

```bash
railway up
```

### Option 3: Railway Dashboard

1. Go to Railway dashboard → Your project
2. Click your service → **Deployments**
3. Click **Deploy** → **Redeploy**

## After Deployment

### Test the Booking Flow

1. Send "Hi" to WhatsApp bot
2. Reply "1" (Book new appointment)
3. **Expected**: You should now see doctor selection list instead of error

Example:
```
[You] Hi
[Bot] 👋 Welcome to ClinicBot! Reply NUMBER ONLY: 1. Book new appointment...

[You] 1
[Bot] Which doctor would you like to see?
      1. Dr. [Name] ([Specialization])
      2. Dr. [Name] ([Specialization])
      
      Reply with the number or doctor name.
```

### If It Still Fails

Check Railway logs for the detailed error:
1. Railway dashboard → Deployments → View Logs
2. Look for lines starting with "❌ BOOKING HANDLER ERROR"
3. Share the error message with me

## Quick Deployment Commands

```bash
# Navigate to project
cd C:\Users\Param\.gemini\antigravity\scratch\clinicbot-ai

# Stage changes
git add app/models/doctor.py app/services/whatsapp_handler.py app/services/conversation_manager.py

# Commit
git commit -m "Fix: remove non-existent DB columns from Doctor model"

# Push (triggers Railway auto-deploy)
git push
```

## Expected Timeline

- **Commit → Push**: 10 seconds
- **Railway Build**: 2-3 minutes
- **Ready to Test**: 3-4 minutes total
