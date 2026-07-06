"""Authentication routes: register, login, and whoami.

Slice 1 scope — this establishes identity (who you are, which org, what role)
and hands back a JWT. It does NOT yet protect the other routes or enforce
roles; that's Slice 2. The one protected endpoint here is /auth/me, which
doubles as a way for the frontend to validate a stored token on load.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr, Field

from auth import store
from auth.security import (
    hash_password, verify_password, create_access_token, get_current_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])


# --- request / response models ----------------------------------------------
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: str = Field(min_length=1)
    org_name: str = Field(min_length=1)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict
    org: dict | None = None


# --- endpoints ---------------------------------------------------------------
@router.post("/register", response_model=TokenResponse)
def register(req: RegisterRequest):
    """Create a new organization and its first user (an Admin), then log in."""
    if store.get_user_by_email(req.email):
        raise HTTPException(status_code=409, detail="An account with this email already exists")

    result = store.register_user_and_org(
        email=req.email,
        password_hash=hash_password(req.password),
        name=req.name,
        org_name=req.org_name,
    )
    user, org = result["user"], result["org"]

    token = create_access_token(
        user_id=user["user_id"], email=user["email"],
        org_id=user["org_id"], role=user["role"],
    )
    return TokenResponse(access_token=token, user=store.public_user(user), org=org)


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest):
    user = store.get_user_by_email(req.email)
    if not user or not verify_password(req.password, user.get("password_hash", "")):
        # Same message for both cases so we don't reveal which emails exist.
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(
        user_id=user["user_id"], email=user["email"],
        org_id=user["org_id"], role=user["role"],
    )
    org = store.get_org_by_id(user["org_id"])
    if org:
        org.pop("_id", None)
    return TokenResponse(access_token=token, user=store.public_user(user), org=org)


@router.get("/me")
def me(current=Depends(get_current_user)):
    """Return the current user + org from a valid Bearer token.

    Used by the frontend to hydrate its auth state on page load and to verify
    a stored token is still valid.
    """
    user = store.get_user_by_id(current["user_id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    org = store.get_org_by_id(user["org_id"])
    if org:
        org.pop("_id", None)
    return {"user": store.public_user(user), "org": org}