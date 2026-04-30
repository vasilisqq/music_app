from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    APP_NAME: str = "MUSIC APP"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str
    # JWT
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_DAYS: int

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
