import uuid

from app.common.cache import cache
from app.common.config import settings
from app.common.security.passwords import hash_password
from app.modules.users.model import User
from app.modules.users.repository import UserRepository
from app.modules.users.schemas import UserPublicDTO


class UsersService:
    def __init__(self, db):
        self.db = db
        self.repo = UserRepository(db)

    def _profile_cache_key(self, user_id: uuid.UUID) -> str:
        return cache.key("users", "profile", user_id)

    def _cache_public_profile(self, user: User) -> None:
        public_user = UserPublicDTO.model_validate(user).model_dump(mode="json")
        cache.set(
            self._profile_cache_key(user.id),
            public_user,
            settings.USER_PROFILE_CACHE_TTL_SECONDS,
        )

    def _invalidate_profile(self, user_id: uuid.UUID) -> None:
        cache.del_key(self._profile_cache_key(user_id))

    def get_active_by_id(self, user_id):
        cached = cache.get(self._profile_cache_key(user_id))
        if cached is not None:
            public_user = UserPublicDTO.model_validate(cached)
            return User(
                id=public_user.id,
                email=str(public_user.email),
                phone=public_user.phone,
                display_name=public_user.display_name,
                bio=public_user.bio,
                avatar_file_id=public_user.avatar_file_id,
                created_at=public_user.created_at,
            )

        user = self.repo.get_active_by_id(user_id)
        if user is not None:
            self._cache_public_profile(user)
        return user

    def get_active_by_email(self, email: str):
        return self.repo.get_active_by_email(email.lower().strip())

    def get_by_yandex_id(self, yandex_id: str):
        return self.repo.get_by_yandex_id(yandex_id)

    def create_local_user(self, email: str, password: str) -> User:
        password_hash, password_salt = hash_password(password)
        user = self.repo.create(
            {
                "email": email.lower().strip(),
                "password_hash": password_hash,
                "password_salt": password_salt,
            }
        )
        self._cache_public_profile(user)
        return user

    def create_oauth_user(self, email: str, yandex_id: str) -> User:
        user = self.repo.create(
            {
                "email": email.lower().strip(),
                "yandex_id": yandex_id,
            }
        )
        self._cache_public_profile(user)
        return user

    def link_yandex_account(self, user: User, yandex_id: str) -> User:
        updated = self.repo.update(user, {"yandex_id": yandex_id})
        self._invalidate_profile(user.id)
        return updated

    def update_password(self, user: User, new_password: str) -> User:
        password_hash, password_salt = hash_password(new_password)
        updated = self.repo.update(
            user,
            {
                "password_hash": password_hash,
                "password_salt": password_salt,
            },
        )
        self._invalidate_profile(user.id)
        return updated

    def update_profile(self, user: User, data: dict) -> User:
        updated = self.repo.update(user, data)
        self._invalidate_profile(user.id)
        self._cache_public_profile(updated)
        return updated
