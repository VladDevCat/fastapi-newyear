import uuid
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, UploadFile, status
from starlette.background import BackgroundTask
from starlette.responses import Response, StreamingResponse

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
from app.modules.storage.schemas import FileResponseDTO
from app.modules.storage.service import StorageService
from app.modules.users.model import User

router = APIRouter(prefix="/files", tags=["Files"])


def get_storage_service(db=Depends(get_db)) -> StorageService:
    return StorageService(db)


@router.post(
    "",
    response_model=FileResponseDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a file",
    description="Uploads an avatar image to MinIO using a file stream and stores metadata in MongoDB.",
    openapi_extra={"security": [{"cookieAuth": []}]},
    responses={
        201: {
            "description": "File uploaded",
            "content": {
                "application/json": {
                    "example": {
                        "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                        "original_name": "avatar.png",
                        "size": 128000,
                        "mimetype": "image/png",
                        "created_at": "2026-04-17T19:30:00Z",
                        "updated_at": "2026-04-17T19:30:00Z",
                    }
                }
            },
        },
        400: json_example(BAD_REQUEST_EXAMPLE),
        401: json_example(UNAUTHORIZED_EXAMPLE),
        500: json_example(INTERNAL_ERROR_EXAMPLE),
    },
)
def upload_file(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[StorageService, Depends(get_storage_service)],
    file: UploadFile = File(
        ...,
        description="Avatar image. Allowed MIME types: image/png, image/jpeg, image/jpg.",
    ),
):
    file_record = service.upload_user_file(file, current_user)
    return service.to_response(file_record)


@router.get(
    "/{file_id}",
    status_code=status.HTTP_200_OK,
    summary="Download a file",
    description="Streams a file from MinIO. Only the owner can download it.",
    openapi_extra={"security": [{"cookieAuth": []}]},
    responses={
        200: {
            "description": "File stream",
            "content": {
                "image/png": {},
                "image/jpeg": {},
            },
        },
        401: json_example(UNAUTHORIZED_EXAMPLE),
        403: json_example(FORBIDDEN_EXAMPLE),
        404: json_example(NOT_FOUND_EXAMPLE),
        500: json_example(INTERNAL_ERROR_EXAMPLE),
    },
)
def download_file(
    file_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[StorageService, Depends(get_storage_service)],
):
    file_record = service.get_owned_file(file_id, current_user)
    minio_response = service.getFileStream(file_record.object_key)
    disposition_name = quote(file_record.original_name)

    return StreamingResponse(
        minio_response.stream(32 * 1024),
        media_type=file_record.mimetype,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{disposition_name}",
            "Content-Length": str(file_record.size),
        },
        background=BackgroundTask(
            lambda: (minio_response.close(), minio_response.release_conn())
        ),
    )


@router.delete(
    "/{file_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a file",
    description="Soft deletes file metadata and removes the object from MinIO. Only the owner can delete it.",
    openapi_extra={"security": [{"cookieAuth": []}]},
    responses={
        204: {"description": "File deleted"},
        401: json_example(UNAUTHORIZED_EXAMPLE),
        403: json_example(FORBIDDEN_EXAMPLE),
        404: json_example(NOT_FOUND_EXAMPLE),
        500: json_example(INTERNAL_ERROR_EXAMPLE),
    },
)
def delete_file(
    file_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[StorageService, Depends(get_storage_service)],
):
    service.delete_owned_file(file_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
