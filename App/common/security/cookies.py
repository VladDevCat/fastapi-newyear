from fastapi import Response

from app.common.config import settings

ACCESS_COOKIE_NAME = "access_token"
REFRESH_COOKIE_NAME = "refresh_token"


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    cookie_kwargs = {
        "httponly": True,
        "secure": settings.COOKIE_SECURE,
        "samesite": settings.COOKIE_SAMESITE,
        "path": "/",
    }

    if settings.COOKIE_DOMAIN:
        cookie_kwargs["domain"] = settings.COOKIE_DOMAIN

    response.set_cookie(
        key=ACCESS_COOKIE_NAME,
        value=access_token,
        max_age=int(settings.access_ttl.total_seconds()),
        **cookie_kwargs,
    )

    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        max_age=int(settings.refresh_ttl.total_seconds()),
        **cookie_kwargs,
    )


def clear_auth_cookies(response: Response) -> None:
    cookie_kwargs = {"path": "/"}

    if settings.COOKIE_DOMAIN:
        cookie_kwargs["domain"] = settings.COOKIE_DOMAIN

    response.delete_cookie(ACCESS_COOKIE_NAME, **cookie_kwargs)
    response.delete_cookie(REFRESH_COOKIE_NAME, **cookie_kwargs)