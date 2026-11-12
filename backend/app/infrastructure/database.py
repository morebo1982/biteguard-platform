from urllib.parse import quote_plus

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings


def build_database_url(settings: Settings) -> str | None:
    if not settings.database_is_configured:
        return None

    parts = [
        f"DRIVER={{{settings.database_driver}}}",
        f"SERVER=tcp:{settings.database_host},{settings.database_port}",
        f"DATABASE={settings.database_name}",
        "Encrypt=yes",
        (f"TrustServerCertificate={'yes' if settings.database_trust_server_certificate else 'no'}"),
    ]

    if settings.database_windows_authentication:
        parts.append("Trusted_Connection=yes")
    else:
        parts.extend(
            [
                f"UID={settings.database_user}",
                f"PWD={settings.database_password}",
            ]
        )

    return f"mssql+pyodbc:///?odbc_connect={quote_plus(';'.join(parts))}"


def create_database_engine(settings: Settings) -> Engine | None:
    url = build_database_url(settings)
    if url is None:
        return None

    return create_engine(
        url,
        pool_pre_ping=True,
        pool_recycle=1800,
    )


def check_database_connection(engine: Engine) -> bool:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return True


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create a session factory bound to the supplied engine."""
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
