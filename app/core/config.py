from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    DATABASE_URL: str = "sqlite:///./teacher_management.db"
    SECRET_KEY: str = "deo-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    UPLOAD_MAX_SIZE: int = 5 * 1024 * 1024
    ALLOWED_EXTENSIONS: set = {"pdf"}
    USE_LOCAL_STORAGE: bool = True
    ENCRYPTION_KEY: str = ""
    FRONTEND_URL: str = "http://localhost:3000"

    class Config:
        env_file = ".env"

@lru_cache
def get_settings():
    return Settings()
