"""
Doctor Messages Routes

WhatsApp conversation preview (read-only).
"""
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from sqlalchemy.orm import Session

from app.api.doctor.dependencies import require_doctor
from app.models.doctor import Doctor
from app.models.conversation_state import ConversationState
from app.db.session import get_db


router = APIRouter(prefix="/doctor", tags=["doctor-messages"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent.parent / "templates"))


@router.get("/messages", response_class=HTMLResponse)
async def messages_page(
    request: Request,
    doctor: Doctor = Depends(require_doctor),
    db: Session = Depends(get_db)
):
    """Display recent WhatsApp conversations."""
    try:
        # Get recent conversations (limited view)
        try:
            conversations = db.query(ConversationState).order_by(
                ConversationState.last_message_at.desc()
            ).limit(20).all()
        except Exception as db_error:
            # Table might not exist yet
            print(f"⚠️ Could not query conversations: {db_error}")
            conversations = []
        
        return templates.TemplateResponse(
            "doctor/messages.html",
            {
                "request": request,
                "doctor": doctor,
                "csrf_token": request.state.csrf_token,
                "conversations": conversations
            }
        )
    
    except Exception as e:
        import traceback
        print(f"❌ Messages error: {traceback.format_exc()}")
        return HTMLResponse(
            content=f"<h1>Error</h1><pre>{traceback.format_exc()}</pre>",
            status_code=500
        )
