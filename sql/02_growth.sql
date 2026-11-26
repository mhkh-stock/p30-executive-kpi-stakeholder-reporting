-- P30 — 02_growth.sql: month-on-month and year-on-year growth.
-- MoM compares a month with the previous month in monthly_kpi.
-- YoY compares a 2026 month with the same month in 2025
-- (monthly_prior_year). Both are plain ratios — no smoothing,
-- no annualisation — so the owner sees the real swing.

SELECT
    k.month,
    k.net_revenue_pkr,
    LAG(k.net_revenue_pkr) OVER (ORDER BY k.month) AS prev_month_revenue_pkr,
    ROUND(100.0 * (k.net_revenue_pkr
                   - LAG(k.net_revenue_pkr) OVER (ORDER BY k.month))
          / NULLIF(LAG(k.net_revenue_pkr) OVER (ORDER BY k.month), 0), 2)
        AS revenue_mom_pct,
    p.revenue_pkr AS prior_year_revenue_pkr,
    ROUND(100.0 * (k.net_revenue_pkr - p.revenue_pkr)
          / NULLIF(p.revenue_pkr, 0), 2) AS revenue_yoy_pct,
    k.orders,
    LAG(k.orders) OVER (ORDER BY k.month) AS prev_month_orders,
    ROUND(100.0 * (k.orders - LAG(k.orders) OVER (ORDER BY k.month))
          / NULLIF(LAG(k.orders) OVER (ORDER BY k.month), 0), 2)
        AS orders_mom_pct,
    p.orders AS prior_year_orders,
    ROUND(100.0 * (k.orders - p.orders)
          / NULLIF(p.orders, 0), 2) AS orders_yoy_pct
FROM monthly_kpi k
LEFT JOIN monthly_prior_year p
    ON p.month = '2025-' || substr(k.month, 6, 2)
ORDER BY k.month;
