"""Four-page analytics web UI."""

from __future__ import annotations

from flask import Blueprint, Response, redirect, render_template, url_for

from services.chart_analytics import ChartAnalyticsService

main_bp = Blueprint("main", __name__)


def _charts() -> ChartAnalyticsService:
    return ChartAnalyticsService()


@main_bp.route("/")
def index():
    return redirect(url_for("main.executive_dashboard"))


@main_bp.route("/analytics/executive")
def executive_dashboard():
    payload = _charts().get_executive_dashboard()
    return render_template(
        "analytics/executive.html",
        kpis=payload["kpis"],
        charts=payload["charts"],
        data_source=payload["data_source"],
        export_page="executive",
    )


@main_bp.route("/analytics/customers")
def customer_analytics():
    payload = _charts().get_customer_analytics()
    return render_template(
        "analytics/customers.html",
        kpis=payload["kpis"],
        charts=payload["charts"],
        data_source=payload["data_source"],
        export_page="customers",
    )


@main_bp.route("/analytics/products")
def product_analytics():
    payload = _charts().get_product_analytics()
    return render_template(
        "analytics/products.html",
        kpis=payload["kpis"],
        charts=payload["charts"],
        data_source=payload["data_source"],
        export_page="products",
    )


@main_bp.route("/analytics/advanced")
def advanced_analytics():
    payload = _charts().get_advanced_analytics()
    return render_template(
        "analytics/advanced.html",
        kpis=payload["kpis"],
        charts=payload["charts"],
        recommendations=payload["recommendations"],
        data_source=payload["data_source"],
        export_page="advanced",
    )


@main_bp.route("/analytics/<page>/export.csv")
def analytics_export(page: str):
    try:
        filename, csv_content = _charts().export_page_csv(page)
    except ValueError:
        return Response("Not found", status=404)
    return Response(
        csv_content,
        mimetype="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
