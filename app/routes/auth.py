from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
from app.services.job_manager import get_or_create_session, list_sessions

router = APIRouter(tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/admin/login")
async def admin_login(request: LoginRequest):
    if request.username == "Huzaifa" and request.password == "100043155Hu":
        return {"success": True, "message": "Admin authenticated"}
    raise HTTPException(status_code=401, detail="Invalid credentials")


@router.get("/admin/sessions")
async def admin_sessions():
    return list_sessions()


@router.get("/session")
async def get_session(x_session_id: Optional[str] = Header(default=None)):
    """
    Get or create a browser session with 3 free scrapes.
    Client should store session_id in localStorage and send it as X-Session-Id.
    """
    session = get_or_create_session(x_session_id)
    return {
        "success": True,
        "session_id": session["session_id"],
        "uses_left": session["uses_left"],
    }
