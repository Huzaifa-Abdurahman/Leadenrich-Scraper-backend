from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Firecrawl
    firecrawl_api_key: str = "fc-2ea185e1f4d14283b9ebe4227685093e"

    # Server
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    # CORS
    cors_origins: List[str] = ["*"]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

settings = Settings()
