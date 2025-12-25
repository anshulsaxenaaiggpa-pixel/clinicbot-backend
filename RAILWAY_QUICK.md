# Railway Deployment - Quick Start

**Time:** 15 minutes | **Cost:** FREE ($5 credit)

---

## ✅ Step-by-Step Checklist

### 1. Sign Up (2 min)
- [ ] Go to: https://railway.app
- [ ] Click "Login with GitHub"
- [ ] Add credit card ($5 free credit given)

### 2. Deploy (3 min)
- [ ] Click **"New Project"**
- [ ] Select **"Deploy from GitHub repo"**
- [ ] Choose **"clinicbot-backend"**
- [ ] Railway auto-deploys! ✨

### 3. Add Database (1 min)
- [ ] Click **"+ New"** → **"Database"** → **"PostgreSQL"**
- [ ] Auto-configured! ✅

### 4. Add Redis (1 min)
- [ ] Click **"+ New"** → **"Database"** → **"Redis"**
- [ ] Auto-configured! ✅

### 5. Add Variables (3 min)
Go to service → **"Variables"** tab, add:

- [ ] `OPENAI_API_KEY` = `sk-...`
- [ ] `TWILIO_ACCOUNT_SID` = `AC...`
- [ ] `TWILIO_AUTH_TOKEN` = `...`
- [ ] `TWILIO_WHATSAPP_NUMBER` = `whatsapp:+14155238886`
- [ ] `SECRET_KEY` = `(64 char string)`
- [ ] `ENVIRONMENT` = `production`
- [ ] `DEBUG` = `False`

**Note:** `DATABASE_URL` and `REDIS_URL` auto-added by Railway!

### 6. Get URL (30 sec)
- [ ] Go to **Settings** → **Domains**
- [ ] Copy your URL: `_______________________`
- [ ] Test: `https://your-url.up.railway.app/docs`

### 7. Run Seed Script (2 min)
**Edit Start Command:**
- [ ] Settings → Start Command
- [ ] Set to: `python backend/seed_test_data.py && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- [ ] Save & redeploy
- [ ] Copy Clinic ID: `_______________________`
- [ ] Copy API Key: `_______________________`

### 8. WhatsApp (3 min)
- [ ] Twilio Console → WhatsApp Sandbox
- [ ] Webhook: `https://your-url.up.railway.app/api/v1/webhooks/whatsapp`
- [ ] Method: POST
- [ ] WhatsApp: join sandbox
- [ ] Test: Send "Hi"

---

## 🎉 Done!

- [ ] Bot responds to "Hi" ✅
- [ ] Railway URL: `_______________________`
- [ ] Status: **LIVE!** 🚀

**Total deployment time: 15 minutes**
