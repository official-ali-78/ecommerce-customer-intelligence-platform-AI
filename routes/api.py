"""JSON API for the four analytics dashboards."""

from __future__ import annotations

from flask import Blueprint, jsonify

from services.chart_analytics import ChartAnalyticsService
from services.data_loader import resolve_data_source

api_bp = Blueprint("api", __name__, url_prefix="/api/v1")


@api_bp.route("/health")
def health():
    return jsonify({"status": "ok", "data_source": resolve_data_source()})


@api_bp.route("/analytics/executive")
def analytics_executive():
    return jsonify(ChartAnalyticsService().get_executive_dashboard())


@api_bp.route("/analytics/customers")
def analytics_customers():
    return jsonify(ChartAnalyticsService().get_customer_analytics())


@api_bp.route("/analytics/products")
def analytics_products():
    return jsonify(ChartAnalyticsService().get_product_analytics())


@api_bp.route("/analytics/advanced")
def analytics_advanced():
    return jsonify(ChartAnalyticsService().get_advanced_analytics())
