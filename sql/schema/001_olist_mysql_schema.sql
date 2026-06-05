-- =============================================================================
-- Olist Brazilian E-Commerce — Production MySQL Schema
-- Engine: InnoDB | Charset: utf8mb4 | Collation: utf8mb4_unicode_ci
--
-- Load order (respects foreign keys):
--   1. product_category_name_translation
--   2. geolocation
--   3. customers, sellers, products
--   4. orders
--   5. order_items, order_payments, order_reviews
-- =============================================================================

SET NAMES utf8mb4;

CREATE DATABASE IF NOT EXISTS ecommerce_analytics
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE ecommerce_analytics;

SET FOREIGN_KEY_CHECKS = 0;

-- ---------------------------------------------------------------------------
-- Reference / lookup
-- ---------------------------------------------------------------------------

DROP TABLE IF EXISTS order_reviews;
DROP TABLE IF EXISTS order_payments;
DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS sellers;
DROP TABLE IF EXISTS geolocation;
DROP TABLE IF EXISTS product_category_name_translation;

SET FOREIGN_KEY_CHECKS = 1;

-- Portuguese → English category labels (71 rows)
CREATE TABLE product_category_name_translation (
    product_category_name         VARCHAR(100)  NOT NULL,
    product_category_name_english VARCHAR(100)  NOT NULL,
    created_at                    TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at                    TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (product_category_name)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='Product category display names (PT → EN)';

-- Zip-prefix reference; source has multiple lat/lng rows per prefix (~1M rows)
CREATE TABLE geolocation (
    geolocation_id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    geolocation_zip_code_prefix CHAR(8)         NOT NULL,
    geolocation_lat             DECIMAL(10, 7)  NOT NULL,
    geolocation_lng             DECIMAL(10, 7)  NOT NULL,
    geolocation_city            VARCHAR(120)    NOT NULL,
    geolocation_state           CHAR(2)         NOT NULL,
    created_at                  TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (geolocation_id),
    KEY idx_geolocation_zip_prefix (geolocation_zip_code_prefix),
    KEY idx_geolocation_state_city (geolocation_state, geolocation_city)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='CEP prefix coordinates (dedupe in ETL for dim_geography)';

-- ---------------------------------------------------------------------------
-- Dimensions (operational)
-- ---------------------------------------------------------------------------

-- One row per order in source; customer_id is order-level surrogate
CREATE TABLE customers (
    customer_id              CHAR(32)     NOT NULL,
    customer_unique_id       CHAR(32)     NOT NULL COMMENT 'Business key for repeat-customer analytics',
    customer_zip_code_prefix CHAR(8)      NOT NULL,
    customer_city            VARCHAR(120) NOT NULL,
    customer_state           CHAR(2)      NOT NULL,
    created_at               TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at               TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (customer_id),
    KEY idx_customers_unique_id (customer_unique_id),
    KEY idx_customers_geo (customer_state, customer_city),
    KEY idx_customers_zip (customer_zip_code_prefix)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='Customer shipping profile per order';

CREATE TABLE sellers (
    seller_id              CHAR(32)     NOT NULL,
    seller_zip_code_prefix CHAR(8)      NOT NULL,
    seller_city            VARCHAR(120) NOT NULL,
    seller_state           CHAR(2)      NOT NULL,
    created_at             TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at             TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (seller_id),
    KEY idx_sellers_geo (seller_state, seller_city),
    KEY idx_sellers_zip (seller_zip_code_prefix)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='Marketplace seller locations';

CREATE TABLE products (
    product_id                   CHAR(32)       NOT NULL,
    product_category_name        VARCHAR(100)   NULL,
    product_name_lenght          SMALLINT UNSIGNED NULL COMMENT 'Source column spelling preserved',
    product_description_lenght   SMALLINT UNSIGNED NULL,
    product_photos_qty           TINYINT UNSIGNED NULL,
    product_weight_g             INT UNSIGNED   NULL,
    product_length_cm            DECIMAL(8, 2)  NULL,
    product_height_cm            DECIMAL(8, 2)  NULL,
    product_width_cm             DECIMAL(8, 2)  NULL,
    created_at                   TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at                   TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (product_id),
    KEY idx_products_category (product_category_name),
    CONSTRAINT fk_products_category
        FOREIGN KEY (product_category_name)
        REFERENCES product_category_name_translation (product_category_name)
        ON UPDATE CASCADE
        ON DELETE SET NULL
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='Product catalog and physical attributes';

-- ---------------------------------------------------------------------------
-- Facts / transactions
-- ---------------------------------------------------------------------------

CREATE TABLE orders (
    order_id                      CHAR(32)    NOT NULL,
    customer_id                   CHAR(32)    NOT NULL,
    order_status                  VARCHAR(20) NOT NULL,
    order_purchase_timestamp      DATETIME    NOT NULL,
    order_approved_at             DATETIME    NULL,
    order_delivered_carrier_date  DATETIME    NULL,
    order_delivered_customer_date DATETIME    NULL,
    order_estimated_delivery_date DATETIME    NULL,
    created_at                    TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at                    TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (order_id),
    KEY idx_orders_customer (customer_id),
    KEY idx_orders_status (order_status),
    KEY idx_orders_purchase_ts (order_purchase_timestamp),
    KEY idx_orders_delivered_ts (order_delivered_customer_date),
    CONSTRAINT fk_orders_customer
        FOREIGN KEY (customer_id)
        REFERENCES customers (customer_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT chk_orders_status CHECK (
        order_status IN (
            'created', 'approved', 'processing', 'invoiced',
            'shipped', 'delivered', 'canceled', 'unavailable'
        )
    )
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='Order header and lifecycle timestamps';

-- Marketplace line items (grain: one product line per order)
CREATE TABLE order_items (
    order_id             CHAR(32)        NOT NULL,
    order_item_id        TINYINT UNSIGNED NOT NULL COMMENT 'Line sequence within order (1–21 in source)',
    product_id           CHAR(32)        NOT NULL,
    seller_id            CHAR(32)        NOT NULL,
    shipping_limit_date  DATETIME        NOT NULL,
    price                DECIMAL(10, 2)  NOT NULL,
    freight_value        DECIMAL(10, 2)  NOT NULL,
    created_at           TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (order_id, order_item_id),
    KEY idx_order_items_product (product_id),
    KEY idx_order_items_seller (seller_id),
    KEY idx_order_items_shipping_limit (shipping_limit_date),
    CONSTRAINT fk_order_items_order
        FOREIGN KEY (order_id)
        REFERENCES orders (order_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT fk_order_items_product
        FOREIGN KEY (product_id)
        REFERENCES products (product_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT fk_order_items_seller
        FOREIGN KEY (seller_id)
        REFERENCES sellers (seller_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT chk_order_items_price_nonneg CHECK (price >= 0),
    CONSTRAINT chk_order_items_freight_nonneg CHECK (freight_value >= 0)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='Order line items (revenue grain)';

-- Split payments per order (vouchers, multiple cards, etc.)
CREATE TABLE order_payments (
    order_id              CHAR(32)        NOT NULL,
    payment_sequential    TINYINT UNSIGNED NOT NULL COMMENT 'Payment split sequence (1–29 in source)',
    payment_type          VARCHAR(20)     NOT NULL,
    payment_installments  SMALLINT UNSIGNED NOT NULL DEFAULT 1,
    payment_value         DECIMAL(10, 2)  NOT NULL,
    created_at            TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (order_id, payment_sequential),
    KEY idx_order_payments_type (payment_type),
    CONSTRAINT fk_order_payments_order
        FOREIGN KEY (order_id)
        REFERENCES orders (order_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT chk_order_payments_type CHECK (
        payment_type IN ('credit_card', 'boleto', 'voucher', 'debit_card', 'not_defined')
    ),
    CONSTRAINT chk_order_payments_installments CHECK (payment_installments >= 1),
    CONSTRAINT chk_order_payments_value_nonneg CHECK (payment_value >= 0)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='Payment splits and methods per order';

-- review_id is unique per order_id only (not globally unique in source)
CREATE TABLE order_reviews (
    order_id                 CHAR(32)       NOT NULL,
    review_id                CHAR(32)       NOT NULL,
    review_score             TINYINT UNSIGNED NOT NULL,
    review_comment_title     VARCHAR(255)   NULL,
    review_comment_message   TEXT           NULL,
    review_creation_date     DATETIME       NOT NULL,
    review_answer_timestamp  DATETIME       NULL,
    created_at               TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at               TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (order_id, review_id),
    KEY idx_order_reviews_score (review_score),
    KEY idx_order_reviews_creation (review_creation_date),
    CONSTRAINT fk_order_reviews_order
        FOREIGN KEY (order_id)
        REFERENCES orders (order_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT chk_order_reviews_score CHECK (review_score BETWEEN 1 AND 5)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='Customer satisfaction reviews (1–N per order)';
