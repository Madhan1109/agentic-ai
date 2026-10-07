from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # auto | groq (free) | ollama (local/free) | openai | local (tools only)
    llm_provider: str = "auto"

    groq_api_key: str = ""
    # Free/developer tier: llama-3.3-70b-versatile was retired Aug 2026
    groq_model: str = "openai/gpt-oss-20b"

    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "llama3.1"

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"

    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 480

    database_url: str = f"sqlite:///{(ROOT_DIR / 'data' / 'hr.db').as_posix()}"
    policies_dir: str = str(ROOT_DIR / "data" / "policies")
    chroma_dir: str = str(ROOT_DIR / "data" / "chroma")

    api_host: str = "127.0.0.1"
    api_port: int = 8000
    api_base_url: str = "http://127.0.0.1:8000"


@lru_cache
def get_settings() -> Settings:
    return Settings()
