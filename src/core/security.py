"""
JWT creation and validation.

Two token types are issued:
  1. Standard token  – for all roles, 24h expiry, contains user_id + role
  2. Monitoring token – for Monitoring Officer only, 1h expiry, scoped to
     monitoring endpoints. Requires a valid standard token PLUS a secret API key.

Token payload structure
-----------------------
Standard:
  { "sub": "<user_id>", "role": "<role>", "token_type": "standard",
    "iat": <epoch>, "exp": <epoch> }

Monitoring:
  { "sub": "<user_id>", "role": "monitoring_officer",
    "token_type": "monitoring", "iat": <epoch>, "exp": <epoch> }
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status

from src.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _create_token(data: dict, expires_delta: timedelta) -> str:
    payload = data.copy()
    now = datetime.now(timezone.utc)
    payload.update({"iat": now, "exp": now + expires_delta})
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_access_token(user_id: int, role: str) -> str:
    """Standard 24-hour JWT for all roles."""
    return _create_token(
        {"sub": str(user_id), "role": role, "token_type": "standard"},
        timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS),
    )


def create_monitoring_token(user_id: int) -> str:
    """Short-lived 1-hour token scoped to monitoring endpoints only."""
    return _create_token(
        {
            "sub": str(user_id),
            "role": "monitoring_officer",
            "token_type": "monitoring",
        },
        timedelta(hours=settings.MONITORING_TOKEN_EXPIRE_HOURS),
    )


def decode_token(token: str) -> dict:
    """Decode and validate a JWT. Raises 401 on any failure."""
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
