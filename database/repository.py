"""Data access layer: SQL queries for analytics KPIs."""

from __future__ import annotations

from typing import Any

from sqlalchemy import text

from database.connection import db


class AnalyticsRepository:
    """Read-only analytics queries against the Olist warehouse schema."""

    REVENUE_STATUSES = ("delivered", "shipped", "invoiced")

    @staticmethod
    def _rows(result) -> list[dict[str, Any]]:
        return [dict(row._mapping) for row in result]

    def health_check(self) -> bool:
        try:
            db.session.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    def get_executive_kpis(self) -> dict[str, Any]:
        sql = text(
            """
            SELECT
                COUNT(DISTINCT o.order_id) AS total_orders,
                COUNT(DISTINCT c.customer_unique_id) AS unique_customers,
                COALESCE(SUM(oi.price), 0) AS product_revenue,
                COALESCE(SUM(oi.freight_value), 0) AS total_freight,
                COALESCE(SUM(oi.price + oi.freight_value), 0) AS gmv,
                COALESCE(AVG(order_totals.order_revenue), 0) AS avg_order_value
            FROM orders o
            JOIN customers c ON c.customer_id = o.customer_id
            LEFT JOIN order_items oi ON oi.order_id = o.order_id
            LEFT JOIN (
                SELECT order_id, SUM(price) AS order_revenue
                FROM order_items
                GROUP BY order_id
            ) order_totals ON order_totals.order_id = o.order_id
            WHERE o.order_status IN :statuses
            """
        )
        row = db.session.execute(sql, {"statuses": self.REVENUE_STATUSES}).one()
        return dict(row._mapping)

    def get_monthly_revenue(self, limit: int = 24) -> list[dict[str, Any]]:
        sql = text(
            """
            SELECT
                DATE_FORMAT(o.order_purchase_timestamp, '%Y-%m') AS month,
                SUM(oi.price) AS revenue,
                SUM(oi.freight_value) AS freight,
                SUM(oi.price + oi.freight_value) AS gmv,
                COUNT(DISTINCT o.order_id) AS orders
            FROM orders o
            JOIN order_items oi ON oi.order_id = o.order_id
            WHERE o.order_status IN :statuses
            GROUP BY DATE_FORMAT(o.order_purchase_timestamp, '%Y-%m')
            ORDER BY month
            LIMIT :limit
            """
        )
        return self._rows(
            db.session.execute(
                sql, {"statuses": self.REVENUE_STATUSES, "limit": limit}
            )
        )

    def get_top_categories(self, limit: int = 10) -> list[dict[str, Any]]:
        sql = text(
            """
            SELECT
                COALESCE(t.product_category_name_english, p.product_category_name) AS category,
                SUM(oi.price) AS revenue,
                COUNT(*) AS line_items
            FROM order_items oi
            JOIN products p ON p.product_id = oi.product_id
            LEFT JOIN product_category_name_translation t
                ON t.product_category_name = p.product_category_name
            JOIN orders o ON o.order_id = oi.order_id
            WHERE o.order_status IN :statuses
            GROUP BY category
            ORDER BY revenue DESC
            LIMIT :limit
            """
        )
        return self._rows(
            db.session.execute(sql, {"statuses": self.REVENUE_STATUSES, "limit": limit})
        )

    def get_revenue_by_state(self, limit: int = 10) -> list[dict[str, Any]]:
        sql = text(
            """
            SELECT
                c.customer_state AS state,
                SUM(oi.price) AS revenue,
                COUNT(DISTINCT o.order_id) AS orders
            FROM orders o
            JOIN customers c ON c.customer_id = o.customer_id
            JOIN order_items oi ON oi.order_id = o.order_id
            WHERE o.order_status IN :statuses
            GROUP BY c.customer_state
            ORDER BY revenue DESC
            LIMIT :limit
            """
        )
        return self._rows(
            db.session.execute(sql, {"statuses": self.REVENUE_STATUSES, "limit": limit})
        )

    def get_payment_mix(self) -> list[dict[str, Any]]:
        sql = text(
            """
            SELECT
                payment_type,
                SUM(payment_value) AS total_value,
                COUNT(*) AS payment_count
            FROM order_payments
            GROUP BY payment_type
            ORDER BY total_value DESC
            """
        )
        return self._rows(db.session.execute(sql))

    def get_delivery_metrics(self) -> dict[str, Any]:
        sql = text(
            """
            SELECT
                AVG(DATEDIFF(o.order_delivered_customer_date, o.order_purchase_timestamp)) AS avg_delivery_days,
                SUM(
                    CASE
                        WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date
                        THEN 1 ELSE 0
                    END
                ) / COUNT(*) * 100 AS late_pct,
                SUM(CASE WHEN o.order_status = 'delivered' THEN 1 ELSE 0 END) / COUNT(*) * 100 AS delivered_pct
            FROM orders o
            WHERE o.order_status = 'delivered'
              AND o.order_delivered_customer_date IS NOT NULL
            """
        )
        row = db.session.execute(sql).one()
        return dict(row._mapping)

    def get_repeat_customer_rate(self) -> dict[str, Any]:
        sql = text(
            """
            SELECT
                COUNT(*) AS unique_customers,
                SUM(CASE WHEN order_count > 1 THEN 1 ELSE 0 END) AS repeat_customers
            FROM (
                SELECT c.customer_unique_id, COUNT(DISTINCT o.order_id) AS order_count
                FROM orders o
                JOIN customers c ON c.customer_id = o.customer_id
                GROUP BY c.customer_unique_id
            ) t
            """
        )
        row = db.session.execute(sql).one()
        data = dict(row._mapping)
        total = data.get("unique_customers") or 0
        repeat = data.get("repeat_customers") or 0
        data["repeat_rate_pct"] = round((repeat / total * 100) if total else 0, 2)
        return data
