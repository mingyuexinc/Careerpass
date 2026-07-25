"""Password and Access Token primitives for the authentication module."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import jwt
from jwt import InvalidTokenError

from app.core.config import Settings

_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1
_SALT_BYTES = 16
_KEY_LENGTH = 32
_JWT_ALGORITHM = "HS256"


class InvalidAccessTokenError(ValueError):
    """Raised when an access token cannot be trusted."""


def hash_password(password: str) -> str:
    """Create a salted scrypt password hash; callers must never log the result."""
    salt = secrets.token_bytes(_SALT_BYTES)
    derived_key = _derive_password_key(password, salt)
    return "$".join(
        (
            "scrypt",
            str(_SCRYPT_N),
            str(_SCRYPT_R),
            str(_SCRYPT_P),
            base64.b64encode(salt).decode("ascii"),
            base64.b64encode(derived_key).decode("ascii"),
        )
    )


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against a hash produced by :func:`hash_password`."""
    try:
        algorithm, n_value, r_value, p_value, encoded_salt, encoded_key = password_hash.split("$")
        if algorithm != "scrypt":
            return False
        n, r, p = int(n_value), int(r_value), int(p_value)
        if (n, r, p) != (_SCRYPT_N, _SCRYPT_R, _SCRYPT_P):
            return False
        salt = base64.b64decode(encoded_salt, validate=True)
        expected_key = base64.b64decode(encoded_key, validate=True)
        actual_key = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=n,
            r=r,
            p=p,
            dklen=len(expected_key),
        )
    except (TypeError, ValueError, UnicodeEncodeError):
        return False
    return hmac.compare_digest(actual_key, expected_key)


def create_access_token(*, user_id: UUID, settings: Settings, now: datetime | None = None) -> str:
    """Issue a short-lived JWT containing only the authenticated user identifier."""
    issued_at = now or datetime.now(UTC)
    expires_at = issued_at + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": issued_at,
        "exp": expires_at,
    }
    return jwt.encode(
        payload,
        settings.jwt_secret_key.get_secret_value(),
        algorithm=_JWT_ALGORITHM,
    )


def decode_access_token(*, token: str, settings: Settings) -> UUID:
    """Validate an access token and return its user identifier without logging the token."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=[_JWT_ALGORITHM],
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
            options={"require": ["sub", "iss", "aud", "iat", "exp"]},
        )
        return UUID(str(payload["sub"]))
    except (InvalidTokenError, KeyError, TypeError, ValueError) as exc:
        raise InvalidAccessTokenError("invalid access token") from exc


def _derive_password_key(password: str, salt: bytes) -> bytes:
    return hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=_KEY_LENGTH,
    )
