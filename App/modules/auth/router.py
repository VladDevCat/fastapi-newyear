import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import RedirectResponse

from app.common.config import settings
from app.common.exceptions import UnauthorizedException
from app.common.security.cookies import REFRESH_COOKIE_NAME, clear_auth_cookies, set_auth_cookies
from app.common.web.openapi import (
    BAD_REQUEST_EXAMPLE,
    FORBIDDEN_EXAMPLE,
    INTERNAL_ERROR_EXAMPLE,
    NOT_FOUND_EXAMPLE,
    UNAUTHORIZED_EXAMPLE,
    json_example,
)
from app.modules.auth.dependencies import AuthContext, get_auth_service, get_current_auth
from app.modules.auth.schemas import (
    AuthResponseDTO,
    ForgotPasswordDTO,
    ForgotPasswordResponseDTO,
    LoginDTO,
    MessageDTO,
    RegisterDTO,
    ResetPasswordDTO,
)
from app.modules.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register",
    response_model=AuthResponseDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация нового пользователя",
    description="Создаёт пользователя, хеширует пароль, создаёт локальную сессию и устанавливает HttpOnly cookies.",
    responses={
        201: {
            "description": "Пользователь успешно зарегистрирован",
            "content": {
                "application/json": {
                    "example": {
                        "user": {
                            "id": "cf48ed93-fa37-49f7-b71b-04d8bf477e4f",
                            "email": "maria.test@example.com",
                            "phone": None,
                            "created_at": "2026-03-13T17:17:29.897877Z",
                        }
                    }
                }
            },
        },
        400: json_example(BAD_REQUEST_EXAMPLE, "Ошибка валидации тела запроса"),
        409: json_example({"detail": "User with this email already exists"}, "Email уже занят"),
        500: json_example(INTERNAL_ERROR_EXAMPLE, "Внутренняя ошибка сервера"),
    },
)
def register(
    payload: RegisterDTO,
    response: Response,
    service: Annotated[AuthService, Depends(get_auth_service)],
):
    result = service.register(payload)
    set_auth_cookies(response, result.access_token, result.refresh_token)
    return {"user": result.user}


@router.post(
    "/login",
    response_model=AuthResponseDTO,
    status_code=status.HTTP_200_OK,
    summary="Вход пользователя",
    description="Проверяет email и пароль, создаёт новую локальную сессию и устанавливает HttpOnly cookies.",
    responses={
        200: {
            "description": "Успешный вход",
            "content": {
                "application/json": {
                    "example": {
                        "user": {
                            "id": "cf48ed93-fa37-49f7-b71b-04d8bf477e4f",
                            "email": "maria.test@example.com",
                            "phone": None,
                            "created_at": "2026-03-13T17:17:29.897877Z",
                        }
                    }
                }
            },
        },
        400: json_example(BAD_REQUEST_EXAMPLE),
        401: json_example({"detail": "Invalid email or password"}),
        500: json_example(INTERNAL_ERROR_EXAMPLE),
    },
)
def login(
    payload: LoginDTO,
    response: Response,
    service: Annotated[AuthService, Depends(get_auth_service)],
):
    result = service.login(payload)
    set_auth_cookies(response, result.access_token, result.refresh_token)
    return {"user": result.user}


@router.post(
    "/refresh",
    response_model=AuthResponseDTO,
    status_code=status.HTTP_200_OK,
    summary="Обновление Access/Refresh токенов",
    description="Проверяет refresh token из cookies, отзывает старую сессию и выдаёт новую пару токенов.",
    responses={
        200: {
            "description": "Токены успешно обновлены",
            "content": {
                "application/json": {
                    "example": {
                        "user": {
                            "id": "cf48ed93-fa37-49f7-b71b-04d8bf477e4f",
                            "email": "maria.test@example.com",
                            "phone": None,
                            "created_at": "2026-03-13T17:17:29.897877Z",
                        }
                    }
                }
            },
        },
        401: json_example({"detail": "Missing refresh token"}),
        500: json_example(INTERNAL_ERROR_EXAMPLE),
    },
)
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


@router.get(
    "/whoami",
    response_model=AuthResponseDTO,
    status_code=status.HTTP_200_OK,
    summary="Получить профиль текущего пользователя",
    description="Проверяет текущую авторизованную сессию по access_token из HttpOnly cookie.",
    openapi_extra={"security": [{"cookieAuth": []}, {"bearerAuth": []}]},
    responses={
        200: {
            "description": "Профиль текущего пользователя",
            "content": {
                "application/json": {
                    "example": {
                        "user": {
                            "id": "cf48ed93-fa37-49f7-b71b-04d8bf477e4f",
                            "email": "user@example.com",
                            "phone": None,
                            "created_at": "2026-03-13T17:17:29.897877Z",
                        }
                    }
                }
            },
        },
        401: json_example(UNAUTHORIZED_EXAMPLE),
        500: json_example(INTERNAL_ERROR_EXAMPLE),
    },
)
def whoami(
    auth: Annotated[AuthContext, Depends(get_current_auth)],
):
    return {"user": auth.user}


@router.post(
    "/logout",
    response_model=MessageDTO,
    status_code=status.HTTP_200_OK,
    summary="Завершить текущую сессию",
    description="Отзывает текущую сессию по session_id из access token и очищает cookies.",
    openapi_extra={"security": [{"cookieAuth": []}, {"bearerAuth": []}]},
    responses={
        200: {
            "description": "Текущая сессия завершена",
            "content": {
                "application/json": {
                    "example": {"message": "Logged out successfully"}
                }
            },
        },
        401: json_example(UNAUTHORIZED_EXAMPLE),
        500: json_example(INTERNAL_ERROR_EXAMPLE),
    },
)
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


@router.post(
    "/logout-all",
    response_model=MessageDTO,
    status_code=status.HTTP_200_OK,
    summary="Завершить все сессии пользователя",
    description="Отзывает все активные сессии пользователя и очищает cookies текущего браузера.",
    openapi_extra={"security": [{"cookieAuth": []}, {"bearerAuth": []}]},
    responses={
        200: {
            "description": "Все сессии завершены",
            "content": {
                "application/json": {
                    "example": {"message": "All sessions logged out successfully"}
                }
            },
        },
        401: json_example(UNAUTHORIZED_EXAMPLE),
        500: json_example(INTERNAL_ERROR_EXAMPLE),
    },
)
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
    summary="Запрос на сброс пароля",
    description="Создаёт reset token и, в отладочном режиме, может вернуть его в ответе.",
    responses={
        200: {
            "description": "Запрос обработан",
            "content": {
                "application/json": {
                    "example": {
                        "message": "If the account exists, a reset instruction has been generated",
                        "reset_token": None,
                    }
                }
            },
        },
        400: json_example(BAD_REQUEST_EXAMPLE),
        500: json_example(INTERNAL_ERROR_EXAMPLE),
    },
)
def forgot_password(
    payload: ForgotPasswordDTO,
    service: Annotated[AuthService, Depends(get_auth_service)],
):
    return service.forgot_password(payload)


@router.post(
    "/reset-password",
    response_model=MessageDTO,
    status_code=status.HTTP_200_OK,
    summary="Установить новый пароль",
    description="Проверяет reset token, обновляет пароль пользователя и отзывает все активные сессии.",
    responses={
        200: {
            "description": "Пароль успешно изменён",
            "content": {
                "application/json": {
                    "example": {"message": "Password has been reset successfully"}
                }
            },
        },
        400: json_example(BAD_REQUEST_EXAMPLE),
        401: json_example({"detail": "Invalid or expired reset token"}),
        404: json_example({"detail": "User not found"}),
        500: json_example(INTERNAL_ERROR_EXAMPLE),
    },
)
def reset_password(
    payload: ResetPasswordDTO,
    service: Annotated[AuthService, Depends(get_auth_service)],
):
    service.reset_password(payload)
    return {"message": "Password has been reset successfully"}


@router.get(
    "/oauth/{provider}",
    status_code=status.HTTP_302_FOUND,
    summary="Инициация OAuth-входа",
    description="Формирует state и перенаправляет пользователя на Yandex OAuth Authorization Code flow.",
    responses={
        302: {"description": "Редирект на OAuth-провайдера"},
        404: json_example({"detail": "OAuth provider not supported"}),
        500: json_example(INTERNAL_ERROR_EXAMPLE),
    },
)
def oauth_redirect(
    provider: str,
    service: Annotated[AuthService, Depends(get_auth_service)],
):
    redirect_url = service.get_oauth_redirect_url(provider)
    return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)


@router.get(
    "/oauth/{provider}/callback",
    status_code=status.HTTP_302_FOUND,
    summary="OAuth callback",
    description="Обрабатывает callback от Yandex: проверяет state, получает профиль и создаёт локальную сессию.",
    responses={
        302: {"description": "Редирект обратно в приложение после успешного входа"},
        401: json_example({"detail": "Invalid or expired OAuth state"}),
        404: json_example({"detail": "OAuth provider not supported"}),
        500: json_example(INTERNAL_ERROR_EXAMPLE),
    },
)
def oauth_callback(
    provider: str,
    code: str,
    state: str,
    service: Annotated[AuthService, Depends(get_auth_service)],
):
    result = service.handle_oauth_callback(provider, code, state)

    response = RedirectResponse(
        url=settings.FRONTEND_REDIRECT_URL,
        status_code=status.HTTP_302_FOUND,
    )
    set_auth_cookies(response, result.access_token, result.refresh_token)
    return response
