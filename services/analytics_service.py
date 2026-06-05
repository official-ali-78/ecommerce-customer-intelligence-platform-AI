"""Analytics service: reads Olist CSVs (dataset/ or demo sample) — optional MySQL."""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd
from flask import current_app

from database.repository import AnalyticsRepository
from services.data_loader import load_frames, resolve_data_source

logger = logging.getLogger(__name__)


class AnalyticsService:
    """
    Aggregates metrics for the four analytics dashboards.

    Data priority:
      1. MySQL (only when USE_MYSQL=true and DB is populated)
      2. Raw Olist CSVs in dataset/
      3. Bundled demo CSVs in data/sample/
    """

    def __init__(self, repository: AnalyticsRepository | None = None) -> None:
        self._repo = repository or AnalyticsRepository()
        self._use_csv: bool | None = None
        self._csv_cache: dict[str, pd.DataFrame] | None = None

    def _prefer_csv(self) -> bool:
        if self._use_csv is not None:
            return self._use_csv
        if not current_app.config.get("USE_MYSQL", False):
            self._use_csv = True
            return True
        if not self._repo.health_check():
            logger.warning("MySQL unavailable — using CSV data")
            self._use_csv = True
            return True
        try:
            kpis = self._repo.get_executive_kpis()
            self._use_csv = (kpis.get("total_orders") or 0) == 0
        except Exception as exc:
            logger.warning("DB query failed (%s) — CSV fallback", exc)
            self._use_csv = True
        return self._use_csv

    def _load_csv_frames(self) -> dict[str, pd.DataFrame]:
        if self._csv_cache is not None:
            return self._csv_cache
        self._csv_cache = load_frames()
        return self._csv_cache

    def get_executive_summary(self) -> dict[str, Any]:
        if not self._prefer_csv():
            return self._repo.get_executive_kpis()
        return self._executive_from_csv()

    def get_monthly_revenue(self) -> list[dict[str, Any]]:
        if not self._prefer_csv():
            return self._repo.get_monthly_revenue()
        return self._monthly_revenue_from_csv()

    def get_top_categories(self, limit: int = 10) -> list[dict[str, Any]]:
        if not self._prefer_csv():
            return self._repo.get_top_categories(limit)
        return self._top_categories_from_csv(limit)

    def get_revenue_by_state(self, limit: int = 10) -> list[dict[str, Any]]:
        if not self._prefer_csv():
            return self._repo.get_revenue_by_state(limit)
        return self._revenue_by_state_from_csv(limit)

    def get_payment_mix(self) -> list[dict[str, Any]]:
        if not self._prefer_csv():
            return self._repo.get_payment_mix()
        return self._payment_mix_from_csv()

    def get_delivery_metrics(self) -> dict[str, Any]:
        if not self._prefer_csv():
            return self._repo.get_delivery_metrics()
        return self._delivery_from_csv()

    def get_customer_metrics(self) -> dict[str, Any]:
        if not self._prefer_csv():
            return self._repo.get_repeat_customer_rate()
        return self._customer_metrics_from_csv()

    @property
    def data_source(self) -> str:
        if self._prefer_csv():
            return resolve_data_source()
        return "mysql"

    # --- CSV implementations ---

    def _executive_from_csv(self) -> dict[str, Any]:
        d = self._load_csv_frames()
        orders = d["orders"]
        items = d["order_items"]
        customers = d["customers"]
        statuses = {"delivered", "shipped", "invoiced"}
        o = orders[orders["order_status"].isin(statuses)]
        revenue = items[items["order_id"].isin(o["order_id"])]["price"].sum()
        freight = items[items["order_id"].isin(o["order_id"])]["freight_value"].sum()
        order_rev = items.groupby("order_id")["price"].sum()
        return {
            "total_orders": int(o["order_id"].nunique()),
            "unique_customers": int(customers["customer_unique_id"].nunique()),
            "product_revenue": float(revenue),
            "total_freight": float(freight),
            "gmv": float(revenue + freight),
            "avg_order_value": float(order_rev.mean()) if len(order_rev) else 0.0,
        }

    def _monthly_revenue_from_csv(self) -> list[dict[str, Any]]:
        d = self._load_csv_frames()
        orders = pd.to_datetime(d["orders"]["order_purchase_timestamp"])
        o = d["orders"].copy()
        o["month"] = orders.dt.to_period("M").astype(str)
        items = d["order_items"]
        merged = o.merge(items, on="order_id")
        g = merged.groupby("month").agg(
            revenue=("price", "sum"),
            freight=("freight_value", "sum"),
            orders=("order_id", "nunique"),
        )
        g["gmv"] = g["revenue"] + g["freight"]
        return g.reset_index().to_dict(orient="records")

    def _top_categories_from_csv(self, limit: int) -> list[dict[str, Any]]:
        d = self._load_csv_frames()
        items = d["order_items"].merge(d["products"], on="product_id", how="left")
        items = items.merge(
            d["category_translation"],
            on="product_category_name",
            how="left",
        )
        items["category"] = items["product_category_name_english"].fillna(
            items["product_category_name"]
        )
        g = (
            items.groupby("category")
            .agg(revenue=("price", "sum"), line_items=("order_item_id", "count"))
            .nlargest(limit, "revenue")
            .reset_index()
        )
        return g.to_dict(orient="records")

    def _revenue_by_state_from_csv(self, limit: int) -> list[dict[str, Any]]:
        d = self._load_csv_frames()
        o = d["orders"].merge(d["customers"], on="customer_id")
        items = d["order_items"]
        m = o.merge(items, on="order_id")
        g = (
            m.groupby("customer_state")
            .agg(revenue=("price", "sum"), orders=("order_id", "nunique"))
            .nlargest(limit, "revenue")
            .reset_index()
            .rename(columns={"customer_state": "state"})
        )
        return g.to_dict(orient="records")

    def _payment_mix_from_csv(self) -> list[dict[str, Any]]:
        d = self._load_csv_frames()
        g = (
            d["order_payments"]
            .groupby("payment_type")
            .agg(total_value=("payment_value", "sum"), payment_count=("order_id", "count"))
            .reset_index()
        )
        return g.to_dict(orient="records")

    def _delivery_from_csv(self) -> dict[str, Any]:
        d = self._load_csv_frames()
        o = d["orders"]
        delivered = o[o["order_status"] == "delivered"].copy()
        if delivered.empty:
            return {"avg_delivery_days": 0.0, "late_pct": 0.0, "delivered_pct": 0.0}
        delivered["order_purchase_timestamp"] = pd.to_datetime(delivered["order_purchase_timestamp"])
        delivered["order_delivered_customer_date"] = pd.to_datetime(
            delivered["order_delivered_customer_date"]
        )
        delivered["order_estimated_delivery_date"] = pd.to_datetime(
            delivered["order_estimated_delivery_date"]
        )
        delivered["days"] = (
            delivered["order_delivered_customer_date"] - delivered["order_purchase_timestamp"]
        ).dt.days
        late = delivered["order_delivered_customer_date"] > delivered["order_estimated_delivery_date"]
        return {
            "avg_delivery_days": float(delivered["days"].mean()),
            "late_pct": float(late.mean() * 100),
            "delivered_pct": float(len(delivered) / len(o) * 100),
        }

    def _customer_metrics_from_csv(self) -> dict[str, Any]:
        d = self._load_csv_frames()
        o = d["orders"].merge(d["customers"][["customer_id", "customer_unique_id"]], on="customer_id")
        counts = o.groupby("customer_unique_id")["order_id"].nunique()
        total = len(counts)
        repeat = int((counts > 1).sum())
        return {
            "unique_customers": total,
            "repeat_customers": repeat,
            "repeat_rate_pct": round(repeat / total * 100, 2) if total else 0,
        }
