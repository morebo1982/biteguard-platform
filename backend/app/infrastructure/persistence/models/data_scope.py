"""Persisted grants describing which data a user may access."""

import uuid
from typing import Literal

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.infrastructure.persistence.base import Base, TimestampMixin

ScopeType = Literal["global", "company", "department", "owner"]


class UserDataScope(TimestampMixin, Base):
    __tablename__ = "user_data_scopes"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    scope_type: Mapped[str] = mapped_column(String(20), nullable=False)
    scope_value: Mapped[str] = mapped_column(String(160), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "scope_type IN ('global', 'company', 'department', 'owner')",
            name="ck_user_data_scopes_type",
        ),
        UniqueConstraint("user_id", "scope_type", "scope_value", name="uq_user_data_scopes_grant"),
        Index("ix_user_data_scopes_user_type", "user_id", "scope_type"),
    )
