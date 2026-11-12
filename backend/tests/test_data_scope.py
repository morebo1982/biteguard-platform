"""Data-scope repository and fail-closed query filtering tests."""

import uuid

import pytest
from sqlalchemy import String, Uuid, create_engine, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.application.data_scope import DataScopeContext, DataScopeGrant, apply_data_scope
from app.infrastructure.persistence.base import Base
from app.infrastructure.persistence.models.identity import User
from app.infrastructure.persistence.repositories.data_scope import UserDataScopeRepository


class ScopedOrder(Base):
    __tablename__ = "test_scoped_orders"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    company_id: Mapped[str] = mapped_column(String(40))
    department_id: Mapped[str] = mapped_column(String(40))
    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True))


@pytest.fixture
def session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        yield db
    engine.dispose()


def test_scope_repository_grant_is_idempotent_and_revoke(session):
    user = User(username="scope-user", display_name="Scope User")
    session.add(user)
    session.flush()
    repository = UserDataScopeRepository(session)
    first = repository.grant(user.id, "company", "company-001")
    second = repository.grant(user.id, "company", "company-001")
    assert first.id == second.id
    assert len(repository.list_for_user(user.id)) == 1
    assert repository.revoke(user.id, "company", "company-001") is True
    assert repository.revoke(user.id, "company", "company-001") is False


def test_scope_repository_validates_global_and_owner_values(session):
    user = User(username="scope-user2", display_name="Scope User")
    session.add(user)
    session.flush()
    repository = UserDataScopeRepository(session)
    with pytest.raises(ValueError, match="Global scope"):
        repository.grant(user.id, "global", "all")
    with pytest.raises(ValueError, match="Owner scope"):
        repository.grant(user.id, "owner", str(user.id))
    with pytest.raises(ValueError, match="Unsupported"):
        repository.grant(user.id, "tenant", "x")


def test_query_scope_fails_closed_when_no_grants_or_no_matching_columns(session):
    user_id = uuid.uuid4()
    session.add_all(
        [
            ScopedOrder(company_id="c1", department_id="d1", owner_id=user_id),
            ScopedOrder(company_id="c2", department_id="d2", owner_id=uuid.uuid4()),
        ]
    )
    session.flush()
    empty = DataScopeContext(user_id, ())
    assert session.scalars(apply_data_scope(select(ScopedOrder), ScopedOrder, empty)).all() == []

    # A company grant cannot accidentally authorize a model without company_id.
    context = DataScopeContext(user_id, (DataScopeGrant("company", "c1"),))
    assert session.scalars(apply_data_scope(select(User), User, context)).all() == []


def test_company_department_and_owner_scopes_are_or_combined(session):
    owner = uuid.uuid4()
    other = uuid.uuid4()
    records = [
        ScopedOrder(company_id="c1", department_id="d1", owner_id=other),
        ScopedOrder(company_id="c2", department_id="d2", owner_id=owner),
        ScopedOrder(company_id="c3", department_id="d3", owner_id=other),
    ]
    session.add_all(records)
    session.flush()
    context = DataScopeContext(
        owner,
        (
            DataScopeGrant("company", "c1"),
            DataScopeGrant("department", "d2"),
            DataScopeGrant("owner", "self"),
        ),
    )
    visible = session.scalars(apply_data_scope(select(ScopedOrder), ScopedOrder, context)).all()
    assert {row.id for row in visible} == {records[0].id, records[1].id}


def test_global_scope_allows_all_rows(session):
    session.add_all(
        [
            ScopedOrder(company_id="c1", department_id="d1", owner_id=uuid.uuid4()),
            ScopedOrder(company_id="c2", department_id="d2", owner_id=uuid.uuid4()),
        ]
    )
    session.flush()
    context = DataScopeContext(uuid.uuid4(), (DataScopeGrant("global", "*"),))
    assert (
        len(session.scalars(apply_data_scope(select(ScopedOrder), ScopedOrder, context)).all()) == 2
    )
