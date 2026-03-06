import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.api.deps import get_item_service
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
    service: Annotated[ItemService, Depends(get_item_service)],
):
    return service.list_items(pagination)


@router.get("/{item_id}", response_model=ItemResponseDTO, status_code=status.HTTP_200_OK)
def get_item(
    item_id: uuid.UUID,
    service: Annotated[ItemService, Depends(get_item_service)],
):
    return service.get_item(item_id)


@router.post("", response_model=ItemResponseDTO, status_code=status.HTTP_201_CREATED)
def create_item(
    payload: ItemCreateDTO,
    service: Annotated[ItemService, Depends(get_item_service)],
):
    return service.create_item(payload)


@router.put("/{item_id}", response_model=ItemResponseDTO, status_code=status.HTTP_200_OK)
def put_item(
    item_id: uuid.UUID,
    payload: ItemUpdateDTO,
    service: Annotated[ItemService, Depends(get_item_service)],
):
    return service.put_item(item_id, payload)


@router.patch("/{item_id}", response_model=ItemResponseDTO, status_code=status.HTTP_200_OK)
def patch_item(
    item_id: uuid.UUID,
    payload: ItemPatchDTO,
    service: Annotated[ItemService, Depends(get_item_service)],
):
    return service.patch_item(item_id, payload)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(
    item_id: uuid.UUID,
    service: Annotated[ItemService, Depends(get_item_service)],
):
    service.delete_item(item_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)