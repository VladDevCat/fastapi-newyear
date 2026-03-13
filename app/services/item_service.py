import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictException, ForbiddenException, NotFoundException
from app.models.user import User
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

    def list_items(self, pagination: PaginationDTO, current_user: User) -> ItemListResponseDTO:
        offset = (pagination.page - 1) * pagination.limit
        items, total = self.repo.list_active_by_owner(
            owner_id=current_user.id,
            offset=offset,
            limit=pagination.limit,
        )
        return ItemListResponseDTO.build(
            items=items,
            page=pagination.page,
            limit=pagination.limit,
            total_items=total,
        )

    def get_item(self, item_id: uuid.UUID, current_user: User) -> ItemResponseDTO:
        item = self.repo.get_active_by_id(item_id)
        if item is None:
            raise NotFoundException("Item not found")

        if item.owner_id != current_user.id:
            raise ForbiddenException("You do not have access to this item")

        return ItemResponseDTO.model_validate(item)

    def create_item(self, payload: ItemCreateDTO, current_user: User) -> ItemResponseDTO:
        existing = self.repo.get_active_by_title_for_owner(
            title=payload.title,
            owner_id=current_user.id,
        )
        if existing is not None:
            raise ConflictException("You already have an active item with this title")

        item = self.repo.create(
            {
                **payload.model_dump(),
                "owner_id": current_user.id,
            }
        )
        self.db.commit()
        return ItemResponseDTO.model_validate(item)

    def put_item(
        self,
        item_id: uuid.UUID,
        payload: ItemUpdateDTO,
        current_user: User,
    ) -> ItemResponseDTO:
        item = self.repo.get_active_by_id(item_id)
        if item is None:
            raise NotFoundException("Item not found")

        if item.owner_id != current_user.id:
            raise ForbiddenException("You do not have access to this item")

        duplicate = self.repo.get_active_by_title_for_owner(
            title=payload.title,
            owner_id=current_user.id,
            exclude_id=item_id,
        )
        if duplicate is not None:
            raise ConflictException("You already have an active item with this title")

        updated = self.repo.update(item, payload.model_dump())
        self.db.commit()
        return ItemResponseDTO.model_validate(updated)

    def patch_item(
        self,
        item_id: uuid.UUID,
        payload: ItemPatchDTO,
        current_user: User,
    ) -> ItemResponseDTO:
        item = self.repo.get_active_by_id(item_id)
        if item is None:
            raise NotFoundException("Item not found")

        if item.owner_id != current_user.id:
            raise ForbiddenException("You do not have access to this item")

        patch_data = payload.model_dump(exclude_unset=True)

        if "title" in patch_data:
            duplicate = self.repo.get_active_by_title_for_owner(
                title=patch_data["title"],
                owner_id=current_user.id,
                exclude_id=item_id,
            )
            if duplicate is not None:
                raise ConflictException("You already have an active item with this title")

        updated = self.repo.update(item, patch_data)
        self.db.commit()
        return ItemResponseDTO.model_validate(updated)

    def delete_item(self, item_id: uuid.UUID, current_user: User) -> None:
        item = self.repo.get_active_by_id(item_id)
        if item is None:
            raise NotFoundException("Item not found")

        if item.owner_id != current_user.id:
            raise ForbiddenException("You do not have access to this item")

        self.repo.soft_delete(item)
        self.db.commit()