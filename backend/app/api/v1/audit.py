"""Read-only, permission-protected audit log API."""

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies.authorization import require_permission
from app.api.dependencies.database import get_db
from app.infrastructure.persistence.models.audit_log import AuditLog

router = APIRouter(prefix="/audit-logs", tags=["audit"])
DBSession = Annotated[Session, Depends(get_db)]


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    actor_user_id: uuid.UUID | None
    actor_role_code: str | None
    action: str
    entity_type: str
    entity_id: str | None
    occurred_at: datetime
    result: str
    source: str
    correlation_id: str | None
    ip_address: str | None
    context_data: dict | None


class AuditLogPage(BaseModel):
    items: list[AuditLogRead]
    total: int
    offset: int
    limit: int


@router.get(
    "", response_model=AuditLogPage, dependencies=[Depends(require_permission("audit.read"))]
)
def list_audit_logs(
    db: DBSession,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    action: str | None = None,
    entity_type: str | None = None,
    result: str | None = None,
):
    statement = select(AuditLog)
    count_statement = select(func.count()).select_from(AuditLog)
    for field, value in (
        (AuditLog.action, action),
        (AuditLog.entity_type, entity_type),
        (AuditLog.result, result),
    ):
        if value:
            statement = statement.where(field == value)
            count_statement = count_statement.where(field == value)
    items = db.scalars(
        statement.order_by(AuditLog.occurred_at.desc()).offset(offset).limit(limit)
    ).all()
    return {
        "items": items,
        "total": db.scalar(count_statement) or 0,
        "offset": offset,
        "limit": limit,
    }
