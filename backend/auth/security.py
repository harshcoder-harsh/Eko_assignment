"""Security primitives for auth: password hashing + JWT + the FastAPI
`get_current_user` dependency.

Kept deliberately small and dependency-light: `bcrypt` for password hashing,
`PyJWT` for tokens. No secret is ever logged. The JWT secret comes from the
JWT_SECRET env var; a dev fallback is used if unset, with a loud warning,
because shipping the fallback to production would let anyone forge tokens.
"""
import os
import datetime as dt

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

_ALGO = "HS256"
_TOKEN_TTL_HOURS = int(os.getenv("JWT_TTL_HOURS", "24"))

_DEV_FALLBACK_SECRET = "dev-only-change-me-in-production"


def _secret() -> str:
    s = os.getenv("JWT_SECRET")
    if s:
        return s

    # Outside development a missing secret is fatal, not a warning: with the
    # fallback in place anyone can forge a token for any org_id and role,
    # including admin, which defeats both auth and tenant isolation.
    if os.getenv("ENVIRONMENT", "development").lower() != "development":
        raise RuntimeError(
            "JWT_SECRET must be set when ENVIRONMENT is not 'development'. "
            "Generate one with: python3 -c \"import secrets; print(secrets.token_urlsafe(48))\""
        )

    # Dev machines shouldn't need env setup to try the app — but make it
    # impossible to miss that this is insecure.
    print(
        "WARNING: JWT_SECRET is not set; using an insecure development "
        "fallback. Set JWT_SECRET in the environment before deploying."
    )
    return _DEV_FALLBACK_SECRET


# --- password hashing -------------------------------------------------------
def hash_password(plain: str) -> str:
    """Return a bcrypt hash (utf-8 string) of the plaintext password."""
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


# --- JWT --------------------------------------------------------------------
def create_access_token(*, user_id: str, email: str, org_id: str, role: str) -> str:
    now = dt.datetime.now(dt.timezone.utc)
    payload = {
        "sub": user_id,
        "email": email,
        "org_id": org_id,
        "role": role,
        "iat": now,
        "exp": now + dt.timedelta(hours=_TOKEN_TTL_HOURS),
    }
    return jwt.encode(payload, _secret(), algorithm=_ALGO)


def decode_token(token: str) -> dict:
    """Decode + verify a JWT. Raises jwt exceptions on failure."""
    return jwt.decode(token, _secret(), algorithms=[_ALGO])


# --- FastAPI dependency -----------------------------------------------------
_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(_bearer),
) -> dict:
    """Resolve the caller from the Bearer token into a user context dict:
        {user_id, email, org_id, role}

    Raises 401 if the token is missing, malformed, or expired. This is the
    dependency every protected route will use in Slice 2.
    """
    if creds is None or not creds.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_token(creds.credentials)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    return {
        "user_id": payload.get("sub"),
        "email": payload.get("email"),
        "org_id": payload.get("org_id"),
        "role": payload.get("role"),
    }


def require_role(*allowed: str):
    """Dependency factory: allow the route only for the listed roles.

    Usage:
        @router.post("/x")
        def x(current=Depends(require_role("admin", "manager"))):
            ...
    Returns the same user-context dict as get_current_user on success,
    raises 403 otherwise.
    """
    allowed_set = set(allowed)

    def _checker(current: dict = Depends(get_current_user)) -> dict:
        if current.get("role") not in allowed_set:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to perform this action",
            )
        return current

    return _checker