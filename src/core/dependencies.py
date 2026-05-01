"""
FastAPI dependency injection helpers for authentication and RBAC.

Usage in route:
    current_user = Depends(require_roles("trainer", "institution"))
"""

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from src.core.security import decode_token
from src.db.database import get_db
from src.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Extract and validate standard bearer token; return the User ORM object."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_token(credentials.credentials)

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def require_roles(*roles: str):
    """Return a dependency that enforces the caller's role is one of *roles*."""

    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.role}' is not permitted for this endpoint",
            )
        return current_user

    return dependency


def get_monitoring_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Validate the scoped monitoring token (token_type == 'monitoring').
    Returns 401 if missing/expired/wrong type.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Monitoring token required",
        )
    payload = decode_token(credentials.credentials)

    if payload.get("token_type") != "monitoring":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Scoped monitoring token required, not a standard token",
        )
    if payload.get("role") != "monitoring_officer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token not issued for monitoring_officer role",
        )

    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user
