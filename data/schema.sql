-- P30 — Executive KPI & Stakeholder Reporting Pack: schema (NoorMart).
-- Staging tables hold the SAMPLE CSVs verbatim (all text, as exported).
-- Target tables are the clean star schema the pack is built from:
-- dim_product / dim_customer dimensions + fact_sales (line level) +
-- monthly_kpi (the pack's KPI table, built by sql/01_monthly_kpi.sql)
-- and monthly_targets (the management plan).
-- The .db rebuilds from the scripts and is never committed.
-- Run: sqlite3 data/processed/noormart.db < data/schema.sql
-- (or via src/load_data.py, which runs the schema + all sql/ files).

DROP TABLE IF EXISTS stg_daily_sales;
DROP TABLE IF EXISTS stg_monthly_targets;
DROP TABLE IF EXISTS stg_prior_year;
DROP TABLE IF EXISTS dim_product;
DROP TABLE IF EXISTS dim_customer;
DROP TABLE IF EXISTS fact_sales;
DROP TABLE IF EXISTS monthly_targets;
DROP TABLE IF EXISTS monthly_prior_year;
DROP TABLE IF EXISTS monthly_kpi;
DROP TABLE IF EXISTS category_monthly;

-- ---------- staging: SAMPLE files, verbatim ----------
CREATE TABLE stg_daily_sales (
    row_no         INTEGER PRIMARY KEY,   -- 1-based line in the source file
    order_id       TEXT,
    sale_date      TEXT,
    customer_id    TEXT,
    customer_type  TEXT,
    channel        TEXT,
    product        TEXT,
    category       TEXT,
    qty            TEXT,
    unit_price_pkr TEXT,
    unit_cost_pkr  TEXT,
    line_amount_pkr TEXT,
    returned       TEXT
);

CREATE TABLE stg_monthly_targets (
    row_no                    INTEGER PRIMARY KEY,
    month                     TEXT,
    revenue_target_pkr        TEXT,
    orders_target             TEXT,
    gross_margin_pct_target   TEXT,
    returns_rate_pct_target   TEXT,
    new_customers_target      TEXT
);

CREATE TABLE stg_prior_year (
    row_no         INTEGER PRIMARY KEY,
    month          TEXT,
    revenue_pkr    TEXT,
    orders         TEXT,
    new_customers  TEXT
);

-- ---------- target: star schema ----------
CREATE TABLE dim_product (
    product_key     INTEGER PRIMARY KEY,
    product_name    TEXT NOT NULL UNIQUE,
    category        TEXT NOT NULL,
    base_price_pkr  REAL NOT NULL,
    margin_pct      REAL NOT NULL          -- category margin, e.g. 0.16
);

CREATE TABLE dim_customer (
    customer_key    INTEGER PRIMARY KEY,
    customer_id     TEXT NOT NULL UNIQUE,  -- CUST-nnn, as in the source
    first_order_id  TEXT NOT NULL,
    first_order_date TEXT NOT NULL         -- ISO YYYY-MM-DD
);

CREATE TABLE fact_sales (
    sale_key        INTEGER PRIMARY KEY,
    order_id        TEXT NOT NULL,
    sale_date       TEXT NOT NULL,         -- ISO YYYY-MM-DD
    month           TEXT NOT NULL,         -- YYYY-MM
    customer_key    INTEGER NOT NULL REFERENCES dim_customer(customer_key),
    product_key     INTEGER NOT NULL REFERENCES dim_product(product_key),
    channel         TEXT NOT NULL,         -- Store / Online
    qty             INTEGER NOT NULL,
    unit_price_pkr  REAL NOT NULL,
    unit_cost_pkr   REAL NOT NULL,
    line_amount_pkr REAL NOT NULL,         -- qty x unit_price
    gross_profit_pkr REAL NOT NULL,        -- (unit_price - unit_cost) x qty
    returned        INTEGER NOT NULL       -- 1 = returned in full
);

CREATE TABLE monthly_targets (
    month                   TEXT PRIMARY KEY,  -- YYYY-MM
    revenue_target_pkr      REAL NOT NULL,
    orders_target           INTEGER NOT NULL,
    gross_margin_pct_target REAL NOT NULL,
    returns_rate_pct_target REAL NOT NULL,
    new_customers_target    INTEGER NOT NULL
);

CREATE TABLE monthly_prior_year (
    month          TEXT PRIMARY KEY,       -- YYYY-MM, 2025
    revenue_pkr    REAL NOT NULL,
    orders         INTEGER NOT NULL,
    new_customers  INTEGER NOT NULL
);

-- monthly_kpi and category_monthly are built by sql/01_monthly_kpi.sql
-- and sql/04_category_mix.sql (CREATE TABLE AS), not here, so the
-- schema file stays load-only and the KPI SQL stays the source of
-- truth for how each KPI is defined.
