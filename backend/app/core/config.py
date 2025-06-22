from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    database_url: str
    openai_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    secret_key: str
    
    class Config:
        env_file = ".env"

settings = Settings()