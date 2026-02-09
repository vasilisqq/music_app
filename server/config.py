from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # App
    APP_NAME: str = "MUSIC APP"
    DEBUG: bool = True
    
    # Database
    DATABASE_URL: str
    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"

    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()