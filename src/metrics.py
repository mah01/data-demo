"""
Business metrics computed ONLY from the generated raw records in ./data.

This module deliberately does not import the generator or its config: it
reads the CSV exports the way an analyst (or an AI agent) would, joining the
systems through the mapping files.
"""
import csv
from collections import defaultdict
from pathlib import Path

H1_25, H1_26 = ("2025-01-01", "2025-06-30"), ("2026-01-01", "2026-06-30")
YTD_25, YTD_26 = ("2025-01-01", "2025-08-31"), ("2026-01-01", "2026-08-31")
PERIODS = {"2025H1": H1_25, "2026H1": H1_26, "2025YTD": YTD_25, "2026YTD": YTD_26}


def num(x):
    return float(x) if x not in (None, "") else 0.0


def within(d, period):
    return period[0] <= d[:10] <= period[1]


def pct_change(a, b):
    return (b - a) / a if a else None


class Data:
    def __init__(self, root):
        self.root = Path(root)
        self._cache = {}

    def __getattr__(self, name):
        # data.erp_invoices -> data/erp/invoices.csv
        if name.startswith("_"):
            raise AttributeError(name)
        if name not in self._cache:
            system, table = name.split("_", 1)
            with open(self.root / system / f"{table}.csv", encoding="utf-8") as f:
                self._cache[name] = list(csv.DictReader(f))
        return self._cache[name]


# ---------------------------------------------------------------------------
# ERP
# ---------------------------------------------------------------------------
def erp_lines(data):
    """Invoice lines enriched with date, DKK revenue, market and category."""
    vm = {(r["domain"], r["system"], r["source_value"]): r["canonical_value"] for r in data.mappings_value_mappings}
    inv = {r["invoice_number"]: r for r in data.erp_invoices}
    cust = {r["customer_number"]: r for r in data.erp_customers}
    prod = {r["product_number"]: r for r in data.erp_products}
    out = []
    for ln in data.erp_invoice_lines:
        i = inv[ln["invoice_number"]]
        c = cust[i["customer_number"]]
        out.append({"date": i["invoice_date"], "customer": i["customer_number"], "customer_name": c["name"],
                    "market": vm[("market", "erp", c["country"])],
                    "category": vm[("product_category", "erp", prod[ln["product_number"]]["product_group_number"])],
                    "product": ln["product_number"], "revenue": num(ln["net_amount"]) * num(i["exchange_rate"]),
                    "cost": num(ln["total_cost_dkk"])})
    return out


def sum_by(rows, period, keyf, valf):
    out = defaultdict(float)
    for r in rows:
        if within(r["date"], period):
            out[keyf(r)] += valf(r)
    return out


def pnl(data, lines):
    accounts = {r["account_number"]: r["type"] for r in data.erp_accounts}
    res = {}
    for p, span in PERIODS.items():
        rev = sum(l["revenue"] for l in lines if within(l["date"], span))
        cogs = sum(l["cost"] for l in lines if within(l["date"], span))
        pers = sum(num(e["amount_dkk"]) for e in data.erp_ledger_entries
                   if within(e["date"], span) and accounts[e["account_number"]] == "personnel")
        opex = sum(num(e["amount_dkk"]) for e in data.erp_ledger_entries
                   if within(e["date"], span) and accounts[e["account_number"]] == "opex")
        profit = rev - cogs - pers - opex
        res[p] = {"revenue": rev, "cogs": cogs, "gross_profit": rev - cogs, "gross_margin": (rev - cogs) / rev,
                  "personnel_ledger": pers, "other_opex": opex, "profit": profit, "margin": profit / rev}
    return res


def market_category(lines, period):
    rev = sum_by(lines, period, lambda l: (l["market"], l["category"]), lambda l: l["revenue"])
    gp = sum_by(lines, period, lambda l: (l["market"], l["category"]), lambda l: l["revenue"] - l["cost"])
    out = {}
    for m in ("DK", "SE", "DE"):
        mrev = sum(v for (mm, _), v in rev.items() if mm == m)
        mgp = sum(v for (mm, _), v in gp.items() if mm == m)
        out[m] = {"revenue": mrev, "gross_profit": mgp, "gross_margin": mgp / mrev,
                  "by_category": {c: {"revenue": rev[(m, c)], "share": rev[(m, c)] / mrev,
                                      "gross_margin": gp[(m, c)] / rev[(m, c)] if rev[(m, c)] else None}
                                  for c in ("Equipment", "Components", "Service")}}
    return out


# ---------------------------------------------------------------------------
# Payroll
# ---------------------------------------------------------------------------
def payroll(data):
    emp = {e["employee_id"]: e for e in data.payroll_employees}
    rows = data.payroll_payroll_entries

    def cost(period, pred=lambda e: True, field="employer_cost_dkk"):
        return sum(num(r[field]) * (1 if field.endswith("_dkk") else num(r["fx_rate_to_dkk"]))
                   for r in rows if within(r["pay_period"] + "-01", period) and pred(emp[r["employee_id"]]))

    def headcount(day, pred=lambda e: True):
        return sum(1 for e in emp.values() if e["employment_start"] <= day and
                   (not e["employment_end"] or e["employment_end"] >= day) and pred(e))

    de_sales = lambda e: e["country"] == "DE" and e["department"] == "Sales"
    expansion = lambda e: de_sales(e) and "2025-07-01" <= e["employment_start"] <= "2026-06-30"
    out = {"total": {p: cost(PERIODS[p]) for p in ("2025H1", "2026H1")},
           "de_sales": {p: cost(PERIODS[p], de_sales) for p in ("2025H1", "2026H1")},
           "de_expansion_hires_2026H1": cost(H1_26, expansion),
           "headcount": {"2025-06-30": headcount("2025-06-30"), "2026-06-30": headcount("2026-06-30")},
           "de_sales_headcount": {"2025-06-30": headcount("2025-06-30", de_sales),
                                  "2026-06-30": headcount("2026-06-30", de_sales)},
           "variable_pay": {p: cost(PERIODS[p], field="commission") + cost(PERIODS[p], field="bonus")
                            for p in ("2025H1", "2026H1")},
           "inactive_employees": sum(1 for e in emp.values() if e["status"] == "terminated")}
    # Salary inflation: base-salary change for employees paid a full month in both June 2025 and June 2026.
    june = {p: {r["employee_id"]: num(r["base_salary"]) * num(r["fx_rate_to_dkk"]) for r in rows if r["pay_period"] == p}
            for p in ("2025-06", "2026-06")}
    both = [e for e in june["2025-06"] if e in june["2026-06"] and june["2025-06"][e] > 0]
    raise_pct = sum(june["2026-06"][e] for e in both) / sum(june["2025-06"][e] for e in both) - 1
    continuing_h1_25 = cost(H1_25, lambda e: e["employee_id"] in both)
    out["salary_inflation_pct"] = raise_pct
    out["salary_inflation_effect"] = raise_pct * continuing_h1_25
    out["increase"] = out["total"]["2026H1"] - out["total"]["2025H1"]
    out["de_sales_increase"] = out["de_sales"]["2026H1"] - out["de_sales"]["2025H1"]
    return out


# ---------------------------------------------------------------------------
# CRM
# ---------------------------------------------------------------------------
def crm_deals(data):
    vm = {(r["domain"], r["system"], r["source_value"]): r["canonical_value"] for r in data.mappings_value_mappings}
    comp = {c["company_id"]: c for c in data.crm_companies}
    out = []
    for d in data.crm_deals:
        # market field -> company country -> deal currency (each market invoices in its own currency)
        labels = (d["market"], comp.get(d["company_id"], {}).get("country"), d["deal_currency"])
        mkt = next((vm[("market", "crm", x)] for x in labels if ("market", "crm", x) in vm), "unknown")
        out.append(dict(d, mkt=mkt, amount_dkk=num(d["amount_company_currency"])))
    return out


def rep_cohorts(data):
    """CRM owner id -> payroll employee record (via mapping file)."""
    emp = {e["employee_id"]: e for e in data.payroll_employees}
    return {m["crm_user_id"]: emp[m["payroll_employee_id"]] for m in data.mappings_employee_crm_user if m["payroll_employee_id"]}


def pipeline_and_winrate(deals, market, period, owners=None):
    sel = [d for d in deals if d["mkt"] == market and d["deal_type"] != "Renewal" and (owners is None or d["owner_id"] in owners)]
    created = [d for d in sel if within(d["created_at"], period)]
    closed = [d for d in sel if d["closed_at"] and within(d["closed_at"], period)]
    won = [d for d in closed if d["outcome"] == "won"]
    return {"pipeline_created": sum(d["amount_dkk"] for d in created), "deals_created": len(created),
            "deals_closed": len(closed), "deals_won": len(won),
            "win_rate": len(won) / len(closed) if closed else None,
            "won_value": sum(d["amount_dkk"] for d in won),
            "avg_lost_deal": sum(d["amount_dkk"] for d in closed if d["outcome"] == "lost") / max(1, len(closed) - len(won)),
            "loss_reasons": dict(sorted(_count(d["loss_reason"] or "(blank)" for d in closed if d["outcome"] == "lost").items(),
                                        key=lambda kv: -kv[1]))}


def _count(items):
    c = defaultdict(int)
    for i in items:
        c[i] += 1
    return c
