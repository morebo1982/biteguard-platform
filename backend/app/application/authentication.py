"""Authentication primitives and application service."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import jwt
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.infrastructure.persistence.models.auth import RevokedToken, UserCredential
from app.infrastructure.persistence.models.identity import User


class AuthenticationError(Exception):
    pass


def hash_password(password: str) -> str:
    if len(password) < 12 or len(password) > 256:
        raise ValueError("Password must contain between 12 and 256 characters.")
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1)
    return f"scrypt$16384$8$1${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, n, r, p, salt_hex, digest_hex = encoded.split("$")
        if algorithm != "scrypt":
            return False
        digest = hashlib.scrypt(
            password.encode("utf-8"),
            salt=bytes.fromhex(salt_hex),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(bytes.fromhex(digest_hex)),
        )
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def set_user_password(db: Session, user: User, password: str) -> None:
    encoded = hash_password(password)
    credential = db.get(UserCredential, user.id)
    if credential is None:
        credential = UserCredential(
            user_id=user.id, password_hash=encoded, password_changed_at=datetime.now(UTC)
        )
        db.add(credential)
    else:
        credential.password_hash = encoded
        credential.password_changed_at = datetime.now(UTC)
    db.flush()


def issue_access_token(user: User, settings: Settings) -> tuple[str, datetime]:
    if len(settings.auth_jwt_secret_key) < 32:
        raise RuntimeError("AUTH_JWT_SECRET_KEY must be configured with at least 32 characters.")
    now = datetime.now(UTC)
    expires = now + timedelta(minutes=settings.auth_access_token_minutes)
    claims = {
        "sub": str(user.id),
        "jti": str(uuid.uuid4()),
        "iat": now,
        "nbf": now,
        "exp": expires,
        "type": "access",
    }
    return jwt.encode(claims, settings.auth_jwt_secret_key, algorithm="HS256"), expires


def authenticate(
    db: Session, username: str, password: str, settings: Settings
) -> tuple[User, str, datetime]:
    user = db.scalar(select(User).where(User.username == username))
    credential = db.get(UserCredential, user.id) if user else None
    # Always perform a scrypt verification for unknown users to reduce timing leakage.
    if credential is None:
        dummy = hash_password("Dummy-Password-For-Timing-Only-123!")
        verify_password(password, dummy)
        raise AuthenticationError("Invalid username or password.")
    if not user.is_active or not verify_password(password, credential.password_hash):
        raise AuthenticationError("Invalid username or password.")
    token, expires = issue_access_token(user, settings)
    return user, token, expires


def decode_access_token(token: str, settings: Settings) -> dict:
    try:
        claims = jwt.decode(
            token,
            settings.auth_jwt_secret_key,
            algorithms=["HS256"],
            options={"require": ["exp", "iat", "nbf", "sub", "jti"]},
        )
        if claims.get("type") != "access":
            raise AuthenticationError("Invalid token.")
        return claims
    except jwt.PyJWTError as exc:
        raise AuthenticationError("Invalid or expired access token.") from exc


def get_active_user(db: Session, claims: dict) -> User:
    jti = claims["jti"]
    if db.get(RevokedToken, jti) is not None:
        raise AuthenticationError("Access token has been revoked.")
    try:
        user_id = uuid.UUID(claims["sub"])
    except (ValueError, TypeError) as exc:
        raise AuthenticationError("Invalid token subject.") from exc
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise AuthenticationError("User is unavailable.")
    return user


def revoke_access_token(db: Session, claims: dict) -> None:
    if db.get(RevokedToken, claims["jti"]) is None:
        expires = datetime.fromtimestamp(claims["exp"], UTC)
        db.add(RevokedToken(jti=claims["jti"], expires_at=expires))
        db.flush()
    # Opportunistic cleanup of expired revocation entries.
    db.execute(delete(RevokedToken).where(RevokedToken.expires_at < datetime.now(UTC)))
