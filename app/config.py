"""Application configuration using Pydantic Settings"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Database
    DATABASE_URL: Optional[str] = "sqlite:///./clinicbot.db"
    REDIS_URL: Optional[str] = None
    
    # API Keys
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-3.5-turbo"  # Default OpenAI model for intent classification
    GEMINI_API_KEY: Optional[str] = None
    
    # WhatsApp (Twilio)
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_WHATSAPP_NUMBER: Optional[str] = None
    
    # WhatsApp (Meta Cloud API)
    META_WHATSAPP_TOKEN: Optional[str] = None
    META_PHONE_NUMBER_ID: Optional[str] = None
    META_VERIFY_TOKEN: Optional[str] = None
    
    # WhatsApp (Gupshup - India optimized, ₹0.30/msg)
    GUPSHUP_API_KEY: Optional[str] = None
    GUPSHUP_APP_NAME: Optional[str] = None
    GUPSHUP_SOURCE_NUMBER: Optional[str] = None  # Your WhatsApp Business number
    WHATSAPP_PROVIDER: str = "twilio"  # twilio, meta, or gupshup
    
    # Payment
    RAZORPAY_KEY_ID: Optional[str] = None
    RAZORPAY_KEY_SECRET: Optional[str] = None
    
    # Security
    SECRET_KEY: str  # JWT signing (legacy)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Admin UI Security (CRITICAL - DO NOT HARD-CODE)
    SESSION_SECRET_KEY: str  # Required: >=32 chars, for session cookie signing
    ADMIN_UI_ENABLED: bool = True  # Feature flag - enabled by default for dashboard
    ADMIN_UI_HTTPS_ONLY: bool = True  # Force HTTPS-only cookies (False only for local dev)
    PASSWORD_HASH_ROUNDS: int = 12  # Bcrypt cost factor (10-14 recommended)
    
    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
    def validate_security_config(self):
        """Validate security configuration on startup."""
        # Ensure SESSION_SECRET_KEY is strong
        if len(self.SESSION_SECRET_KEY) < 32:
            raise ValueError("SESSION_SECRET_KEY must be at least 32 characters")
        
        # Ensure HTTPS in production
        if self.ENVIRONMENT == "production" and not self.ADMIN_UI_HTTPS_ONLY:
            raise ValueError("ADMIN_UI_HTTPS_ONLY must be True in production")
        
        # Ensure DEBUG is off in production
        if self.ENVIRONMENT == "production" and self.DEBUG:
            raise ValueError("DEBUG must be False in production")
        
        # Validate password hash rounds
        if self.PASSWORD_HASH_ROUNDS < 10 or self.PASSWORD_HASH_ROUNDS > 14:
            raise ValueError("PASSWORD_HASH_ROUNDS must be between 10 and 14")


settings = Settings()

# Validate on import
settings.validate_security_config()
