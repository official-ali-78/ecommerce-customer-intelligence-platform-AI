# Olist E-Commerce Analytics Platform

A **4-page Flask web app** with Plotly dashboards for Brazilian Olist e-commerce data.

| Page | URL |
|------|-----|
| Executive Dashboard | `/analytics/executive` |
| Customer Analytics | `/analytics/customers` |
| Product Analytics | `/analytics/products` |
| Advanced Analytics | `/analytics/advanced` |

## Features

- Bootstrap 5 sidebar layout, light/dark mode, glassmorphism UI
- Interactive Plotly charts, chart PNG download, CSV export
- Customer RFM, segmentation, CLV, product treemap, K-Means, forecasting
- **No cleaned-data pipeline** — reads raw Olist CSVs from `dataset/` directly

## Quick start (GitHub clone)

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
flask --app app run --debug
```

Open http://127.0.0.1:5000 — uses bundled **demo data** in `data/sample/` (~100 KB).

## Full Olist dataset

Place Kaggle CSV files in `dataset/` (see [dataset/README.md](dataset/README.md)).  
Large files are gitignored; the app picks `dataset/` over `data/sample/` when present.

## Optional MySQL

Set `USE_MYSQL=true` in `.env` and load the schema from `sql/schema/`.  
By default the app runs on CSV only — no database required.

## Project layout

```
app.py                  # Flask entry
routes/main.py          # 4 dashboard routes
services/
  data_loader.py        # dataset/ or data/sample/
  analytics_service.py  # KPIs
  chart_analytics.py    # Plotly + ML pages
data/sample/            # Small demo CSVs (committed)
dataset/                # Your Olist CSVs (gitignored)
templates/analytics/    # 4 HTML pages
sql/schema/             # Optional MySQL setup
```

## Regenerate demo sample (optional)

```bash
python scripts/build_sample_data.py
```
