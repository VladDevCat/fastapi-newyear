from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.common.security.cookies import set_auth_cookies
from app.modules.auth.dependencies import get_auth_service
from app.modules.auth.schemas import AuthResponseDTO, RegisterDTO
from app.modules.auth.service import AuthService

router = APIRouter(prefix="/users", tags=["Users"])


@router.post(
    "",
    response_model=AuthResponseDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Create user",
    description="Lab 9 alias for registration. Creates a local user, publishes user.registered, and sets auth cookies.",
)
def create_user(
    payload: RegisterDTO,
    response: Response,
    service: Annotated[AuthService, Depends(get_auth_service)],
):
    result = service.register(payload)
    set_auth_cookies(response, result.access_token, result.refresh_token)
    return {"user": result.user}
