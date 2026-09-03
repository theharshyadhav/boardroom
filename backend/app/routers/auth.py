from fastapi import APIRouter, HTTPException
from ..schemas import LoginRequest
from ..roles import ROLES, get_role

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.get("/roles")
def list_roles():
    return [{"key": k, **v} for k, v in ROLES.items()]

@router.post("/login")
def login(req: LoginRequest):
    if req.role not in ROLES:
        raise HTTPException(status_code=400, detail="Unknown role")
    role = get_role(req.role)
    # Demo auth as specified in the brief — no password, just a role token.
    return {"token": f"demo-token-{req.role}", "role": req.role, "profile": role}
