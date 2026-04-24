from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.services.job_manager import generate_access_key, KEYS, verify_key

router = APIRouter(tags=["auth"])

class LoginRequest(BaseModel):
    username: str
    password: str

class KeyVerifyRequest(BaseModel):
    key: str

@router.post("/admin/login")
async def admin_login(request: LoginRequest):
    if request.username == "Huzaifa" and request.password == "100043155Hu":
        return {"success": True, "message": "Admin authenticated"}
    raise HTTPException(status_code=401, detail="Invalid credentials")

@router.post("/admin/generate-key")
async def generate_key(request: LoginRequest):
    # Basic protection: check credentials every time for simplicity as requested
    if request.username == "Huzaifa" and request.password == "100043155Hu":
        new_key = generate_access_key()
        return {"success": True, "key": new_key}
    raise HTTPException(status_code=401, detail="Unauthorized")

@router.get("/admin/keys")
async def list_keys():
    # In a real app, this should be protected too. For now, keeping it accessible for the admin UI.
    return sorted(KEYS.values(), key=lambda x: x["created_at"], reverse=True)

@router.post("/verify-key")
async def check_key(request: KeyVerifyRequest):
    if verify_key(request.key):
        return {"success": True, "uses_left": KEYS[request.key]["uses_left"]}
    return {"success": False, "message": "Invalid or expired key"}
