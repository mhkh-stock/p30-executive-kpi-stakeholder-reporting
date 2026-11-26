-- P30 — 01_monthly_kpi.sql: the pack's KPI table, one row per month.
-- Net revenue = gross sales - returns (returned lines are excluded
-- from revenue AND from gross profit, because the goods came back).
-- New customers = customers whose FIRST order falls in that month;
-- repeat customers = distinct customers ordering again that month.
-- A customer who is new in January and buys again in March counts
-- as new once (January) and repeat in March.
-- Run after the staging load; rebuilds monthly_kpi from scratch.
-- This file is the definition of every KPI in the pack — the
-- workbook, the PDF and summary.json all recompute from it.

DROP TABLE IF EXISTS monthly_kpi;

CREATE TABLE monthly_kpi AS
WITH lines AS (
    SELECT
        substr(sale_date, 1, 7) AS month,
        order_id,
        customer_key,
        line_amount_pkr,
        gross_profit_pkr,
        returned
    FROM fact_sales
),
month_agg AS (
    SELECT
        month,
        COUNT(DISTINCT order_id) AS orders,
        SUM(CASE WHEN returned = 0 THEN line_amount_pkr ELSE 0 END)
            AS net_revenue_pkr,
        SUM(line_amount_pkr) AS gross_sales_pkr,
        SUM(CASE WHEN returned = 1 THEN line_amount_pkr ELSE 0 END)
            AS returns_pkr,
        SUM(CASE WHEN returned = 0 THEN gross_profit_pkr ELSE 0 END)
            AS gross_profit_pkr,
        COUNT(*) AS sale_lines,
        SUM(returned) AS returned_lines
    FROM lines
    GROUP BY month
),
new_cust AS (
    SELECT
        substr(first_order_date, 1, 7) AS month,
        COUNT(*) AS new_customers
    FROM dim_customer
    GROUP BY month
),
repeat_cust AS (
    -- repeat in month M = ordered in M AND first ordered before M
    SELECT
        l.month,
        COUNT(DISTINCT l.customer_key) AS repeat_customers
    FROM (SELECT DISTINCT month, customer_key FROM lines) l
    JOIN dim_customer c ON c.customer_key = l.customer_key
    WHERE substr(c.first_order_date, 1, 7) < l.month
    GROUP BY l.month
)
SELECT
    m.month,
    m.orders,
    ROUND(m.net_revenue_pkr, 2) AS net_revenue_pkr,
    ROUND(m.gross_sales_pkr, 2) AS gross_sales_pkr,
    ROUND(m.returns_pkr, 2) AS returns_pkr,
    ROUND(m.gross_profit_pkr, 2) AS gross_profit_pkr,
    ROUND(100.0 * m.gross_profit_pkr / NULLIF(m.net_revenue_pkr, 0), 2)
        AS gross_margin_pct,
    ROUND(100.0 * m.returns_pkr / NULLIF(m.gross_sales_pkr, 0), 2)
        AS returns_rate_pct,
    ROUND(m.net_revenue_pkr / NULLIF(m.orders, 0), 2) AS avg_order_value_pkr,
    COALESCE(n.new_customers, 0) AS new_customers,
    COALESCE(r.repeat_customers, 0) AS repeat_customers,
    COALESCE(n.new_customers, 0) + COALESCE(r.repeat_customers, 0)
        AS active_customers,
    ROUND(100.0 * COALESCE(r.repeat_customers, 0)
          / NULLIF(COALESCE(n.new_customers, 0)
                   + COALESCE(r.repeat_customers, 0), 0), 2)
        AS repeat_rate_pct,
    m.sale_lines,
    m.returned_lines
FROM month_agg m
LEFT JOIN new_cust n ON n.month = m.month
LEFT JOIN repeat_cust r ON r.month = m.month
ORDER BY m.month;
