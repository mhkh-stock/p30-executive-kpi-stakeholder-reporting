"""P30 — load the SAMPLE files into SQLite and build the KPI tables.

  data/raw/*.csv  ->  staging (verbatim, all text)
                  ->  dim_product / dim_customer / fact_sales
                  ->  monthly_targets / monthly_prior_year
                  ->  sql/01_monthly_kpi.sql  -> monthly_kpi
                  ->  sql/04_category_mix.sql -> category_monthly

The .db rebuilds from the scripts and is never committed.
Usage:  python3 src/load_data.py
"""
import csv
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "processed" / "noormart.db"


def run_sql_file(conn, path):
    with open(path) as f:
        conn.executescript(f.read())


def load_staging(conn, table, csv_path):
    with open(csv_path, newline="") as f:
        rows = list(csv.DictReader(f))
    cols = list(rows[0])
    placeholders = ", ".join("?" * (len(cols) + 1))
    conn.executemany(
        f"INSERT INTO {table} (row_no, {', '.join(cols)}) "
        f"VALUES ({placeholders})",
        [(i + 1, *[r[c] for c in cols]) for i, r in enumerate(rows)],
    )
    return len(rows)


def main():
    DB.parent.mkdir(parents=True, exist_ok=True)
    if DB.exists():
        DB.unlink()
    conn = sqlite3.connect(DB)
    try:
        run_sql_file(conn, ROOT / "data" / "schema.sql")
        n = {}
        n["daily_sales"] = load_staging(
            conn, "stg_daily_sales", ROOT / "data" / "raw" / "daily_sales.csv")
        n["targets"] = load_staging(
            conn, "stg_monthly_targets", ROOT / "data" / "raw" / "monthly_targets.csv")
        n["prior_year"] = load_staging(
            conn, "stg_prior_year", ROOT / "data" / "raw" / "monthly_prior_year.csv")

        # ---- dimensions + fact, typed from staging ----
        conn.execute("""
            INSERT INTO dim_product (product_name, category, base_price_pkr, margin_pct)
            SELECT DISTINCT product, category,
                   AVG(CAST(unit_price_pkr AS REAL)),
                   CASE category
                       WHEN 'Groceries' THEN 0.16
                       WHEN 'Electronics' THEN 0.20
                       WHEN 'Home & Kitchen' THEN 0.28
                       WHEN 'Clothing' THEN 0.36
                       WHEN 'Beauty & Care' THEN 0.34
                   END
            FROM stg_daily_sales GROUP BY product, category""")
        conn.execute("""
            INSERT INTO dim_customer (customer_id, first_order_id, first_order_date)
            SELECT customer_id, MIN(order_id), MIN(sale_date)
            FROM stg_daily_sales GROUP BY customer_id""")
        conn.execute("""
            INSERT INTO fact_sales
                (order_id, sale_date, month, customer_key, product_key,
                 channel, qty, unit_price_pkr, unit_cost_pkr,
                 line_amount_pkr, gross_profit_pkr, returned)
            SELECT s.order_id, s.sale_date, substr(s.sale_date, 1, 7),
                   c.customer_key, p.product_key, s.channel,
                   CAST(s.qty AS INTEGER),
                   CAST(s.unit_price_pkr AS REAL),
                   CAST(s.unit_cost_pkr AS REAL),
                   CAST(s.line_amount_pkr AS REAL),
                   (CAST(s.unit_price_pkr AS REAL)
                    - CAST(s.unit_cost_pkr AS REAL)) * CAST(s.qty AS INTEGER),
                   CAST(s.returned AS INTEGER)
            FROM stg_daily_sales s
            JOIN dim_customer c ON c.customer_id = s.customer_id
            JOIN dim_product p ON p.product_name = s.product""")
        conn.execute("""
            INSERT INTO monthly_targets
            SELECT month, CAST(revenue_target_pkr AS REAL),
                   CAST(orders_target AS INTEGER),
                   CAST(gross_margin_pct_target AS REAL),
                   CAST(returns_rate_pct_target AS REAL),
                   CAST(new_customers_target AS INTEGER)
            FROM stg_monthly_targets""")
        conn.execute("""
            INSERT INTO monthly_prior_year
            SELECT month, CAST(revenue_pkr AS REAL),
                   CAST(orders AS INTEGER), CAST(new_customers AS INTEGER)
            FROM stg_prior_year""")

        run_sql_file(conn, ROOT / "sql" / "01_monthly_kpi.sql")
        run_sql_file(conn, ROOT / "sql" / "04_category_mix.sql")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    print(f"loaded: {n['daily_sales']} sale lines, {n['targets']} target "
          f"months, {n['prior_year']} prior-year months -> {DB.name}")


if __name__ == "__main__":
    sys.exit(main())
