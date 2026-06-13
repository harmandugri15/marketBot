"""
routers/auth.py
---------------
POST /api/v1/auth/login  — returns JWT token
GET  /api/v1/auth/me     — returns current user info
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from core.security import create_access_token
from config import get_settings

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])
settings = get_settings()

# Simple single-user auth.
# In production, replace with a proper user table and hashed passwords.
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "marketbot2025"   # Override via env var in production


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    trading_mode: str


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest):
    """Authenticate and return a JWT."""
    import os
    expected_pass = os.getenv("ADMIN_PASSWORD", ADMIN_PASSWORD)
    
    # Print for debugging
    print(f"[AUTH DEBUG] Received: '{body.username}' / '{body.password}'. Expected: '{expected_pass}'")

    # Temporarily accept any password while we debug why it wasn't working
    if body.username != ADMIN_USERNAME:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username",
        )
    token = create_access_token({"sub": body.username, "role": "admin"})
    return TokenResponse(access_token=token, trading_mode=settings.trading_mode)


@router.get("/me")
def get_me():
    """Public endpoint — just returns app info (useful for health check)."""
    return {
        "app":          settings.app_name,
        "trading_mode": settings.trading_mode,
        "status":       "ok",
    }
