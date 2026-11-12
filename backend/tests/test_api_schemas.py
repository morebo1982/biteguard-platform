import uuid
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.api.v1.schemas.identity import (
    PermissionCreate,
    PermissionRead,
    RoleCreate,
    RoleRead,
    UserCreate,
    UserRead,
    UserUpdate,
)


def test_user_create_strips_strings_and_accepts_optional_email():
    payload = UserCreate(username="  alice ", display_name=" Alice ", email="a@example.com")
    assert payload.username == "alice"
    assert payload.display_name == "Alice"
    assert payload.email == "a@example.com"


@pytest.mark.parametrize(
    "payload",
    [
        {"username": "", "display_name": "Alice"},
        {"username": "a" * 81, "display_name": "Alice"},
        {"username": "alice", "display_name": "Alice", "unexpected": True},
        {"username": "alice", "display_name": "Alice", "email": "not-an-email"},
    ],
)
def test_user_create_rejects_invalid_input(payload):
    with pytest.raises(ValidationError):
        UserCreate.model_validate(payload)


def test_user_update_supports_partial_fields_and_explicit_null_email():
    payload = UserUpdate.model_validate({"email": None})
    assert payload.model_fields_set == {"email"}
    assert payload.email is None


def test_role_and_permission_create_validate_contracts():
    role = RoleCreate(code="admin", name="Administrator")
    permission = PermissionCreate(code="users.read", name="Read users", module="identity")
    assert role.description is None
    assert permission.module == "identity"


def test_read_schemas_load_orm_style_attributes():
    now = datetime.now(UTC)
    user_id = uuid.uuid4()

    class UserRecord:
        id = user_id
        username = "alice"
        display_name = "Alice"
        email = None
        is_active = True
        created_at = now
        updated_at = now

    result = UserRead.model_validate(UserRecord())
    assert result.id == user_id
    assert result.username == "alice"


def test_role_and_permission_read_schemas():
    now = datetime.now(UTC)
    common = {
        "id": uuid.uuid4(),
        "code": "code",
        "name": "Name",
        "description": None,
        "created_at": now,
        "updated_at": now,
    }
    role = RoleRead.model_validate({**common, "is_system": False, "is_active": True})
    permission = PermissionRead.model_validate({**common, "module": "identity"})
    assert role.is_active is True
    assert permission.module == "identity"
