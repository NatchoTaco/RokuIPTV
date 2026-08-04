from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from streamforge_api.api.deps import get_current_user, get_db, get_settings
from streamforge_api.core.config import Settings
from streamforge_api.core.security import sign_session_cookie
from streamforge_api.models import User
from streamforge_api.schemas.auth import AuthResponse, BootstrapAdminRequest, SignInRequest, UserPublic
from streamforge_api.schemas.common import MessageResponse
from streamforge_api.services.auth import AuthService
from streamforge_api.services.setup import SetupService

router = APIRouter()


@router.post("/bootstrap-admin", response_model=AuthResponse, status_code=201)
def bootstrap_admin(
    payload: BootstrapAdminRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AuthResponse:
    authenticated_session = AuthService(db, settings).bootstrap_admin(
        email=payload.email,
        password=payload.password,
        display_name=payload.display_name,
        request=request,
    )
    _set_session_cookie(response, authenticated_session.raw_token, settings)
    return AuthResponse(
        user=UserPublic.model_validate(authenticated_session.user),
        setup=SetupService(db).to_response(),
    )


@router.post("/sign-in", response_model=AuthResponse)
def sign_in(
    payload: SignInRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AuthResponse:
    authenticated_session = AuthService(db, settings).sign_in(
        email=payload.email,
        password=payload.password,
        request=request,
    )
    _set_session_cookie(response, authenticated_session.raw_token, settings)
    return AuthResponse(
        user=UserPublic.model_validate(authenticated_session.user),
        setup=SetupService(db).to_response(),
    )


@router.post("/sign-out", response_model=MessageResponse)
def sign_out(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> MessageResponse:
    AuthService(db, settings).sign_out(request.cookies.get(settings.cookie_name), request)
    response.delete_cookie(settings.cookie_name, path="/")
    return MessageResponse(message="Signed out.")


@router.get("/me", response_model=UserPublic)
def me(current_user: User = Depends(get_current_user)) -> UserPublic:
    return UserPublic.model_validate(current_user)


def _set_session_cookie(response: Response, raw_token: str, settings: Settings) -> None:
    response.set_cookie(
        key=settings.cookie_name,
        value=sign_session_cookie(raw_token, settings),
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.session_ttl_minutes * 60,
        path="/",
    )
