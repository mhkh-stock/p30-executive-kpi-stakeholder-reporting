# P30 — DAX measures: NoorMart Executive KPI Pack (SAMPLE)

12 measures. Every one is written against the model in `model.md`
and verified against the SQL in `sql/` — the numbers in Power BI
must match `outputs/summary.json` to the rupee. Paste them into
**Modeling → New measure** in the table named in brackets.

## Revenue and profit

```dax
-- 1. Total Revenue [fact_sales] — NET revenue: returned lines earn nothing
Total Revenue =
SUMX (
    fact_sales,
    IF ( fact_sales[returned] = 0, fact_sales[line_amount_pkr], 0 )
)

-- 2. Gross Sales [fact_sales] — before returns, so the owner sees both
Gross Sales = SUM ( fact_sales[line_amount_pkr] )

-- 3. Returns Amount [fact_sales]
Returns Amount =
SUMX (
    fact_sales,
    IF ( fact_sales[returned] = 1, fact_sales[line_amount_pkr], 0 )
)

-- 4. Returns Rate % [fact_sales]
Returns Rate % =
DIVIDE ( [Returns Amount], [Gross Sales] )

-- 5. Gross Profit [fact_sales] — kept lines only
Gross Profit =
SUMX (
    fact_sales,
    IF ( fact_sales[returned] = 0, fact_sales[gross_profit_pkr], 0 )
)

-- 6. Gross Margin % [fact_sales]
Gross Margin % = DIVIDE ( [Gross Profit], [Total Revenue] )
```

## Orders and customers

```dax
-- 7. Total Orders [fact_sales]
Total Orders = DISTINCTCOUNT ( fact_sales[order_id] )

-- 8. Average Order Value [fact_sales]
Average Order Value = DIVIDE ( [Total Revenue], [Total Orders] )

-- 9. New Customers [dim_customer] — first order in the current month
New Customers =
COUNTROWS (
    FILTER (
        dim_customer,
        FORMAT ( dim_customer[first_order_date], "yyyy-MM" )
            = SELECTEDVALUE ( dim_date[month] )
    )
)

-- 10. Repeat Rate % [fact_sales] — share of active customers who bought before
Repeat Rate % =
VAR ActiveCustomers =
    DISTINCTCOUNT ( fact_sales[customer_key] )
VAR RepeatCustomers =
    COUNTROWS (
        FILTER (
            VALUES ( fact_sales[customer_key] ),
            CALCULATE ( MIN ( dim_customer[first_order_date] ) )
                < MIN ( fact_sales[sale_date] )
        )
    )
RETURN
    DIVIDE ( RepeatCustomers, ActiveCustomers )
```

## Growth and targets

```dax
-- 11. Revenue MoM % [fact_sales]
Revenue MoM % =
VAR CurrentMonth = [Total Revenue]
VAR PreviousMonth =
    CALCULATE (
        [Total Revenue],
        PREVIOUSMONTH ( dim_date[date] )
    )
RETURN
    DIVIDE ( CurrentMonth - PreviousMonth, PreviousMonth )

-- 12. Revenue YoY % [fact_sales] — 2025 monthly totals table
Revenue YoY % =
VAR CurrentMonth = [Total Revenue]
VAR PriorYearRevenue =
    CALCULATE (
        SUM ( monthly_prior_year[revenue_pkr] ),
        TREATAS (
            VALUES ( dim_date[month] ),
            monthly_prior_year[month]
        )
    )
RETURN
    DIVIDE ( CurrentMonth - PriorYearRevenue, PriorYearRevenue )
```

## Targets (bonus measures, used by the pack's RAG cards)

```dax
-- Target Revenue [monthly_targets]
Target Revenue = SUM ( monthly_targets[revenue_target_pkr] )

-- Revenue vs Target % [fact_sales]
Revenue vs Target % =
DIVIDE ( [Total Revenue] - [Target Revenue], [Target Revenue] )

-- Revenue YTD [fact_sales]
Revenue YTD =
TOTALYTD ( [Total Revenue], dim_date[date] )

-- Revenue RAG [fact_sales] — the pack's rule, as a measure
Revenue RAG =
VAR Ratio = DIVIDE ( [Total Revenue], [Target Revenue] )
RETURN
    SWITCH (
        TRUE (),
        Ratio >= 1, "GREEN",
        Ratio >= 0.95, "AMBER",
        "RED"
    )
```

## Verification table (check these after building)

| Measure | December 2026 | Year 2026 |
|---|---|---|
| Total Revenue | PKR 1,234,359 | PKR 13,486,543 |
| Gross Sales | PKR 1,293,465 | PKR 13,983,480 |
| Returns Amount | PKR 59,106 | PKR 496,937 |
| Returns Rate % | 4.6% | 3.6% |
| Gross Profit | PKR 280,326 | PKR 3,167,590 |
| Gross Margin % | 22.7% | 23.5% |
| Total Orders | 117 | 1,321 |
| Average Order Value | PKR 10,550 | PKR 10,209 |
| New Customers | 35 | 392 |
| Revenue MoM % | −11.5% | — |
| Revenue YoY % | +23.6% | — |
| Revenue vs Target % | −1.8% | — |

If any of these differ, the model is wrong — check the `returned`
filter first (it is the most common mistake: a measure that sums
`line_amount_pkr` without excluding returned lines overstates
revenue by the returns amount).
