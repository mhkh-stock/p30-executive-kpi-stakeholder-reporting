-- P30 — 03_target_variance.sql: actual vs the management plan.
-- Variance % = (actual - target) / target. RAG is the pack's rule:
--   revenue / orders:  GREEN >= 100% of target,
--                      AMBER 95–99.9%, RED < 95%
--   gross margin %:    GREEN >= target, AMBER within 2pts below, else RED
--   returns rate %:    GREEN <= target (lower is better),
--                      AMBER up to 1pt above, else RED
--   new customers:     GREEN >= target, AMBER >= 80% of target, else RED
-- The same CASE expressions are re-implemented in src/checks.py and
-- in the workbook's formulas — the three must agree.

SELECT
    k.month,
    k.net_revenue_pkr,
    t.revenue_target_pkr,
    ROUND(100.0 * (k.net_revenue_pkr - t.revenue_target_pkr)
          / t.revenue_target_pkr, 2) AS revenue_variance_pct,
    CASE
        WHEN k.net_revenue_pkr >= t.revenue_target_pkr THEN 'GREEN'
        WHEN k.net_revenue_pkr >= 0.95 * t.revenue_target_pkr THEN 'AMBER'
        ELSE 'RED'
    END AS revenue_rag,
    k.orders,
    t.orders_target,
    ROUND(100.0 * (k.orders - t.orders_target) / t.orders_target, 2)
        AS orders_variance_pct,
    CASE
        WHEN k.orders >= t.orders_target THEN 'GREEN'
        WHEN k.orders >= 0.95 * t.orders_target THEN 'AMBER'
        ELSE 'RED'
    END AS orders_rag,
    k.gross_margin_pct,
    t.gross_margin_pct_target,
    ROUND(k.gross_margin_pct - t.gross_margin_pct_target, 2)
        AS margin_variance_pts,
    CASE
        WHEN k.gross_margin_pct >= t.gross_margin_pct_target THEN 'GREEN'
        WHEN k.gross_margin_pct >= t.gross_margin_pct_target - 2.0 THEN 'AMBER'
        ELSE 'RED'
    END AS margin_rag,
    k.returns_rate_pct,
    t.returns_rate_pct_target,
    ROUND(k.returns_rate_pct - t.returns_rate_pct_target, 2)
        AS returns_variance_pts,
    CASE
        WHEN k.returns_rate_pct <= t.returns_rate_pct_target THEN 'GREEN'
        WHEN k.returns_rate_pct <= t.returns_rate_pct_target + 1.0 THEN 'AMBER'
        ELSE 'RED'
    END AS returns_rag,
    k.new_customers,
    t.new_customers_target,
    ROUND(100.0 * (k.new_customers - t.new_customers_target)
          / t.new_customers_target, 2) AS new_customers_variance_pct,
    CASE
        WHEN k.new_customers >= t.new_customers_target THEN 'GREEN'
        WHEN k.new_customers >= 0.80 * t.new_customers_target THEN 'AMBER'
        ELSE 'RED'
    END AS new_customers_rag
FROM monthly_kpi k
JOIN monthly_targets t ON t.month = k.month
ORDER BY k.month;
