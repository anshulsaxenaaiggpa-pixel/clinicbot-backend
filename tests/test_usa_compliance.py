import pytest
from app.services.consent_handler import get_consent_text, CONSENT_TEXT_V1, CONSENT_TEXT_V1_USA, BOOKING_FOR_MENU
from app.services.data_requests import handle_ccpa_request
from unittest.mock import AsyncMock, patch

def test_consent_selection():
    """Verify USA phone detection for consent text."""
    usa_phone = "+14155551234"
    global_phone = "+919876543210"
    
    assert get_consent_text(usa_phone) == CONSENT_TEXT_V1_USA
    assert get_consent_text(global_phone) == CONSENT_TEXT_V1

@pytest.mark.asyncio
@patch("app.services.data_requests.log_action")
async def test_ccpa_handlers(mock_log):
    """Verify CCPA data request responses."""
    phone = "+14155551234"
    
    # Test DATA request
    data_resp = await handle_ccpa_request(phone, "DATA")
    assert "access request received for +14155551234" in data_resp.lower()
    
    # Test DELETE request
    del_resp = await handle_ccpa_request(phone, "DELETE")
    assert "deletion request received for +14155551234" in del_resp.lower()
    
    # Test EXPORT request
    exp_resp = await handle_ccpa_request(phone, "EXPORT")
    assert "portability request received for +14155551234" in exp_resp.lower()

def test_booking_for_menu_content():
    """Verify the BOOKING_FOR_MENU contains required options."""
    assert "Myself (Adult)" in BOOKING_FOR_MENU
    assert "Child (Parent booking)" in BOOKING_FOR_MENU
