import uuid

from app.common.cache import cache
from app.common.config import settings
from app.common.exceptions import ConflictException, ForbiddenException, NotFoundException
from app.modules.items.repository import ItemRepository
from app.modules.items.schemas import (
    ItemCreateDTO,
    ItemListResponseDTO,
    ItemPatchDTO,
    ItemResponseDTO,
    ItemUpdateDTO,
    PaginationDTO,
)
from app.modules.users.model import User


class ItemService:
    def __init__(self, db):
        self.db = db
        self.repo = ItemRepository(db)

    def _list_cache_key(self, user_id: uuid.UUID, page: int, limit: int) -> str:
        return cache.key("items", "list", "user", user_id, "page", page, "limit", limit)

    def _item_cache_key(self, user_id: uuid.UUID, item_id: uuid.UUID) -> str:
        return cache.key("items", "entity", "user", user_id, item_id)

    def _invalidate_user_items_cache(self, user_id: uuid.UUID) -> None:
        cache.delByPattern(cache.key("items", "list", "user", user_id, "*"))

    def _invalidate_item_cache(self, item_id: uuid.UUID) -> None:
        cache.delByPattern(cache.key("items", "entity", "user", "*", item_id))

    def list_items(self, pagination: PaginationDTO, current_user: User) -> ItemListResponseDTO:
        cache_key = self._list_cache_key(current_user.id, pagination.page, pagination.limit)
        cached = cache.get(cache_key)
        if cached is not None:
            return ItemListResponseDTO.model_validate(cached)

        offset = (pagination.page - 1) * pagination.limit
        items, total = self.repo.list_active_by_owner(
            owner_id=current_user.id,
            offset=offset,
            limit=pagination.limit,
        )
        response = ItemListResponseDTO.build(
            items=items,
            page=pagination.page,
            limit=pagination.limit,
            total_items=total,
        )
        cache.set(cache_key, response.model_dump(mode="json"), settings.ITEMS_CACHE_TTL_SECONDS)
        return response

    def get_item(self, item_id: uuid.UUID, current_user: User) -> ItemResponseDTO:
        cache_key = self._item_cache_key(current_user.id, item_id)
        cached = cache.get(cache_key)
        if cached is not None:
            cached_item = ItemResponseDTO.model_validate(cached)
            return cached_item

        item = self.repo.get_active_by_id(item_id)
        if item is None:
            raise NotFoundException("Item not found")

        if item.owner_id != current_user.id:
            raise ForbiddenException("You do not have access to this item")

        response = ItemResponseDTO.model_validate(item)
        cache.set(cache_key, response.model_dump(mode="json"), settings.ITEMS_CACHE_TTL_SECONDS)
        return response

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
        self._invalidate_user_items_cache(current_user.id)
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
        self._invalidate_user_items_cache(current_user.id)
        self._invalidate_item_cache(item_id)
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
        self._invalidate_user_items_cache(current_user.id)
        self._invalidate_item_cache(item_id)
        return ItemResponseDTO.model_validate(updated)

    def delete_item(self, item_id: uuid.UUID, current_user: User) -> None:
        item = self.repo.get_active_by_id(item_id)
        if item is None:
            raise NotFoundException("Item not found")

        if item.owner_id != current_user.id:
            raise ForbiddenException("You do not have access to this item")

        self.repo.soft_delete(item)
        self.db.commit()
        self._invalidate_user_items_cache(current_user.id)
        self._invalidate_item_cache(item_id)
