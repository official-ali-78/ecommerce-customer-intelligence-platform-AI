# Olist dataset (not included in Git)

GitHub does not allow large CSV files. **Do not commit** files from this folder.

## Option A — Kaggle (full dataset)

1. Create a [Kaggle](https://www.kaggle.com) account.
2. Download [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce).
3. Copy all `*.csv` files into this `dataset/` folder.

Required files (only these six are used by the app):

- `olist_orders_dataset.csv`
- `olist_order_items_dataset.csv`
- `olist_customers_dataset.csv`
- `olist_products_dataset.csv`
- `olist_order_payments_dataset.csv`
- `product_category_name_translation.csv`

Other Kaggle files (geolocation, sellers, reviews) are not needed.

When these files are present, the app uses them automatically (no cleaning step).

## Option B — Demo data (default)

If `dataset/` is empty, the app uses the small bundled files in `data/sample/` so the dashboards work out of the box after `git clone`.

## Optional: Kaggle Hub

```bash
pip install kagglehub
python -c "import kagglehub; print(kagglehub.dataset_download('olistbr/brazilian-ecommerce'))"
```

Copy the downloaded CSVs into `dataset/`.
