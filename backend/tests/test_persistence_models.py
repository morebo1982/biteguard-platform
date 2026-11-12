from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.infrastructure.persistence.base import Base
from app.infrastructure.persistence.models import AuditLog, User


def test_foundational_tables_and_relationship_tables_are_registered():
    expected = {
        "users",
        "roles",
        "permissions",
        "user_roles",
        "role_permissions",
        "audit_logs",
    }
    assert expected.issubset(Base.metadata.tables.keys())


def test_foundational_schema_can_be_created_in_sqlite_for_testing():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    table_names = set(inspect(engine).get_table_names())
    assert {
        "users",
        "roles",
        "permissions",
        "user_roles",
        "role_permissions",
        "audit_logs",
    }.issubset(table_names)
    engine.dispose()


def test_user_username_must_be_unique():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add_all(
            [
                User(username="operator", display_name="Operator"),
                User(username="operator", display_name="Duplicate"),
            ]
        )
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
        else:
            raise AssertionError("Duplicate usernames should be rejected by the database.")
    engine.dispose()


def test_audit_log_defaults_and_required_fields():
    record = AuditLog(
        actor_user_id=None,
        action="test.action",
        entity_type="TestEntity",
        result="success",
        source="test",
    )
    assert record.id is None  # assigned by SQLAlchemy on insert
    assert record.action == "test.action"
    assert record.entity_type == "TestEntity"
