"""Transactional audit integration tests."""
import uuid

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.infrastructure.persistence.audit import configure_audit_session, record_explicit_audit
from app.infrastructure.persistence.base import Base
from app.infrastructure.persistence.models.audit_log import AuditLog
from app.infrastructure.persistence.models.identity import Permission, Role, User


def _engine():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


def test_entity_create_update_and_delete_are_audited_transactionally():
    engine = _engine()
    with Session(engine) as db:
        actor_id = uuid.uuid4()
        configure_audit_session(db, actor_user_id=actor_id,
                                correlation_id="corr-123", ip_address="127.0.0.1")
        user = User(username="audit-user", display_name="Audit User")
        role = Role(code="audit-role", name="Audit Role")
        permission = Permission(code="audit.read", name="Audit Read", module="audit")
        db.add_all([user, role, permission])
        db.flush()
        user.display_name = "Updated Name"
        db.flush()
        db.delete(permission)
        db.commit()

        records = db.scalars(select(AuditLog).order_by(AuditLog.action)).all()
        actions = [row.action for row in records]
        assert "user.created" in actions
        assert "user.updated" in actions
        assert "role.created" in actions
        assert "permission.created" in actions
        assert "permission.deleted" in actions
        assert all(row.actor_user_id == actor_id for row in records)
        assert all(row.correlation_id == "corr-123" for row in records)
        assert all(row.ip_address == "127.0.0.1" for row in records)
        updated = next(row for row in records if row.action == "user.updated")
        assert updated.context_data["display_name"] == {
            "before": "Audit User", "after": "Updated Name"
        }
    engine.dispose()


def test_audit_records_rollback_with_business_transaction():
    engine = _engine()
    with Session(engine) as db:
        configure_audit_session(db, actor_user_id=uuid.uuid4())
        db.add(User(username="rolled-back", display_name="Rolled Back"))
        db.flush()
        db.rollback()
        assert db.scalar(select(AuditLog)) is None
    engine.dispose()


def test_explicit_audit_supports_bulk_permission_and_security_events():
    engine = _engine()
    with Session(engine) as db:
        actor_id = uuid.uuid4()
        configure_audit_session(db, actor_user_id=actor_id,
                                correlation_id="corr-security")
        record_explicit_audit(
            db, action="authorization.denied", entity_type="permission",
            entity_id="users.delete", result="denied",
            context_data={"path": "/api/v1/users/1", "method": "DELETE"},
        )
        db.commit()
        record = db.scalar(select(AuditLog))
        assert record is not None
        assert record.actor_user_id == actor_id
        assert record.result == "denied"
        assert record.correlation_id == "corr-security"
    engine.dispose()
