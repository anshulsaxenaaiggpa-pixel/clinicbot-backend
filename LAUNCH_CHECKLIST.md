# 🚀 V3 LAUNCH CHECKLIST

## ✅ COMPLETED
- [x] Code pushed to Railway (commit: d8f6842)
- [x] Subscription API built
- [x] Modern homepage with glassmorphism
- [x] PWA manifest + service worker
- [x] Seed script ready (20 doctors)

## 🎯 FINAL STEPS (30 min)

### Step 1: Verify Railway Deployment ⏱️ 2min
```bash
# Check deployment status
railway status

# View logs to confirm migration
railway logs
```

**Look for**: `✅ Database migrations completed successfully`

---

### Step 2: Create Stripe Price IDs ⏱️ 5min

**URL**: https://dashboard.stripe.com/test/products

**Create 6 Recurring Prices**:

1. **Starter India**
   - Product: "CuraSlot Starter (India)"
   - Price: ₹1,999 INR
   - Billing: Monthly recurring
   - **Copy Price ID**: `price_...` → Save as `STARTER_INR`

2. **Starter International**
   - Product: "CuraSlot Starter (Global)"
   - Price: $25 USD
   - Billing: Monthly recurring
   - **Copy Price ID**: `price_...` → Save as `STARTER_USD`

3. **Growth India**
   - Product: "CuraSlot Growth (India)"
   - Price: ₹3,999 INR
   - Billing: Monthly recurring
   - **Copy Price ID**: `price_...` → Save as `GROWTH_INR`

4. **Growth International**
   - Product: "CuraSlot Growth (Global)"
   - Price: $50 USD
   - Billing: Monthly recurring
   - **Copy Price ID**: `price_...` → Save as `GROWTH_USD`

5. **Enterprise India**
   - Product: "CuraSlot Enterprise (India)"
   - Price: ₹7,499 INR
   - Billing: Monthly recurring
   - **Copy Price ID**: `price_...` → Save as `ENTERPRISE_INR`

6. **Enterprise International**
   - Product: "CuraSlot Enterprise (Global)"
   - Price: $95 USD
   - Billing: Monthly recurring
   - **Copy Price ID**: `price_...` → Save as `ENTERPRISE_USD`

---

### Step 3: Update Database ⏱️ 3min

**Railway Dashboard** → Your Project → **Data** tab → **Query**

```sql
-- Update with your actual Price IDs from Step 2
UPDATE subscription_plans 
SET stripe_price_id_inr = 'price_REPLACE_WITH_STARTER_INR',
    stripe_price_id_usd = 'price_REPLACE_WITH_STARTER_USD'
WHERE tier = 'starter';

UPDATE subscription_plans 
SET stripe_price_id_inr = 'price_REPLACE_WITH_GROWTH_INR',
    stripe_price_id_usd = 'price_REPLACE_WITH_GROWTH_USD'
WHERE tier = 'growth';

UPDATE subscription_plans 
SET stripe_price_id_inr = 'price_REPLACE_WITH_ENTERPRISE_INR',
    stripe_price_id_usd = 'price_REPLACE_WITH_ENTERPRISE_USD'
WHERE tier = 'enterprise';
```

**Verify**:
```sql
SELECT tier, stripe_price_id_inr, stripe_price_id_usd FROM subscription_plans;
```

---

### Step 4: Seed 20 Doctors ⏱️ 5min

```bash
railway run python seed_global_doctors.py
```

**Expected Output**:
```
✅ SUCCESSFULLY SEEDED 20 DOCTORS
   • 10 in Bhopal, India (INR)
   • 5 in Dubai, UAE (AED)
   • 5 in New York, USA (USD)

💰 PROJECTED MRR: ₹79,980 (20 doctors × ₹3,999)
```

---

### Step 5: Test Everything ⏱️ 15min

**Test 1: Homepage**
- URL: `https://your-app.up.railway.app/`
- ✅ See glassmorphism hero
- ✅ City cards visible (Bhopal, Dubai, NYC, etc)
- ✅ Search box functional
- ✅ PWA install button in bottom-right

**Test 2: City Directory**
- URL: `/city/bhopal`
- ✅ See 10 doctors listed
- ✅ Each shows: name, specialty, rating, fee
- ✅ WhatsApp "Book Now" buttons work

**Test 3: Doctor Login & Subscriptions**
- URL: `/doctor/login`
- Login: Any seeded doctor (password: `doctor123`)
- Go to: `/doctor/billing`
- ✅ Current plan shows (Starter/Growth/Enterprise)
- ✅ WhatsApp quota: "0 / 200" (for Growth tier)
- ✅ Click "Upgrade to Enterprise" → Stripe Checkout opens
- ✅ Checkout shows correct price (₹7,499 or $95)

**Test 4: PWA Installation**
- Chrome browser → Visit homepage
- ✅ See install prompt in address bar
- ✅ Click install → App installs to desktop/home screen

**Test 5: Search**
- Homepage → Search "Cardiologist Bhopal"
- ✅ Redirects to `/city/bhopal?specialty=cardiology`
- ✅ Filters to cardiologists only

---

## 📊 LAUNCH METRICS

**Current**:
- 20 doctors seeded
- 3 cities live (Bhopal, Dubai, NYC)
- MRR: ₹79,980

**Target**:
- 50 doctors = ₹199,950 MRR
- 10 cities
- 1,000+ doctors (global marketplace)

---

## 🎬 GO LIVE

1. **Share**: `/city/bhopal` on social media
2. **Screenshot**: Homepage + city page for marketing
3. **Monitor**: Railway logs for any errors
4. **Track**: MRR in `/admin/payments`

---

## 🔧 TROUBLESHOOTING

**Migration didn't run?**
```bash
railway run alembic upgrade head
```

**Seed script fails?**
- Check doctor model has all V3 fields
- Verify clinic exists first
- Check for unique constraint errors (slug/whatsapp)

**Stripe Checkout not opening?**
- Verify Price IDs in database
- Check Stripe API keys in Railway env vars
- Look for errors in browser console

---

## ✅ LAUNCH READY

Once all 5 tests pass → **LIVE!** 🚀

**Next**: Onboard first 10 doctors → ₹40k MRR
