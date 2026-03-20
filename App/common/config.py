import re
from datetime import timedelta

from pydantic_settings import BaseSettings, SettingsConfigDict


def parse_duration(value: str) -> timedelta:
    match = re.fullmatch(r"(\d+)([mhd])", value.strip().lower())
    if not match:
        raise ValueError(f"Invalid duration format: {value}. Use formats like 15m, 2h, 7d")

    amount = int(match.group(1))
    unit = match.group(2)

    if unit == "m":
        return timedelta(minutes=amount)
    if unit == "h":
        return timedelta(hours=amount)
    if unit == "d":
        return timedelta(days=amount)

    raise ValueError(f"Unsupported duration unit: {unit}")


class Settings(BaseSettings):
    APP_NAME: str = "Holiday Prep API"
    APP_ENV: str = "development"
    SWAGGER_ENABLED: bool = True

    DB_USER: str = "student"
    DB_PASSWORD: str = "student_secure_password"
    DB_NAME: str = "wp_labs"
    DB_HOST: str = "db"
    DB_PORT: int = 5432

    JWT_ACCESS_SECRET: str = "change_me_access_secret"
    JWT_REFRESH_SECRET: str = "change_me_refresh_secret"
    JWT_ACCESS_EXPIRATION: str = "15m"
    JWT_REFRESH_EXPIRATION: str = "7d"

    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: str = "lax"
    COOKIE_DOMAIN: str | None = None

    APP_BASE_URL: str = "http://localhost:4200"
    FRONTEND_REDIRECT_URL: str = "http://localhost:4200/docs"

    YANDEX_CLIENT_ID: str = ""
    YANDEX_CLIENT_SECRET: str = ""
    YANDEX_CALLBACK_URL: str = "http://localhost:4200/auth/oauth/yandex/callback"

    RESET_PASSWORD_EXPIRE_MINUTES: int = 30
    OAUTH_STATE_EXPIRE_MINUTES: int = 10
    AUTH_DEBUG_RETURN_RESET_TOKEN: bool = False

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def docs_enabled(self) -> bool:
        return self.APP_ENV.lower() in {"development", "local"} and self.SWAGGER_ENABLED

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def access_ttl(self) -> timedelta:
        return parse_duration(self.JWT_ACCESS_EXPIRATION)

    @property
    def refresh_ttl(self) -> timedelta:
        return parse_duration(self.JWT_REFRESH_EXPIRATION)

    @property
    def reset_password_ttl(self) -> timedelta:
        return timedelta(minutes=self.RESET_PASSWORD_EXPIRE_MINUTES)

    @property
    def oauth_state_ttl(self) -> timedelta:
        return timedelta(minutes=self.OAUTH_STATE_EXPIRE_MINUTES)


settings = Settings()
