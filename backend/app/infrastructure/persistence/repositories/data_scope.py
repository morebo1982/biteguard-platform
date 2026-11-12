"""Persistence operations for user data-scope grants."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.infrastructure.persistence.models.data_scope import UserDataScope

VALID_SCOPE_TYPES = {"global", "company", "department", "owner"}


class UserDataScopeRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_for_user(self, user_id: uuid.UUID) -> Sequence[UserDataScope]:
        return self.session.scalars(
            select(UserDataScope)
            .where(UserDataScope.user_id == user_id)
            .order_by(UserDataScope.scope_type, UserDataScope.scope_value)
        ).all()

    def grant(self, user_id: uuid.UUID, scope_type: str, scope_value: str) -> UserDataScope:
        if scope_type not in VALID_SCOPE_TYPES:
            raise ValueError("Unsupported scope type.")
        value = scope_value.strip()
        if scope_type == "global" and value != "*":
            raise ValueError("Global scope value must be '*'.")
        if scope_type == "owner" and value != "self":
            raise ValueError("Owner scope value must be 'self'.")
        if scope_type in {"company", "department"} and not value:
            raise ValueError("Scope value is required.")
        existing = self.session.scalar(
            select(UserDataScope).where(
                UserDataScope.user_id == user_id,
                UserDataScope.scope_type == scope_type,
                UserDataScope.scope_value == value,
            )
        )
        if existing:
            return existing
        grant = UserDataScope(user_id=user_id, scope_type=scope_type, scope_value=value)
        self.session.add(grant)
        self.session.flush()
        return grant

    def revoke(self, user_id: uuid.UUID, scope_type: str, scope_value: str) -> bool:
        result = self.session.execute(
            delete(UserDataScope).where(
                UserDataScope.user_id == user_id,
                UserDataScope.scope_type == scope_type,
                UserDataScope.scope_value == scope_value,
            )
        )
        self.session.flush()
        return bool(result.rowcount)
