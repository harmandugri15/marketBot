"""
routers/auth.py
---------------
POST /api/v1/auth/register — register a new user
POST /api/v1/auth/login    — returns JWT token
GET  /api/v1/auth/me       — returns current user info
GET  /api/v1/auth/check-username — check username availability
"""

from fastapi import APIRouter, HTTPException, status, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db
from models.user import User
from schemas.user import UserCreate, UserRead
from core.security import create_access_token, verify_password, get_password_hash, get_current_user
from config import get_settings

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])
settings = get_settings()


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    trading_mode: str
    username: str


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(body: UserCreate, db: Session = Depends(get_db)):
    """Register a new user in the platform."""
    existing = db.query(User).filter(User.username == body.username).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    new_user = User(
        username=body.username,
        password_hash=get_password_hash(body.password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token = create_access_token({"sub": str(new_user.id)})
    return TokenResponse(
        access_token=token,
        trading_mode=new_user.trading_mode,
        username=new_user.username
    )


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate a user and return a JWT access token."""
    user = db.query(User).filter(User.username == body.username).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is deactivated"
        )

    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(
        access_token=token,
        trading_mode=user.trading_mode,
        username=user.username
    )


@router.get("/me", response_model=UserRead)
def get_me(current_user: User = Depends(get_current_user)):
    """Get profile of current logged in user."""
    return current_user


@router.get("/check-username")
def check_username(username: str = Query(..., min_length=1), db: Session = Depends(get_db)):
    """Check if a username is available for registration."""
    existing = db.query(User).filter(User.username == username).first()
    return {"available": existing is None}

