# How to Deploy Your Fixes to Railway

## ⚠️ CRITICAL: Changes are NOT live yet!

Your browser is still running the OLD code. You need to **restart the Railway service**.

---

## Option 1: Push to Git (Recommended - Auto Deploys)

```bash
# 1. Check what files changed
git status

# 2. Stage all changes
git add .

# 3. Commit with message
git commit -m "Fix AuditLog schema mismatches - created_at to timestamp"

# 4. Push to GitHub
git push origin main

# 5. Railway will AUTO-DEPLOY in ~2-3 minutes
```

**Railway will automatically detect the push and redeploy.**

---

## Option 2: Manual Restart in Railway Dashboard

1. Go to https://railway.app
2. Click on your **ClinicBot project**
3. Click on the **service** (backend)
4. Click **"Deployments"** tab
5. Click the **three dots (...)** on the latest deployment
6. Select **"Redeploy"**

---

## How to Verify It Worked

After deployment completes:

1. ✅ **Check Deployment Logs**
   - Look for: `INFO:     Application startup complete.`
   - No errors should appear

2. ✅ **Test Dashboard**
   - Visit: `https://your-app.up.railway.app/admin/dashboard`
   - Should see **200 OK** (not 500 error)

3. ✅ **Test Login**
   - Visit: `https://your-app.up.railway.app/admin/login`
   - Try logging in with your credentials

---

## If Login Still Fails After Restart

Run this command on Railway to verify admin user exists:

```python
# Via Railway CLI or console
python -c "
from app.db.session import SessionLocal
from app.models.admin_user import AdminUser

db = SessionLocal()
user = db.query(AdminUser).filter(AdminUser.email == 'curaslot@gmail.com').first()
if user:
    print(f'✅ Admin user found: {user.email}')
    print(f'   Password hash: {user.password_hash[:50]}...')
    print(f'   Is active: {user.is_active}')
else:
    print('❌ Admin user NOT found in database!')
db.close()
"
```

---

## Summary

**What's Fixed:**
- ✅ AuditLog.created_at → AuditLog.timestamp
- ✅ AuditLog.event_type → AuditLog.action  
- ✅ AuditLog.actor_id → AuditLog.actor_reference
- ✅ All 7 files updated

**What You Need to Do:**
1. Push code to Git (Railway auto-deploys)
2. OR manually redeploy in Railway dashboard
3. Wait 2-3 minutes for deployment
4. Test login + dashboard

**Expected Result:**
- Dashboard loads without 500 error
- Login should work (if separate issue, we'll debug next)
