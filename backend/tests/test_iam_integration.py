"""End-to-end integration coverage for the IAM security boundary."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies.database import get_db
from app.application.authentication import set_user_password
from app.core.config import Settings
from app.infrastructure.persistence.base import Base
from app.infrastructure.persistence.models.audit_log import AuditLog
from app.infrastructure.persistence.models.data_scope import UserDataScope
from app.infrastructure.persistence.models.identity import (
    Permission,
    Role,
    User,
    role_permissions,
    user_roles,
)
from app.main import app


@pytest.fixture()
def iam_client():
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

    permissions = [
        "users.create", "users.read", "users.update", "users.activate",
        "users.deactivate", "users.roles.assign", "users.scopes.manage",
        "roles.create", "roles.read", "roles.update", "roles.activate",
        "roles.deactivate", "roles.delete", "roles.permissions.assign",
        "permissions.create", "permissions.read", "permissions.update",
        "permissions.delete", "audit.read",
    ]
    with factory() as db:
        admin = User(username="integration-admin", display_name="Integration Admin", is_active=True)
        role = Role(code="integration-admin", name="Integration Administrator", is_active=True)
        db.add_all([admin, role])
        db.flush()
        set_user_password(db, admin, "Integration-Admin-Password-2026!")
        permission_rows = [
            Permission(code=code, name=code, module=code.split(".", 1)[0])
            for code in permissions
        ]
        db.add_all(permission_rows)
        db.flush()
        db.execute(user_roles.insert().values(user_id=admin.id, role_id=role.id))
        for permission in permission_rows:
            db.execute(role_permissions.insert().values(
                role_id=role.id, permission_id=permission.id
            ))
        db.commit()

    app.dependency_overrides[get_db] = override_get_db
    app.state.session_factory = factory
    app.state.settings = Settings(
        _env_file=None,
        auth_jwt_secret_key="integration-test-secret-key-at-least-32-bytes-long",
        auth_failed_attempts=5,
        auth_lockout_minutes=15,
    )
    # Ensure the process-local login limiter does not leak between test runs.
    from app.api.v1 import authentication as auth_routes
    auth_routes._attempts.clear()

    with TestClient(app) as client:
        # Lifespan initializes app.state; install the test session factory afterwards.
        app.state.session_factory = factory
        yield client, factory

    app.dependency_overrides.clear()
    app.state.session_factory = None
    Base.metadata.drop_all(engine)
    engine.dispose()
    auth_routes._attempts.clear()


def _login(client: TestClient) -> str:
    response = client.post("/api/v1/auth/login", json={
        "username": "integration-admin",
        "password": "Integration-Admin-Password-2026!",
    })
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def test_iam_end_to_end_login_permissions_data_scope_and_audit(iam_client):
    client, factory = iam_client
    token = _login(client)
    headers = {"Authorization": f"Bearer {token}"}

    me = client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["username"] == "integration-admin"

    # Reuse the existing users.read permission instead of creating a duplicate.
    with factory() as db:
        existing_permission = db.scalar(
            select(Permission).where(Permission.code == "users.read")
        )
        assert existing_permission is not None
        role = db.scalar(select(Role).where(Role.code == "integration-admin"))
        assert db.scalar(select(role_permissions.c.permission_id).where(
            role_permissions.c.role_id == role.id,
            role_permissions.c.permission_id == existing_permission.id,
        )) is not None

    created = client.post(
        "/api/v1/users",
        json={"username": "integration-target", "display_name": "Integration Target"},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    target_id = created.json()["id"]

    grant_payload = {"scope_type": "company", "scope_value": "company-int-01"}
    grant = client.post(
        f"/api/v1/users/{target_id}/data-scopes", json=grant_payload, headers=headers
    )
    assert grant.status_code == 201, grant.text
    grant_again = client.post(
        f"/api/v1/users/{target_id}/data-scopes", json=grant_payload, headers=headers
    )
    assert grant_again.status_code == 201
    assert grant_again.json()["id"] == grant.json()["id"]

    revoked = client.delete(
        f"/api/v1/users/{target_id}/data-scopes/company/company-int-01", headers=headers
    )
    assert revoked.status_code == 200
    assert revoked.json() == {"changed": True}

    with factory() as db:
        events = db.scalars(select(AuditLog).where(
            (AuditLog.entity_id == target_id)
            | (AuditLog.entity_id == "integration-target")
        )).all()
        actions = [event.action for event in events]
        assert "user.created" in actions
        assert actions.count("user.data_scope_granted") == 1
        assert "user.data_scope_revoked" in actions
        assert db.scalars(select(UserDataScope).where(
            UserDataScope.user_id == uuid.UUID(target_id)
        )).all() == []

    logout = client.post("/api/v1/auth/logout", headers=headers)
    assert logout.status_code == 204
    after_logout = client.get("/api/v1/auth/me", headers=headers)
    assert after_logout.status_code == 401


def test_iam_permission_denial_is_audited_and_does_not_create_user(iam_client):
    client, factory = iam_client
    token = _login(client)
    headers = {"Authorization": f"Bearer {token}"}

    with factory() as db:
        role = db.scalar(select(Role).where(Role.code == "integration-admin"))
        permission = db.scalar(select(Permission).where(Permission.code == "users.create"))
        db.execute(role_permissions.delete().where(
            role_permissions.c.role_id == role.id,
            role_permissions.c.permission_id == permission.id,
        ))
        db.commit()

    denied = client.post(
        "/api/v1/users",
        json={"username": "should-not-exist", "display_name": "Should Not Exist"},
        headers=headers,
    )
    assert denied.status_code == 403

    with factory() as db:
        assert db.scalar(select(User).where(User.username == "should-not-exist")) is None
        denial = db.scalar(select(AuditLog).where(
            AuditLog.action == "authorization.denied",
            AuditLog.entity_id == "users.create",
        ))
        assert denial is not None
        assert denial.result == "denied"


def test_unauthenticated_iam_request_is_rejected(iam_client):
    client, _ = iam_client
    response = client.get("/api/v1/users")
    assert response.status_code == 401


def test_audit_log_read_endpoint_requires_permission_and_returns_events(iam_client):
    client, factory = iam_client
    token = _login(client)
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/v1/audit-logs?limit=10", headers=headers)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["total"] >= 1
    assert any(item["action"] == "auth.login" for item in payload["items"])
