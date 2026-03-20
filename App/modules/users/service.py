from app.common.security.passwords import hash_password
from app.modules.users.model import User
from app.modules.users.repository import UserRepository


class UsersService:
    def __init__(self, db):
        self.db = db
        self.repo = UserRepository(db)

    def get_active_by_id(self, user_id):
        return self.repo.get_active_by_id(user_id)

    def get_active_by_email(self, email: str):
        return self.repo.get_active_by_email(email.lower().strip())

    def get_by_yandex_id(self, yandex_id: str):
        return self.repo.get_by_yandex_id(yandex_id)

    def create_local_user(self, email: str, password: str) -> User:
        password_hash, password_salt = hash_password(password)
        return self.repo.create(
            {
                "email": email.lower().strip(),
                "password_hash": password_hash,
                "password_salt": password_salt,
            }
        )

    def create_oauth_user(self, email: str, yandex_id: str) -> User:
        return self.repo.create(
            {
                "email": email.lower().strip(),
                "yandex_id": yandex_id,
            }
        )

    def link_yandex_account(self, user: User, yandex_id: str) -> User:
        return self.repo.update(user, {"yandex_id": yandex_id})

    def update_password(self, user: User, new_password: str) -> User:
        password_hash, password_salt = hash_password(new_password)
        return self.repo.update(
            user,
            {
                "password_hash": password_hash,
                "password_salt": password_salt,
            },
        )
