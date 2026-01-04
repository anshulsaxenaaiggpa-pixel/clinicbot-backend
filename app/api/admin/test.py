"""
Test route to verify basic admin functionality works
"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter(prefix="/admin", tags=["admin-test"])

@router.get("/test-minimal")
async def test_minimal(request: Request):
    """Absolute minimal test - no dependencies, no database, no templates"""
    return HTMLResponse(content="<h1>✅ Admin Routes Work!</h1><p>If you see this, basic routing is functional.</p>")
