from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import get_settings
from app.infrastructure.database import build_database_url
from app.infrastructure.persistence.base import Base
from app.infrastructure.persistence import models  # noqa: F401 - register model metadata

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


# SQL Server may contain this optional database-diagram support table.
# It is not owned by BiteGuard and must not be treated as a table to drop.
IGNORED_REFLECTED_TABLES = {"sysdiagrams"}


def include_object(object, name, type_, reflected, compare_to) -> bool:
    if type_ == "table" and reflected and name in IGNORED_REFLECTED_TABLES:
        return False
    return True


def _database_url() -> str:
    url = build_database_url(get_settings())
    if url is None:
        raise RuntimeError(
            "Database is not configured. Set DATABASE_HOST and DATABASE_NAME, "
            "plus Windows Authentication or SQL credentials, before running migrations."
        )
    return url


def run_migrations_offline() -> None:
    url = _database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = _database_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            include_object=include_object,
        )
        with context.begin_transaction():
            context.run_migrations()
    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
