import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies.database import get_db
from app.application.authentication import (
    AuthenticationError, authenticate, decode_access_token, get_active_user,
    hash_password, issue_access_token, revoke_access_token, set_user_password,
    verify_password,
)
from app.core.config import Settings
from app.infrastructure.persistence.base import Base
from app.infrastructure.persistence.models.identity import (
    Permission, Role, User, role_permissions, user_roles,
)
from app.main import app


def test_scrypt_password_hash_and_verification():
    encoded = hash_password("Correct-Horse-Battery-123!")
    assert encoded.startswith("scrypt$")
    assert verify_password("Correct-Horse-Battery-123!", encoded)
    assert not verify_password("wrong-password", encoded)
    with pytest.raises(ValueError):
        hash_password("short")


def test_jwt_issue_decode_and_revocation():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    settings = Settings(_env_file=None, auth_jwt_secret_key="test-secret-key-that-is-at-least-32-chars")
    with factory.begin() as db:
        user = User(username="auth-user", display_name="Auth User", is_active=True)
        db.add(user)
        db.flush()
        token, _ = issue_access_token(user, settings)
        claims = decode_access_token(token, settings)
        assert get_active_user(db, claims).id == user.id
        revoke_access_token(db, claims)
        with pytest.raises(AuthenticationError):
            get_active_user(db, claims)
    engine.dispose()


def test_login_authenticates_active_user_and_rejects_wrong_password():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    settings = Settings(_env_file=None, auth_jwt_secret_key="test-secret-key-that-is-at-least-32-chars")
    with factory.begin() as db:
        user = User(username="login-user", display_name="Login User", is_active=True)
        db.add(user)
        db.flush()
        set_user_password(db, user, "Correct-Horse-Battery-123!")
        found, token, _ = authenticate(db, "login-user", "Correct-Horse-Battery-123!", settings)
        assert found.id == user.id
        assert decode_access_token(token, settings)["sub"] == str(user.id)
        with pytest.raises(AuthenticationError):
            authenticate(db, "login-user", "wrong-password", settings)
    engine.dispose()


def test_inactive_user_cannot_authenticate():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    settings = Settings(_env_file=None, auth_jwt_secret_key="test-secret-key-that-is-at-least-32-chars")
    with factory.begin() as db:
        user = User(username="inactive-user", display_name="Inactive User", is_active=False)
        db.add(user)
        db.flush()
        set_user_password(db, user, "Correct-Horse-Battery-123!")
        with pytest.raises(AuthenticationError):
            authenticate(db, "inactive-user", "Correct-Horse-Battery-123!", settings)
    engine.dispose()


def test_auth_router_and_protected_iam_require_authentication():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    def override_get_db():
        with factory() as db:
            yield db
    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            app.state.settings.auth_jwt_secret_key = "test-secret-key-that-is-at-least-32-chars"
            assert client.get("/api/v1/users").status_code == 401
            assert client.get("/api/v1/auth/me").status_code == 401
            assert client.post("/api/v1/auth/login", json={"username": "nobody", "password": "bad"}).status_code == 401
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_login_me_logout_revokes_token_end_to_end():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_get_db():
        db = factory()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with factory.begin() as db:
            user = User(username="flow-user", display_name="Flow User", is_active=True)
            db.add(user)
            db.flush()
            set_user_password(db, user, "Correct-Horse-Battery-123!")
            role = Role(code="flow-role", name="Flow Role", is_active=True)
            permission = Permission(code="users.read", name="Read users", module="users")
            db.add_all([role, permission])
            db.flush()
            db.execute(user_roles.insert().values(user_id=user.id, role_id=role.id))
            db.execute(role_permissions.insert().values(role_id=role.id, permission_id=permission.id))
        with TestClient(app) as client:
            app.state.session_factory = factory
            app.state.settings.auth_jwt_secret_key = "test-secret-key-that-is-at-least-32-chars"
            login = client.post("/api/v1/auth/login", json={
                "username": "flow-user", "password": "Correct-Horse-Battery-123!"
            })
            assert login.status_code == 200
            token = login.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            assert client.get("/api/v1/auth/me", headers=headers).status_code == 200
            assert client.get("/api/v1/users", headers=headers).status_code == 200
            assert client.post("/api/v1/auth/logout", headers=headers).status_code == 204
            assert client.get("/api/v1/auth/me", headers=headers).status_code == 401
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
        engine.dispose()
