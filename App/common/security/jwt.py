import uuid
from datetime import datetime, timezone

import jwt
from jwt import ExpiredSignatureError, InvalidTokenError

from app.common.config import settings
from app.common.exceptions import UnauthorizedException

ALGORITHM = "HS256"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _create_jwt(
    *,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    token_id: uuid.UUID,
    token_type: str,
    secret: str,
    ttl,
) -> tuple[str, datetime]:
    now = utc_now()
    expires_at = now + ttl

    payload = {
        "sub": str(user_id),
        "sid": str(session_id),
        "jti": str(token_id),
        "typ": token_type,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }

    token = jwt.encode(payload, secret, algorithm=ALGORITHM)
    return token, expires_at


def create_access_token(
    *,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    token_id: uuid.UUID,
) -> tuple[str, datetime]:
    return _create_jwt(
        user_id=user_id,
        session_id=session_id,
        token_id=token_id,
        token_type="access",
        secret=settings.JWT_ACCESS_SECRET,
        ttl=settings.access_ttl,
    )


def create_refresh_token(
    *,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    token_id: uuid.UUID,
) -> tuple[str, datetime]:
    return _create_jwt(
        user_id=user_id,
        session_id=session_id,
        token_id=token_id,
        token_type="refresh",
        secret=settings.JWT_REFRESH_SECRET,
        ttl=settings.refresh_ttl,
    )


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.JWT_ACCESS_SECRET, algorithms=[ALGORITHM])
    except ExpiredSignatureError:
        raise UnauthorizedException("Access token expired")
    except InvalidTokenError:
        raise UnauthorizedException("Invalid access token")

    if payload.get("typ") != "access":
        raise UnauthorizedException("Invalid access token type")

    return payload


def decode_refresh_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.JWT_REFRESH_SECRET, algorithms=[ALGORITHM])
    except ExpiredSignatureError:
        raise UnauthorizedException("Refresh token expired")
    except InvalidTokenError:
        raise UnauthorizedException("Invalid refresh token")

    if payload.get("typ") != "refresh":
        raise UnauthorizedException("Invalid refresh token type")

    return payload