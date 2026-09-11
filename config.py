from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    api_key: str = Field(..., description="LLM的API Key")
    base_url: str = Field(..., description="LLM的URL")
    model: str = Field(..., description="LLM的模型名")


settings = Settings()
