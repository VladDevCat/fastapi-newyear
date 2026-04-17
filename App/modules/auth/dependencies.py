import uuid
from dataclasses import dataclass

from fastapi import Depends, Request

from app.common.db import get_db
from app.common.exceptions import UnauthorizedException
from app.common.security.cookies import ACCESS_COOKIE_NAME
from app.common.security.hashes import hash_token
from app.common.security.jwt import decode_access_token
from app.modules.auth.service import AuthService
from app.modules.auth.token_repository import SessionTokenRepository
from app.modules.users.model import User
from app.modules.users.service import UsersService


@dataclass
class AuthContext:
    user: User
    payload: dict


def get_auth_service(db=Depends(get_db)) -> AuthService:
    return AuthService(db)


def get_current_auth(
    request: Request,
    db=Depends(get_db),
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
    users_service = UsersService(db)
    auth_service = AuthService(db)

    redis_status = auth_service.is_access_jti_valid(user_id=user_id, token_id=token_id)
    if redis_status is False:
        raise UnauthorizedException("Access token revoked or not found")

    token_record = token_repo.get_valid_token(
        token_id=token_id,
        token_hash=hash_token(access_token),
        token_type="access",
    )
    if token_record is None:
        raise UnauthorizedException("Access token revoked or not found")

    user = users_service.get_active_by_id(user_id)
    if user is None:
        raise UnauthorizedException("User not found")

    return AuthContext(user=user, payload=payload)


def get_current_user(auth: AuthContext = Depends(get_current_auth)) -> User:
    return auth.user
