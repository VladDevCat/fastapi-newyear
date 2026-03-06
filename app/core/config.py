from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Holiday Prep API"

    DB_USER: str = "student"
    DB_PASSWORD: str = "student_secure_password"
    DB_NAME: str = "wp_labs"
    DB_HOST: str = "db"
    DB_PORT: int = 5432

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )


settings = Settings()