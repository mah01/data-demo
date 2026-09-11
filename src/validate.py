"""
Validate the generated NordFlow dataset.

    python3 src/validate.py            # checks + executive walkthrough
    python3 src/validate.py --quiet    # checks only
    python3 src/validate.py --data DIR --json OUT.json   # other data folder, machine-readable results

Every number is recomputed from the raw CSVs (see metrics.py / analysis.py)
and compared with the ranges in ground_truth.json. Exit code 1 on any failure.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

from analysis import compute_all
from metrics import num

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
FILES = ["payroll/employees", "payroll/payroll_entries", "crm/owners", "crm/companies", "crm/deals", "crm/activities",
         "crm/property_history", "erp/customers", "erp/products", "erp/invoices", "erp/invoice_lines",
         "erp/exchange_rates", "erp/accounts", "erp/ledger_entries", "mappings/employee_crm_user",
         "mappings/crm_company_erp_customer", "mappings/value_mappings"]


class Report:
    def __init__(self):
        self.rows, self.failed, self.records = [], 0, []

    def add(self, group, name, ok, value, expected, raw=None):
        self.rows.append((group, name, ok, value, expected))
        self.records.append({"group": group, "id": name, "ok": ok, "value": raw if raw is not None else value})
        self.failed += not ok

    def print(self):
        group = None
        for g, name, ok, value, expected in self.rows:
            if g != group:
                print(f"\n== {g} " + "=" * (70 - len(g)))
                group = g
            print(f"  [{'PASS' if ok else 'FAIL'}] {name:<46} {value:>18}   {expected}")


def fmt(v, unit=None):
    if isinstance(v, str):
        return v if len(v) <= 18 else v[:15] + "..."
    if unit == "DKK" or (isinstance(v, float) and abs(v) >= 10000):
        return f"{v / 1e6:,.2f}m"
    if unit == "ratio":
        return f"{v * 100:.1f}%"
    return f"{v:,.2f}" if isinstance(v, float) else str(v)


def resolve(m, path):
    cur = m
    for part in path.split("."):
        cur = cur[int(part)] if isinstance(cur, list) else cur[part]
    return cur


# ---------------------------------------------------------------------------
# Structure, identity and realism
# ---------------------------------------------------------------------------
def structural_checks(data, rep):
    g = "Structure & referential integrity"
    for f in FILES:
        p = data.root / f"{f}.csv"
        rep.add(g, f"exists: {f}.csv", p.exists() and p.stat().st_size > 100, "ok" if p.exists() else "missing", "non-empty")
    emp = {e["employee_id"] for e in data.payroll_employees}
    users = {u["user_id"] for u in data.crm_owners}
    comps = {c["company_id"] for c in data.crm_companies}
    deals = {d["deal_id"] for d in data.crm_deals}
    custs = {c["customer_number"] for c in data.erp_customers}
    prods = {p["product_number"] for p in data.erp_products}
    invs = {i["invoice_number"]: i for i in data.erp_invoices}

    def fk(name, values, universe):
        bad = [v for v in values if v and v not in universe]
        rep.add(g, name, not bad, f"{len(bad)} orphans", "0 orphans")
    fk("invoice_lines -> invoices", (l["invoice_number"] for l in data.erp_invoice_lines), invs)
    fk("invoice_lines -> products", (l["product_number"] for l in data.erp_invoice_lines), prods)
    fk("invoices -> customers", (i["customer_number"] for i in data.erp_invoices), custs)
    fk("deals -> companies", (d["company_id"] for d in data.crm_deals), comps)
    fk("deals -> owners", (d["owner_id"] for d in data.crm_deals), users)
    fk("activities -> companies/deals", [a["company_id"] for a in data.crm_activities] + [a["deal_id"] for a in data.crm_activities], comps | deals)
    fk("payroll_entries -> employees", (r["employee_id"] for r in data.payroll_payroll_entries), emp)
    fk("mapping employee -> payroll/crm", [m["payroll_employee_id"] for m in data.mappings_employee_crm_user], emp)
    fk("mapping crm user -> crm", [m["crm_user_id"] for m in data.mappings_employee_crm_user], users)
    fk("mapping company -> crm", [m["crm_company_id"] for m in data.mappings_crm_company_erp_customer], comps)
    fk("mapping customer -> erp", [m["erp_customer_number"] for m in data.mappings_crm_company_erp_customer], custs)
    rep.add(g, "unique customer numbers", len(custs) == len(data.erp_customers), len(custs), len(data.erp_customers))

    sums = Counter()
    for l in data.erp_invoice_lines:
        sums[l["invoice_number"]] += num(l["net_amount"])
    bad = [n for n, i in invs.items() if abs(sums[n] - num(i["net_amount"])) > 0.05]
    rep.add(g, "invoice net = sum of lines", not bad, f"{len(bad)} mismatches", "0")
    dates = [i["invoice_date"] for i in data.erp_invoices]
    rep.add(g, "invoice dates inside data period", min(dates) >= "2025-01-01" and max(dates) <= "2026-08-31",
            f"{min(dates)}..{max(dates)}", "2025-01..2026-08")

    g = "Cross-system identity"
    patterns = [("payroll employee_id", emp, r"^(DK|SE|DE)\d{4}$"), ("crm user_id", users, r"^usr_\d{6}$"),
                ("crm company_id", comps, r"^cmp_\d{5}$"), ("erp customer_number", custs, r"^\d{5}$"),
                ("crm deal_id", deals, r"^\d{10}$")]
    for name, ids, pat in patterns:
        bad = [i for i in ids if not re.match(pat, i)]
        rep.add(g, f"{name} format", not bad, f"{len(bad)} bad", pat)
    overlap = (emp & users) | (emp & custs) | (users & comps) | (comps & custs)
    rep.add(g, "no identifier shared across systems", not overlap, f"{len(overlap)} shared", "0")
    mapped = {m["crm_company_id"]: m["erp_customer_number"] for m in data.mappings_crm_company_erp_customer}
    cname = {c["company_id"]: c["name"] for c in data.crm_companies}
    ename = {c["customer_number"]: c["name"] for c in data.erp_customers}
    differ = sum(1 for c, e in mapped.items() if cname[c] != ename[e]) / len(mapped)
    rep.add(g, "CRM/ERP names differ for mapped companies", differ >= 0.4, f"{differ * 100:.0f}%", ">= 40%")
    many = max(Counter(mapped.values()).values())
    rep.add(g, "duplicate CRM records mapped to one ERP customer", many >= 2, many, ">= 2")
    unmapped_emp = sum(1 for m in data.mappings_employee_crm_user if not m["payroll_employee_id"])
    rep.add(g, "CRM users without payroll record", unmapped_emp >= 1, unmapped_emp, ">= 1")

    g = "Realism / imperfections"
    credits = [i for i in data.erp_invoices if i["document_type"] == "credit_note"]
    rep.add(g, "credit notes present (0.3-3% of invoices)", 0.003 <= len(credits) / len(invs) <= 0.03,
            f"{len(credits)} ({len(credits) / len(invs) * 100:.1f}%)", "0.3-3%")
    neg = sum(1 for l in data.erp_invoice_lines if num(l["net_amount"]) < 0)
    rep.add(g, "negative invoice lines", neg > 0, neg, "> 0")
    per_cust = Counter(i["customer_number"] for i in data.erp_invoices)
    rep.add(g, "customers with several invoices", sum(1 for v in per_cust.values() if v >= 5) >= 100,
            sum(1 for v in per_cust.values() if v >= 5), ">= 100 with 5+")
    multi_ccy = {i["currency"] for i in data.erp_invoices}
    rep.add(g, "invoices in DKK, SEK and EUR", multi_ccy == {"DKK", "SEK", "EUR"}, ",".join(sorted(multi_ccy)), "3 currencies")
    blank_reason = sum(1 for d in data.crm_deals if d["outcome"] == "lost" and not d["loss_reason"])
    rep.add(g, "lost deals with missing loss_reason", blank_reason > 0, blank_reason, "> 0")
    blank_ind = sum(1 for c in data.crm_companies if not c["industry"])
    rep.add(g, "companies with missing industry", blank_ind > 0, blank_ind, "> 0")
    crossing = sum(1 for d in data.crm_deals if d["closed_at"] and d["created_at"][:7] <= "2025-12" and d["closed_at"][:7] >= "2026-01")
    rep.add(g, "deals crossing 2025/2026", crossing >= 20, crossing, ">= 20")
    open_deals = sum(1 for d in data.crm_deals if d["outcome"] == "open")
    rep.add(g, "open deals at data end", open_deals >= 30, open_deals, ">= 30")
    terminated = sum(1 for e in data.payroll_employees if e["status"] == "terminated")
    rep.add(g, "inactive (terminated) employees", terminated >= 1, terminated, ">= 1")
    months = Counter()
    for r in data.payroll_payroll_entries:
        months[r["pay_period"]] += num(r["commission"]) > 0
    rep.add(g, "commission varies by month", len(set(months.values())) > 3, len(set(months.values())), "> 3 distinct")


# ---------------------------------------------------------------------------
# Story checks
# ---------------------------------------------------------------------------
def story_checks(m, truth, rep):
    for c in truth["checks"]:
        label = "Scenario invariant" if c.get("invariant") else "Story"
        group = f"{label} Q" + ",".join(str(q) for q in c["questions"]) + "  [" + "+".join(c["systems"]) + "]"
        try:
            v = resolve(m, c["metric"])
        except (KeyError, IndexError, TypeError):
            rep.add(group, c["id"], False, "missing", c["metric"])
            continue
        unit = c.get("unit")
        if "equals" in c:
            ok, exp = v == c["equals"], f"== {c['equals']}"
        elif "contains_all" in c:
            ok, exp = all(s in v for s in c["contains_all"]), "contains " + ", ".join(c["contains_all"])
        elif "min_str" in c:
            ok, exp = v is not None and v >= c["min_str"], f">= {c['min_str']}"
        else:
            lo, hi = c.get("min"), c.get("max")
            ok = v is not None and (lo is None or v >= lo) and (hi is None or v <= hi)
            exp = f"[{fmt(lo, unit) if lo is not None else '-inf'} .. {fmt(hi, unit) if hi is not None else 'inf'}]"
        rep.add(group, c["id"], ok, fmt(v, unit), exp, raw=v)


# ---------------------------------------------------------------------------
# Executive walkthrough
# ---------------------------------------------------------------------------
def walkthrough(m):
    M = lambda x: f"DKK {x / 1e6:,.1f}m"
    P = lambda x: f"{x * 100:.1f}%"
    p25, p26 = m["pnl"]["2025H1"], m["pnl"]["2026H1"]
    y25, y26 = m["pnl"]["2025YTD"], m["pnl"]["2026YTD"]
    pay, gs, gc, dk, cf, br, dv = (m["payroll"], m["germany_sales"], m["germany_customers"], m["denmark"],
                                   m["counterfactual"], m["bridge"], m["derived"])
    t1, t2 = gc["top2_trail"]
    top = gc["top_decliners"]
    out = [
        ("1. How are we performing vs last year?  [ERP + payroll journal]",
         f"H1 revenue {M(p25['revenue'])} -> {M(p26['revenue'])} ({P(dv['revenue_growth'])}); operating profit "
         f"{M(p25['profit'])} -> {M(p26['profit'])}; margin {P(p25['margin'])} -> {P(p26['margin'])}. "
         f"Jan-Aug: revenue {M(y25['revenue'])} -> {M(y26['revenue'])}, profit {M(y25['profit'])} -> {M(y26['profit'])}."),
        ("2. Revenue is up, why is profitability down?  [ERP + payroll + CRM]",
         f"Gross margin {P(p25['gross_margin'])} -> {P(p26['gross_margin'])}, personnel +{M(pay['increase'])}, other opex "
         f"+{M(p26['other_opex'] - p25['other_opex'])}. Bridge: Germany {M(br['germany_total'])} "
         f"(gross profit {M(br['gross_profit_DE'])}, sales payroll {M(br['personnel_de_sales'])}, opex {M(br['opex_de'])}), "
         f"Denmark gross profit {M(br['gross_profit_DK'])}, other personnel {M(br['personnel_other'])}, Sweden {M(br['gross_profit_SE'])}."),
        ("3. What drives the personnel cost increase?  [payroll]",
         f"{M(pay['total']['2025H1'])} -> {M(pay['total']['2026H1'])} (+{M(pay['increase'])}). German sales +{M(pay['de_sales_increase'])} "
         f"({P(dv['de_sales_share_of_personnel_increase'])}); the {P(pay['salary_inflation_pct'])} general raise explains only "
         f"~{M(pay['salary_inflation_effect'])} ({P(dv['inflation_share_of_profit_decline'])} of the profit decline) - a red herring."),
        ("4. Did the German sales hiring pay off?  [payroll + CRM + ERP]",
         f"German sales headcount {pay['de_sales_headcount']['2025-06-30']} -> {pay['de_sales_headcount']['2026-06-30']}; "
         f"revenue per German salesperson {M(dv['de_revenue_per_salesperson']['2025H1'])} -> {M(dv['de_revenue_per_salesperson']['2026H1'])}. "
         f"New reps win {P(gs['2026H1_new_reps']['win_rate'])} vs veterans {P(gs['2026H1_veterans']['win_rate'])}. "
         f"Germany's net profit contribution changed by {M(br['germany_total'])}. Not yet."),
        ("5. Why is German pipeline growing while revenue falls?  [CRM + ERP]",
         f"New pipeline {M(gs['2025H1']['pipeline_created'])} -> {M(gs['2026H1']['pipeline_created'])} (+{P(gs['pipeline_growth'])}), "
         f"win rate {P(gs['2025H1']['win_rate'])} -> {P(gs['2026H1']['win_rate'])}, won value {P(gs['won_value_change'])}. "
         f"New reps create {P(gs['new_rep_share_of_pipeline_2026H1'])} of pipeline; top 2026 loss reasons: "
         f"{', '.join([r for r in gs['2026H1']['loss_reasons'] if r != '(blank)'][:3])}. "
         f"German revenue {P(m['markets']['change']['DE'])}."),
        ("6. New business, existing customers, or both?  [ERP + CRM]",
         f"Both. Existing customers {M(gc['existing_customers_change'])} (of which top-2 {M(gc['top2_change'])}); "
         f"{gc['new_customers_count']} new customers brought {M(gc['new_customers_revenue_2026H1'])}, "
         f"covering {P(dv['de_new_customer_revenue_vs_existing_loss'])} of the loss, while win rates collapsed."),
        ("7. Which customers drove the German decline?  [ERP + mappings + CRM + payroll]",
         f"{top[0]['name']} {M(top[0]['change'])} and {top[1]['name']} {M(top[1]['change'])} "
         f"({P(gc['top2_share_of_net_decline'])} of Germany's net decline). Both were reassigned in CRM "
         f"({t1['owner_changed_on']}, {t2['owner_changed_on']}) to reps hired {t1['new_owner_start']} / {t2['new_owner_start']} (payroll); "
         f"activity fell {t1['activities_per_month_before']:.1f}->{t1['activities_per_month_after']:.1f} and "
         f"{t2['activities_per_month_before']:.1f}->{t2['activities_per_month_after']:.1f} per month; lost since: "
         f"{len(t1['lost_deals_since_reassignment'])} and {len(t2['lost_deals_since_reassignment'])} deals."),
        ("8. Is Denmark really performing well?  [ERP + CRM]",
         f"Revenue {P(dk['revenue_change'])}, but service {P(dk['service_revenue_change'])} and equipment {P(dk['equipment_revenue_change'])}; "
         f"service share {P(dk['service_share']['2025H1'])} -> {P(dk['service_share']['2026H1'])}, gross margin "
         f"{P(dk['gross_margin']['2025H1'])} -> {P(dk['gross_margin']['2026H1'])}, gross profit {M(dv['dk_gross_profit_change'])}. "
         f"CRM: {dk['renewals_2025H2']['lost']} of {dk['renewals_2025H2']['closed']} service renewals lost in H2 2025 "
         f"({P(dk['renewals_2025H2']['lost_value_share'])} of value)."),
        ("9. Profit if German conversion had stayed at 2025 level?  [CRM + ERP]",
         f"~{cf['extra_wins']:.0f} extra wins, ~{M(cf['extra_bookings'])} bookings at {P(cf['de_equipment_gross_margin_2026H1'])} "
         f"margin -> profit ~{M(cf['profit'])}, margin ~{P(cf['margin'])} (upper bound). Conversion alone does not restore 14%."),
        ("10. Three issues to investigate first",
         f"(1) German sales expansion ROI - Germany {M(br['germany_total'])}, {P(dv['germany_share_of_profit_decline'])} of the decline; "
         f"(2) German key-account attrition after reassignment - {M(gc['top2_change'])}; "
         f"(3) Danish service erosion / mix shift - DK gross profit {M(dv['dk_gross_profit_change'])} on {P(dk['revenue_change'])} revenue."),
    ]
    print("\n== Executive questions (derived from raw records) " + "=" * 21)
    for q, a in out:
        print(f"\n{q}\n   {a}")


def _arg(name):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else None


def main():
    truth = json.loads((ROOT / "ground_truth.json").read_text(encoding="utf-8"))
    m = compute_all(Path(_arg("--data") or DATA))
    rep = Report()
    structural_checks(m["_data"], rep)
    story_checks(m, truth, rep)
    if _arg("--json"):
        Path(_arg("--json")).write_text(json.dumps(rep.records, default=str), encoding="utf-8")
    rep.print()
    total = len(rep.rows)
    print(f"\n{total - rep.failed}/{total} checks passed.")
    if "--quiet" not in sys.argv:
        walkthrough(m)
    if rep.failed:
        print(f"\nVALIDATION FAILED: {rep.failed} check(s) failed.")
        sys.exit(1)
    print("\nVALIDATION PASSED: the NordFlow business story is derivable from the raw records.")


if __name__ == "__main__":
    main()
