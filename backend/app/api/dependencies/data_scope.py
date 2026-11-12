"""Request dependency that loads the authenticated user's data scopes."""

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies.authentication import get_current_user
from app.api.dependencies.database import get_db
from app.application.data_scope import DataScopeContext, DataScopeGrant
from app.infrastructure.persistence.models.data_scope import UserDataScope


def get_data_scope_context(
    user=Depends(get_current_user), db: Session = Depends(get_db)
) -> DataScopeContext:
    rows = db.scalars(
        select(UserDataScope).where(UserDataScope.user_id == user.id)
    ).all()
    return DataScopeContext(
        user_id=user.id,
        grants=tuple(DataScopeGrant(row.scope_type, row.scope_value) for row in rows),
    )
