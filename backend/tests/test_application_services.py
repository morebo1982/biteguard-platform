"""Unit tests for IAM application services."""

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.application.exceptions import (
    EntityConflictError,
    EntityNotFoundError,
    InvalidOperationError,
)
from app.application.services import PermissionService, RoleService, UserService
from app.infrastructure.persistence.base import Base
from app.infrastructure.persistence.models.identity import Permission, Role


@pytest.fixture
def session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db_session:
        yield db_session
    engine.dispose()


def test_user_service_create_update_activation_and_roles(session):
    users = UserService(session)
    roles = RoleService(session)
    user = users.create_user(
        username="  alice  ", display_name=" Alice ", email="alice@example.com"
    )
    role = roles.create_role(code="operator", name="Operator")
    assert user.username == "alice"
    assert users.assign_role(user.id, role.id) is True
    assert users.assign_role(user.id, role.id) is False
    assert [item.id for item in users.list_user_roles(user.id)] == [role.id]
    updated = users.update_user(user.id, display_name="Alice Smith")
    assert updated.display_name == "Alice Smith"
    assert users.deactivate_user(user.id).is_active is False
    with pytest.raises(InvalidOperationError, match="inactive user"):
        users.assign_role(user.id, role.id)
    assert users.activate_user(user.id).is_active is True
    assert users.remove_role(user.id, role.id) is True


def test_user_service_conflicts_and_missing_entities(session):
    users = UserService(session)
    first = users.create_user(username="alice", display_name="Alice", email="a@example.com")
    with pytest.raises(EntityConflictError, match="Username"):
        users.create_user(username="alice", display_name="Other")
    with pytest.raises(EntityConflictError, match="Email"):
        users.create_user(username="bob", display_name="Bob", email="a@example.com")
    with pytest.raises(EntityNotFoundError):
        users.get_user(uuid.uuid4())
    with pytest.raises(InvalidOperationError, match="must not be empty"):
        users.create_user(username="  ", display_name="Empty")
    with pytest.raises(InvalidOperationError, match="At least one"):
        users.update_user(first.id)


def test_role_service_protects_system_roles_and_manages_permissions(session):
    roles = RoleService(session)
    permissions = PermissionService(session)
    role = roles.create_role(code="support", name="Support")
    permission = permissions.create_permission(
        code="customers.read", name="Read customers", module="customers"
    )
    assert roles.assign_permission(role.id, permission.id) is True
    assert roles.assign_permission(role.id, permission.id) is False
    assert roles.list_role_permissions(role.id) == [permission]
    assert permissions.list_permissions(module="customers") == [permission]
    assert roles.remove_permission(role.id, permission.id) is True

    system_role = Role(code="system_admin", name="System administrator", is_system=True)
    session.add(system_role)
    session.flush()
    with pytest.raises(InvalidOperationError, match="cannot be modified"):
        roles.update_role(system_role.id, name="Changed")
    with pytest.raises(InvalidOperationError, match="cannot be deactivated"):
        roles.deactivate_role(system_role.id)
    with pytest.raises(InvalidOperationError, match="cannot be deleted"):
        roles.delete_role(system_role.id)


def test_role_and_permission_conflicts_and_missing_entities(session):
    roles = RoleService(session)
    permissions = PermissionService(session)
    role = roles.create_role(code="auditor", name="Auditor")
    permission = permissions.create_permission(
        code="audit.read", name="Read audit", module="audit"
    )
    with pytest.raises(EntityConflictError):
        roles.create_role(code="auditor", name="Duplicate")
    with pytest.raises(EntityConflictError):
        permissions.create_permission(code="audit.read", name="Duplicate", module="audit")
    with pytest.raises(EntityNotFoundError):
        roles.get_role(uuid.uuid4())
    with pytest.raises(EntityNotFoundError):
        roles.assign_permission(role.id, uuid.uuid4())
    with pytest.raises(InvalidOperationError, match="At least one"):
        permissions.update_permission(permission.id)


def test_inactive_role_cannot_be_assigned(session):
    users = UserService(session)
    roles = RoleService(session)
    user = users.create_user(username="bob", display_name="Bob")
    role = roles.create_role(code="temporary", name="Temporary")
    roles.deactivate_role(role.id)
    with pytest.raises(InvalidOperationError, match="inactive role"):
        users.assign_role(user.id, role.id)


def test_services_do_not_commit_the_callers_transaction(session):
    service = UserService(session)
    service.create_user(username="transactional", display_name="Transactional")
    assert session.in_transaction()
    session.rollback()
    assert service.users.get_by_username("transactional") is None
