import uuid
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
from app.modules.items.schemas import (
    ItemCreateDTO,
    ItemListResponseDTO,
    ItemPatchDTO,
    ItemResponseDTO,
    ItemUpdateDTO,
    PaginationDTO,
)
from app.modules.items.service import ItemService
from app.modules.users.model import User

router = APIRouter(prefix="/items", tags=["Items"])


def get_item_service(db=Depends(get_db)) -> ItemService:
    return ItemService(db)


@router.get(
    "",
    response_model=ItemListResponseDTO,
    status_code=status.HTTP_200_OK,
    summary="Получить список активных элементов",
    description="Возвращает только активные элементы текущего пользователя с пагинацией.",
    openapi_extra={"security": [{"cookieAuth": []}, {"bearerAuth": []}]},
    responses={
        200: {
            "description": "Список элементов с мета-информацией пагинации",
            "content": {
                "application/json": {
                    "example": {
                        "meta": {
                            "page": 1,
                            "limit": 10,
                            "total_items": 1,
                            "total_pages": 1,
                        },
                        "items": [
                            {
                                "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                                "title": "Купить гирлянду",
                                "description": "Тёплый белый свет",
                                "status": "planned",
                                "created_at": "2026-03-06T18:08:03.739Z",
                                "updated_at": "2026-03-06T18:08:03.739Z",
                            }
                        ],
                    }
                }
            },
        },
        400: json_example(BAD_REQUEST_EXAMPLE),
        401: json_example(UNAUTHORIZED_EXAMPLE),
        500: json_example(INTERNAL_ERROR_EXAMPLE),
    },
)
def list_items(
    pagination: Annotated[PaginationDTO, Depends()],
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ItemService, Depends(get_item_service)],
):
    return service.list_items(pagination, current_user)


@router.get(
    "/{item_id}",
    response_model=ItemResponseDTO,
    status_code=status.HTTP_200_OK,
    summary="Получить активный элемент по ID",
    description="Возвращает один активный элемент текущего пользователя.",
    openapi_extra={"security": [{"cookieAuth": []}, {"bearerAuth": []}]},
    responses={
        200: {
            "description": "Элемент найден",
            "content": {
                "application/json": {
                    "example": {
                        "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                        "title": "Купить гирлянду",
                        "description": "Тёплый белый свет",
                        "status": "planned",
                        "created_at": "2026-03-06T18:08:03.739Z",
                        "updated_at": "2026-03-06T18:08:03.739Z",
                    }
                }
            },
        },
        401: json_example(UNAUTHORIZED_EXAMPLE),
        403: json_example(FORBIDDEN_EXAMPLE),
        404: json_example(NOT_FOUND_EXAMPLE),
        500: json_example(INTERNAL_ERROR_EXAMPLE),
    },
)
def get_item(
    item_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ItemService, Depends(get_item_service)],
):
    return service.get_item(item_id, current_user)


@router.post(
    "",
    response_model=ItemResponseDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Создать новый элемент",
    description="Создаёт новый элемент для текущего пользователя.",
    openapi_extra={"security": [{"cookieAuth": []}, {"bearerAuth": []}]},
    responses={
        201: {
            "description": "Элемент успешно создан",
            "content": {
                "application/json": {
                    "example": {
                        "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                        "title": "Купить гирлянду",
                        "description": "Тёплый белый свет",
                        "status": "planned",
                        "created_at": "2026-03-06T18:08:03.739Z",
                        "updated_at": "2026-03-06T18:08:03.739Z",
                    }
                }
            },
        },
        400: json_example(BAD_REQUEST_EXAMPLE),
        401: json_example(UNAUTHORIZED_EXAMPLE),
        409: json_example({"detail": "You already have an active item with this title"}),
        500: json_example(INTERNAL_ERROR_EXAMPLE),
    },
)
def create_item(
    payload: ItemCreateDTO,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ItemService, Depends(get_item_service)],
):
    return service.create_item(payload, current_user)


@router.put(
    "/{item_id}",
    response_model=ItemResponseDTO,
    status_code=status.HTTP_200_OK,
    summary="Полностью обновить элемент",
    description="Полностью заменяет содержимое элемента текущего пользователя.",
    openapi_extra={"security": [{"cookieAuth": []}, {"bearerAuth": []}]},
    responses={
        200: {"description": "Элемент успешно обновлён"},
        400: json_example(BAD_REQUEST_EXAMPLE),
        401: json_example(UNAUTHORIZED_EXAMPLE),
        403: json_example(FORBIDDEN_EXAMPLE),
        404: json_example(NOT_FOUND_EXAMPLE),
        409: json_example({"detail": "You already have an active item with this title"}),
        500: json_example(INTERNAL_ERROR_EXAMPLE),
    },
)
def put_item(
    item_id: uuid.UUID,
    payload: ItemUpdateDTO,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ItemService, Depends(get_item_service)],
):
    return service.put_item(item_id, payload, current_user)


@router.patch(
    "/{item_id}",
    response_model=ItemResponseDTO,
    status_code=status.HTTP_200_OK,
    summary="Частично обновить элемент",
    description="Изменяет только переданные поля элемента текущего пользователя.",
    openapi_extra={"security": [{"cookieAuth": []}, {"bearerAuth": []}]},
    responses={
        200: {"description": "Элемент успешно обновлён"},
        400: json_example(BAD_REQUEST_EXAMPLE),
        401: json_example(UNAUTHORIZED_EXAMPLE),
        403: json_example(FORBIDDEN_EXAMPLE),
        404: json_example(NOT_FOUND_EXAMPLE),
        409: json_example({"detail": "You already have an active item with this title"}),
        500: json_example(INTERNAL_ERROR_EXAMPLE),
    },
)
def patch_item(
    item_id: uuid.UUID,
    payload: ItemPatchDTO,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ItemService, Depends(get_item_service)],
):
    return service.patch_item(item_id, payload, current_user)


@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Мягко удалить элемент",
    description="Помечает элемент как удалённый, не удаляя строку физически из базы данных.",
    openapi_extra={"security": [{"cookieAuth": []}, {"bearerAuth": []}]},
    responses={
        204: {"description": "Элемент успешно помечен как удалённый"},
        401: json_example(UNAUTHORIZED_EXAMPLE),
        403: json_example(FORBIDDEN_EXAMPLE),
        404: json_example(NOT_FOUND_EXAMPLE),
        500: json_example(INTERNAL_ERROR_EXAMPLE),
    },
)
def delete_item(
    item_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ItemService, Depends(get_item_service)],
):
    service.delete_item(item_id, current_user)
