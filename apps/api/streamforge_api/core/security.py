from __future__ import annotations

import hashlib
import hmac
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError, VerificationError
from argon2.low_level import Type
from itsdangerous import BadSignature, URLSafeSerializer

from streamforge_api.core.config import Settings
from streamforge_api.core.errors import InvalidSessionError

_password_hasher = PasswordHasher(
    time_cost=2,
    memory_cost=65536,
    parallelism=2,
    hash_len=32,
    salt_len=16,
    type=Type.ID,
)


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, password)
    except (InvalidHashError, VerificationError, VerifyMismatchError):
        return False


def generate_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_session_token(token: str, settings: Settings) -> str:
    return hmac.new(
        settings.secret_key.encode("utf-8"),
        token.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _session_serializer(settings: Settings) -> URLSafeSerializer:
    return URLSafeSerializer(settings.secret_key, salt="streamforge-dashboard-session")


def sign_session_cookie(token: str, settings: Settings) -> str:
    return _session_serializer(settings).dumps({"token": token})


def unsign_session_cookie(cookie_value: str, settings: Settings) -> str:
    try:
        payload = _session_serializer(settings).loads(cookie_value)
    except BadSignature as exc:
        raise InvalidSessionError() from exc
    token = payload.get("token") if isinstance(payload, dict) else None
    if not isinstance(token, str) or not token:
        raise InvalidSessionError()
    return token
