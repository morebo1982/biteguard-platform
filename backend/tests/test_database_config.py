from urllib.parse import parse_qs, urlsplit

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.infrastructure.database import build_database_url


def test_database_url_not_built_without_required_values():
    settings = Settings(
        _env_file=None,
        database_host=None,
        database_name=None,
        database_user=None,
        database_password=None,
    )
    assert build_database_url(settings) is None


def test_database_url_built_when_configured():
    settings = Settings(
        _env_file=None,
        database_host="localhost",
        database_name="BiteGuardDev",
        database_user="dev_user",
        database_password="example-only",
    )
    url = build_database_url(settings)
    assert url is not None and url.startswith("mssql+pyodbc:///")


def test_windows_authentication_does_not_require_sql_credentials():
    settings = Settings(
        _env_file=None,
        database_host="localhost",
        database_name="BiteGuardDev",
        database_windows_authentication=True,
    )
    assert settings.database_is_configured is True
    url = build_database_url(settings) or ""
    odbc_options = parse_qs(urlsplit(url).query)["odbc_connect"][0]
    assert "Trusted_Connection=yes" in odbc_options


def test_production_rejects_trust_server_certificate():
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            app_env="production",
            database_trust_server_certificate=True,
        )
