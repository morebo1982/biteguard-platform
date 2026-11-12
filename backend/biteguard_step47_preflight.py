"""Read-only preflight for BiteGuard Step 47 (SQL Server).
Run from backend directory with the project's virtual environment active.
This script does not create, alter, or delete database objects.
"""
from sqlalchemy import inspect, text

from app.core.config import get_settings
from app.infrastructure.database import create_database_engine

EXPECTED_TABLES = {
    "users",
    "roles",
    "permissions",
    "user_roles",
    "role_permissions",
    "audit_logs",
}


def main() -> int:
    settings = get_settings()
    if settings.app_env != "development":
        print(f"STOP: APP_ENV is {settings.app_env!r}, not 'development'.")
        return 2
    if not settings.database_is_configured:
        print("STOP: Database configuration is incomplete. Check backend .env.")
        return 2

    engine = create_database_engine(settings)
    if engine is None:
        print("STOP: Could not build database connection.")
        return 2

    try:
        with engine.connect() as connection:
            identity = connection.execute(
                text("SELECT @@SERVERNAME AS server_name, DB_NAME() AS database_name")
            ).mappings().one()
            tables = set(inspect(connection).get_table_names())
            user_tables = sorted(t for t in tables if t != "alembic_version")

            print("READ-ONLY DATABASE PREFLIGHT")
            print(f"Server: {identity['server_name']}")
            print(f"Database: {identity['database_name']}")
            print(f"APP_ENV: {settings.app_env}")
            print(f"Existing tables ({len(user_tables)}):")
            for table in user_tables:
                print(f"  - {table}")

            present = EXPECTED_TABLES.intersection(tables)
            if present:
                print("STOP: Some Step 46 tables already exist:")
                for table in sorted(present):
                    print(f"  - {table}")
                print("Do not run upgrade until the existing schema and Alembic state are reviewed.")
                return 3

            if user_tables:
                print("STOP: Database is not structurally empty. Review before migration.")
                return 3

            if "alembic_version" in tables:
                print("STOP: alembic_version exists although target tables are absent; review migration state.")
                return 3

            print("PASS: No application tables or Alembic version table found.")
            print("No database changes were made. After confirming the backup, run:")
            print("  python -m alembic upgrade head")
            return 0
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
