# app/core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    FPL_BASE_URL: str

    class Config:
        env_file = ".env"

settings = Settings()
