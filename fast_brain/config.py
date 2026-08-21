from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    api_key: str = Field(default="", validation_alias="FAST_BRAIN_API_KEY")
    database_url: str = Field(
        default="postgresql://fastbrain:fastbrain@localhost:5432/fastbrain",
        validation_alias="DATABASE_URL",
    )
    embeddings_base_url: str = Field(validation_alias="EMBEDDINGS_BASE_URL")
    embeddings_api_key: str = Field(validation_alias="EMBEDDINGS_API_KEY")
    embeddings_model: str = Field(validation_alias="EMBEDDINGS_MODEL")
    embeddings_dimensions: int = Field(default=1536, validation_alias="EMBEDDINGS_DIMENSIONS")
    summarizer_base_url: str = Field(default="", validation_alias="SUMMARIZER_BASE_URL")
    summarizer_api_key: str = Field(default="", validation_alias="SUMMARIZER_API_KEY")
    summarizer_model: str = Field(default="", validation_alias="SUMMARIZER_MODEL")


settings = Settings()
