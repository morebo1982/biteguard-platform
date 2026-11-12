"""Interactive one-time password provisioning for an existing BiteGuard user."""

import getpass

from sqlalchemy import select

from app.application.authentication import set_user_password
from app.core.config import get_settings
from app.infrastructure.database import create_database_engine, create_session_factory
from app.infrastructure.persistence.models.identity import User


def main() -> None:
    settings = get_settings()
    engine = create_database_engine(settings)
    if engine is None:
        raise SystemExit("Database is not configured. Check the project .env file.")
    factory = create_session_factory(engine)
    try:
        username = input("Username: ").strip()
        password = getpass.getpass("New password (12+ characters): ")
        confirmation = getpass.getpass("Confirm password: ")
        if password != confirmation:
            raise SystemExit("Passwords do not match.")
        with factory.begin() as db:
            user = db.scalar(select(User).where(User.username == username))
            if user is None:
                raise SystemExit("User not found.")
            if not user.is_active:
                raise SystemExit("Cannot set password for an inactive user.")
            set_user_password(db, user, password)
        print("Password updated successfully.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
