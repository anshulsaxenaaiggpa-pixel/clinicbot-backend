"""
Legal Compliance API Endpoints - DPDP/GDPR

Provides public legal documents and contact information:
- Global Privacy Policy
- Data Processing Agreement template
- Grievance Officer contact
- Consent text
"""
from fastapi import APIRouter
from typing import Dict, Any
from datetime import datetime

router = APIRouter()


@router.get("/privacy")
async def get_privacy_policy() -> Dict[str, Any]:
    """
    Get Global Privacy Policy v1.0
    
    Returns privacy policy metadata and links.
    Full PDF available at the policy_url.
    """
    return {
        "version": "1.0",
        "effective_date": "2025-01-01",
        "last_updated": "2024-12-31",
        "policy_url": "https://curaslot.in/docs/global-privacy-policy-v1.0.pdf",
        "company": {
            "name": "Trendoos Products Private Limited",
            "address": "Bhopal, Madhya Pradesh, India",
            "email": "privacy@trendoosproducts.com"
        },
        "data_controller": "Individual Clinic (identifies themselves to patients)",
        "data_processor": "Trendoos Products Private Limited (CuraSlot platform)",
        "data_collected": [
            "Phone number (required for booking)",
            "Name (optional)",
            "Appointment details"
        ],
        "data_not_collected": [
            "Medical records",
            "Prescriptions",
            "Health conditions",
            "Payment/financial information"
        ],
        "retention_period": "3 years or until erasure request",
        "patient_rights": [
            "Access your data",
            "Correct your data",
            "Delete your data",
            "Withdraw consent (reply STOP)",
            "Lodge complaint with grievance officer"
        ],
        "grievance_officer": {
            "email": "grievance@trendoosproducts.com",
            "response_time": "72 hours"
        },
        "jurisdictions": ["India (DPDP 2023)", "GDPR (EU)", "CCPA (USA)"]
    }


@router.get("/contact")
async def get_legal_contact() -> Dict[str, Any]:
    """
    Get legal and grievance contact information.
    
    Grievance Officer details for DPDP/GDPR compliance.
    """
    return {
        "company": "Trendoos Products Private Limited",
        "grievance_officer": {
            "email": "grievance@trendoosproducts.com",
            "phone": "+91-XXXXXXXXXX",  # To be updated
            "address": "Bhopal, Madhya Pradesh, India",
            "response_time": "72 hours"
        },
        "support": {
            "email": "support@curaslot.in",
            "whatsapp": "+14155238886"  # Twilio sandbox, to be updated
        },
        "dpo_designation": "Data Protection Officer designated per DPDP 2023 Section 10",
        "complaint_escalation": [
            "1. Email grievance@trendoosproducts.com",
            "2. Response within 72 hours",
            "3. Resolution within 30 days",
            "4. Escalate to Data Protection Board of India if unsatisfied"
        ]
    }


@router.get("/dpa")
async def get_dpa_template() -> Dict[str, Any]:
    """
    Get Data Processing Agreement template link.
    
    Clinics must sign DPA before going live.
    """
    return {
        "version": "1.0",
        "template_url": "https://curaslot.in/docs/clinic-dpa-template-v1.0.pdf",
        "description": "Data Processing Agreement between CuraSlot (Processor) and Clinic (Controller)",
        "required_before": "Production launch",
        "key_terms": [
            "Clinic is Data Controller",
            "CuraSlot is Data Processor",
            "Data used only for appointment booking",
            "No data sharing with third parties",
            "Patient deletion within 72 hours on request",
            "3-year data retention maximum"
        ],
        "signing_instructions": [
            "1. Download template from template_url",
            "2. Fill in clinic details",
            "3. Sign and email to legal@curaslot.in",
            "4. Receive countersigned copy within 24 hours",
            "5. Account activated for production"
        ]
    }


@router.get("/consent")
async def get_consent_text() -> Dict[str, Any]:
    """
    Get current consent text shown to patients.
    
    This is the consent prompt sent via WhatsApp.
    """
    return {
        "version": "v1.0",
        "language": "en",
        "text": """🤖 CuraSlot Appointment Bot

We collect ONLY:
✅ Phone (booking)
✅ Name (optional)

We NEVER collect:
❌ Prescriptions/Medical Records

Data → Clinic ONLY
Privacy: curaslot.in/privacy

Reply NUMBER ONLY:
1. AGREE & CONTINUE
2. DECLINE""",
        "options": {
            "1": "AGREE & CONTINUE",
            "2": "DECLINE"
        },
        "withdrawal": "Reply STOP at any time to withdraw consent"
    }


@router.get("/usa-compliance")
async def usa_compliance() -> Dict[str, Any]:
    """
    Get USA Compliance status (HIPAA/COPPA/CCPA).
    
    Verified for USA market requirements.
    """
    return {
        "hipaa": {"status": "EXEMPT", "reason": "Scheduling only (NO PHI)"},
        "coppa": {"status": "COMPLIANT", "method": "Parent WhatsApp = Adult consent"},
        "ccpa": {"access": "Reply DATA", "delete": "Reply DELETE"},
        "contact": "trendoosproducts@gmail.com"
    }


@router.get("/health")
async def legal_health() -> Dict[str, str]:
    """Legal endpoints health check"""
    return {
        "status": "healthy",
        "service": "CuraSlot Legal API",
        "timestamp": datetime.utcnow().isoformat()
    }
