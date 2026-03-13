import uuid
from dataclasses import dataclass

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.cookies import ACCESS_COOKIE_NAME
from app.core.db import get_db
from app.core.exceptions import UnauthorizedException
from app.core.security import decode_access_token, hash_token
from app.models.user import User
from app.repositories.session_token_repository import SessionTokenRepository
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.services.item_service import ItemService


@dataclass
class AuthContext:
    user: User
    payload: dict


def get_item_service(db: Session = Depends(get_db)) -> ItemService:
    return ItemService(db)


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(db)


def get_current_auth(
    request: Request,
    db: Session = Depends(get_db),
) -> AuthContext:
    access_token = request.cookies.get(ACCESS_COOKIE_NAME)
    if not access_token:
        raise UnauthorizedException("Missing access token")

    payload = decode_access_token(access_token)

    try:
        token_id = uuid.UUID(payload["jti"])
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError):
        raise UnauthorizedException("Invalid access token payload")

    token_repo = SessionTokenRepository(db)
    user_repo = UserRepository(db)

    token_record = token_repo.get_valid_token(
        token_id=token_id,
        token_hash=hash_token(access_token),
        token_type="access",
    )
    if token_record is None:
        raise UnauthorizedException("Access token revoked or not found")

    user = user_repo.get_active_by_id(user_id)
    if user is None:
        raise UnauthorizedException("User not found")

    return AuthContext(user=user, payload=payload)


def get_current_user(auth: AuthContext = Depends(get_current_auth)) -> User:
    return auth.user