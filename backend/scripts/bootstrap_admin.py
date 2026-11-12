
from __future__ import annotations

import getpass
import sys
from datetime import UTC, datetime

from sqlalchemy import func, select, text

from app.application.authentication import hash_password
from app.core.config import get_settings
from app.infrastructure.database import (
    create_database_engine,
    create_session_factory,
)
from app.infrastructure.persistence.models.auth import UserCredential
from app.infrastructure.persistence.models.identity import (
    Permission,
    Role,
    User,
    role_permissions,
    user_roles,
)


PERMISSIONS = [
    ("users.create", "Create users", "users"),
    ("users.read", "Read users", "users"),
    ("users.update", "Update users", "users"),
    ("users.activate", "Activate users", "users"),
    ("users.deactivate", "Deactivate users", "users"),
    ("users.roles.assign", "Assign user roles", "users"),
    ("roles.create", "Create roles", "roles"),
    ("roles.read", "Read roles", "roles"),
    ("roles.update", "Update roles", "roles"),
    ("roles.activate", "Activate roles", "roles"),
    ("roles.deactivate", "Deactivate roles", "roles"),
    ("roles.delete", "Delete roles", "roles"),
    ("roles.permissions.assign", "Assign role permissions", "roles"),
    ("permissions.create", "Create permissions", "permissions"),
    ("permissions.read", "Read permissions", "permissions"),
    ("permissions.update", "Update permissions", "permissions"),
    ("permissions.delete", "Delete permissions", "permissions"),
    ("users.scopes.manage", "Manage user data scopes", "users"),
    ("audit.read", "Read audit logs", "audit"),
]


def acquire_bootstrap_lock(session) -> None:
    """Prevent concurrent initial administrator creation on SQL Server."""

    if session.bind.dialect.name != "mssql":
        raise RuntimeError("Bootstrap requires SQL Server.")

    result = session.execute(
        text("""
            DECLARE @lock_result int;

            EXEC @lock_result = sys.sp_getapplock
                @Resource = :resource,
                @LockMode = 'Exclusive',
                @LockOwner = 'Transaction',
                @LockTimeout = 10000;

            SELECT @lock_result;
        """),
        {"resource": "BiteGuard:bootstrap_admin"},
    ).scalar_one()

    if result < 0:
        raise RuntimeError(
            f"Could not acquire bootstrap lock. SQL Server result: {result}"
        )


def ensure_empty(session) -> None:
    """Refuse bootstrap if identity records already exist."""

    checks = [
        (User, "users"),
        (Role, "roles"),
        (Permission, "permissions"),
        (UserCredential, "user_credentials"),
        (user_roles, "user_roles"),
        (role_permissions, "role_permissions"),
    ]

    occupied = []

    for model_or_table, name in checks:
        count = session.scalar(
            select(func.count()).select_from(model_or_table)
        )

        if count:
            occupied.append(f"{name}={count}")

    if occupied:
        raise RuntimeError(
            "Bootstrap refused. Identity data already exists: "
            + ", ".join(occupied)
        )


def main() -> int:
    print()
    print("BiteGuard Platform")
    print("Initial Administrator Setup")
    print("=" * 36)

    username = input("Admin username: ").strip()
    display_name = input("Admin display name: ").strip()
    email = input("Admin email (optional): ").strip() or None

    if not username or len(username) > 80:
        print("Error: Username must contain 1 to 80 characters.")
        return 1

    if not display_name or len(display_name) > 160:
        print("Error: Display name must contain 1 to 160 characters.")
        return 1

    if email and len(email) > 254:
        print("Error: Email must not exceed 254 characters.")
        return 1

    password = getpass.getpass(
        "Admin password (12-256 characters): "
    )
    confirmation = getpass.getpass("Confirm password: ")

    if password != confirmation:
        print("Error: Passwords do not match.")
        return 1

    try:
        password_hash = hash_password(password)
    except ValueError as exc:
        print(f"Error: {exc}")
        return 1
    finally:
        password = ""
        confirmation = ""

    settings = get_settings()
    engine = create_database_engine(settings)

    if engine is None:
        print("Error: Database is not configured.")
        return 1

    session_factory = create_session_factory(engine)

    try:
        with session_factory() as session:
            with session.begin():

                # Serialize all bootstrap attempts.
                acquire_bootstrap_lock(session)

                # Never overwrite or mix with existing identity data.
                ensure_empty(session)

                # Create initial administrator.
                admin = User(
                    username=username,
                    display_name=display_name,
                    email=email,
                    is_active=True,
                )

                session.add(admin)
                session.flush()

                # Store the password hash, never the plain password.
                credential = UserCredential(
                    user_id=admin.id,
                    password_hash=password_hash,
                    password_changed_at=datetime.now(UTC),
                )

                session.add(credential)

                # Create the protected system administrator role.
                admin_role = Role(
                    code="system_admin",
                    name="System Administrator",
                    description="Initial BiteGuard platform administrator",
                    is_system=True,
                    is_active=True,
                )

                session.add(admin_role)
                session.flush()

                # Create all API permissions.
                permission_objects = [
                    Permission(
                        code=code,
                        name=name,
                        module=module,
                    )
                    for code, name, module in PERMISSIONS
                ]

                session.add_all(permission_objects)
                session.flush()

                # Grant every permission to system_admin.
                session.execute(
                    role_permissions.insert(),
                    [
                        {
                            "role_id": admin_role.id,
                            "permission_id": permission.id,
                        }
                        for permission in permission_objects
                    ],
                )

                # Assign system_admin role to the initial user.
                session.execute(
                    user_roles.insert().values(
                        user_id=admin.id,
                        role_id=admin_role.id,
                    )
                )

        # Transaction has committed successfully.
        print()
        print("Initial administrator created successfully.")
        print(f"Username: {username}")
        print("Role: system_admin")
        print(f"Permissions: {len(PERMISSIONS)}")
        print()
        print("You can now sign in to BiteGuard Platform.")

        return 0

    except Exception as exc:
        print()
        print("Bootstrap failed.")
        print(f"Error type: {type(exc).__name__}")
        print(f"Details: {exc}")
        print("The transaction was rolled back if it had started.")
        return 1

    finally:
        engine.dispose()


if __name__ == "__main__":
    sys.exit(main())
