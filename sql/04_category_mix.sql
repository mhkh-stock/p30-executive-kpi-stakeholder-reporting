-- P30 — 04_category_mix.sql: revenue mix by category, per month
-- and for the year. Share % = category net revenue / month net
-- revenue. Builds category_monthly (the workbook's Category Mix
-- sheet reads it) and prints the annual mix the pack's charts use.

DROP TABLE IF EXISTS category_monthly;

CREATE TABLE category_monthly AS
SELECT
    f.month,
    p.category,
    COUNT(*) AS sale_lines,
    ROUND(SUM(CASE WHEN f.returned = 0 THEN f.line_amount_pkr ELSE 0 END), 2)
        AS net_revenue_pkr,
    ROUND(SUM(CASE WHEN f.returned = 1 THEN f.line_amount_pkr ELSE 0 END), 2)
        AS returns_pkr,
    ROUND(SUM(CASE WHEN f.returned = 0 THEN f.gross_profit_pkr ELSE 0 END), 2)
        AS gross_profit_pkr
FROM fact_sales f
JOIN dim_product p ON p.product_key = f.product_key
GROUP BY f.month, p.category
ORDER BY f.month, net_revenue_pkr DESC;

-- annual mix
SELECT
    p.category,
    COUNT(*) AS sale_lines,
    ROUND(SUM(CASE WHEN f.returned = 0 THEN f.line_amount_pkr ELSE 0 END), 2)
        AS net_revenue_pkr,
    ROUND(100.0 * SUM(CASE WHEN f.returned = 0 THEN f.line_amount_pkr ELSE 0 END)
          / (SELECT SUM(net_revenue_pkr) FROM monthly_kpi), 2)
        AS share_pct,
    ROUND(SUM(CASE WHEN f.returned = 0 THEN f.gross_profit_pkr ELSE 0 END), 2)
        AS gross_profit_pkr,
    ROUND(100.0 * SUM(CASE WHEN f.returned = 0 THEN f.gross_profit_pkr ELSE 0 END)
          / NULLIF(SUM(CASE WHEN f.returned = 0 THEN f.line_amount_pkr ELSE 0 END), 0), 2)
        AS margin_pct
FROM fact_sales f
JOIN dim_product p ON p.product_key = f.product_key
GROUP BY p.category
ORDER BY net_revenue_pkr DESC;
