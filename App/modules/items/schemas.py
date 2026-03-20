import uuid
from datetime import datetime
from math import ceil

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.items.model import ItemStatus


class ItemCreateDTO(BaseModel):
    title: str = Field(
        ...,
        min_length=3,
        max_length=150,
        description="Название элемента подготовки",
        examples=["Купить гирлянду"],
    )
    description: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="Описание элемента",
        examples=["Тёплый белый свет для ёлки"],
    )
    status: ItemStatus = Field(
        default=ItemStatus.planned,
        description="Текущий статус элемента",
        examples=["planned"],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Купить гирлянду",
                "description": "Тёплый белый свет для ёлки",
                "status": "planned",
            }
        }
    )


class ItemUpdateDTO(BaseModel):
    title: str = Field(..., min_length=3, max_length=150, description="Новое название элемента", examples=["Купить гирлянду"])
    description: str = Field(..., min_length=3, max_length=1000, description="Новое описание элемента", examples=["Тёплый белый свет"])
    status: ItemStatus = Field(..., description="Новый статус элемента", examples=["purchased"])

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Купить гирлянду",
                "description": "Тёплый белый свет",
                "status": "purchased",
            }
        }
    )


class ItemPatchDTO(BaseModel):
    title: str | None = Field(None, min_length=3, max_length=150, description="Новое название элемента")
    description: str | None = Field(None, min_length=3, max_length=1000, description="Новое описание элемента")
    status: ItemStatus | None = Field(None, description="Новый статус элемента")

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "status": "done"
            }
        },
    )

    @model_validator(mode="after")
    def validate_not_empty(self):
        if self.title is None and self.description is None and self.status is None:
            raise ValueError("At least one field must be provided")
        return self


class PaginationDTO(BaseModel):
    page: int = Field(1, gt=0, description="Номер страницы", examples=[1])
    limit: int = Field(10, ge=1, le=100, description="Размер страницы", examples=[10])


class ItemResponseDTO(BaseModel):
    id: uuid.UUID = Field(..., description="UUID ресурса", examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6"])
    title: str = Field(..., description="Название элемента", examples=["Купить гирлянду"])
    description: str = Field(..., description="Описание элемента", examples=["Тёплый белый свет"])
    status: ItemStatus = Field(..., description="Статус элемента", examples=["planned"])
    created_at: datetime = Field(..., description="Дата создания", examples=["2026-03-06T18:08:03.739Z"])
    updated_at: datetime = Field(..., description="Дата обновления", examples=["2026-03-06T18:08:03.739Z"])

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "title": "Купить гирлянду",
                "description": "Тёплый белый свет",
                "status": "planned",
                "created_at": "2026-03-06T18:08:03.739Z",
                "updated_at": "2026-03-06T18:08:03.739Z",
            }
        },
    )


class PaginationMetaDTO(BaseModel):
    page: int = Field(..., description="Текущая страница", examples=[1])
    limit: int = Field(..., description="Лимит элементов на странице", examples=[10])
    total_items: int = Field(..., description="Общее число элементов", examples=[25])
    total_pages: int = Field(..., description="Общее число страниц", examples=[3])


class ItemListResponseDTO(BaseModel):
    meta: PaginationMetaDTO
    items: list[ItemResponseDTO]

    model_config = ConfigDict(
        json_schema_extra={
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
    )

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
