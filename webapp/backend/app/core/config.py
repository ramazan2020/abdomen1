from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Genel
    app_name: str = "Lezyon Tespiti Web Uygulaması"
    environment: str = "local"

    # Veritabanı
    database_url: str = "postgresql+psycopg2://webapp:webapp@localhost:5433/webapp"

    # Auth
    jwt_secret_key: str = "CHANGE_ME_DEV_ONLY"
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60 * 12

    # Storage (Bölüm 1: StorageBackend soyutlaması — Faz 1'de LocalFSBackend)
    storage_backend: str = "local"
    storage_local_root: Path = Path("/workspace/webapp/storage")

    # Redis / RQ (job kuyruğu)
    redis_url: str = "redis://localhost:6379/0"

    # PNG önbellek — lazy strateji (bkz. plan Bölüm 1)
    png_cache_warmup_slices: int = 25

    # ML bağımlılıkları (torch/ultralytics) bu makinede mevcut mu?
    # inference/training servisleri bunu kontrol edip MLDependencyUnavailable fırlatır.
    ml_dependencies_available: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
