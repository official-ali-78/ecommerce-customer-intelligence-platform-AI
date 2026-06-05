"""One-time helper to regenerate tiny demo CSVs in data/sample/ (GitHub-safe sizes)."""

from __future__ import annotations

import random
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "sample"
random.seed(42)

STATES = ["SP", "RJ", "MG", "RS", "PR", "BA", "SC"]
CATEGORIES_PT = [
    "cama_mesa_banho",
    "esporte_lazer",
    "moveis_decoracao",
    "beleza_saude",
    "informatica_acessorios",
]
CATEGORIES_EN = [
    "bed_bath_table",
    "sports_leisure",
    "furniture_decor",
    "health_beauty",
    "computers_accessories",
]
PAYMENTS = ["credit_card", "boleto", "voucher", "debit_card"]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    customers = pd.DataFrame(
        {
            "customer_id": [f"c{i:04d}" for i in range(120)],
            "customer_unique_id": [f"u{i:04d}" for i in range(120)],
            "customer_zip_code_prefix": [random.randint(10000, 99999) for _ in range(120)],
            "customer_city": ["City"] * 120,
            "customer_state": [random.choice(STATES) for _ in range(120)],
        }
    )
    products = pd.DataFrame(
        {
            "product_id": [f"p{i:03d}" for i in range(40)],
            "product_category_name": [random.choice(CATEGORIES_PT) for _ in range(40)],
            "product_name_lenght": [random.randint(10, 60) for _ in range(40)],
            "product_description_lenght": [random.randint(50, 500) for _ in range(40)],
            "product_photos_qty": [random.randint(1, 5) for _ in range(40)],
            "product_weight_g": [random.randint(200, 5000) for _ in range(40)],
            "product_length_cm": [random.randint(10, 80) for _ in range(40)],
            "product_height_cm": [random.randint(5, 50) for _ in range(40)],
            "product_width_cm": [random.randint(10, 60) for _ in range(40)],
        }
    )
    months = pd.date_range("2017-01-01", "2018-08-01", freq="MS")
    orders_rows = []
    items_rows = []
    pay_rows = []
    for i in range(280):
        oid = f"o{i:05d}"
        cid = f"c{i % 120:04d}"
        ts = random.choice(months) + pd.Timedelta(days=random.randint(0, 27))
        status = random.choices(
            ["delivered", "shipped", "invoiced", "canceled"],
            weights=[75, 10, 8, 7],
        )[0]
        delivered = ts + pd.Timedelta(days=random.randint(3, 20))
        orders_rows.append(
            {
                "order_id": oid,
                "customer_id": cid,
                "order_status": status,
                "order_purchase_timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
                "order_approved_at": (ts + pd.Timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S"),
                "order_delivered_carrier_date": (ts + pd.Timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S"),
                "order_delivered_customer_date": delivered.strftime("%Y-%m-%d %H:%M:%S"),
                "order_estimated_delivery_date": (delivered + pd.Timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
        pid = f"p{random.randint(0, 39):03d}"
        price = round(random.uniform(20, 400), 2)
        freight = round(random.uniform(5, 40), 2)
        items_rows.append(
            {
                "order_id": oid,
                "order_item_id": 1,
                "product_id": pid,
                "seller_id": f"s{random.randint(1, 20):03d}",
                "shipping_limit_date": (ts + pd.Timedelta(days=5)).strftime("%Y-%m-%d %H:%M:%S"),
                "price": price,
                "freight_value": freight,
            }
        )
        pay_rows.append(
            {
                "order_id": oid,
                "payment_sequential": 1,
                "payment_type": random.choice(PAYMENTS),
                "payment_installments": random.randint(1, 6),
                "payment_value": round(price + freight, 2),
            }
        )
    orders = pd.DataFrame(orders_rows)
    order_items = pd.DataFrame(items_rows)
    order_payments = pd.DataFrame(pay_rows)
    category_translation = pd.DataFrame(
        {
            "product_category_name": CATEGORIES_PT,
            "product_category_name_english": CATEGORIES_EN,
        }
    )
    customers.to_csv(OUT / "customers.csv", index=False)
    products.to_csv(OUT / "products.csv", index=False)
    orders.to_csv(OUT / "orders.csv", index=False)
    order_items.to_csv(OUT / "order_items.csv", index=False)
    order_payments.to_csv(OUT / "order_payments.csv", index=False)
    category_translation.to_csv(OUT / "category_translation.csv", index=False)
    print(f"Wrote demo sample to {OUT}")


if __name__ == "__main__":
    main()
