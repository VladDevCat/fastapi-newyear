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

    MONGO_INITDB_ROOT_USERNAME: str = "student"
    MONGO_INITDB_ROOT_PASSWORD: str = "student_secure_password"
    MONGO_DB_NAME: str = "wp_labs"
    MONGO_HOST: str = "mongo"
    MONGO_PORT: int = 27017
    MONGO_AUTH_SOURCE: str = "admin"
    MONGO_URI: str | None = None

    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = "redis_secure_password"
    REDIS_DB: int = 0
    REDIS_KEY_PREFIX: str = "wp"
    ITEMS_CACHE_TTL_SECONDS: int = 120
    USER_PROFILE_CACHE_TTL_SECONDS: int = 300
    FILE_META_CACHE_TTL_SECONDS: int = 300

    MINIO_ENDPOINT: str = "minio:9000"
    MINIO_PUBLIC_ENDPOINT: str = "localhost:9000"
    MINIO_ROOT_USER: str = "minioadmin"
    MINIO_ROOT_PASSWORD: str = "minioadmin_secure_password"
    MINIO_BUCKET: str = "wp-files"
    MINIO_SECURE: bool = False
    MAX_UPLOAD_SIZE_BYTES: int = 10485760
    AVATAR_ALLOWED_MIME_TYPES: str = "image/png,image/jpeg,image/jpg"

    RABBITMQ_HOST: str = "rabbitmq"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "student"
    RABBITMQ_PASS: str = "student_secure_rabbit_pass_change_in_prod"
    RABBITMQ_EXCHANGE: str = "app.events"
    RABBITMQ_DLX: str = "app.dlx"
    QUEUE_USER_REGISTERED: str = "wp.auth.user.registered"
    QUEUE_USER_REGISTERED_DLQ: str = "wp.auth.user.registered.dlq"
    RABBITMQ_MAX_RETRIES: int = 3
    RABBITMQ_CONSUMER_MAX_FAILURES: int = 5

    SMTP_HOST: str = "mailpit"
    SMTP_PORT: int = 1025
    SMTP_USER: str = ""
    SMTP_PASS: str = ""
    SMTP_FROM: str = "no-reply@wp-labs.local"
    SMTP_SECURE: bool = False
    SMTP_LOGIN_URL: str = "http://localhost:4200/api/docs"

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
    def mongo_uri(self) -> str:
        if self.MONGO_URI:
            return self.MONGO_URI
        return (
            f"mongodb://{self.MONGO_INITDB_ROOT_USERNAME}:{self.MONGO_INITDB_ROOT_PASSWORD}"
            f"@{self.MONGO_HOST}:{self.MONGO_PORT}/{self.MONGO_DB_NAME}"
            f"?authSource={self.MONGO_AUTH_SOURCE}"
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

    @property
    def avatar_allowed_mime_types(self) -> set[str]:
        return {
            item.strip().lower()
            for item in self.AVATAR_ALLOWED_MIME_TYPES.split(",")
            if item.strip()
        }

    def validate_smtp_config(self) -> None:
        missing = []
        if not self.SMTP_HOST:
            missing.append("SMTP_HOST")
        if not self.SMTP_PORT:
            missing.append("SMTP_PORT")
        if not self.SMTP_FROM:
            missing.append("SMTP_FROM")
        if bool(self.SMTP_USER) != bool(self.SMTP_PASS):
            missing.append("SMTP_USER and SMTP_PASS must be set together")
        if missing:
            raise RuntimeError(f"Invalid SMTP configuration: {', '.join(missing)}")


settings = Settings()
