"""Currency configuration and multi-currency utilities for global marketplace"""
from enum import Enum
from decimal import Decimal
from typing import Optional
import requests


class Currency(str, Enum):
    """Supported currencies"""
    INR = "INR"
    USD = "USD"
    AED = "AED"
    GBP = "GBP"
    AUD = "AUD"
    EUR = "EUR"


CURRENCY_CONFIG = {
    "INR": {
        "symbol": "₹",
        "locale": "en-IN",
        "stripe_min_amount": 50,  # Minimum charge in paise (₹0.50)
        "decimal_places": 0,  # INR doesn't use decimals in pricing
    },
    "USD": {
        "symbol": "$",
        "locale": "en-US",
        "stripe_min_amount": 50,  # Minimum charge in cents ($0.50)
        "decimal_places": 2,
    },
    "AED": {
        "symbol": "د.إ",
        "locale": "ar-AE",
        "stripe_min_amount": 200,  # Minimum charge in fils (2 AED)
        "decimal_places": 2,
    },
    "GBP": {
        "symbol": "£",
        "locale": "en-GB",
        "stripe_min_amount": 30,  # Minimum charge in pence (£0.30)
        "decimal_places": 2,
    },
    "AUD": {
        "symbol": "A$",
        "locale": "en-AU",
        "stripe_min_amount": 50,  # Minimum charge in cents (A$0.50)
        "decimal_places": 2,
    },
    "EUR": {
        "symbol": "€",
        "locale": "en-EU",
        "stripe_min_amount": 50,  # Minimum charge in cents (€0.50)
        "decimal_places": 2,
    },
}

# Country to currency mapping
COUNTRY_CURRENCY_MAP = {
    "IN": "INR",
    "US": "USD",
    "AE": "AED",
    "GB": "GBP",
    "AU": "AUD",
    "DE": "EUR",
    "FR": "EUR",
    "ES": "EUR",
    "IT": "EUR",
}


def detect_country_from_ip(ip_address: str) -> Optional[str]:
    """
    Detect country from IP address using ipapi.co
    
    Args:
        ip_address: IPv4 or IPv6 address
        
    Returns:
        2-letter country code (e.g., 'IN', 'US') or None if detection fails
    """
    try:
        response = requests.get(
            f"https://ipapi.co/{ip_address}/country_code/",
            timeout=2
        )
        if response.status_code == 200:
            country_code = response.text.strip()
            return country_code if len(country_code) == 2 else None
    except Exception as e:
        print(f"IP detection failed: {e}")
        return None
    return None


def get_currency_for_country(country_code: str) -> str:
    """
    Get currency for a country code
    
    Args:
        country_code: 2-letter country code
        
    Returns:
        3-letter currency code (defaults to USD if not found)
    """
    return COUNTRY_CURRENCY_MAP.get(country_code, "USD")


def convert_currency(
    amount: Decimal,
    from_currency: str,
    to_currency: str
) -> Decimal:
    """
    Convert between currencies using live exchange rates
    Uses exchangerate-api.com (free tier)
    
    Args:
        amount: Amount to convert
        from_currency: Source currency code (e.g., 'INR')
        to_currency: Target currency code (e.g., 'USD')
        
    Returns:
        Converted amount as Decimal
    """
    if from_currency == to_currency:
        return amount
    
    try:
        # Using exchangerate-api.com free tier
        response = requests.get(
            f"https://api.exchangerate-api.com/v4/latest/{from_currency}",
            timeout=3
        )
        if response.status_code == 200:
            rates = response.json()['rates']
            rate = Decimal(str(rates[to_currency]))
            return amount * rate
    except Exception as e:
        print(f"Currency conversion failed: {e}")
        # Fallback to approximate rates if API fails
        return amount * get_fallback_rate(from_currency, to_currency)
    
    return amount


def get_fallback_rate(from_currency: str, to_currency: str) -> Decimal:
    """Fallback exchange rates (updated monthly)"""
    # Approximate rates as of Jan 2026
    rates = {
        ("INR", "USD"): Decimal("0.012"),
        ("USD", "INR"): Decimal("83.0"),
        ("INR", "AED"): Decimal("0.044"),
        ("AED", "INR"): Decimal("22.6"),
        ("USD", "AED"): Decimal("3.67"),
        ("AED", "USD"): Decimal("0.27"),
    }
    return rates.get((from_currency, to_currency), Decimal("1.0"))


def format_price(amount: Decimal, currency: str) -> str:
    """
    Format price with currency symbol
    
    Args:
        amount: Price amount
        currency: Currency code
        
    Returns:
        Formatted price string (e.g., "₹500", "$25.00")
    """
    config = CURRENCY_CONFIG.get(currency, CURRENCY_CONFIG["USD"])
    symbol = config["symbol"]
    decimals = config["decimal_places"]
    
    if decimals == 0:
        return f"{symbol}{int(amount)}"
    else:
        return f"{symbol}{amount:.{decimals}f}"


def get_stripe_amount(amount: Decimal, currency: str) -> int:
    """
    Convert amount to Stripe's smallest currency unit
    
    Args:
        amount: Amount in standard currency unit
        currency: Currency code
        
    Returns:
        Amount in smallest unit (e.g., paise for INR, cents for USD)
    """
    # Most currencies use 2 decimals, but some (JPY, INR) don't
    multiplier = 100 if currency not in ["JPY", "KRW"] else 1
    return int(amount * multiplier)


def get_payment_provider(currency: str, country: str) -> str:
    """
    Determine which payment provider to use
    
    Args:
        currency: Currency code
        country: Country code
        
    Returns:
        Payment provider name: 'stripe', 'razorpay', or 'tap'
    """
    if country == "IN":
        return "razorpay"  # Best for Indian UPI/cards
    elif country == "AE":
        return "stripe"  # Tap as fallback, but Stripe is more common
    else:
        return "stripe"  # Default for global
