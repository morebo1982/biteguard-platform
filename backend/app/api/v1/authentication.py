"""Login, current-user, and logout endpoints."""

from collections import defaultdict
import threading
import time
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies.authentication import get_current_user, get_actor_role_code
from app.api.dependencies.database import get_db
from app.api.v1.schemas.authentication import CurrentUserResponse, LoginRequest, TokenResponse
from app.application.authentication import (
    AuthenticationError, authenticate, decode_access_token, revoke_access_token,
)
from app.core.config import Settings
from app.infrastructure.persistence.models.identity import (
    Permission, Role, User, role_permissions, user_roles,
)
from app.infrastructure.persistence.audit import configure_audit_session, record_explicit_audit
from app.infrastructure.persistence.models.audit_log import AuditLog

router = APIRouter(prefix="/auth", tags=["authentication"])
_bearer = HTTPBearer(auto_error=False)
DBSession = Annotated[Session, Depends(get_db)]
# Process-local guard. For multi-worker/multi-instance deployments, put this limiter
# behind a shared Redis/API gateway before production exposure.
_attempts: dict[str, list[float]] = defaultdict(list)
_attempts_lock = threading.Lock()


def _check_rate_limit(key: str, max_attempts: int, lockout_seconds: int) -> None:
    now = time.monotonic()
    with _attempts_lock:
        recent = [stamp for stamp in _attempts[key] if now - stamp < lockout_seconds]
        _attempts[key] = recent
        if len(recent) >= max_attempts:
            raise HTTPException(status_code=429, detail="Too many login attempts. Try again later.")


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: DBSession):
    settings: Settings = request.app.state.settings
    configure_audit_session(
        db,
        correlation_id=getattr(request.state, "correlation_id", None) or request.headers.get("X-Correlation-ID"),
        ip_address=request.client.host if request.client else None,
    )
    key = f"{request.client.host if request.client else 'unknown'}:{payload.username.casefold()}"
    _check_rate_limit(key, settings.auth_failed_attempts, settings.auth_lockout_minutes * 60)
    try:
        user, token, expires = authenticate(db, payload.username, payload.password, settings)
    except AuthenticationError as exc:
        with _attempts_lock:
            _attempts[key].append(time.monotonic())
        _write_auth_failure(request, db, payload.username)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid username or password.") from exc
    with _attempts_lock:
        _attempts.pop(key, None)
    configure_audit_session(
        db,
        actor_user_id=user.id,
        actor_role_code=get_actor_role_code(db, user.id),
        correlation_id=getattr(request.state, "correlation_id", None) or request.headers.get("X-Correlation-ID"),
        ip_address=request.client.host if request.client else None,
    )
    record_explicit_audit(
        db, action="auth.login", entity_type="user", entity_id=user.id,
        context_data={"username": user.username},
    )
    return TokenResponse(access_token=token, expires_at=expires, user_id=user.id,
                         username=user.username)


@router.get("/me", response_model=CurrentUserResponse)
def me(
    current_user: Annotated[User, Depends(get_current_user)],
    db: DBSession,
):
    roles_statement = (
        select(Role.code)
        .join(user_roles, user_roles.c.role_id == Role.id)
        .where(
            user_roles.c.user_id == current_user.id,
            Role.is_active == True,  # noqa: E712
        )
        .order_by(Role.code)
    )

    permissions_statement = (
        select(Permission.code)
        .join(
            role_permissions,
            role_permissions.c.permission_id == Permission.id,
        )
        .join(Role, Role.id == role_permissions.c.role_id)
        .join(user_roles, user_roles.c.role_id == Role.id)
        .where(
            user_roles.c.user_id == current_user.id,
            Role.is_active == True,  # noqa: E712
        )
        .distinct()
        .order_by(Permission.code)
    )

    return CurrentUserResponse(
        id=current_user.id,
        username=current_user.username,
        display_name=current_user.display_name,
        email=current_user.email,
        is_active=current_user.is_active,
        roles=list(db.scalars(roles_statement).all()),
        permissions=list(db.scalars(permissions_statement).all()),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, db: DBSession,
           credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]):
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Bearer access token required.")
    settings: Settings = request.app.state.settings
    try:
        claims = decode_access_token(credentials.credentials, settings)
        actor_id = uuid.UUID(str(claims["sub"]))
        configure_audit_session(
            db,
            actor_user_id=actor_id,
            actor_role_code=get_actor_role_code(db, actor_id),
            correlation_id=getattr(request.state, "correlation_id", None) or request.headers.get("X-Correlation-ID"),
            ip_address=request.client.host if request.client else None,
        )
        revoke_access_token(db, claims)
        record_explicit_audit(
            db, action="auth.logout", entity_type="user", entity_id=actor_id,
        )
    except (AuthenticationError, AttributeError) as exc:
        raise HTTPException(status_code=401, detail="Invalid access token.") from exc
    return None


def _write_auth_failure(request: Request, db: Session, username: str) -> None:
    """Persist failed logins independently because the request transaction returns 401."""
    factory = getattr(request.app.state, "session_factory", None)
    if factory is None:
        return
    try:
        with factory() as audit_session:
            audit_session.add(AuditLog(
                action="auth.login", entity_type="user", entity_id=None,
                result="failure", source="api",
                correlation_id=getattr(request.state, "correlation_id", None) or request.headers.get("X-Correlation-ID"),
                ip_address=request.client.host if request.client else None,
                context_data={"username": username[:80]},
            ))
            audit_session.commit()
    except Exception:
        import logging
        logging.getLogger("biteguard.security.audit").exception("login_failure_audit_persist_failed")
