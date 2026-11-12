"""Append-oriented repository for audit records."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.persistence.models.audit_log import AuditLog


class AuditLogRepository:
    """Write and query audit records; intentionally exposes no update/delete methods."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, record: AuditLog) -> AuditLog:
        self.session.add(record)
        self.session.flush()
        return record

    def get(self, audit_id: uuid.UUID) -> AuditLog | None:
        return self.session.get(AuditLog, audit_id)

    def list_for_entity(
        self,
        entity_type: str,
        entity_id: str,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[AuditLog]:
        _validate_pagination(offset, limit)
        statement = (
            select(AuditLog)
            .where(AuditLog.entity_type == entity_type, AuditLog.entity_id == entity_id)
            .order_by(AuditLog.occurred_at.desc(), AuditLog.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return self.session.scalars(statement).all()

    def list_for_actor(
        self,
        actor_user_id: uuid.UUID,
        *,
        since: datetime | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[AuditLog]:
        _validate_pagination(offset, limit)
        statement = select(AuditLog).where(AuditLog.actor_user_id == actor_user_id)
        if since is not None:
            statement = statement.where(AuditLog.occurred_at >= since)
        statement = (
            statement.order_by(AuditLog.occurred_at.desc(), AuditLog.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return self.session.scalars(statement).all()


def _validate_pagination(offset: int, limit: int) -> None:
    if offset < 0:
        raise ValueError("offset must be greater than or equal to zero.")
    if not 1 <= limit <= 500:
        raise ValueError("limit must be between 1 and 500.")
