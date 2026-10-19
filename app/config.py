from logging import log

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Application configuration settings"""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://rag:rag@localhost:5432/rag"
    ollama_url: str = "http://localhost:11434"

    embed_model: str = "bge-m3"
    embed_dim: int = 1024
    llm_model: str = "qwen2.5:7b"

    chunk_size: int = 800
    chunk_overlap: int = 120
    top_k: int = 4
    min_score: float = 0.0

    data_dir: str = "data"

settings = Settings()
