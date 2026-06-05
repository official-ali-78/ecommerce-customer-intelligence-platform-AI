"""Plotly chart builders and advanced analytics for dashboard pages."""

from __future__ import annotations

import json
import logging
from typing import Any

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.utils import PlotlyJSONEncoder
from sklearn.cluster import KMeans
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler

from services.analytics_service import AnalyticsService
from services.plotly_theme import apply_layout

logger = logging.getLogger(__name__)

REVENUE_STATUSES = {"delivered", "shipped", "invoiced"}


class ChartAnalyticsService(AnalyticsService):
    """Extended analytics with Plotly figures and ML insights."""

    def _fig_data(self, fig, title: str | None = None, height: int = 360) -> dict:
        apply_layout(fig, title=title, height=height)
        return json.loads(json.dumps(fig, cls=PlotlyJSONEncoder))

    def _order_facts(self) -> pd.DataFrame:
        d = self._load_csv_frames()
        orders = d["orders"]
        orders = orders[orders["order_status"].isin(REVENUE_STATUSES)].copy()
        orders["order_purchase_timestamp"] = pd.to_datetime(
            orders["order_purchase_timestamp"]
        )
        items = d["order_items"]
        customers = d["customers"]
        merged = orders.merge(customers, on="customer_id")
        merged = merged.merge(items, on="order_id")
        return merged

    def _customer_rfm(self) -> pd.DataFrame:
        facts = self._order_facts()
        snapshot = facts["order_purchase_timestamp"].max()
        order_rev = facts.groupby("order_id").agg(
            customer_unique_id=("customer_unique_id", "first"),
            order_date=("order_purchase_timestamp", "first"),
            monetary=("price", "sum"),
        ).reset_index()
        rfm = order_rev.groupby("customer_unique_id").agg(
            recency=("order_date", lambda s: (snapshot - s.max()).days),
            frequency=("order_id", "nunique"),
            monetary=("monetary", "sum"),
        )
        return rfm.reset_index()

    def _score_quintile(self, series: pd.Series, ascending: bool = True) -> pd.Series:
        ranked = series.rank(method="first", ascending=ascending)
        return pd.qcut(ranked, 5, labels=[1, 2, 3, 4, 5], duplicates="drop").astype(int)

    def get_executive_dashboard(self) -> dict[str, Any]:
        svc = self
        kpis = svc.get_executive_summary()
        customers = svc.get_customer_metrics()
        monthly = pd.DataFrame(svc.get_monthly_revenue())
        states = pd.DataFrame(svc.get_revenue_by_state(12))
        payments = pd.DataFrame(svc.get_payment_mix())

        charts: dict[str, dict] = {}

        if not monthly.empty:
            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=monthly["month"],
                    y=monthly["revenue"],
                    mode="lines+markers",
                    name="Revenue",
                    line={"color": "#2563eb", "width": 2.5},
                    fill="tozeroy",
                    fillcolor="rgba(37, 99, 235, 0.08)",
                )
            )
            charts["revenue_trend"] = self._fig_data(fig, "Revenue Trend", 340)

            fig2 = go.Figure()
            fig2.add_trace(
                go.Bar(
                    x=monthly["month"],
                    y=monthly["orders"],
                    marker_color="#1e3a5f",
                    name="Orders",
                )
            )
            charts["orders_trend"] = self._fig_data(fig2, "Orders Trend", 340)

        if not states.empty:
            fig = px.bar(
                states,
                x="state",
                y="revenue",
                labels={"state": "State", "revenue": "Revenue (R$)"},
            )
            fig.update_traces(marker_color="#0ea5e9")
            charts["top_states"] = self._fig_data(fig, "Top States by Revenue", 340)

        if not payments.empty:
            fig = px.pie(
                payments,
                names="payment_type",
                values="total_value",
                hole=0.45,
                labels={"payment_type": "Method", "total_value": "Volume"},
            )
            fig.update_traces(textposition="inside", textinfo="percent+label")
            charts["payment_methods"] = self._fig_data(fig, "Payment Methods", 340)

        return {
            "kpis": {**kpis, "repeat_rate_pct": customers.get("repeat_rate_pct", 0)},
            "charts": charts,
            "data_source": self.data_source,
        }

    def get_customer_analytics(self) -> dict[str, Any]:
        rfm = self._customer_rfm()
        facts = self._order_facts()
        metrics = self.get_customer_metrics()

        rfm["R"] = self._score_quintile(rfm["recency"], ascending=True)
        rfm["F"] = self._score_quintile(rfm["frequency"], ascending=False)
        rfm["M"] = self._score_quintile(rfm["monetary"], ascending=False)
        rfm["RFM_score"] = rfm["R"].astype(str) + rfm["F"].astype(str) + rfm["M"].astype(str)

        def segment(row: pd.Series) -> str:
            if row["R"] >= 4 and row["F"] >= 4:
                return "Champions"
            if row["R"] >= 3 and row["F"] >= 3:
                return "Loyal"
            if row["R"] <= 2 and row["F"] >= 3:
                return "At Risk"
            if row["R"] <= 2:
                return "Hibernating"
            return "Potential"

        rfm["segment"] = rfm.apply(segment, axis=1)
        rfm["clv"] = rfm["monetary"]

        seg_counts = rfm["segment"].value_counts().reset_index()
        seg_counts.columns = ["segment", "customers"]

        charts: dict[str, dict] = {}

        fig = px.pie(
            seg_counts,
            names="segment",
            values="customers",
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        charts["segmentation"] = self._fig_data(fig, "Customer Segmentation", 360)

        sample = rfm.sample(min(2500, len(rfm)), random_state=42)
        fig = px.scatter(
            sample,
            x="recency",
            y="monetary",
            size="frequency",
            color="segment",
            hover_data=["RFM_score"],
            labels={
                "recency": "Recency (days)",
                "monetary": "Monetary (R$)",
                "frequency": "Orders",
            },
        )
        charts["rfm"] = self._fig_data(fig, "RFM Analysis", 380)

        fig = px.histogram(
            rfm,
            x="clv",
            nbins=40,
            labels={"clv": "Customer Lifetime Value (R$)"},
            color_discrete_sequence=["#2563eb"],
        )
        charts["clv"] = self._fig_data(fig, "Customer Lifetime Value Distribution", 340)

        repeat_df = pd.DataFrame(
            [
                {"type": "One-time", "count": metrics["unique_customers"] - metrics["repeat_customers"]},
                {"type": "Repeat", "count": metrics["repeat_customers"]},
            ]
        )
        fig = px.bar(
            repeat_df,
            x="type",
            y="count",
            text="count",
            color="type",
            color_discrete_map={"Repeat": "#14b8a6", "One-time": "#94a3b8"},
        )
        fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
        charts["repeat_customers"] = self._fig_data(fig, "Repeat vs One-time Customers", 320)

        state_dist = (
            facts.groupby("customer_state")["customer_unique_id"]
            .nunique()
            .nlargest(15)
            .reset_index()
            .rename(columns={"customer_state": "state", "customer_unique_id": "customers"})
        )
        fig = px.bar(
            state_dist,
            x="state",
            y="customers",
            labels={"state": "State", "customers": "Unique Customers"},
        )
        fig.update_traces(marker_color="#6366f1")
        charts["state_distribution"] = self._fig_data(fig, "Customer Distribution by State", 340)

        order_freq = facts.groupby("customer_unique_id")["order_id"].nunique()
        freq_bins = pd.cut(
            order_freq,
            bins=[0, 1, 2, 3, 5, 1000],
            labels=["1", "2", "3", "4-5", "6+"],
        ).value_counts().reset_index()
        freq_bins.columns = ["orders", "customers"]
        fig = px.bar(
            freq_bins,
            x="orders",
            y="customers",
            labels={"orders": "Orders per customer", "customers": "Customers"},
        )
        fig.update_traces(marker_color="#1e3a5f")
        charts["order_frequency"] = self._fig_data(fig, "Order Frequency Distribution", 320)

        avg_clv = float(rfm["clv"].mean())
        median_clv = float(rfm["clv"].median())

        return {
            "kpis": {
                **metrics,
                "avg_clv": round(avg_clv, 2),
                "median_clv": round(median_clv, 2),
                "champions": int((rfm["segment"] == "Champions").sum()),
            },
            "charts": charts,
            "data_source": self.data_source,
        }

    def get_product_analytics(self) -> dict[str, Any]:
        categories = pd.DataFrame(self.get_top_categories(15))
        facts = self._order_facts()
        d = self._load_csv_frames()
        products = d["products"].merge(
            d["category_translation"],
            on="product_category_name",
            how="left",
        )
        products["category"] = products["product_category_name_english"].fillna(
            products["product_category_name"]
        )

        cat_rev = (
            facts.merge(products[["product_id", "category"]], on="product_id", how="left")
            .groupby("category")
            .agg(revenue=("price", "sum"), units=("order_item_id", "count"))
            .nlargest(20, "revenue")
            .reset_index()
        )

        charts: dict[str, dict] = {}

        if not categories.empty:
            fig = px.bar(
                categories.head(10),
                x="revenue",
                y="category",
                orientation="h",
                labels={"category": "Category", "revenue": "Revenue (R$)"},
            )
            fig.update_traces(marker_color="#2563eb")
            charts["top_categories"] = self._fig_data(fig, "Top Categories", 380)

        fig = px.bar(
            cat_rev.head(12),
            x="category",
            y="revenue",
            labels={"category": "Category", "revenue": "Revenue (R$)"},
        )
        fig.update_traces(marker_color="#0ea5e9")
        charts["revenue_by_category"] = self._fig_data(fig, "Revenue by Category", 360)

        fig = px.treemap(
            cat_rev,
            path=["category"],
            values="revenue",
            color="revenue",
            color_continuous_scale="Blues",
        )
        charts["treemap"] = self._fig_data(fig, "Category Revenue Treemap", 400)

        prod_perf = (
            facts.groupby("product_id")
            .agg(revenue=("price", "sum"), units=("order_item_id", "count"))
            .nlargest(500, "revenue")
            .reset_index()
            .merge(
                products[["product_id", "category", "product_name_lenght", "product_weight_g"]],
                on="product_id",
                how="left",
            )
        )
        prod_perf["product_name_lenght"] = pd.to_numeric(
            prod_perf["product_name_lenght"], errors="coerce"
        ).fillna(0)
        prod_perf["product_weight_g"] = pd.to_numeric(
            prod_perf["product_weight_g"], errors="coerce"
        ).fillna(0)

        sample = prod_perf.sample(min(400, len(prod_perf)), random_state=7)
        fig = px.scatter(
            sample,
            x="units",
            y="revenue",
            size="product_weight_g",
            color="category",
            hover_name="product_id",
            labels={"units": "Units Sold", "revenue": "Revenue (R$)"},
        )
        charts["scatter"] = self._fig_data(fig, "Product Performance Scatter", 400)

        matrix = (
            facts.merge(products[["product_id", "category"]], on="product_id")
            .groupby("category")
            .agg(revenue=("price", "sum"), units=("order_item_id", "count"), orders=("order_id", "nunique"))
            .reset_index()
        )
        matrix["avg_unit_price"] = matrix["revenue"] / matrix["units"].clip(lower=1)
        fig = px.scatter(
            matrix,
            x="units",
            y="revenue",
            size="orders",
            color="avg_unit_price",
            text="category",
            color_continuous_scale="Viridis",
            labels={
                "units": "Units",
                "revenue": "Revenue (R$)",
                "orders": "Orders",
                "avg_unit_price": "Avg unit price",
            },
        )
        fig.update_traces(textposition="top center")
        charts["performance_matrix"] = self._fig_data(fig, "Category Performance Matrix", 420)

        total_rev = float(cat_rev["revenue"].sum())
        top_cat = cat_rev.iloc[0]["category"] if len(cat_rev) else "—"

        return {
            "kpis": {
                "categories_tracked": len(cat_rev),
                "total_category_revenue": round(total_rev, 2),
                "top_category": top_cat,
            },
            "charts": charts,
            "data_source": self.data_source,
        }

    def get_advanced_analytics(self) -> dict[str, Any]:
        rfm = self._customer_rfm()
        monthly = pd.DataFrame(self.get_monthly_revenue())
        charts: dict[str, dict] = {}
        recommendations: list[dict[str, str]] = []

        # K-Means clustering
        features = rfm[["recency", "frequency", "monetary"]].copy()
        sample_n = min(4000, len(features))
        idx = features.sample(sample_n, random_state=11).index
        X = features.loc[idx]
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        kmeans = KMeans(n_clusters=4, random_state=42, n_init=10)
        clusters = kmeans.fit_predict(X_scaled)
        cluster_df = X.copy()
        cluster_df["cluster"] = [f"Cluster {c + 1}" for c in clusters]

        fig = px.scatter(
            cluster_df,
            x="recency",
            y="monetary",
            color="cluster",
            size="frequency",
            labels={"recency": "Recency", "monetary": "Monetary (R$)"},
        )
        charts["clustering"] = self._fig_data(fig, "K-Means Customer Clustering", 400)

        # Revenue forecasting
        if len(monthly) >= 6:
            monthly = monthly.sort_values("month")
            monthly["t"] = np.arange(len(monthly))
            train = monthly.iloc[:-3]
            test = monthly.iloc[-3:]
            model = LinearRegression()
            model.fit(train[["t"]], train["revenue"])
            future_t = np.arange(len(monthly), len(monthly) + 3, dtype=float).reshape(-1, 1)
            forecast_vals = model.predict(future_t)
            last_month = pd.Period(monthly["month"].iloc[-1], freq="M").to_timestamp()
            future_months = pd.date_range(last_month, periods=4, freq="MS")[1:]
            future_labels = [d.strftime("%Y-%m") for d in future_months]

            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=monthly["month"],
                    y=monthly["revenue"],
                    name="Actual",
                    mode="lines+markers",
                    line={"color": "#2563eb"},
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=future_labels,
                    y=forecast_vals,
                    name="Forecast",
                    mode="lines+markers",
                    line={"color": "#f59e0b", "dash": "dash"},
                )
            )
            charts["forecast"] = self._fig_data(fig, "Revenue Forecast (3 months)", 380)

            growth = (forecast_vals[-1] - monthly["revenue"].iloc[-1]) / max(
                monthly["revenue"].iloc[-1], 1
            )
            recommendations.append(
                {
                    "priority": "high",
                    "title": "Revenue outlook",
                    "detail": f"Projected 3-month trend suggests "
                    f"{'growth' if growth > 0 else 'decline'} "
                    f"of {abs(growth) * 100:.1f}% vs latest month.",
                }
            )

        # Correlation analysis
        corr_df = monthly[["revenue", "freight", "gmv", "orders"]].corr() if not monthly.empty else pd.DataFrame()
        if not corr_df.empty:
            fig = px.imshow(
                corr_df,
                text_auto=".2f",
                color_continuous_scale="RdBu_r",
                zmin=-1,
                zmax=1,
            )
            charts["correlation"] = self._fig_data(fig, "Metric Correlation Matrix", 380)
            rev_orders = corr_df.loc["revenue", "orders"] if "orders" in corr_df else 0
            recommendations.append(
                {
                    "priority": "medium",
                    "title": "Revenue–orders correlation",
                    "detail": f"Correlation coefficient: {rev_orders:.2f}. "
                    "Align inventory and marketing with order volume patterns.",
                }
            )

        metrics = self.get_customer_metrics()
        if metrics.get("repeat_rate_pct", 0) < 25:
            recommendations.append(
                {
                    "priority": "high",
                    "title": "Retention opportunity",
                    "detail": f"Repeat rate is {metrics['repeat_rate_pct']}%. "
                    "Launch win-back campaigns for one-time buyers.",
                }
            )
        else:
            recommendations.append(
                {
                    "priority": "low",
                    "title": "Strong retention",
                    "detail": f"Repeat rate at {metrics['repeat_rate_pct']}% — "
                    "prioritize loyalty rewards for champions segment.",
                }
            )

        payments = pd.DataFrame(self.get_payment_mix())
        if not payments.empty:
            top_pay = payments.sort_values("total_value", ascending=False).iloc[0]
            recommendations.append(
                {
                    "priority": "medium",
                    "title": "Payment optimization",
                    "detail": f"Dominant method: {top_pay['payment_type']}. "
                    "Ensure checkout UX prioritizes this flow and monitor installment costs.",
                }
            )

        states = pd.DataFrame(self.get_revenue_by_state(5))
        if not states.empty:
            top_state = states.iloc[0]["state"]
            recommendations.append(
                {
                    "priority": "medium",
                    "title": "Regional focus",
                    "detail": f"State {top_state} leads revenue — "
                    "consider regional promotions and faster shipping SLAs.",
                }
            )

        cluster_summary = (
            cluster_df.groupby("cluster")["monetary"].mean().sort_values(ascending=False)
        )
        if len(cluster_summary):
            recommendations.append(
                {
                    "priority": "high",
                    "title": "Cluster targeting",
                    "detail": f"Highest-value cluster avg spend R$ {cluster_summary.iloc[0]:,.0f}. "
                    "Personalize offers for low-frequency, high-recency clusters.",
                }
            )

        return {
            "kpis": {
                "clusters": 4,
                "customers_analyzed": sample_n,
                "recommendations_count": len(recommendations),
            },
            "charts": charts,
            "recommendations": recommendations,
            "data_source": self.data_source,
        }

    def _csv_from_frames(self, frames: list[tuple[str, pd.DataFrame]]) -> str:
        parts: list[pd.DataFrame] = []
        for label, df in frames:
            if df is None or df.empty:
                continue
            chunk = df.copy()
            chunk.insert(0, "dataset", label)
            parts.append(chunk)
        if not parts:
            return "dataset,message\nexport,No data available\n"
        return pd.concat(parts, ignore_index=True).to_csv(index=False)

    def export_page_csv(self, page: str) -> tuple[str, str]:
        """Return (filename, csv_string) for dashboard export."""
        page = page.lower().strip()
        if page == "executive":
            kpis = {**self.get_executive_summary(), **self.get_customer_metrics()}
            kpi_df = pd.DataFrame([{"metric": k, "value": v} for k, v in kpis.items()])
            frames = [
                ("kpis", kpi_df),
                ("monthly_revenue", pd.DataFrame(self.get_monthly_revenue())),
                ("revenue_by_state", pd.DataFrame(self.get_revenue_by_state(50))),
                ("payment_mix", pd.DataFrame(self.get_payment_mix())),
            ]
            filename = "executive_dashboard.csv"
        elif page == "customers":
            rfm = self._customer_rfm()
            rfm["R"] = self._score_quintile(rfm["recency"], ascending=True)
            rfm["F"] = self._score_quintile(rfm["frequency"], ascending=False)
            rfm["M"] = self._score_quintile(rfm["monetary"], ascending=False)
            seg = rfm.assign(segment=self._rfm_segment(rfm)).groupby("segment").size().reset_index(name="customers")
            facts = self._order_facts()
            state_df = (
                facts.groupby("customer_state")["customer_unique_id"]
                .nunique()
                .nlargest(30)
                .reset_index(name="customers")
            )
            frames = [
                ("segment_summary", seg),
                ("rfm_sample", rfm.head(2000)),
                ("customers_by_state", state_df),
            ]
            filename = "customer_analytics.csv"
        elif page == "products":
            frames = [
                ("top_categories", pd.DataFrame(self.get_top_categories(50))),
            ]
            facts = self._order_facts()
            d = self._load_csv_frames()
            products = d["products"].merge(
                d["category_translation"], on="product_category_name", how="left"
            )
            products["category"] = products["product_category_name_english"].fillna(
                products["product_category_name"]
            )
            cat_rev = (
                facts.merge(products[["product_id", "category"]], on="product_id", how="left")
                .groupby("category")
                .agg(revenue=("price", "sum"), units=("order_item_id", "count"))
                .nlargest(50, "revenue")
                .reset_index()
            )
            frames.append(("category_revenue", cat_rev))
            filename = "product_analytics.csv"
        elif page == "advanced":
            recs = pd.DataFrame(self.get_advanced_analytics().get("recommendations", []))
            monthly = pd.DataFrame(self.get_monthly_revenue())
            rfm = self._customer_rfm().head(2000)
            frames = [
                ("recommendations", recs),
                ("monthly_metrics", monthly),
                ("customer_rfm_sample", rfm),
            ]
            filename = "advanced_analytics.csv"
        else:
            raise ValueError(f"Unknown export page: {page}")
        return filename, self._csv_from_frames(frames)

    def _rfm_segment(self, rfm: pd.DataFrame) -> pd.Series:
        def segment(row: pd.Series) -> str:
            if row["R"] >= 4 and row["F"] >= 4:
                return "Champions"
            if row["R"] >= 3 and row["F"] >= 3:
                return "Loyal"
            if row["R"] <= 2 and row["F"] >= 3:
                return "At Risk"
            if row["R"] <= 2:
                return "Hibernating"
            return "Potential"

        return rfm.apply(segment, axis=1)
