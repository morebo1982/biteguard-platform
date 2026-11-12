"""HTTP-level tests for the version 1 IAM API."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import delete, select
from sqlalchemy.pool import StaticPool

from app.api.dependencies.database import get_db
from app.api.dependencies.authentication import get_current_user
from types import SimpleNamespace
from app.infrastructure.persistence.base import Base
from app.infrastructure.persistence.models.identity import Permission, Role, User, user_roles, role_permissions
from app.infrastructure.persistence.models.audit_log import AuditLog
from app.main import app


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_get_db():
        session = factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # Give the test principal an explicit role with the permissions used by this API suite.
    with factory() as setup_session:
        test_user = User(username="test-admin", display_name="Test Admin", is_active=True)
        test_role = Role(code="test-admin", name="Test Admin", is_active=True)
        codes = [
            "users.create", "users.read", "users.update", "users.activate",
            "users.deactivate", "users.roles.assign", "roles.create", "roles.read",
            "roles.update", "roles.activate", "roles.deactivate", "roles.delete",
            "roles.permissions.assign", "users.scopes.manage", "permissions.create", "permissions.read",
            "permissions.update", "permissions.delete",
        ]
        permissions = [Permission(code=code, name=code, module=code.split('.')[0]) for code in codes]
        setup_session.add_all([test_user, test_role, *permissions])
        setup_session.flush()
        setup_session.execute(user_roles.insert().values(user_id=test_user.id, role_id=test_role.id))
        for permission in permissions:
            setup_session.execute(role_permissions.insert().values(role_id=test_role.id, permission_id=permission.id))
        setup_session.commit()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: test_user
    with TestClient(app) as test_client:
        app.state.session_factory = factory
        yield test_client
    app.dependency_overrides.clear()
    app.state.session_factory = None
    Base.metadata.drop_all(engine)
    engine.dispose()


def test_user_crud_and_role_assignment_api(client):
    created = client.post(
        "/api/v1/users", json={"username": "alice", "display_name": "Alice"}
    )
    assert created.status_code == 201
    user = created.json()

    role_response = client.post("/api/v1/roles", json={"code": "ops", "name": "Operations"})
    assert role_response.status_code == 201
    role = role_response.json()

    assigned = client.post(f"/api/v1/users/{user['id']}/roles", json={"role_id": role["id"]})
    assert assigned.status_code == 200
    assert assigned.json() == {"changed": True}
    assert len(client.get(f"/api/v1/users/{user['id']}/roles").json()) == 1

    updated = client.patch(f"/api/v1/users/{user['id']}", json={"display_name": "Alice B"})
    assert updated.status_code == 200
    assert updated.json()["display_name"] == "Alice B"

    listed = client.get("/api/v1/users?offset=0&limit=10")
    assert listed.status_code == 200
    assert listed.json()["page"]["total"] == 2

    assert client.post(f"/api/v1/users/{user['id']}/deactivate").status_code == 200
    assert client.post(f"/api/v1/users/{user['id']}/activate").json()["is_active"] is True

    removed = client.delete(f"/api/v1/users/{user['id']}/roles/{role['id']}")
    assert removed.json() == {"changed": True}


def test_role_permission_assignment_and_catalogue_api(client):
    role = client.post("/api/v1/roles", json={"code": "qa", "name": "Quality"}).json()
    permission_response = client.post(
        "/api/v1/permissions",
        json={"code": "quality.read", "name": "Read quality", "module": "quality"},
    )
    assert permission_response.status_code == 201
    permission = permission_response.json()

    assigned = client.post(
        f"/api/v1/roles/{role['id']}/permissions",
        json={"permission_id": permission["id"]},
    )
    assert assigned.json() == {"changed": True}
    assert len(client.get(f"/api/v1/roles/{role['id']}/permissions").json()) == 1

    filtered = client.get("/api/v1/permissions?module=quality")
    assert filtered.status_code == 200
    assert filtered.json()["page"]["total"] == 1

    updated = client.patch(
        f"/api/v1/permissions/{permission['id']}", json={"name": "View quality"}
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "View quality"

    assert client.delete(f"/api/v1/roles/{role['id']}").status_code == 204
    assert client.delete(f"/api/v1/permissions/{permission['id']}").status_code == 204


def test_api_maps_not_found_conflict_and_validation(client):
    missing = client.get(f"/api/v1/users/{uuid.uuid4()}")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "NOT_FOUND"

    payload = {"username": "duplicate", "display_name": "Duplicate"}
    assert client.post("/api/v1/users", json=payload).status_code == 201
    conflict = client.post("/api/v1/users", json=payload)
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "CONFLICT"

    invalid = client.get("/api/v1/users?offset=-1")
    assert invalid.status_code == 422


def test_permission_enforcement_denies_and_audits(client):
    # Remove the create permission from the test administrator's role.
    with app.state.session_factory() as session:
        role = session.scalar(select(Role).where(Role.code == "test-admin"))
        permission = session.scalar(select(Permission).where(Permission.code == "users.create"))
        session.execute(
            delete(role_permissions).where(
                role_permissions.c.role_id == role.id,
                role_permissions.c.permission_id == permission.id,
            )
        )
        session.commit()

    denied = client.post(
        "/api/v1/users", json={"username": "blocked", "display_name": "Blocked"}
    )
    assert denied.status_code == 403
    assert denied.json()["detail"]["code"] == "PERMISSION_DENIED"

    with app.state.session_factory() as session:
        audit = session.scalar(
            select(AuditLog).where(
                AuditLog.action == "authorization.denied",
                AuditLog.entity_id == "users.create",
            )
        )
        assert audit is not None
        assert audit.result == "denied"


def test_user_data_scope_grants_api(client):
    user_response = client.post("/api/v1/users", json={"username": "scoped", "display_name": "Scoped"})
    assert user_response.status_code == 201
    user_id = user_response.json()["id"]

    grant = client.post(
        f"/api/v1/users/{user_id}/data-scopes",
        json={"scope_type": "company", "scope_value": "company-001"},
    )
    assert grant.status_code == 201
    assert grant.json()["scope_type"] == "company"
    assert client.get(f"/api/v1/users/{user_id}/data-scopes").json()[0]["scope_value"] == "company-001"

    revoked = client.delete(f"/api/v1/users/{user_id}/data-scopes/company/company-001")
    assert revoked.json() == {"changed": True}


def test_user_data_scope_api_rejects_invalid_grant(client):
    user_response = client.post("/api/v1/users", json={"username": "scoped2", "display_name": "Scoped"})
    user_id = user_response.json()["id"]
    invalid = client.post(
        f"/api/v1/users/{user_id}/data-scopes",
        json={"scope_type": "global", "scope_value": "all"},
    )
    assert invalid.status_code == 422
