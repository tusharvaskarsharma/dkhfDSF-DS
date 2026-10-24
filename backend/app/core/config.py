from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import List

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PROJECT_NAME: str = "UK Wind Forecast Accuracy Dashboard"
    API_V1_STR: str = "/api/v1"
    
    # Elexon BMRS API
    ELEXON_BASE_URL: str = "https://data.elexon.co.uk/bmrs/api/v1"
    ELEXON_TIMEOUT_SECONDS: float = 20.0
    ELEXON_MAX_RETRIES: int = 3
    ELEXON_RETRY_BACKOFF: float = 1.0
    
    # Storage
    DATABASE_PATH: str = Field(default="data/wind_forecast.db")
    
    # Evaluation Defaults
    DEFAULT_DATE_FROM: str = "2026-01-01"
    DEFAULT_DATE_TO: str = "2026-01-31"
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://localhost:8000",
        "*"
    ]
    
    # Demo fixture fallback if API is unreachable
    ALLOW_FIXTURE_FALLBACK: bool = True

settings = Settings()
