# P30 — Package Note (Fiverr-ready)

**Gig title:** I will build your monthly executive KPI pack — one page that tells you how the month went, against target

**What the client gets:** a monthly one-page KPI pack for the
owner or manager — seven KPIs (revenue, orders, average order
value, gross margin, returns rate, new customers, repeat rate)
with RAG against the targets they set, the 12-month trend, the
category mix, and a narrative in plain words that names the cause,
not just the number. Under it: a SQLite star-schema database built
from their daily sales lines, the SQL that defines every KPI
(monthly table, MoM/YoY growth, target variance, category mix),
a live-formula Excel workbook (cover pack + monthly detail +
targets + category mix + data dictionary), a one-page report PDF
they can print or forward, and a Power BI model doc with 12 DAX
measures and a step-by-step build guide so the pack refreshes
itself every month. Delivered as a GitHub repo they can re-run
themselves on the next month's sales.

**Honest note (in the repo, stated plainly):** this is a sample
delivery on synthetic data — a fictional retailer, 2,230 sale
lines, 1,321 orders, 392 customers, Jan–Dec 2026, annual net
revenue PKR 13,486,543 at 23.5% gross margin. The skill and the
method are real, the business is not. The pack never invents a
sale, a target or a customer — a missing month is shown as
missing, not filled — and the margin target is set from the mix
the shop actually sells, not from a wish.

## Tiers (Hashir's band)

| Tier | Price | Delivery | Includes |
|---|---|---|---|
| Basic | $20 | 2 days | The one-page KPI pack for one month: the 7 KPIs with RAG vs their targets, the 12-month trend table, the narrative in plain words, as a live-formula Excel workbook + one-page PDF |
| Standard | $65 | 4 days | Everything in Basic + the SQLite database built from their daily sales lines (star schema), the SQL query pack (monthly KPI table, MoM/YoY growth, target variance with RAG rules, category mix), the full workbook (cover + monthly detail + targets + category mix + data dictionary), the category-mix and trend charts, the data-quality checks as code |
| Premium | $140 | 6 days | Everything in Standard + the Power BI build (model doc, 12 DAX measures with a verification table, step-by-step build guide so the pack refreshes monthly), a second month's pack after they send the next month's sales — to show the pack updating, 1 revision round |

**What's NOT included:** the client's sales data itself (this
service builds the pack from the sales export they share — a
sample month's file is enough to start); a live Power BI Service
workspace or scheduled refresh setup on their tenant (this
service gives them the model, measures and guide — publishing
under their own account is a separate setup step); changing their
targets for them (this service shows actual vs the targets they
set and says plainly when a target does not fit the mix — setting
new targets is their call); accounting or tax advice (this service
reports revenue, margin and returns as the sales lines state
them — the books stay with their accountant).

**Delivery time note:** counts from the day the client shares the
sales export (or a sample of it) and their monthly targets, not
from order placement.

**Proof this service works:** this repo's SAMPLE — 2,230 sale
lines, 1,321 orders, 392 customers, Jan–Dec 2026, net revenue
PKR 13,486,543 (gross PKR 13,983,480 − returns PKR 496,937),
gross profit PKR 3,167,590 at 23.49% margin, December PKR
1,234,359 at −1.8% vs target (AMBER), −11.5% MoM, +23.6% YoY,
best month March PKR 1,396,518, weakest June PKR 929,233,
revenue RAG 6 green / 3 amber / 3 red over the year, repeat rate
climbed from 0% to 67%, Electronics 44% of revenue at 20%
margin, a verified one-page report PDF, a workbook whose formulas
were recalculated in LibreOffice with zero error values, 12 DAX
measures with a verification table, and a full verification suite
passing — plus a what-needs-attention list the owner can act on.
