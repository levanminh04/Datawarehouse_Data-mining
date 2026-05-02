"""Cấu hình tập trung — đọc từ biến môi trường / file .env."""
from __future__ import annotations

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/hm_mining"
    MODEL_STORE: str = "./models_store"

    # Layer 1
    KMEANS_N_CLUSTERS: int = 5
    KMEANS_SAMPLE_SIZE: int = 100_000

    # Layer 2
    APRIORI_MIN_SUPPORT: float = 0.01
    APRIORI_MIN_CONFIDENCE: float = 0.20

    # Layer 3
    RF_PREDICTION_WINDOW_DAYS: int = 7
    RF_SAMPLE_SIZE: int = 300_000

    # Scheduler
    RETRAIN_L1_CRON: str = "0 2 * * 0"
    RETRAIN_L2_CRON: str = "0 3 * * 0"
    RETRAIN_L3_CRON: str = "0 1 * * *"
    ENABLE_SCHEDULER: bool = True

    @property
    def model_store_path(self) -> Path:
        p = Path(self.MODEL_STORE).resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p


settings = Settings()
