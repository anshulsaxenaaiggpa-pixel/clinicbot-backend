"""
Log Scrubber - Sprint Task 2 & 5

Automatically remove PII from logs before persistence.
Implements privacy-by-design principle.
"""
import re
from typing import Any, Dict


# Patterns for PII detection
PHONE_PATTERN = re.compile(r'\+?\d{10,15}')  # Matches phone numbers
EMAIL_PATTERN = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
NAME_PATTERN_KEYWORDS = ['name', 'patient_name', 'full_name', 'user_name']


class LogScrubber:
    """
    Automatically scrub PII from logs.
    
    Conservative approach: When in doubt, redact.
    """
    
    @staticmethod
    def scrub_phone(text: str) -> str:
        """
        Mask phone numbers, showing last 4 digits only.
        
        Example: +919999999999 → +91XXXXXXX9999
        """
        def replacer(match):
            phone = match.group(0)
            if len(phone) < 8:
                return "XXXX"  # Too short, fully mask
            
            # Keep country code (if present) and last 4 digits
            if phone.startswith('+'):
                country_code = phone[:3]  # e.g., +91
                last_four = phone[-4:]
                masked_middle = 'X' * (len(phone) - 7)
                return f"{country_code}{masked_middle}{last_four}"
            else:
                # No country code
                last_four = phone[-4:]
                masked = 'X' * (len(phone) - 4)
                return f"{masked}{last_four}"
        
        return PHONE_PATTERN.sub(replacer, text)
    
    @staticmethod
    def scrub_email(text: str) -> str:
        """
        Mask email addresses.
        
        Example: user@example.com → u***@e***.com
        """
        def replacer(match):
            email = match.group(0)
            parts = email.split('@')
            if len(parts) != 2:
                return "[EMAIL]"
            
            local, domain = parts
            domain_parts = domain.split('.')
            
            # Mask local part (show first char)
            masked_local = local[0] + '***' if len(local) > 1 else '***'
            
            # Mask domain (show first char and TLD)
            if len(domain_parts) > 1:
                masked_domain = domain_parts[0][0] + '***.' + domain_parts[-1]
            else:
                masked_domain = '***'
            
            return f"{masked_local}@{masked_domain}"
        
        return EMAIL_PATTERN.sub(replacer, text)
    
    @staticmethod
    def scrub_dict(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Scrub PII from dictionary (e.g., JSON logs).
        
        Redacts keys matching PII field names.
        """
        scrubbed = {}
        
        for key, value in data.items():
            key_lower = key.lower()
            
            # Check if key indicates PII
            is_pii_field = (
                'phone' in key_lower or
                'email' in key_lower or
                any(keyword in key_lower for keyword in NAME_PATTERN_KEYWORDS) or
                'password' in key_lower or
                'token' in key_lower or
                'secret' in key_lower
            )
            
            if is_pii_field:
                # Redact based on field type
                if isinstance(value, str):
                    if 'phone' in key_lower:
                        scrubbed[key] = LogScrubber.scrub_phone(value)
                    elif 'email' in key_lower:
                        scrubbed[key] = LogScrubber.scrub_email(value)
                    else:
                        scrubbed[key] = "[REDACTED]"
                else:
                    scrubbed[key] = "[REDACTED]"
            elif isinstance(value, dict):
                # Recursively scrub nested dicts
                scrubbed[key] = LogScrubber.scrub_dict(value)
            elif isinstance(value, list):
                # Scrub list items
                scrubbed[key] = [
                    LogScrubber.scrub_dict(item) if isinstance(item, dict)
                    else str(item)
                    for item in value
                ]
            elif isinstance(value, str):
                # Scrub phone/email from free text
                scrubbed[key] = LogScrubber.scrub_email(LogScrubber.scrub_phone(value))
            else:
                scrubbed[key] = value
        
        return scrubbed
    
    @staticmethod
    def scrub_message(message: str) -> str:
        """
        Scrub PII from log message string.
        
        Used for error messages, debug logs, etc.
        """
        # Scrub phone numbers
        message = LogScrubber.scrub_phone(message)
        
        # Scrub emails
        message = LogScrubber.scrub_email(message)
        
        return message


# Logging configuration for application
def configure_logging():
    """
    Configure application logging with PII scrubbing.
    
    Assumption: Using Python's logging module with custom formatter.
    """
    import logging
    import json
    
    class ScrubberFormatter(logging.Formatter):
        """Custom formatter that scrubs PII before logging."""
        
        def format(self, record):
            # Scrub message
            if hasattr(record, 'msg'):
                record.msg = LogScrubber.scrub_message(str(record.msg))
            
            # Scrub args if present
            if hasattr(record, 'args') and record.args:
                if isinstance(record.args, dict):
                    record.args = LogScrubber.scrub_dict(record.args)
                elif isinstance(record.args, tuple):
                    record.args = tuple(
                        LogScrubber.scrub_message(str(arg))
                        for arg in record.args
                    )
            
            return super().format(record)
    
    # Create handler with scrubber
    handler = logging.StreamHandler()
    handler.setFormatter(ScrubberFormatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    
    # Configure root logger
    logger = logging.getLogger()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    
    return logger


# Example usage in exception handlers
def safe_error_log(error: Exception, context: Dict = None):
    """
    Safely log errors with PII scrubbing.
    
    Use this instead of logging exceptions directly.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    error_msg = LogScrubber.scrub_message(str(error))
    
    if context:
        scrubbed_context = LogScrubber.scrub_dict(context)
        logger.error(f"Error: {error_msg}, Context: {json.dumps(scrubbed_context)}")
    else:
        logger.error(f"Error: {error_msg}")
