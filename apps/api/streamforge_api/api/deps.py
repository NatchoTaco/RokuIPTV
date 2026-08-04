from collections.abc import Generator
from typing import cast

from fastapi import Depends, Request
from sqlalchemy.orm import Session, sessionmaker

from streamforge_api.core.config import Settings
from streamforge_api.core.errors import AuthorizationError, StreamForgeError
from streamforge_api.models import User
from streamforge_api.services.auth import AuthService


def get_settings(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


def get_db(request: Request) -> Generator[Session]:
    session_factory = cast("sessionmaker[Session]", request.app.state.db_session_factory)
    db: Session = session_factory()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> User:
    try:
        return AuthService(db, settings).current_user_from_cookie(
            request.cookies.get(settings.cookie_name)
        )
    except StreamForgeError:
        raise


def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise AuthorizationError()
    return current_user
