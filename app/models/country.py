"""Country model"""
from sqlalchemy import Column, String, Boolean

from app.db.base_class import Base


class Country(Base):
    """Country reference model for multi-currency support"""
    __tablename__ = "countries"
    
    code = Column(String(2), primary_key=True)                  # IN, US, AE, etc.
    name = Column(String(100), nullable=False)
    currency = Column(String(3), nullable=False)                # INR, USD, AED, etc.
    currency_symbol = Column(String(10), nullable=False)         # ₹, $, د.إ, etc.
    payment_provider = Column(String(20), nullable=False)        # stripe, razorpay, tap
    language = Column(String(5), default='en')                   # en, ar, etc.
    is_active = Column(Boolean, default=True)
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "code": self.code,
            "name": self.name,
            "currency": self.currency,
            "currency_symbol": self.currency_symbol,
            "payment_provider": self.payment_provider,
            "language": self.language,
            "is_active": self.is_active
        }
