"""Application services for users, roles, and permissions.

Services coordinate repositories and enforce application rules. They flush but
never commit or roll back: transaction ownership belongs to the calling unit of
work (for example, an API dependency or a background-job boundary).
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.application.exceptions import (
    EntityConflictError,
    EntityNotFoundError,
    InvalidOperationError,
)
from app.infrastructure.persistence.models.identity import Permission, Role, User
from app.infrastructure.persistence.repositories import (
    PermissionRepository,
    RoleRepository,
    UserRepository,
)


class UserService:
    """Coordinate user lifecycle and role assignments."""

    def __init__(self, session: Session) -> None:
        self.users = UserRepository(session)
        self.roles = RoleRepository(session)

    def create_user(self, *, username: str, display_name: str, email: str | None = None) -> User:
        username = _required_text(username, "username")
        display_name = _required_text(display_name, "display_name")
        email = _optional_text(email)
        if self.users.get_by_username(username) is not None:
            raise EntityConflictError("Username is already in use.")
        if email is not None and self.users.get_by_email(email) is not None:
            raise EntityConflictError("Email is already in use.")
        return self.users.add(
            User(username=username, display_name=display_name, email=email, is_active=True)
        )

    def get_user(self, user_id: uuid.UUID) -> User:
        user = self.users.get(user_id)
        if user is None:
            raise EntityNotFoundError("User was not found.")
        return user

    def get_by_username(self, username: str) -> User:
        user = self.users.get_by_username(username)
        if user is None:
            raise EntityNotFoundError("User was not found.")
        return user

    def list_users(self, *, offset: int = 0, limit: int = 100) -> Sequence[User]:
        return self.users.list(offset=offset, limit=limit)

    def count_users(self) -> int:
        return self.users.count()

    def update_user(
        self,
        user_id: uuid.UUID,
        *,
        username: str | None = None,
        display_name: str | None = None,
        email: str | None = None,
    ) -> User:
        user = self.get_user(user_id)
        changes: dict[str, object] = {}
        if username is not None:
            username = _required_text(username, "username")
            existing = self.users.get_by_username(username)
            if existing is not None and existing.id != user_id:
                raise EntityConflictError("Username is already in use.")
            changes["username"] = username
        if display_name is not None:
            changes["display_name"] = _required_text(display_name, "display_name")
        if email is not None:
            email = _optional_text(email)
            existing = self.users.get_by_email(email) if email else None
            if existing is not None and existing.id != user_id:
                raise EntityConflictError("Email is already in use.")
            changes["email"] = email
        if not changes:
            raise InvalidOperationError("At least one user field must be supplied.")
        return self.users.update(user, **changes)

    def deactivate_user(self, user_id: uuid.UUID) -> User:
        user = self.get_user(user_id)
        if not user.is_active:
            return user
        return self.users.update(user, is_active=False)

    def activate_user(self, user_id: uuid.UUID) -> User:
        user = self.get_user(user_id)
        if user.is_active:
            return user
        return self.users.update(user, is_active=True)

    def assign_role(self, user_id: uuid.UUID, role_id: uuid.UUID) -> bool:
        user = self.get_user(user_id)
        role = self.roles.get(role_id)
        if role is None:
            raise EntityNotFoundError("Role was not found.")
        if not user.is_active:
            raise InvalidOperationError("An inactive user cannot receive role assignments.")
        if not role.is_active:
            raise InvalidOperationError("An inactive role cannot be assigned.")
        return self.users.assign_role(user_id, role_id)

    def remove_role(self, user_id: uuid.UUID, role_id: uuid.UUID) -> bool:
        self.get_user(user_id)
        if self.roles.get(role_id) is None:
            raise EntityNotFoundError("Role was not found.")
        return self.users.remove_role(user_id, role_id)

    def list_user_roles(self, user_id: uuid.UUID) -> Sequence[Role]:
        self.get_user(user_id)
        return self.users.list_roles(user_id)


class RoleService:
    """Coordinate role lifecycle and permission assignments."""

    def __init__(self, session: Session) -> None:
        self.roles = RoleRepository(session)
        self.permissions = PermissionRepository(session)

    def create_role(self, *, code: str, name: str, description: str | None = None) -> Role:
        code = _required_text(code, "code")
        name = _required_text(name, "name")
        if self.roles.get_by_code(code) is not None:
            raise EntityConflictError("Role code is already in use.")
        return self.roles.add(
            Role(code=code, name=name, description=_optional_text(description), is_system=False)
        )

    def get_role(self, role_id: uuid.UUID) -> Role:
        role = self.roles.get(role_id)
        if role is None:
            raise EntityNotFoundError("Role was not found.")
        return role

    def list_roles(self, *, offset: int = 0, limit: int = 100) -> Sequence[Role]:
        return self.roles.list(offset=offset, limit=limit)

    def count_roles(self) -> int:
        return self.roles.count()

    def update_role(
        self,
        role_id: uuid.UUID,
        *,
        code: str | None = None,
        name: str | None = None,
        description: str | None = None,
    ) -> Role:
        role = self.get_role(role_id)
        if role.is_system:
            raise InvalidOperationError("System roles cannot be modified.")
        changes: dict[str, object] = {}
        if code is not None:
            code = _required_text(code, "code")
            existing = self.roles.get_by_code(code)
            if existing is not None and existing.id != role_id:
                raise EntityConflictError("Role code is already in use.")
            changes["code"] = code
        if name is not None:
            changes["name"] = _required_text(name, "name")
        if description is not None:
            changes["description"] = _optional_text(description)
        if not changes:
            raise InvalidOperationError("At least one role field must be supplied.")
        return self.roles.update(role, **changes)

    def deactivate_role(self, role_id: uuid.UUID) -> Role:
        role = self.get_role(role_id)
        if role.is_system:
            raise InvalidOperationError("System roles cannot be deactivated.")
        if role.is_active:
            return self.roles.update(role, is_active=False)
        return role

    def activate_role(self, role_id: uuid.UUID) -> Role:
        role = self.get_role(role_id)
        if not role.is_active:
            return self.roles.update(role, is_active=True)
        return role

    def delete_role(self, role_id: uuid.UUID) -> None:
        role = self.get_role(role_id)
        if role.is_system:
            raise InvalidOperationError("System roles cannot be deleted.")
        self.roles.delete(role)

    def assign_permission(self, role_id: uuid.UUID, permission_id: uuid.UUID) -> bool:
        role = self.get_role(role_id)
        permission = self.permissions.get(permission_id)
        if permission is None:
            raise EntityNotFoundError("Permission was not found.")
        if not role.is_active:
            raise InvalidOperationError("Permissions cannot be assigned to an inactive role.")
        return self.roles.assign_permission(role_id, permission_id)

    def remove_permission(self, role_id: uuid.UUID, permission_id: uuid.UUID) -> bool:
        self.get_role(role_id)
        if self.permissions.get(permission_id) is None:
            raise EntityNotFoundError("Permission was not found.")
        return self.roles.remove_permission(role_id, permission_id)

    def list_role_permissions(self, role_id: uuid.UUID) -> Sequence[Permission]:
        self.get_role(role_id)
        return self.roles.list_permissions(role_id)


class PermissionService:
    """Manage the permission catalogue."""

    def __init__(self, session: Session) -> None:
        self.permissions = PermissionRepository(session)

    def create_permission(
        self,
        *,
        code: str,
        name: str,
        module: str,
        description: str | None = None,
    ) -> Permission:
        code = _required_text(code, "code")
        name = _required_text(name, "name")
        module = _required_text(module, "module")
        if self.permissions.get_by_code(code) is not None:
            raise EntityConflictError("Permission code is already in use.")
        return self.permissions.add(
            Permission(
                code=code,
                name=name,
                module=module,
                description=_optional_text(description),
            )
        )

    def get_permission(self, permission_id: uuid.UUID) -> Permission:
        permission = self.permissions.get(permission_id)
        if permission is None:
            raise EntityNotFoundError("Permission was not found.")
        return permission

    def list_permissions(
        self, *, module: str | None = None, offset: int = 0, limit: int = 100
    ) -> Sequence[Permission]:
        if module is not None:
            module = _required_text(module, "module")
        return self.permissions.list(module=module, offset=offset, limit=limit)

    def count_permissions(self, *, module: str | None = None) -> int:
        return self.permissions.count(module=module)

    def update_permission(
        self,
        permission_id: uuid.UUID,
        *,
        code: str | None = None,
        name: str | None = None,
        module: str | None = None,
        description: str | None = None,
    ) -> Permission:
        permission = self.get_permission(permission_id)
        changes: dict[str, object] = {}
        if code is not None:
            code = _required_text(code, "code")
            existing = self.permissions.get_by_code(code)
            if existing is not None and existing.id != permission_id:
                raise EntityConflictError("Permission code is already in use.")
            changes["code"] = code
        if name is not None:
            changes["name"] = _required_text(name, "name")
        if module is not None:
            changes["module"] = _required_text(module, "module")
        if description is not None:
            changes["description"] = _optional_text(description)
        if not changes:
            raise InvalidOperationError("At least one permission field must be supplied.")
        return self.permissions.update(permission, **changes)

    def delete_permission(self, permission_id: uuid.UUID) -> None:
        permission = self.get_permission(permission_id)
        self.permissions.delete(permission)


def _required_text(value: str, field: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise InvalidOperationError(f"{field} must not be empty.")
    return cleaned


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None
