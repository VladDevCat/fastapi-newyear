from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.common.db import get_db
from app.common.web.openapi import (
    BAD_REQUEST_EXAMPLE,
    FORBIDDEN_EXAMPLE,
    INTERNAL_ERROR_EXAMPLE,
    NOT_FOUND_EXAMPLE,
    UNAUTHORIZED_EXAMPLE,
    json_example,
)
from app.modules.auth.dependencies import get_current_user
from app.modules.storage.schemas import ProfileResponseDTO, ProfileUpdateDTO
from app.modules.storage.service import ProfileService
from app.modules.users.model import User

router = APIRouter(prefix="/profile", tags=["Profile"])


def get_profile_service(db=Depends(get_db)) -> ProfileService:
    return ProfileService(db)


@router.get(
    "",
    response_model=ProfileResponseDTO,
    status_code=status.HTTP_200_OK,
    summary="Get current profile",
    openapi_extra={"security": [{"cookieAuth": []}]},
    responses={
        200: {"description": "Current profile"},
        401: json_example(UNAUTHORIZED_EXAMPLE),
        404: json_example(NOT_FOUND_EXAMPLE),
        500: json_example(INTERNAL_ERROR_EXAMPLE),
    },
)
def get_profile(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ProfileService, Depends(get_profile_service)],
):
    return service.get_profile(current_user)


@router.post(
    "",
    response_model=ProfileResponseDTO,
    status_code=status.HTTP_200_OK,
    summary="Update current profile",
    description="Updates display_name, bio and avatar_file_id. The avatar file must belong to current user.",
    openapi_extra={"security": [{"cookieAuth": []}]},
    responses={
        200: {"description": "Profile updated"},
        400: json_example(BAD_REQUEST_EXAMPLE),
        401: json_example(UNAUTHORIZED_EXAMPLE),
        403: json_example(FORBIDDEN_EXAMPLE),
        404: json_example(NOT_FOUND_EXAMPLE),
        500: json_example(INTERNAL_ERROR_EXAMPLE),
    },
)
def update_profile(
    payload: ProfileUpdateDTO,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ProfileService, Depends(get_profile_service)],
):
    return service.update_profile(payload, current_user)
