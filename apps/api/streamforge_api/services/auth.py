from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from fastapi import Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session as DbSession

from streamforge_api.core.config import Settings
from streamforge_api.core.errors import (
    AuthenticationFailedError,
    BootstrapClosedError,
    InvalidSessionError,
    NotAuthenticatedError,
)
from streamforge_api.core.security import (
    generate_session_token,
    hash_password,
    hash_session_token,
    unsign_session_cookie,
    verify_password,
)
from streamforge_api.models import Session, User
from streamforge_api.services.audit import AuditService
from streamforge_api.services.setup import SetupService


@dataclass(frozen=True)
class AuthenticatedSession:
    user: User
    raw_token: str


class AuthService:
    def __init__(self, db: DbSession, settings: Settings) -> None:
        self.db = db
        self.settings = settings

    def bootstrap_admin(
        self,
        *,
        email: str,
        password: str,
        display_name: str,
        request: Request,
    ) -> AuthenticatedSession:
        admin_count = self.db.scalar(select(func.count()).select_from(User).where(User.is_admin))
        setup_state = SetupService(self.db).get_or_create_state()
        if admin_count or setup_state.is_complete:
            raise BootstrapClosedError()

        user = User(
            email=email.lower(),
            display_name=display_name,
            password_hash=hash_password(password),
            is_admin=True,
            is_active=True,
        )
        self.db.add(user)
        self.db.flush()
        SetupService(self.db).mark_account_created()
        AuditService(self.db).record(
            "administrator.bootstrap_created",
            actor_user_id=user.id,
            ip_address=self._client_host(request),
            user_agent=request.headers.get("user-agent"),
        )
        authenticated_session = self._create_session(user, request)
        self.db.commit()
        return authenticated_session

    def sign_in(self, *, email: str, password: str, request: Request) -> AuthenticatedSession:
        user = self.db.scalar(select(User).where(User.email == email.lower(), User.is_active))
        if user is None or not verify_password(password, user.password_hash):
            AuditService(self.db).record(
                "authentication.failed",
                ip_address=self._client_host(request),
                user_agent=request.headers.get("user-agent"),
                details={"email": email.lower()},
            )
            self.db.commit()
            raise AuthenticationFailedError()
        authenticated_session = self._create_session(user, request)
        AuditService(self.db).record(
            "authentication.signed_in",
            actor_user_id=user.id,
            ip_address=self._client_host(request),
            user_agent=request.headers.get("user-agent"),
        )
        self.db.commit()
        return authenticated_session

    def sign_out(self, cookie_value: str | None, request: Request) -> None:
        if not cookie_value:
            return
        try:
            raw_token = unsign_session_cookie(cookie_value, self.settings)
            session = self._get_valid_session(raw_token)
        except InvalidSessionError:
            return
        session.revoked_at = datetime.now(UTC)
        AuditService(self.db).record(
            "authentication.signed_out",
            actor_user_id=session.user_id,
            ip_address=self._client_host(request),
            user_agent=request.headers.get("user-agent"),
        )
        self.db.commit()

    def current_user_from_cookie(self, cookie_value: str | None) -> User:
        if not cookie_value:
            raise NotAuthenticatedError()
        raw_token = unsign_session_cookie(cookie_value, self.settings)
        session = self._get_valid_session(raw_token)
        user = self.db.get(User, session.user_id)
        if user is None or not user.is_active:
            raise InvalidSessionError()
        return user

    def _create_session(self, user: User, request: Request) -> AuthenticatedSession:
        raw_token = generate_session_token()
        expires_at = datetime.now(UTC) + timedelta(minutes=self.settings.session_ttl_minutes)
        self.db.add(
            Session(
                user_id=user.id,
                session_token_hash=hash_session_token(raw_token, self.settings),
                expires_at=expires_at,
                user_agent=request.headers.get("user-agent"),
                ip_address=self._client_host(request),
            )
        )
        self.db.flush()
        return AuthenticatedSession(user=user, raw_token=raw_token)

    def _get_valid_session(self, raw_token: str) -> Session:
        token_hash = hash_session_token(raw_token, self.settings)
        session = self.db.scalar(select(Session).where(Session.session_token_hash == token_hash))
        now = datetime.now(UTC)
        if session is None or session.revoked_at is not None or self._as_utc(session.expires_at) <= now:
            raise InvalidSessionError()
        return session

    @staticmethod
    def _client_host(request: Request) -> str | None:
        return request.client.host if request.client else None

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
