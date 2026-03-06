import uuid
from datetime import datetime
from math import ceil

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.item import ItemStatus


class ItemCreateDTO(BaseModel):
    title: str = Field(..., min_length=3, max_length=150)
    description: str = Field(..., min_length=3, max_length=1000)
    status: ItemStatus = ItemStatus.planned


class ItemUpdateDTO(BaseModel):
    title: str = Field(..., min_length=3, max_length=150)
    description: str = Field(..., min_length=3, max_length=1000)
    status: ItemStatus


class ItemPatchDTO(BaseModel):
    title: str | None = Field(None, min_length=3, max_length=150)
    description: str | None = Field(None, min_length=3, max_length=1000)
    status: ItemStatus | None = None

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_not_empty(self):
        if self.title is None and self.description is None and self.status is None:
            raise ValueError("At least one field must be provided")
        return self


class PaginationDTO(BaseModel):
    page: int = Field(1, gt=0)
    limit: int = Field(10, ge=1, le=100)


class ItemResponseDTO(BaseModel):
    id: uuid.UUID
    title: str
    description: str
    status: ItemStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginationMetaDTO(BaseModel):
    page: int
    limit: int
    total_items: int
    total_pages: int


class ItemListResponseDTO(BaseModel):
    meta: PaginationMetaDTO
    items: list[ItemResponseDTO]

    @staticmethod
    def build(items: list, page: int, limit: int, total_items: int):
        total_pages = ceil(total_items / limit) if total_items > 0 else 0
        return ItemListResponseDTO(
            meta=PaginationMetaDTO(
                page=page,
                limit=limit,
                total_items=total_items,
                total_pages=total_pages,
            ),
            items=[ItemResponseDTO.model_validate(item) for item in items],
        )