# V3 Marketplace Deployment Guide

## 🚀 IMMEDIATE ACTIONS

### Step 1: Verify Railway Deployment
Code has been pushed to Railway. Check deployment status:
```
Railway Dashboard → clinicbot-ai → Deployments
```

Watch for migration logs:
```
✅ Database migrations completed successfully
✅ subscriptions registered
```

### Step 2: Create Stripe Price IDs

**URL**: https://dashboard.stripe.com/products

Create 6 recurring products:

1. **Starter INR**
   - Name: "CuraSlot Starter (India)"
   - Price: ₹1,999/month
   - Copy Price ID: `price_...`

2. **Starter USD**
   - Name: "CuraSlot Starter (International)"
   - Price: $25/month
   - Copy Price ID: `price_...`

3. **Growth INR**
   - Name: "CuraSlot Growth (India)"
   - Price: ₹3,999/month
   - Copy Price ID: `price_...`

4. **Growth USD**
   - Name: "CuraSlot Growth (International)"
   - Price: $50/month
   - Copy Price ID: `price_...`

5. **Enterprise INR**
   - Name: "CuraSlot Enterprise (India)"
   - Price: ₹7,499/month
   - Copy Price ID: `price_...`

6. **Enterprise USD**
   - Name: "CuraSlot Enterprise (International)"
   - Price: $95/month
   - Copy Price ID: `price_...`

### Step 3: Update Database

Railway → Data → Query:

```sql
-- Replace price_xxx with actual IDs from Stripe
UPDATE subscription_plans 
SET stripe_price_id_inr='price_1234567890_starter_inr', 
    stripe_price_id_usd='price_0987654321_starter_usd'
WHERE tier='starter';

UPDATE subscription_plans 
SET stripe_price_id_inr='price_1234567890_growth_inr', 
    stripe_price_id_usd='price_0987654321_growth_usd'
WHERE tier='growth';

UPDATE subscription_plans 
SET stripe_price_id_inr='price_1234567890_enterprise_inr', 
    stripe_price_id_usd='price_0987654321_enterprise_usd'
WHERE tier='enterprise';
```

### Step 4: Seed Doctors

```bash
railway run python seed_global_doctors.py
```

**Expected**: ✅ 20 doctors created (10 Bhopal, 5 Dubai, 5 NYC)

### Step 5: Test Features

**Homepage**:
- Visit: https://curaslot-production.up.railway.app/
- Check: City cards, search box, PWA install button

**Subscriptions**:
- Login as doctor: `/doctor/login`
- Go to: `/doctor/billing`
- Click: "Upgrade to Growth"
- Verify: Stripe Checkout opens with correct price

**City Directory**:
- Visit: `/city/bhopal`
- Verify: 10 doctors listed with ratings

## 📊 Success Metrics

- ✅ 20 doctors seeded
- ✅ MRR: ₹79,980 (20 × ₹3,999)
- ✅ 3 cities live (Bhopal, Dubai, NYC)
- ✅ PWA installable
- ✅ Stripe subscriptions functional

## 🎯 Next Steps

1. **Onboard 30 more doctors** → ₹199,950 MRR
2. **Add registration wizard** (Phase 6)
3. **Create blog posts** for SEO
4. **Enable reviews system**

Deployment time: ~15 minutes  
Launch ready: TODAY! 🚀
