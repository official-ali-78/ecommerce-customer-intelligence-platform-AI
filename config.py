"""Application configuration (12-factor: env-driven)."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


class Config:
  """Base configuration."""

  SECRET_KEY = os.getenv("SECRET_KEY", "dev-change-me-in-production")
  DEBUG = False
  TESTING = False

  # MySQL (ecommerce_analytics warehouse)
  MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
  MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
  MYSQL_USER = os.getenv("MYSQL_USER", "root")
  MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
  MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "ecommerce_analytics")

  SQLALCHEMY_DATABASE_URI = (
      f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}"
      f"@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}?charset=utf8mb4"
  )
  SQLALCHEMY_TRACK_MODIFICATIONS = False
  SQLALCHEMY_ENGINE_OPTIONS = {
      "pool_pre_ping": True,
      "pool_recycle": 3600,
      "pool_size": 10,
      "max_overflow": 20,
  }

  # Data paths (no cleaned-data pipeline — raw Olist CSVs or bundled demo)
  DATASET_DIR = BASE_DIR / "dataset"
  SAMPLE_DATA_DIR = BASE_DIR / "data" / "sample"

  # Optional MySQL warehouse (off by default for GitHub / local CSV use)
  USE_MYSQL = os.getenv("USE_MYSQL", "false").lower() in ("1", "true", "yes")

  # Cache KPI responses (seconds); 0 = disabled
  KPI_CACHE_TTL = int(os.getenv("KPI_CACHE_TTL", "300"))


class DevelopmentConfig(Config):
  DEBUG = True


class ProductionConfig(Config):
  DEBUG = False


class TestingConfig(Config):
  TESTING = True
  MYSQL_DATABASE = os.getenv("MYSQL_TEST_DATABASE", "ecommerce_analytics_test")
  SQLALCHEMY_DATABASE_URI = (
      f"mysql+pymysql://{os.getenv('MYSQL_USER', 'root')}:{os.getenv('MYSQL_PASSWORD', '')}"
      f"@{os.getenv('MYSQL_HOST', '127.0.0.1')}:{os.getenv('MYSQL_PORT', '3306')}"
      f"/{os.getenv('MYSQL_TEST_DATABASE', 'ecommerce_analytics_test')}?charset=utf8mb4"
  )


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
