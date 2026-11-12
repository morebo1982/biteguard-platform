"""IAM endpoints for assigning and reviewing user data scopes."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.dependencies.authentication import get_current_user
from app.api.dependencies.authorization import require_permission
from app.api.dependencies.database import get_db
from app.api.v1.schemas.data_scope import DataScopeGrantCreate, DataScopeGrantRead
from app.infrastructure.persistence.audit import (
    configure_audit_session,
    record_explicit_audit,
)
from app.infrastructure.persistence.models.identity import User
from app.infrastructure.persistence.repositories.data_scope import UserDataScopeRepository

router = APIRouter(prefix="/users", tags=["data-scope"])
DBSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
MANAGE_SCOPE = Depends(require_permission("users.scopes.manage"))


def _configure_scope_audit(request: Request, db: Session, actor: User) -> None:
    configure_audit_session(
        db,
        actor_user_id=actor.id,
        correlation_id=(
            getattr(request.state, "correlation_id", None)
            or request.headers.get("X-Correlation-ID")
        ),
        ip_address=request.client.host if request.client else None,
    )


@router.get(
    "/{user_id}/data-scopes",
    response_model=list[DataScopeGrantRead],
    dependencies=[MANAGE_SCOPE],
)
def list_user_data_scopes(user_id: uuid.UUID, db: DBSession):
    if db.get(User, user_id) is None:
        raise HTTPException(status_code=404, detail="User not found.")
    return UserDataScopeRepository(db).list_for_user(user_id)


@router.post(
    "/{user_id}/data-scopes",
    response_model=DataScopeGrantRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[MANAGE_SCOPE],
)
def grant_user_data_scope(
    user_id: uuid.UUID,
    payload: DataScopeGrantCreate,
    request: Request,
    db: DBSession,
    current_user: CurrentUser,
):
    _configure_scope_audit(request, db, current_user)

    if db.get(User, user_id) is None:
        raise HTTPException(status_code=404, detail="User not found.")
    try:
        repository = UserDataScopeRepository(db)
        existing = any(
            grant.scope_type == payload.scope_type
            and grant.scope_value == payload.scope_value.strip()
            for grant in repository.list_for_user(user_id)
        )
        grant = repository.grant(user_id, payload.scope_type, payload.scope_value)
        if not existing:
            record_explicit_audit(
                db,
                action="user.data_scope_granted",
                entity_type="user",
                entity_id=user_id,
                context_data={
                    "scope_type": grant.scope_type,
                    "scope_value": grant.scope_value,
                    "grant_id": str(grant.id),
                },
            )
        return grant
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.delete(
    "/{user_id}/data-scopes/{scope_type}/{scope_value}",
    status_code=status.HTTP_200_OK,
    dependencies=[MANAGE_SCOPE],
)
def revoke_user_data_scope(
    user_id: uuid.UUID,
    scope_type: str,
    scope_value: str,
    request: Request,
    db: DBSession,
    current_user: CurrentUser,
):
    _configure_scope_audit(request, db, current_user)

    if db.get(User, user_id) is None:
        raise HTTPException(status_code=404, detail="User not found.")
    if scope_type not in {"global", "company", "department", "owner"}:
        raise HTTPException(status_code=422, detail="Unsupported scope type.")

    changed = UserDataScopeRepository(db).revoke(user_id, scope_type, scope_value)
    if changed:
        record_explicit_audit(
            db,
            action="user.data_scope_revoked",
            entity_type="user",
            entity_id=user_id,
            context_data={"scope_type": scope_type, "scope_value": scope_value},
        )
    return {"changed": changed}
