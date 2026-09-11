from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Sistema Carvao"
    database_url: str = "sqlite:///./carvao.db"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 720
    whatsapp_provider: str = "mock"
    whatsapp_api_url: str = ""
    whatsapp_token: str = ""
    manager_whatsapp: str = "+5599999999999"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
