from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # LLM
    google_api_key: str | None = None

    @field_validator("google_api_key")
    def check_key(cls, v):
        if not v:
            raise ValueError("GOOGLE_API_KEY is required")
        return v

    gemini_model: str = "gemini-2.5-flash"

    # Database
    database_url: str = "postgresql+asyncpg://localhost/docmind"

    # Chunking — we'll experiment with these in Phase 2
    chunk_size: int = 500
    chunk_overlap: int = 100

    # Retrieval
    top_k: int = 5

    # Chroma
    chroma_persist_dir: str = "./chroma_db"

    # Replaces the old inner Config class
    model_config = SettingsConfigDict(env_file=".env")


# Single instance imported everywhere
settings = Settings()
