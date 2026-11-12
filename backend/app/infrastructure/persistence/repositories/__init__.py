"""Persistence repositories for BiteGuard platform entities."""

from app.infrastructure.persistence.repositories.audit_log import AuditLogRepository
from app.infrastructure.persistence.repositories.data_scope import UserDataScopeRepository
from app.infrastructure.persistence.repositories.identity import (
    PermissionRepository,
    RoleRepository,
    UserRepository,
)

__all__ = [
    "AuditLogRepository",
    "PermissionRepository",
    "RoleRepository",
    "UserRepository",
    "UserDataScopeRepository",
]
