import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import RedirectResponse

from app.api.deps import AuthContext, get_auth_service, get_current_auth
from app.core.config import settings
from app.core.cookies import REFRESH_COOKIE_NAME, clear_auth_cookies, set_auth_cookies
from app.core.exceptions import UnauthorizedException
from app.schemas.auth import (
    AuthResponseDTO,
    ForgotPasswordDTO,
    ForgotPasswordResponseDTO,
    LoginDTO,
    MessageDTO,
    RegisterDTO,
    ResetPasswordDTO,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponseDTO, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterDTO,
    response: Response,
    service: Annotated[AuthService, Depends(get_auth_service)],
):
    result = service.register(payload)
    set_auth_cookies(response, result.access_token, result.refresh_token)
    return {"user": result.user}


@router.post("/login", response_model=AuthResponseDTO, status_code=status.HTTP_200_OK)
def login(
    payload: LoginDTO,
    response: Response,
    service: Annotated[AuthService, Depends(get_auth_service)],
):
    result = service.login(payload)
    set_auth_cookies(response, result.access_token, result.refresh_token)
    return {"user": result.user}


@router.post("/refresh", response_model=AuthResponseDTO, status_code=status.HTTP_200_OK)
def refresh_session(
    request: Request,
    response: Response,
    service: Annotated[AuthService, Depends(get_auth_service)],
):
    refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if not refresh_token:
        raise UnauthorizedException("Missing refresh token")

    result = service.refresh_session(refresh_token)
    set_auth_cookies(response, result.access_token, result.refresh_token)
    return {"user": result.user}


@router.get("/whoami", response_model=AuthResponseDTO, status_code=status.HTTP_200_OK)
def whoami(
    auth: Annotated[AuthContext, Depends(get_current_auth)],
):
    return {"user": auth.user}


@router.post("/logout", response_model=MessageDTO, status_code=status.HTTP_200_OK)
def logout(
    response: Response,
    auth: Annotated[AuthContext, Depends(get_current_auth)],
    service: Annotated[AuthService, Depends(get_auth_service)],
):
    try:
        session_id = uuid.UUID(auth.payload["sid"])
    except (KeyError, ValueError):
        raise UnauthorizedException("Invalid access token payload")

    service.logout_current_session(session_id)
    clear_auth_cookies(response)
    return {"message": "Logged out successfully"}


@router.post("/logout-all", response_model=MessageDTO, status_code=status.HTTP_200_OK)
def logout_all(
    response: Response,
    auth: Annotated[AuthContext, Depends(get_current_auth)],
    service: Annotated[AuthService, Depends(get_auth_service)],
):
    service.logout_all_sessions(auth.user.id)
    clear_auth_cookies(response)
    return {"message": "All sessions logged out successfully"}


@router.post(
    "/forgot-password",
    response_model=ForgotPasswordResponseDTO,
    status_code=status.HTTP_200_OK,
)
def forgot_password(
    payload: ForgotPasswordDTO,
    service: Annotated[AuthService, Depends(get_auth_service)],
):
    return service.forgot_password(payload)


@router.post("/reset-password", response_model=MessageDTO, status_code=status.HTTP_200_OK)
def reset_password(
    payload: ResetPasswordDTO,
    service: Annotated[AuthService, Depends(get_auth_service)],
):
    service.reset_password(payload)
    return {"message": "Password has been reset successfully"}


@router.get("/oauth/{provider}", status_code=status.HTTP_302_FOUND)
def oauth_redirect(
    provider: str,
    service: Annotated[AuthService, Depends(get_auth_service)],
):
    redirect_url = service.get_oauth_redirect_url(provider)
    return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)


@router.get("/oauth/{provider}/callback", status_code=status.HTTP_302_FOUND)
def oauth_callback(
    provider: str,
    code: str,
    state: str,
    service: Annotated[AuthService, Depends(get_auth_service)],
):
    if provider != "yandex":
        raise UnauthorizedException("Unsupported OAuth provider")

    result = service.handle_yandex_callback(code, state)

    response = RedirectResponse(
        url=settings.FRONTEND_REDIRECT_URL,
        status_code=status.HTTP_302_FOUND,
    )
    set_auth_cookies(response, result.access_token, result.refresh_token)
    return response