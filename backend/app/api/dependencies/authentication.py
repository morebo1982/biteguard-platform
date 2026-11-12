"""Authentication dependencies for protected API endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies.database import get_db
from app.application.authentication import (
    AuthenticationError,
    decode_access_token,
    get_active_user,
)
from app.core.config import Settings
from app.infrastructure.persistence.audit import configure_audit_session
from app.infrastructure.persistence.models.identity import Role, User, user_roles

_bearer = HTTPBearer(auto_error=False)


def get_actor_role_code(db: Session, user_id) -> str | None:
    """Return the first active role code in a deterministic order."""
    statement = (
        select(Role.code)
        .join(user_roles, user_roles.c.role_id == Role.id)
        .where(
            user_roles.c.user_id == user_id,
            Role.is_active == True,  # noqa: E712
        )
        .order_by(Role.code)
        .limit(1)
    )
    return db.scalar(statement)


def get_current_user(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(_bearer),
    ],
    db: Session = Depends(get_db),
) -> User:
    """Resolve and validate the active user from a bearer access token."""

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer access token required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    settings: Settings = request.app.state.settings

    try:
        claims = decode_access_token(credentials.credentials, settings)
        user = get_active_user(db, claims)
        configure_audit_session(
            db,
            actor_user_id=user.id,
            actor_role_code=get_actor_role_code(db, user.id),
            correlation_id=(
                getattr(request.state, "correlation_id", None)
                or request.headers.get("X-Correlation-ID")
            ),
            ip_address=request.client.host if request.client else None,
        )
        return user
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
