"""Corporate Plotly layout theme for analytics dashboards."""

from __future__ import annotations

CORPORATE_LAYOUT = {
    "paper_bgcolor": "rgba(0,0,0,0)",
    "plot_bgcolor": "rgba(0,0,0,0)",
    "font": {"family": "Plus Jakarta Sans, system-ui, sans-serif", "color": "#334155", "size": 12},
    "margin": {"l": 48, "r": 24, "t": 48, "b": 48},
    "colorway": [
        "#1e3a5f",
        "#2563eb",
        "#0ea5e9",
        "#14b8a6",
        "#6366f1",
        "#8b5cf6",
        "#64748b",
    ],
    "legend": {"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0},
    "xaxis": {
        "gridcolor": "#e2e8f0",
        "linecolor": "#cbd5e1",
        "zerolinecolor": "#e2e8f0",
    },
    "yaxis": {
        "gridcolor": "#e2e8f0",
        "linecolor": "#cbd5e1",
        "zerolinecolor": "#e2e8f0",
    },
}


def apply_layout(fig, title: str | None = None, height: int = 360) -> None:
    layout = {**CORPORATE_LAYOUT, "height": height, "autosize": True}
    if title:
        layout["title"] = {"text": title, "font": {"size": 14, "color": "#0f172a"}}
    fig.update_layout(**layout)
