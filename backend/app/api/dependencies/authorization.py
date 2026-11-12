"""Role/permission authorization dependencies for API endpoints."""

from __future__ import annotations

import logging
from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies.authentication import get_current_user
from app.api.dependencies.database import get_db
from app.infrastructure.persistence.models.audit_log import AuditLog
from app.infrastructure.persistence.models.identity import (
    Permission,
    Role,
    role_permissions,
    user_roles,
)

logger = logging.getLogger("biteguard.security.authorization")


def require_permission(permission_code: str) -> Callable:
    """Require an active role assigned to the user to grant the named permission."""

    def dependency(
        request: Request,
        user=Depends(get_current_user),
        db: Session = Depends(get_db),
    ):
        statement = (
            select(Role.id)
            .join(user_roles, user_roles.c.role_id == Role.id)
            .join(role_permissions, role_permissions.c.role_id == Role.id)
            .join(Permission, role_permissions.c.permission_id == Permission.id)
            .where(
                user_roles.c.user_id == user.id,
                Role.is_active == True,  # noqa: E712
                Permission.code == permission_code,
            )
            .limit(1)
        )
        if db.scalar(statement) is not None:
            return user

        _record_denial(request, db, user, permission_code)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "PERMISSION_DENIED",
                "message": "You do not have permission to perform this action.",
                "required_permission": permission_code,
            },
        )

    dependency.__name__ = f"require_permission_{permission_code.replace('.', '_')}"
    return dependency


def _record_denial(request: Request, db: Session, user, permission_code: str) -> None:
    """Persist denied access in an independent transaction where possible."""
    record = AuditLog(
        actor_user_id=user.id,
        action="authorization.denied",
        entity_type="permission",
        entity_id=permission_code,
        result="denied",
        source="api",
        correlation_id=getattr(request.state, "correlation_id", None) or request.headers.get("X-Correlation-ID"),
        ip_address=request.client.host if request.client else None,
        context_data={"path": request.url.path, "method": request.method},
    )
    factory = getattr(request.app.state, "session_factory", None)
    if factory is not None:
        try:
            with factory() as audit_session:
                audit_session.add(record)
                audit_session.commit()
            return
        except Exception:
            logger.exception("authorization_denial_audit_persist_failed")
    # Dependency overrides in tests may not expose an app-level session factory.
    try:
        db.add(record)
        db.flush()
    except Exception:
        logger.exception("authorization_denial_audit_fallback_failed")
