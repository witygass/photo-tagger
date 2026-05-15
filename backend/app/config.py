import json
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=["../.env", ".env"], env_file_encoding="utf-8", extra="ignore")

    # Required secrets
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ENCRYPTION_KEY: str = ""  # Fernet key; generated if blank in dev

    # Google OAuth (web application type)
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/auth/callback"

    # Database
    DATABASE_URL: str = f"sqlite+aiosqlite:///{_BACKEND_DIR}/photo_tagger.db"

    # Frontend
    FRONTEND_URL: str = "http://localhost:5173"
    ALLOWED_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:4173"]

    # Thumbnail disk cache
    THUMBNAIL_CACHE_DIR: str = "/tmp/photo_tagger_thumbnails"

    # App behavior
    INSIGHTFACE_MODEL: str = "buffalo_l"
    SIMILARITY_THRESHOLD: float = 0.45
    PET_SIMILARITY_THRESHOLD: float = 0.45
    MAX_UPLOAD_SIZE_MB: int = 10

    @property
    def allowed_origins_list(self) -> list[str]:
        return self.ALLOWED_ORIGINS


settings = Settings()
