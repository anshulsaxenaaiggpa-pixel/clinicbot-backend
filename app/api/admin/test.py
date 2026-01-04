"""
Test route to verify basic admin functionality works
"""
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from app.api.admin.dependencies import require_admin
from app.models.admin_user import AdminUser

router = APIRouter(prefix="/admin", tags=["admin-test"])

@router.get("/test-minimal")
async def test_minimal(request: Request):
    """Absolute minimal test - no dependencies, no database, no templates"""
    return HTMLResponse(content="<h1>✅ Admin Routes Work!</h1><p>If you see this, basic routing is functional.</p>")

@router.get("/test-with-auth")
async def test_with_auth(request: Request, admin_user: AdminUser = Depends(require_admin)):
    """Test with require_admin dependency"""
    return HTMLResponse(content=f"<h1>✅ Auth Works!</h1><p>Logged in as: {admin_user.email}</p>")
