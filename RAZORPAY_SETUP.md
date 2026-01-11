# Razorpay India Launch Guide

## ✅ DONE
- Razorpay integration built (`app/api/payments/razorpay.py`)
- Router registered in `main.py`
- Package added to requirements

## 🚀 5-MINUTE SETUP

### 1. Create Razorpay Account (2 min)
**URL**: https://dashboard.razorpay.com/signup

1. Sign up (instant, no invite needed)
2. Complete KYC (Aadhaar + PAN)
3. Go to **Settings** → **API Keys**
4. Generate **Test Keys** first:
   - Key ID: `rzp_test_xxxxx`
   - Key Secret: `xxxxx`

### 2. Add to Railway (1 min)
Railway → **Variables** → Add:

```
RAZORPAY_KEY_ID=rzp_test_xxxxxxxxxxxxx
RAZORPAY_KEY_SECRET=xxxxxxxxxxxxxxxxxxxxx
RAZORPAY_WEBHOOK_SECRET=(generate from Razorpay dashboard)
```

### 3. Deploy (2 min)
```bash
git add .
git commit -m "Add Razorpay India payments"
git push origin main
```

Railway auto-deploys → Razorpay ready!

---

## 💳 PAYMENT FLOW

**India Doctors** (`country_code='IN'`):
1. Patient clicks "Book Now"
2. Frontend calls `/api/razorpay/create-order`
3. Razorpay Checkout opens (UPI/Card/Wallet)
4. Patient pays ₹500
5. Frontend calls `/api/razorpay/verify-payment`
6. Appointment created + WhatsApp confirmation sent

**International** (`country_code='US/AE/etc'`):
- Uses existing Stripe Connect flow

---

## 🧪 TEST

1. **Create Order**:
```bash
curl -X POST https://your-app.up.railway.app/api/razorpay/create-order \
  -H "Content-Type: application/json" \
  -d '{
    "doctor_id": "xxx",
    "patient_name": "Test Patient",
    "patient_phone": "+919876543210",
    "appointment_date": "2026-01-15",
    "appointment_time": "10:00"
  }'
```

Response:
```json
{
  "order_id": "order_xxxxx",
  "amount": 800,
  "currency": "INR",
  "razorpay_key": "rzp_test_xxxxx"
}
```

2. **Test Payment**: Use test card `4111 1111 1111 1111`

3. **Verify**: Check appointment created in database

---

## 💰 PRICING

**Razorpay Fees**: 2% per transaction
- ₹500 booking = ₹10 fee
- ₹800 booking = ₹16 fee

**Payouts**: T+2 days to doctor's bank account

---

## 🔧 WEBHOOK SETUP

Razorpay Dashboard → **Webhooks**:
- URL: `https://your-app.up.railway.app/api/razorpay/webhook`
- Events: `payment.captured`, `payment.failed`
- Secret: Generate and add to Railway env

---

## 🎯 LAUNCH

**India-first strategy**:
- All India doctors use Razorpay (instant UPI)
- USA/UAE doctors use Stripe Connect
- Hybrid gateway selection based on `doctor.country_code`

**Advantages**:
- ✅ No Stripe India invite wait
- ✅ Native UPI support (90% of India payments)
- ✅ 2% fees (competitive)
- ✅ Instant KYC approval

**Next**: Test booking → WhatsApp confirmation → Launch Bhopal!
