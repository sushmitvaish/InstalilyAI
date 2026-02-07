from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    CHROMA_DB_PATH: str = "./data/chroma_db"
    CHROMA_COLLECTION_NAME: str = "partselect_parts"
    MAX_CONTEXT_CHUNKS: int = 5

    class Config:
        env_file = ".env"


settings = Settings()
