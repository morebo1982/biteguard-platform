import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.infrastructure.persistence.base import Base
from app.infrastructure.persistence.models import AuditLog, Permission, Role, User
from app.infrastructure.persistence.repositories import (
    AuditLogRepository,
    PermissionRepository,
    RoleRepository,
    UserRepository,
)


@pytest.fixture
def session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db_session:
        yield db_session
    engine.dispose()


def test_user_repository_crud_and_lookup(session):
    repository = UserRepository(session)
    user = repository.add(User(username="alice", email="alice@example.com", display_name="Alice"))
    assert repository.get(user.id) is user
    assert repository.get_by_username("alice") is user
    assert repository.get_by_email("alice@example.com") is user
    assert repository.list() == [user]
    repository.update(user, display_name="Alice Smith", is_active=False)
    assert user.display_name == "Alice Smith"
    assert user.is_active is False
    repository.delete(user)
    assert repository.get(user.id) is None


def test_user_repository_rejects_unsafe_updates_and_invalid_pagination(session):
    repository = UserRepository(session)
    user = repository.add(User(username="alice", display_name="Alice"))
    with pytest.raises(ValueError, match="Unsupported field"):
        repository.update(user, id=uuid.uuid4())
    with pytest.raises(ValueError, match="limit"):
        repository.list(limit=0)


def test_user_role_assignment_is_idempotent_and_queryable(session):
    user_repo = UserRepository(session)
    role_repo = RoleRepository(session)
    user = user_repo.add(User(username="alice", display_name="Alice"))
    role = role_repo.add(Role(code="admin", name="Administrator"))
    assert user_repo.assign_role(user.id, role.id) is True
    assert user_repo.assign_role(user.id, role.id) is False
    assert user_repo.list_roles(user.id) == [role]
    assert user_repo.remove_role(user.id, role.id) is True
    assert user_repo.remove_role(user.id, role.id) is False


def test_role_permission_assignment_and_permission_filter(session):
    role_repo = RoleRepository(session)
    permission_repo = PermissionRepository(session)
    role = role_repo.add(Role(code="operator", name="Operator"))
    permission = permission_repo.add(
        Permission(code="orders.read", name="Read orders", module="orders")
    )
    assert role_repo.assign_permission(role.id, permission.id) is True
    assert role_repo.assign_permission(role.id, permission.id) is False
    assert role_repo.list_permissions(role.id) == [permission]
    assert permission_repo.get_by_code("orders.read") is permission
    assert permission_repo.list(module="orders") == [permission]
    assert permission_repo.list(module="finance") == []
    assert role_repo.remove_permission(role.id, permission.id) is True


def test_assignment_rejects_missing_entities(session):
    with pytest.raises(ValueError, match="User does not exist"):
        UserRepository(session).assign_role(uuid.uuid4(), uuid.uuid4())
    with pytest.raises(ValueError, match="Role does not exist"):
        RoleRepository(session).assign_permission(uuid.uuid4(), uuid.uuid4())


def test_audit_repository_is_append_and_query_oriented(session):
    user = User(username="auditor", display_name="Auditor")
    session.add(user)
    session.flush()
    repository = AuditLogRepository(session)
    record = repository.add(
        AuditLog(
            actor_user_id=user.id,
            action="orders.read",
            entity_type="Order",
            entity_id="ORD-001",
            result="success",
            source="test",
        )
    )
    assert repository.get(record.id) is record
    assert repository.list_for_entity("Order", "ORD-001") == [record]
    assert repository.list_for_actor(user.id) == [record]
