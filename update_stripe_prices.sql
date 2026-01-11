-- V3 Stripe Price IDs Update Script
-- Run this in Railway Data → Query after creating Stripe Price IDs

-- INSTRUCTIONS:
-- 1. Replace price_xxxxx with actual Price IDs from Stripe Dashboard
-- 2. Run this entire script in Railway Data tab
-- 3. Verify with SELECT query at the end

-- Update Starter Tier
UPDATE subscription_plans 
SET stripe_price_id_inr = 'price_REPLACE_STARTER_INR_HERE',
    stripe_price_id_usd = 'price_REPLACE_STARTER_USD_HERE'
WHERE tier = 'starter';

-- Update Growth Tier
UPDATE subscription_plans 
SET stripe_price_id_inr = 'price_REPLACE_GROWTH_INR_HERE',
    stripe_price_id_usd = 'price_REPLACE_GROWTH_USD_HERE'
WHERE tier = 'growth';

-- Update Enterprise Tier
UPDATE subscription_plans 
SET stripe_price_id_inr = 'price_REPLACE_ENTERPRISE_INR_HERE',
    stripe_price_id_usd = 'price_REPLACE_ENTERPRISE_USD_HERE'
WHERE tier = 'enterprise';

-- Verify updates
SELECT 
    tier,
    name,
    monthly_price_inr,
    monthly_price_usd,
    stripe_price_id_inr,
    stripe_price_id_usd,
    whatsapp_quota
FROM subscription_plans
ORDER BY monthly_price_inr;

-- Expected result:
-- starter   | Starter    | 1999 | 25  | price_... | price_... | 0
-- growth    | Growth     | 3999 | 50  | price_... | price_... | 200
-- enterprise| Enterprise | 7499 | 95  | price_... | price_... | 999999
