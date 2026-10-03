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
    DB_PATH: str = "data/blackbox.db"
    DATA_DIR: str = "data"
    ARTIFACTS_DIR: str = "artifacts"
    MAX_CONCURRENCY: int = 4
    RPM_LIMIT: int = 30
    HOLDOUT_FAULTS: str = "BAD_QUERY,WRONG_EXTRACTION"
    N_TASKS: int = 300
    BLACKBOX_DEMO_MODE: int = 0
    BLACKBOX_MOCK_API: int = 0
    COST_PER_WRONG_ANSWER_INR: int = 450
    SEED: int = 42


@lru_cache
def get_settings() -> Settings:
    return Settings()
