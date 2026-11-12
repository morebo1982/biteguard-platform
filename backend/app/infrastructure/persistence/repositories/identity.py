"""Repositories for identity and authorization catalogue entities."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import delete, func, insert, select
from sqlalchemy.orm import Session

from app.infrastructure.persistence.models.identity import (
    Permission,
    Role,
    User,
    role_permissions,
    user_roles,
)


class UserRepository:
    """Data-access operations for platform users."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, user_id: uuid.UUID) -> User | None:
        return self.session.get(User, user_id)

    def get_by_username(self, username: str) -> User | None:
        return self.session.scalar(select(User).where(User.username == username))

    def get_by_email(self, email: str) -> User | None:
        return self.session.scalar(select(User).where(User.email == email))

    def list(self, *, offset: int = 0, limit: int = 100) -> Sequence[User]:
        _validate_pagination(offset, limit)
        statement = select(User).order_by(User.username).offset(offset).limit(limit)
        return self.session.scalars(statement).all()

    def count(self) -> int:
        return int(self.session.scalar(select(func.count()).select_from(User)) or 0)

    def add(self, user: User) -> User:
        self.session.add(user)
        self.session.flush()
        return user

    def update(self, user: User, **changes: object) -> User:
        allowed = {"username", "email", "display_name", "is_active"}
        _apply_changes(user, changes, allowed)
        self.session.flush()
        return user

    def delete(self, user: User) -> None:
        self.session.delete(user)
        self.session.flush()

    def assign_role(self, user_id: uuid.UUID, role_id: uuid.UUID) -> bool:
        if self.session.get(User, user_id) is None:
            raise ValueError("User does not exist.")
        if self.session.get(Role, role_id) is None:
            raise ValueError("Role does not exist.")
        exists = self.session.execute(
            select(user_roles.c.user_id).where(
                user_roles.c.user_id == user_id, user_roles.c.role_id == role_id
            )
        ).first()
        if exists:
            return False
        self.session.execute(insert(user_roles).values(user_id=user_id, role_id=role_id))
        self.session.flush()
        return True

    def remove_role(self, user_id: uuid.UUID, role_id: uuid.UUID) -> bool:
        result = self.session.execute(
            delete(user_roles).where(
                user_roles.c.user_id == user_id, user_roles.c.role_id == role_id
            )
        )
        self.session.flush()
        return bool(result.rowcount)

    def list_roles(self, user_id: uuid.UUID) -> Sequence[Role]:
        statement = (
            select(Role)
            .join(user_roles, user_roles.c.role_id == Role.id)
            .where(user_roles.c.user_id == user_id)
            .order_by(Role.code)
        )
        return self.session.scalars(statement).all()


class RoleRepository:
    """Data-access operations for roles and their permission assignments."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, role_id: uuid.UUID) -> Role | None:
        return self.session.get(Role, role_id)

    def get_by_code(self, code: str) -> Role | None:
        return self.session.scalar(select(Role).where(Role.code == code))

    def list(self, *, offset: int = 0, limit: int = 100) -> Sequence[Role]:
        _validate_pagination(offset, limit)
        statement = select(Role).order_by(Role.code).offset(offset).limit(limit)
        return self.session.scalars(statement).all()

    def count(self) -> int:
        return int(self.session.scalar(select(func.count()).select_from(Role)) or 0)

    def add(self, role: Role) -> Role:
        self.session.add(role)
        self.session.flush()
        return role

    def update(self, role: Role, **changes: object) -> Role:
        allowed = {"code", "name", "description", "is_system", "is_active"}
        _apply_changes(role, changes, allowed)
        self.session.flush()
        return role

    def delete(self, role: Role) -> None:
        self.session.delete(role)
        self.session.flush()

    def assign_permission(self, role_id: uuid.UUID, permission_id: uuid.UUID) -> bool:
        if self.session.get(Role, role_id) is None:
            raise ValueError("Role does not exist.")
        if self.session.get(Permission, permission_id) is None:
            raise ValueError("Permission does not exist.")
        exists = self.session.execute(
            select(role_permissions.c.role_id).where(
                role_permissions.c.role_id == role_id,
                role_permissions.c.permission_id == permission_id,
            )
        ).first()
        if exists:
            return False
        self.session.execute(
            insert(role_permissions).values(role_id=role_id, permission_id=permission_id)
        )
        self.session.flush()
        return True

    def remove_permission(self, role_id: uuid.UUID, permission_id: uuid.UUID) -> bool:
        result = self.session.execute(
            delete(role_permissions).where(
                role_permissions.c.role_id == role_id,
                role_permissions.c.permission_id == permission_id,
            )
        )
        self.session.flush()
        return bool(result.rowcount)

    def list_permissions(self, role_id: uuid.UUID) -> Sequence[Permission]:
        statement = (
            select(Permission)
            .join(role_permissions, role_permissions.c.permission_id == Permission.id)
            .where(role_permissions.c.role_id == role_id)
            .order_by(Permission.code)
        )
        return self.session.scalars(statement).all()


class PermissionRepository:
    """Data-access operations for the permission catalogue."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, permission_id: uuid.UUID) -> Permission | None:
        return self.session.get(Permission, permission_id)

    def get_by_code(self, code: str) -> Permission | None:
        return self.session.scalar(select(Permission).where(Permission.code == code))

    def list(
        self, *, module: str | None = None, offset: int = 0, limit: int = 100
    ) -> Sequence[Permission]:
        _validate_pagination(offset, limit)
        statement = select(Permission)
        if module is not None:
            statement = statement.where(Permission.module == module)
        statement = statement.order_by(Permission.code).offset(offset).limit(limit)
        return self.session.scalars(statement).all()

    def count(self, *, module: str | None = None) -> int:
        statement = select(func.count()).select_from(Permission)
        if module is not None:
            statement = statement.where(Permission.module == module)
        return int(self.session.scalar(statement) or 0)

    def add(self, permission: Permission) -> Permission:
        self.session.add(permission)
        self.session.flush()
        return permission

    def update(self, permission: Permission, **changes: object) -> Permission:
        allowed = {"code", "name", "module", "description"}
        _apply_changes(permission, changes, allowed)
        self.session.flush()
        return permission

    def delete(self, permission: Permission) -> None:
        self.session.delete(permission)
        self.session.flush()


def _validate_pagination(offset: int, limit: int) -> None:
    if offset < 0:
        raise ValueError("offset must be greater than or equal to zero.")
    if not 1 <= limit <= 500:
        raise ValueError("limit must be between 1 and 500.")


def _apply_changes(entity: object, changes: dict[str, object], allowed: set[str]) -> None:
    if not changes:
        raise ValueError("At least one field change is required.")
    unknown = set(changes) - allowed
    if unknown:
        names = ", ".join(sorted(unknown))
        raise ValueError(f"Unsupported field(s): {names}.")
    for field, value in changes.items():
        setattr(entity, field, value)
