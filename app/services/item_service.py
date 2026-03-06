import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictException, NotFoundException
from app.repositories.item_repository import ItemRepository
from app.schemas.item import (
    ItemCreateDTO,
    ItemListResponseDTO,
    ItemPatchDTO,
    ItemResponseDTO,
    ItemUpdateDTO,
    PaginationDTO,
)


class ItemService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ItemRepository(db)

    def list_items(self, pagination: PaginationDTO) -> ItemListResponseDTO:
        offset = (pagination.page - 1) * pagination.limit
        items, total = self.repo.list_active(offset=offset, limit=pagination.limit)
        return ItemListResponseDTO.build(
            items=items,
            page=pagination.page,
            limit=pagination.limit,
            total_items=total,
        )

    def get_item(self, item_id: uuid.UUID) -> ItemResponseDTO:
        item = self.repo.get_active_by_id(item_id)
        if item is None:
            raise NotFoundException("Item not found")
        return ItemResponseDTO.model_validate(item)

    def create_item(self, payload: ItemCreateDTO) -> ItemResponseDTO:
        existing = self.repo.get_active_by_title(payload.title)
        if existing is not None:
            raise ConflictException("Active item with this title already exists")

        item = self.repo.create(payload.model_dump())
        self.db.commit()
        return ItemResponseDTO.model_validate(item)

    def put_item(self, item_id: uuid.UUID, payload: ItemUpdateDTO) -> ItemResponseDTO:
        item = self.repo.get_active_by_id(item_id)
        if item is None:
            raise NotFoundException("Item not found")

        duplicate = self.repo.get_active_by_title(payload.title, exclude_id=item_id)
        if duplicate is not None:
            raise ConflictException("Active item with this title already exists")

        updated = self.repo.update(item, payload.model_dump())
        self.db.commit()
        return ItemResponseDTO.model_validate(updated)

    def patch_item(self, item_id: uuid.UUID, payload: ItemPatchDTO) -> ItemResponseDTO:
        item = self.repo.get_active_by_id(item_id)
        if item is None:
            raise NotFoundException("Item not found")

        patch_data = payload.model_dump(exclude_unset=True)

        if "title" in patch_data:
            duplicate = self.repo.get_active_by_title(
                patch_data["title"],
                exclude_id=item_id,
            )
            if duplicate is not None:
                raise ConflictException("Active item with this title already exists")

        updated = self.repo.update(item, patch_data)
        self.db.commit()
        return ItemResponseDTO.model_validate(updated)

    def delete_item(self, item_id: uuid.UUID) -> None:
        item = self.repo.get_active_by_id(item_id)
        if item is None:
            raise NotFoundException("Item not found")

        self.repo.soft_delete(item)
        self.db.commit()