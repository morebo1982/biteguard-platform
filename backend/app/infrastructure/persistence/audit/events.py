"""Transactional ORM audit hooks for security-sensitive platform entities."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import event, inspect
from sqlalchemy.orm import Session

from app.infrastructure.persistence.models.audit_log import AuditLog
from app.infrastructure.persistence.models.data_scope import UserDataScope
from app.infrastructure.persistence.models.identity import Permission, Role, User

_AUDITED = {
    User: ("user", "username"),
    Role: ("role", "code"),
    Permission: ("permission", "code"),
    UserDataScope: ("user_data_scope", "id"),
}
_SENSITIVE = {"password", "password_hash", "secret", "token"}


def _safe_value(value: Any) -> Any:
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _snapshot(obj: Any) -> dict[str, Any]:
    state = inspect(obj)
    result: dict[str, Any] = {}
    for attr in state.mapper.column_attrs:
        key = attr.key
        if any(word in key.lower() for word in _SENSITIVE):
            continue
        history = state.attrs[key].history
        if history.has_changes():
            old = history.deleted[0] if history.deleted else None
            new = history.added[0] if history.added else getattr(obj, key, None)
            result[key] = {"before": _safe_value(old), "after": _safe_value(new)}
        elif state.pending or state.deleted:
            result[key] = _safe_value(getattr(obj, key, None))
    return result


@event.listens_for(Session, "before_flush")
def collect_audit_changes(session: Session, flush_context, instances) -> None:
    if not session.info.get("audit_enabled"):
        return
    pending = session.info.setdefault("audit_pending", [])
    for obj in list(session.new) + list(session.dirty) + list(session.deleted):
        entity = next((entry for model, entry in _AUDITED.items() if isinstance(obj, model)), None)
        if entity is None or isinstance(obj, AuditLog):
            continue
        if obj in session.dirty and not session.is_modified(obj, include_collections=False):
            continue
        entity_type, identity_key = entity
        action_suffix = (
            "created" if obj in session.new else "deleted" if obj in session.deleted else "updated"
        )
        entity_id = getattr(obj, identity_key, None)
        if entity_id is None:
            entity_id = getattr(obj, "id", None)
        pending.append(
            {
                "action": f"{entity_type}.{action_suffix}",
                "entity_type": entity_type,
                "entity_id": _safe_value(entity_id),
                "object": obj,
                "identity_key": identity_key,
                "context_data": _snapshot(obj),
            }
        )


@event.listens_for(Session, "after_flush")
def write_audit_changes(session: Session, flush_context) -> None:
    pending = session.info.pop("audit_pending", [])
    if not pending or not session.info.get("audit_enabled"):
        return
    connection = session.connection()
    request_context = session.info.get("audit_request", {})
    actor_id = session.info.get("audit_actor_user_id")
    actor_role = session.info.get("audit_actor_role_code")
    rows = []
    for item in pending:
        entity_id = item["entity_id"]
        if entity_id is None:
            entity_id = _safe_value(getattr(item["object"], item["identity_key"], None))
        rows.append(
            {
                "id": uuid.uuid4(),
                "actor_user_id": actor_id,
                "actor_role_code": actor_role,
                "action": item["action"],
                "entity_type": item["entity_type"],
                "entity_id": str(entity_id) if entity_id is not None else None,
                "occurred_at": datetime.now(UTC),
                "result": "success",
                "source": "api",
                "correlation_id": request_context.get("correlation_id"),
                "ip_address": request_context.get("ip_address"),
                "context_data": item["context_data"],
            }
        )
    connection.execute(AuditLog.__table__.insert(), rows)


def configure_audit_session(
    session: Session,
    *,
    actor_user_id=None,
    actor_role_code=None,
    correlation_id=None,
    ip_address=None,
) -> None:
    session.info["audit_enabled"] = True
    if actor_user_id is not None:
        session.info["audit_actor_user_id"] = actor_user_id
    if actor_role_code is not None:
        session.info["audit_actor_role_code"] = actor_role_code
    session.info["audit_request"] = {
        "correlation_id": correlation_id,
        "ip_address": ip_address,
    }


def record_explicit_audit(
    session: Session,
    *,
    action: str,
    entity_type: str,
    entity_id: str | uuid.UUID | None,
    result: str = "success",
    context_data: dict[str, Any] | None = None,
) -> None:
    """Append an explicit event for operations performed with bulk SQL statements."""
    from app.infrastructure.persistence.repositories.audit_log import AuditLogRepository

    request_context = session.info.get("audit_request", {})
    AuditLogRepository(session).add(
        AuditLog(
            actor_user_id=session.info.get("audit_actor_user_id"),
            actor_role_code=session.info.get("audit_actor_role_code"),
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            result=result,
            source="api",
            correlation_id=request_context.get("correlation_id"),
            ip_address=request_context.get("ip_address"),
            context_data=context_data,
        )
    )
