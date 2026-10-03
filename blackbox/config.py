from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    LLM_PROVIDER: Literal["gemini", "groq", "fake"] = "gemini"
    LLM_MODEL: str = "gemini-flash-latest"
    GEMINI_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = ""
    DATABASE_URL: str | None = None
    DATABASE_URL_UNPOOLED: str | None = None
    DB_PATH: str = "data/blackbox.db"
    DATA_DIR: str = "data"
    ARTIFACTS_DIR: str = "artifacts"
    MAX_CONCURRENCY: int = 4
    RPM_LIMIT: int = 30
    HOLDOUT_FAULTS: str = "BAD_QUERY,WRONG_EXTRACTION"
    N_TASKS: int = 300
    BLACKBOX_DEMO_MODE: int = 0
    BLACKBOX_MOCK_API: int = 0
    DEMO_AUTH_ENABLED: int = 0
    DEMO_AUTH_EMAIL: str = "blackbox@gmail.com"
    DEMO_AUTH_PASSWORD: str = "blackbox123"
    DEMO_AUTH_SECRET: str = "blackbox-local-demo"
    COST_PER_WRONG_ANSWER_INR: int = 450
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 1025
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_STARTTLS: int = 0
    SMTP_SSL: int = 0
    SMTP_FROM: str = "Black Box <alerts@blackbox.local>"
    APP_BASE_URL: str = "http://localhost:5173"
    NOTIFY_DEFAULT_EMAIL: str = ""
    NOTIFY_THROTTLE_MINUTES: int = 30
    DIGEST_HOUR_LOCAL: int = 9
    SEED: int = 42


@lru_cache
def get_settings() -> Settings:
    return Settings()
