from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.services.job_manager import (
    KEYS, verify_key, generate_verification_code, 
    verify_code_and_generate_key, LEADS_FILE
)
from app.services.email_service import email_service
import json
import os

router = APIRouter(tags=["auth"])

class LoginRequest(BaseModel):
    username: str
    password: str

class KeyVerifyRequest(BaseModel):
    key: str

class EmailRequest(BaseModel):
    email: str

class VerifyRequest(BaseModel):
    email: str
    code: str

@router.post("/admin/login")
async def admin_login(request: LoginRequest):
    if request.username == "Huzaifa" and request.password == "100043155Hu":
        return {"success": True, "message": "Admin authenticated"}
    raise HTTPException(status_code=401, detail="Invalid credentials")

@router.get("/admin/leads")
async def list_leads():
    if os.path.exists(LEADS_FILE):
        with open(LEADS_FILE, 'r') as f:
            return json.load(f)
    return []

@router.post("/request-code")
async def request_code(request: EmailRequest):
    code = generate_verification_code(request.email)
    if code is None:
        return {"success": False, "message": "Maximum 3 extraction protocols reached for this email address. For more credits, contact us at +923100043155 (WhatsApp)."}
        
    print(f"\n🚀 [DEVELOPER MODE] Verification Code for {request.email}: {code}\n")
    
    success = email_service.send_verification_code(request.email, code)
    
    # Locally, we return success even if email fails so you can use the code from terminal
    return {
        "success": True, 
        "message": "Code generated. Check terminal for local testing or email for production."
    }

@router.post("/verify-code")
async def verify_code(request: VerifyRequest):
    key = verify_code_and_generate_key(request.email, request.code)
    if key:
        return {"success": True, "key": key, "uses_left": 3}
    return {"success": False, "message": "Invalid or expired verification code"}

@router.post("/verify-key")
async def check_key(request: KeyVerifyRequest):
    if verify_key(request.key):
        return {"success": True, "uses_left": KEYS[request.key]["uses_left"]}
    return {"success": False, "message": "Invalid or expired key"}
