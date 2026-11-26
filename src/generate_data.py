"""P30 — generate the SAMPLE data for NoorMart, a fictional retailer.

The pack answers one question for the owner: "What should I know
this month, in one page?" The data is synthetic, generated here with
a fixed seed — a fictional shop, not a real client's books. What is
real is the method: daily sales lines reconcile to the monthly KPI
table, targets are the management plan set BEFORE the month's sales,
and every KPI in the pack is recomputed from the loaded lines.

Outputs (data/raw/):
  daily_sales.csv     — one row per sale line, Jan–Dec 2026 (~2,500 lines)
  monthly_targets.csv — the management plan: one target row per month
  monthly_prior_year.csv — 2025 monthly totals, so YoY is computed,
                        not typed (SAMPLE, same generator)
  data_manifest.json  — counts + the planned-vs-actual design, so the
                        checks can prove the pack, not trust it

Design:
  * 12 months, Jan–Dec 2026. Planned monthly revenue is the shop's
    plan (Ramadan/Eid bump in Mar + May, wedding-season peak in Nov).
    Targets = plan x 1.03 (management stretches the plan 3%).
  * Actuals come from the lines: each month is closed when its net
    revenue reaches planned x demand multiplier, so the RAG mix is
    earned, not staged — some months beat target, some miss, none
    are hand-typed. (A fixed orders/day count would swing a month
    by +/-30% because one PKR 42,000 TV is a whole day's trade.)
  * New vs repeat customers: 700-customer pool; an order picks an
    unseen customer ~30% of the time, so "new customers" falls
    naturally as the year goes on.
  * Returns: ~4% of lines are returned in full; net revenue =
    gross sales - returns, and the pack shows both.
  * Gross margin: cost = price x (1 - category margin), margin
    differs by category (Groceries 16% ... Clothing 36%).

Seed 30, deterministic: re-running regenerates byte-identical files.
Usage:  python3 src/generate_data.py
"""
import csv
import json
import random
from calendar import monthrange
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
SEED = 30

# ---- the management plan (set before the year's sales) ----
# month: (planned revenue PKR, demand multiplier vs plan)
PLAN = {
    1: (950_000, 0.97), 2: (880_000, 1.05), 3: (1_250_000, 1.09),
    4: (1_050_000, 0.94), 5: (1_300_000, 1.01), 6: (980_000, 0.92),
    7: (1_020_000, 1.00), 8: (1_060_000, 0.98), 9: (990_000, 0.95),
    10: (1_120_000, 1.06), 11: (1_280_000, 1.08), 12: (1_220_000, 1.01),
}
TARGET_STRETCH = 1.03      # targets sit 3% above the plan
MARGIN_TARGET_PCT = 23.5   # gross-margin % target, every month —
    # the blended margin the category mix actually yields
    # (Electronics is 44% of revenue at 20% margin, so a 26%
    # target would be missed every month and teach nothing)
RETURNS_TARGET_PCT = 4.5   # returns-rate % target, every month
NEW_CUST_TARGET = 32       # new-customers target, every month
EXPECTED_NET_BASKET = 10_500  # realised average net basket, PKR —
    # used only to size the orders target (planned x 1.03 / basket)
RETURN_RATE = 0.04
CHANNELS = ["Store", "Store", "Online"]

PRODUCTS = [
    # (product, category, base price PKR, margin, qty range)
    ("Basmati Rice 5kg", "Groceries", 1450, 0.16, (1, 4)),
    ("Cooking Oil 5L", "Groceries", 2850, 0.16, (1, 3)),
    ("Sugar 5kg", "Groceries", 620, 0.16, (1, 4)),
    ("Tea 900g", "Groceries", 1150, 0.16, (1, 3)),
    ("Flour 10kg", "Groceries", 980, 0.16, (1, 3)),
    ("Washing Powder 3kg", "Groceries", 1240, 0.16, (1, 3)),
    ("LED TV 32in", "Electronics", 42000, 0.20, (1, 1)),
    ("Ceiling Fan", "Electronics", 8500, 0.20, (1, 2)),
    ("Air Cooler", "Electronics", 24500, 0.20, (1, 1)),
    ("LED Bulb 9W", "Electronics", 450, 0.20, (1, 4)),
    ("Electric Iron", "Electronics", 3800, 0.20, (1, 2)),
    ("Electric Kettle 1.7L", "Electronics", 2900, 0.20, (1, 2)),
    ("Dinner Set 24pc", "Home & Kitchen", 9800, 0.28, (1, 2)),
    ("Non-stick Cookware Set", "Home & Kitchen", 7400, 0.28, (1, 2)),
    ("Bed Sheet Double", "Home & Kitchen", 2600, 0.28, (1, 2)),
    ("Curtains Pair", "Home & Kitchen", 3900, 0.28, (1, 2)),
    ("Dinner Plates Set", "Home & Kitchen", 4200, 0.28, (1, 2)),
    ("Men Kurta", "Clothing", 2850, 0.36, (1, 2)),
    ("Lawn 3pc Suit", "Clothing", 4600, 0.36, (1, 2)),
    ("Shawl", "Clothing", 1900, 0.36, (1, 2)),
    ("Kids Frock", "Clothing", 1650, 0.36, (1, 2)),
    ("Shampoo 650ml", "Beauty & Care", 950, 0.34, (1, 3)),
    ("Face Wash", "Beauty & Care", 720, 0.34, (1, 3)),
    ("Body Lotion", "Beauty & Care", 1150, 0.34, (1, 3)),
    ("Soap Pack of 4", "Beauty & Care", 640, 0.34, (1, 3)),
]
CATEGORY_WEIGHT = {"Groceries": 0.34, "Electronics": 0.18,
                   "Home & Kitchen": 0.20, "Clothing": 0.16,
                   "Beauty & Care": 0.12}

FIRST = ["Ahmed", "Bilal", "Usman", "Ali", "Hassan", "Fatima", "Ayesha",
         "Zainab", "Omar", "Sana", "Imran", "Nadia", "Tariq", "Maryam",
         "Shahid", "Hina", "Kamran", "Rabia", "Faisal", "Mehwish"]
LAST = ["Khan", "Malik", "Sheikh", "Butt", "Chaudhry", "Raza", "Ahmed",
        "Hussain", "Qureshi", "Siddiqui", "Iqbal", "Anwar", "Gill",
        "Rana", "Baig", "Mirza"]


def pick_product(rng):
    cats = list(CATEGORY_WEIGHT)
    weights = [CATEGORY_WEIGHT[c] for c in cats]
    cat = rng.choices(cats, weights=weights)[0]
    pool = [p for p in PRODUCTS if p[1] == cat]
    return rng.choice(pool)


def main():
    rng = random.Random(SEED)
    RAW.mkdir(parents=True, exist_ok=True)

    customers = [f"CUST-{i:03d}" for i in range(1, 701)]
    unseen = customers[:]
    rng.shuffle(unseen)
    seen = []
    lines = []
    order_seq = 0

    def make_order(order_date):
        """One order (1-3 lines) on a given date. Returns (lines, net)."""
        nonlocal order_seq
        order_seq += 1
        order_id = f"ORD-{order_date.strftime('%Y%m%d')}-{order_seq:04d}"
        if unseen and rng.random() < 0.30:
            cust = unseen.pop()
            seen.append(cust)
        else:
            cust = rng.choice(seen) if seen else unseen.pop()
            if cust not in seen:
                seen.append(cust)
        channel = rng.choice(CHANNELS)
        n_lines = 1 if rng.random() < 0.45 else (2 if rng.random() < 0.75 else 3)
        order_lines, order_net = [], 0.0
        for _ in range(n_lines):
            name, cat, price, margin, (qlo, qhi) = pick_product(rng)
            qty = rng.randint(qlo, qhi)
            unit_price = round(price * rng.uniform(0.92, 1.10))
            unit_cost = round(unit_price * (1 - margin)
                              * rng.uniform(0.98, 1.02), 2)
            amount = round(qty * unit_price, 2)
            returned = 1 if rng.random() < RETURN_RATE else 0
            order_lines.append({
                "order_id": order_id,
                "sale_date": order_date.isoformat(),
                "customer_id": cust,
                "customer_type": "",  # filled in after the loop
                "channel": channel,
                "product": name,
                "category": cat,
                "qty": qty,
                "unit_price_pkr": unit_price,
                "unit_cost_pkr": unit_cost,
                "line_amount_pkr": amount,
                "returned": returned,
            })
            if not returned:
                order_net += amount
        return order_lines, order_net

    # ---- month by month: keep taking orders on random days until the
    # month's net revenue reaches planned x demand multiplier. ----
    for month in range(1, 13):
        planned, mult = PLAN[month]
        days = monthrange(2026, month)[1]
        month_net_target = planned * mult
        cum_net = 0.0
        guard = 0
        while cum_net < month_net_target and guard < 600:
            guard += 1
            order_lines, order_net = make_order(
                date(2026, month, rng.randint(1, days)))
            lines.extend(order_lines)
            cum_net += order_net
    lines.sort(key=lambda l: (l["sale_date"], l["order_id"]))

    # recompute customer_type honestly: a customer's FIRST order is new,
    # every later order is repeat.
    first_order = {}
    for ln in lines:
        if ln["customer_id"] not in first_order:
            first_order[ln["customer_id"]] = ln["order_id"]
    for ln in lines:
        ln["customer_type"] = ("new" if first_order[ln["customer_id"]] == ln["order_id"]
                               else "repeat")

    with open(RAW / "daily_sales.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(lines[0]))
        w.writeheader()
        w.writerows(lines)

    # ---- monthly targets: the management plan, set before the year ----
    targets = []
    for month in range(1, 13):
        planned, _ = PLAN[month]
        targets.append({
            "month": f"2026-{month:02d}",
            "revenue_target_pkr": round(planned * TARGET_STRETCH),
            "orders_target": round(planned * TARGET_STRETCH / EXPECTED_NET_BASKET),
            "gross_margin_pct_target": MARGIN_TARGET_PCT,
            "returns_rate_pct_target": RETURNS_TARGET_PCT,
            "new_customers_target": NEW_CUST_TARGET,
        })
    with open(RAW / "monthly_targets.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(targets[0]))
        w.writeheader()
        w.writerows(targets)

    # ---- prior year (2025): monthly totals, same generator, so YoY is
    # computed from data — 2025 ran ~14% below the 2026 plan. ----
    prior = []
    for month in range(1, 13):
        planned, _ = PLAN[month]
        rev = round(planned * 0.86 * rng.uniform(0.94, 1.06))
        prior.append({
            "month": f"2025-{month:02d}",
            "revenue_pkr": rev,
            "orders": round(rev / EXPECTED_NET_BASKET),
            "new_customers": round(NEW_CUST_TARGET * rng.uniform(0.8, 1.1)),
        })
    with open(RAW / "monthly_prior_year.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(prior[0]))
        w.writeheader()
        w.writerows(prior)

    # ---- manifest ----
    gross = sum(l["line_amount_pkr"] for l in lines)
    ret = sum(l["line_amount_pkr"] for l in lines if l["returned"])
    manifest = {
        "seed": SEED,
        "scenario": "NoorMart — fictional retailer, Jan–Dec 2026 (SAMPLE)",
        "plan": {f"2026-{m:02d}": {"planned_revenue_pkr": p, "demand_multiplier": d}
                 for m, (p, d) in PLAN.items()},
        "target_stretch": TARGET_STRETCH,
        "totals": {
            "sale_lines": len(lines),
            "orders": len({l["order_id"] for l in lines}),
            "customers_seen": len(first_order),
            "gross_sales_pkr": round(gross, 2),
            "returns_pkr": round(ret, 2),
            "net_revenue_pkr": round(gross - ret, 2),
            "returned_lines": sum(l["returned"] for l in lines),
        },
    }
    with open(RAW / "data_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"sale lines: {len(lines)}, orders: {manifest['totals']['orders']}, "
          f"customers: {len(first_order)}")
    print(f"gross PKR {gross:,.2f} - returns PKR {ret:,.2f} "
          f"= net PKR {gross - ret:,.2f}")


if __name__ == "__main__":
    main()
