"""Application-level data-scope query enforcement."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import false, or_
from sqlalchemy.sql import Select


@dataclass(frozen=True)
class DataScopeGrant:
    scope_type: str
    scope_value: str


@dataclass(frozen=True)
class DataScopeContext:
    user_id: uuid.UUID
    grants: tuple[DataScopeGrant, ...]

    @property
    def is_global(self) -> bool:
        return any(g.scope_type == "global" and g.scope_value == "*" for g in self.grants)


def apply_data_scope(statement: Select, model: type[Any], context: DataScopeContext) -> Select:
    """Apply fail-closed row filtering to a SQLAlchemy SELECT.

    Supported model attributes are company_id, department_id, owner_id and
    created_by_id. Missing attributes never broaden access.
    """
    if context.is_global:
        return statement

    predicates = []
    for grant in context.grants:
        if grant.scope_type == "company":
            column = getattr(model, "company_id", None)
            if column is not None:
                predicates.append(column == _coerce_value(column, grant.scope_value))
        elif grant.scope_type == "department":
            column = getattr(model, "department_id", None)
            if column is not None:
                predicates.append(column == _coerce_value(column, grant.scope_value))
        elif grant.scope_type == "owner" and grant.scope_value == "self":
            owner_columns = [
                column
                for name in ("owner_id", "created_by_id")
                if (column := getattr(model, name, None)) is not None
            ]
            predicates.extend(column == context.user_id for column in owner_columns)

    if not predicates:
        return statement.where(false())
    return statement.where(or_(*predicates))


def _coerce_value(column: Any, value: str) -> Any:
    try:
        python_type = column.type.python_type
    except (AttributeError, NotImplementedError):
        return value
    if python_type is uuid.UUID:
        try:
            return uuid.UUID(value)
        except ValueError:
            return uuid.UUID(int=0)
    return value
