from urllib.parse import urlencode

import httpx

from app.common.config import settings
from app.common.exceptions import AppException, UnauthorizedException


class YandexOAuthClient:
    AUTHORIZE_URL = "https://oauth.yandex.com/authorize"
    TOKEN_URL = "https://oauth.yandex.com/token"
    USERINFO_URL = "https://login.yandex.ru/info"

    def build_authorize_url(self, state: str) -> str:
        if not settings.YANDEX_CLIENT_ID:
            raise AppException("Yandex OAuth is not configured")

        query = urlencode(
            {
                "response_type": "code",
                "client_id": settings.YANDEX_CLIENT_ID,
                "redirect_uri": settings.YANDEX_CALLBACK_URL,
                "state": state,
                "scope": "login:info login:email",
            }
        )
        return f"{self.AUTHORIZE_URL}?{query}"

    def exchange_code(self, code: str) -> dict:
        if not settings.YANDEX_CLIENT_ID or not settings.YANDEX_CLIENT_SECRET:
            raise AppException("Yandex OAuth is not configured")

        response = httpx.post(
            self.TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": settings.YANDEX_CLIENT_ID,
                "client_secret": settings.YANDEX_CLIENT_SECRET,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=20.0,
        )

        if response.status_code >= 400:
            raise UnauthorizedException("Failed to exchange OAuth code")

        data = response.json()
        if "access_token" not in data:
            raise UnauthorizedException("Provider access token not received")

        return data

    def fetch_user_info(self, provider_access_token: str) -> dict:
        response = httpx.get(
            self.USERINFO_URL,
            headers={"Authorization": f"OAuth {provider_access_token}"},
            params={"format": "json"},
            timeout=20.0,
        )

        if response.status_code >= 400:
            raise UnauthorizedException("Failed to fetch Yandex user info")

        data = response.json()

        if not data.get("id"):
            raise UnauthorizedException("Yandex user ID not found in profile")
        if not data.get("default_email"):
            raise UnauthorizedException("Yandex profile did not return email")

        return data
