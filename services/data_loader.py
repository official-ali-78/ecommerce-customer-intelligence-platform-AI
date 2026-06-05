"""Load Olist CSV data from dataset/ (raw) or bundled demo sample — no cleaned-data step."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
from flask import current_app

logger = logging.getLogger(__name__)

# Raw Kaggle filenames → internal table keys used by analytics
RAW_FILES: dict[str, str] = {
    "orders": "olist_orders_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "customers": "olist_customers_dataset.csv",
    "products": "olist_products_dataset.csv",
    "order_payments": "olist_order_payments_dataset.csv",
    "category_translation": "product_category_name_translation.csv",
}

# Demo sample uses short names directly under data/sample/
SAMPLE_FILES: dict[str, str] = {
    "orders": "orders.csv",
    "order_items": "order_items.csv",
    "customers": "customers.csv",
    "products": "products.csv",
    "order_payments": "order_payments.csv",
    "category_translation": "category_translation.csv",
}


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, low_memory=False)


def resolve_data_source() -> str:
    """Return 'dataset', 'sample', or 'none'."""
    cfg = current_app.config
    dataset_dir: Path = cfg["DATASET_DIR"]
    if (dataset_dir / RAW_FILES["orders"]).exists():
        return "dataset"
    sample_dir: Path = cfg["SAMPLE_DATA_DIR"]
    if (sample_dir / SAMPLE_FILES["orders"]).exists():
        return "sample"
    return "none"


def load_frames() -> dict[str, pd.DataFrame]:
    """Load all tables; prefers dataset/ raw Olist CSVs, else data/sample/ demo."""
    source = resolve_data_source()
    if source == "dataset":
        return _load_from_dir(current_app.config["DATASET_DIR"], RAW_FILES)
    if source == "sample":
        return _load_from_dir(current_app.config["SAMPLE_DATA_DIR"], SAMPLE_FILES)
    raise FileNotFoundError(
        "No data found. Place Olist CSVs in dataset/ (see dataset/README.md) "
        "or use the bundled data/sample/ demo files."
    )


def _load_from_dir(directory: Path, mapping: dict[str, str]) -> dict[str, pd.DataFrame]:
    frames: dict[str, pd.DataFrame] = {}
    for key, filename in mapping.items():
        path = directory / filename
        if not path.exists():
            raise FileNotFoundError(f"Missing required file: {path}")
        frames[key] = _read_csv(path)
        logger.debug("Loaded %s from %s", key, path.name)
    return frames
