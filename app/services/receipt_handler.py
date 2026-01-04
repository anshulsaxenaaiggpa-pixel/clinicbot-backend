"""
Receipt Verification Service - UPI Payment OCR

Zero-fee payment verification via UPI screenshot uploads.
Uses Tesseract OCR to extract payment amounts from PhonePe/Paytm receipts.
"""
import re
import io
import requests
from typing import Optional, Dict
from PIL import Image
import pytesseract
from sqlalchemy.orm import Session

from app.core.logging import get_logger

logger = get_logger(__name__)


class ReceiptVerificationService:
    """Service for verifying UPI payment receipts via OCR."""
    
    # Global payment method indicators
    PAYMENT_APPS = {
        # India
        'phonepe', 'paytm', 'googlepay', 'google pay', 'gpay', 'bhim', 'upi',
        # USA
        'zelle', 'venmo', 'cashapp', 'cash app', 'paypal',
        # EU
        'ideal', 'sepa', 'revolut', 'n26', 'monzo',
        # Global
        'wise', 'transferwise', 'stripe',
        # Generic
        'payment', 'paid', 'successful', 'success', 'transaction', 'transfer'
    }
    
    # Multi-currency amount patterns
    AMOUNT_PATTERNS = [
        # INR (₹)
        r'₹\s*(\d+(?:,\d+)*(?:\.\d{2})?)',
        r'Rs\.?\s*(\d+(?:,\d+)*(?:\.\d{2})?)',
        r'INR\s*(\d+(?:,\d+)*(?:\.\d{2})?)',
        # USD ($)
        r'\$\s*(\d+(?:,\d+)*(?:\.\d{2})?)',
        r'USD\s*(\d+(?:,\d+)*(?:\.\d{2})?)',
        # EUR (€)
        r'€\s*(\d+(?:,\d+)*(?:\.\d{2})?)',
        r'EUR\s*(\d+(?:,\d+)*(?:\.\d{2})?)',
        # Generic with currency suffix
        r'\b(\d+(?:,\d+)*(?:\.\d{2})?)\s*(?:rupees|rs|inr|usd|eur|dollars?)\b',
    ]
    
    @staticmethod
    async def download_image(image_url: str) -> Optional[bytes]:
        """Download image from URL."""
        try:
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()
            return response.content
        except Exception as e:
            logger.error(f"Failed to download image: {e}")
            return None
    
    @staticmethod
    def extract_text_from_image(image_bytes: bytes) -> str:
        """Extract text from image using Tesseract OCR."""
        try:
            image = Image.open(io.BytesIO(image_bytes))
            
            # Preprocess image for better OCR
            # Convert to grayscale
            image = image.convert('L')
            
            # Extract text
            text = pytesseract.image_to_string(image, lang='eng')
            return text.lower()
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            return ""
    
    @staticmethod
    def extract_amount(text: str) -> Optional[float]:
        """Extract payment amount from OCR text."""
        for pattern in ReceiptVerificationService.AMOUNT_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                # Take the first match, remove commas, convert to float
                amount_str = matches[0].replace(',', '')
                try:
                    amount = float(amount_str)
                    # Sanity check: amount should be between ₹10 and ₹100,000
                    if 10 <= amount <= 100000:
                        return amount
                except ValueError:
                    continue
        return None
    
    @staticmethod
    def is_payment_receipt(text: str) -> bool:
        """Check if text contains payment app indicators."""
        text_lower = text.lower()
        return any(app in text_lower for app in ReceiptVerificationService.PAYMENT_APPS)
    
    @staticmethod
    def detect_payment_method(text: str) -> str:
        """
        Detect specific payment method from receipt.
        Returns: "UPI", "Zelle", "Venmo", "iDEAL", "SEPA", "Unknown"
        """
        text_lower = text.lower()
        
        # Check for specific payment methods
        if any(x in text_lower for x in ['phonepe', 'paytm', 'gpay', 'bhim', 'upi']):
            return "UPI"
        elif 'zelle' in text_lower:
            return "Zelle"
        elif 'venmo' in text_lower:
            return "Venmo"
        elif 'cashapp' in text_lower or 'cash app' in text_lower:
            return "CashApp"
        elif 'ideal' in text_lower:
            return "iDEAL"
        elif 'sepa' in text_lower:
            return "SEPA"
        elif 'revolut' in text_lower:
            return "Revolut"
        elif 'wise' in text_lower or 'transferwise' in text_lower:
            return "Wise"
        elif 'paypal' in text_lower:
            return "PayPal"
        else:
            return "Unknown"
    
    @classmethod
    async def verify_receipt(
        cls,
        image_url: str,
        expected_amount: float,
        tolerance_percent: float = 0.0
    ) -> Dict[str, any]:
        """
        Verify UPI receipt screenshot.
        
        Args:
            image_url: WhatsApp media URL
            expected_amount: Expected payment amount (e.g., 500.0)
            tolerance_percent: Allowed variance (0.0 = exact match)
        
        Returns:
            {
                "status": "verified" | "invalid" | "error",
                "amount": 500.0,
                "payment_method": "UPI" | "Zelle" | "Venmo" | etc.,
                "text": "extracted ocr text...",
                "is_payment_app": True,
                "confidence": "high" | "low"
            }
        """
        result = {
            "status": "error",
            "amount": None,
            "payment_method": "Unknown",
            "text": "",
            "is_payment_app": False,
            "confidence": "low"
        }
        
        # Download image
        image_bytes = await cls.download_image(image_url)
        if not image_bytes:
            result["status"] = "error"
            logger.error("Could not download receipt image")
            return result
        
        # Extract text via OCR
        text = cls.extract_text_from_image(image_bytes)
        result["text"] = text[:500]  # Store first 500 chars
        
        if not text:
            result["status"] = "error"
            logger.warning("OCR extracted no text from image")
            return result
        
        # Check if it's a payment receipt
        result["is_payment_app"] = cls.is_payment_receipt(text)
        result["payment_method"] = cls.detect_payment_method(text)
        
        # Extract amount
        extracted_amount = cls.extract_amount(text)
        result["amount"] = extracted_amount
        
        if not extracted_amount:
            result["status"] = "invalid"
            logger.warning(f"Could not extract amount from receipt. Text: {text[:200]}")
            return result
        
        # Verify amount matches expected (with tolerance)
        min_amount = expected_amount * (1 - tolerance_percent / 100)
        max_amount = expected_amount * (1 + tolerance_percent / 100)
        
        if min_amount <= extracted_amount <= max_amount:
            result["status"] = "verified"
            result["confidence"] = "high" if result["is_payment_app"] else "low"
            logger.info(f"Receipt verified: ₹{extracted_amount} matches expected ₹{expected_amount}")
        else:
            result["status"] = "invalid"
            logger.warning(
                f"Amount mismatch: extracted ₹{extracted_amount}, "
                f"expected ₹{expected_amount}"
            )
        
        return result
    
    @staticmethod
    async def verify_receipt_with_llm_fallback(
        image_url: str,
        expected_amount: float,
        openai_api_key: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Verify receipt with LLM fallback for complex cases.
        
        If Tesseract fails, use GPT-4o-mini vision to extract amount.
        """
        # Try Tesseract first
        result = await ReceiptVerificationService.verify_receipt(
            image_url, expected_amount
        )
        
        # If OCR failed and we have OpenAI key, try LLM
        if result["status"] == "error" and openai_api_key:
            try:
                import openai
                openai.api_key = openai_api_key
                
                # Use GPT-4o-mini to analyze image
                response = openai.ChatCompletion.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": f"Extract the payment amount from this UPI receipt. Expected: ₹{expected_amount}. Return only the number."
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {"url": image_url}
                                }
                            ]
                        }
                    ]
                )
                
                # Parse LLM response
                llm_text = response.choices[0].message.content
                amount = ReceiptVerificationService.extract_amount(llm_text)
                
                if amount and abs(amount - expected_amount) < 1:
                    result["status"] = "verified"
                    result["amount"] = amount
                    result["confidence"] = "high"
                    logger.info(f"LLM fallback verified: ₹{amount}")
                
            except Exception as e:
                logger.error(f"LLM fallback failed: {e}")
        
        return result


# Singleton instance
receipt_service = ReceiptVerificationService()
