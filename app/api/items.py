import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import get_current_user, get_item_service
from app.models.user import User
from app.schemas.item import (
    ItemCreateDTO,
    ItemListResponseDTO,
    ItemPatchDTO,
    ItemResponseDTO,
    ItemUpdateDTO,
    PaginationDTO,
)
from app.services.item_service import ItemService

router = APIRouter(prefix="/items", tags=["items"])


@router.get("", response_model=ItemListResponseDTO, status_code=status.HTTP_200_OK)
def list_items(
    pagination: Annotated[PaginationDTO, Depends()],
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ItemService, Depends(get_item_service)],
):
    return service.list_items(pagination, current_user)


@router.get("/{item_id}", response_model=ItemResponseDTO, status_code=status.HTTP_200_OK)
def get_item(
    item_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ItemService, Depends(get_item_service)],
):
    return service.get_item(item_id, current_user)


@router.post("", response_model=ItemResponseDTO, status_code=status.HTTP_201_CREATED)
def create_item(
    payload: ItemCreateDTO,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ItemService, Depends(get_item_service)],
):
    return service.create_item(payload, current_user)


@router.put("/{item_id}", response_model=ItemResponseDTO, status_code=status.HTTP_200_OK)
def put_item(
    item_id: uuid.UUID,
    payload: ItemUpdateDTO,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ItemService, Depends(get_item_service)],
):
    return service.put_item(item_id, payload, current_user)


@router.patch("/{item_id}", response_model=ItemResponseDTO, status_code=status.HTTP_200_OK)
def patch_item(
    item_id: uuid.UUID,
    payload: ItemPatchDTO,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ItemService, Depends(get_item_service)],
):
    return service.patch_item(item_id, payload, current_user)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(
    item_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ItemService, Depends(get_item_service)],
):
    service.delete_item(item_id, current_user)