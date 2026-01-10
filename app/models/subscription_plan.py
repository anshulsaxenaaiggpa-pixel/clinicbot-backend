"""Subscription plan model"""
from sqlalchemy import Column, String, Integer, Boolean, DateTime, JSON
from datetime import datetime

from app.db.base_class import Base


class SubscriptionPlan(Base):
    """Subscription plan/pricing tier model"""
    __tablename__ = "subscription_plans"
    
    id = Column(String(36), primary_key=True)
    tier = Column(String(20), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    
    # Pricing in different currencies
    monthly_price_inr = Column(Integer, nullable=False)       # ₹1999, ₹3999, ₹7499
    monthly_price_usd = Column(Integer, nullable=False)       # $25, $50, $95
    
    # WhatsApp quota
    whatsapp_quota = Column(Integer, nullable=False)          # 0, 200, 999999
    
    # Stripe price IDs (for subscription billing)
    stripe_price_id_inr = Column(String(100), nullable=True)
    stripe_price_id_usd = Column(String(100), nullable=True)
    
    # Features JSON
    features = Column(JSON, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "tier": self.tier,
            "name": self.name,
            "monthly_price_inr": self.monthly_price_inr,
            "monthly_price_usd": self.monthly_price_usd,
            "whatsapp_quota": self.whatsapp_quota,
            "features": self.features,
            "is_active": self.is_active
        }
