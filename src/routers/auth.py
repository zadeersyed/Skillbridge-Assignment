"""
Authentication endpoints.

POST /auth/signup         – register any role
POST /auth/login          – get standard JWT
POST /auth/monitoring-token – exchange standard token + API key for scoped monitoring token
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.orm import Session

from src.core.config import settings
from src.core.dependencies import get_current_user
from src.core.security import (
    hash_password, verify_password,
    create_access_token, create_monitoring_token,
)
from src.db.database import get_db
from src.models.user import User

router = APIRouter(prefix="/auth", tags=["Auth"])

VALID_ROLES = {
    "student", "trainer", "institution",
    "programme_manager", "monitoring_officer",
}


# ── Schemas ──────────────────────────────────────────────────────────────────

class SignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str
    institution_id: int | None = None

    @field_validator("role")
    @classmethod
    def role_must_be_valid(cls, v: str) -> str:
        if v not in VALID_ROLES:
            raise ValueError(f"role must be one of {sorted(VALID_ROLES)}")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class MonitoringTokenRequest(BaseModel):
    key: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ── Routes ───────────────────────────────────────────────────────────────────

@router.post("/signup", response_model=TokenResponse, status_code=201)
def signup(payload: SignupRequest, db: Session = Depends(get_db)):
    """Register a new user and return a JWT immediately."""
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A user with this email already exists",
        )

    # If institution_id provided, ensure it references a real institution-role user
    if payload.institution_id is not None:
        inst = db.query(User).filter(
            User.id == payload.institution_id,
            User.role == "institution",
        ).first()
        if not inst:
            raise HTTPException(
                status_code=404,
                detail=f"Institution with id {payload.institution_id} not found",
            )

    user = User(
        name=payload.name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=payload.role,
        institution_id=payload.institution_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id, user.role)
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """Validate credentials and return a signed JWT."""
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    token = create_access_token(user.id, user.role)
    return TokenResponse(access_token=token)


@router.post("/monitoring-token", response_model=TokenResponse)
def get_monitoring_token(
    payload: MonitoringTokenRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Issue a short-lived (1h) scoped monitoring token.
    Requires: valid standard JWT of a monitoring_officer + correct API key.
    """
    if current_user.role != "monitoring_officer":
        raise HTTPException(status_code=403, detail="Only monitoring officers can request this token")
    if payload.key != settings.MONITORING_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

    token = create_monitoring_token(current_user.id)
    return TokenResponse(access_token=token)
