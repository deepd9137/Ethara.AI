from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    ENVIRONMENT: str = "local"
    APP_VERSION: str = "0.1.0"
    GIT_SHA: str = "local"

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ttm"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    JWT_SECRET: str
    JWT_REFRESH_SECRET: str
    JWT_ACCESS_TTL_SECONDS: int = 900
    JWT_REFRESH_TTL_SECONDS: int = 1_209_600
    BCRYPT_ROUNDS: int = 12

    FRONTEND_URLS: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    RATE_LIMIT_AUTH_PER_5MIN: int = 10
    RATE_LIMIT_USER_PER_MIN: int = 120
    LOG_LEVEL: str = "INFO"
    DOCS_ENABLED: bool = True
    SENTRY_DSN: str = ""
    REDIS_URL: str = ""

    @field_validator("FRONTEND_URLS", mode="before")
    @classmethod
    def parse_frontend_urls(cls, v: object) -> object:
        if isinstance(v, str):
            return [url.strip() for url in v.split(",") if url.strip()]
        return v


settings = Settings()
