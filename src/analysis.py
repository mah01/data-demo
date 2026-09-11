"""
Question-level analyses built on metrics.py. Each function notes which
systems it needs; compute_all() returns one nested dict used by validate.py.
"""
from collections import defaultdict

from metrics import (Data, H1_25, H1_26, PERIODS, num, within, pct_change, erp_lines, sum_by, pnl,
                     market_category, payroll, crm_deals, rep_cohorts, pipeline_and_winrate)


def germany_customers(data, lines):
    """ERP: which German customers drove the change; existing vs new. CRM + payroll: what happened to the top decliners."""
    de = [l for l in lines if l["market"] == "DE"]
    first = {}
    for l in lines:
        first[l["customer"]] = min(first.get(l["customer"], l["date"]), l["date"])
    r25 = sum_by(de, H1_25, lambda l: l["customer"], lambda l: l["revenue"])
    r26 = sum_by(de, H1_26, lambda l: l["customer"], lambda l: l["revenue"])
    names = {l["customer"]: l["customer_name"] for l in de}
    changes = sorted(((r26.get(c, 0) - r25.get(c, 0), c) for c in set(r25) | set(r26)))
    total_change = sum(r26.values()) - sum(r25.values())
    top2 = changes[:2]
    existing = [c for c in r25 if r25[c] > 0]
    new = [c for c in r26 if first[c] > "2025-06-30"]
    existing_change = sum(r26.get(c, 0) for c in existing) - sum(r25[c] for c in existing)
    out = {"total_change": total_change,
           "top_decliners": [{"customer_number": c, "name": names[c], "h1_2025": r25.get(c, 0), "h1_2026": r26.get(c, 0),
                              "change": ch} for ch, c in changes[:5]],
           "top2_change": sum(ch for ch, _ in top2),
           "top2_share_of_net_decline": sum(ch for ch, _ in top2) / total_change if total_change < 0 else None,
           "existing_customers_change": existing_change,
           "existing_excl_top2_change": existing_change - sum(ch for ch, _ in top2),
           "new_customers_revenue_2026H1": sum(r26[c] for c in new), "new_customers_count": len(new),
           "existing_customers_lost": sum(1 for c in existing if r26.get(c, 0) == 0)}

    # Cross-system trail for the two biggest decliners: ERP -> mapping -> CRM owner history -> payroll.
    erp_to_crm = defaultdict(list)
    for m in data.mappings_crm_company_erp_customer:
        erp_to_crm[m["erp_customer_number"]].append(m["crm_company_id"])
    owners = rep_cohorts(data)
    trail = []
    for _, cnum in top2:
        cids = erp_to_crm.get(cnum, [])
        changes_ = [h for h in data.crm_property_history if h["object_id"] in cids and h["property"] == "hubspot_owner_id"
                    and "2025-07-01" <= h["changed_at"][:10] <= "2025-12-31"]
        new_owner = owners.get(changes_[-1]["value_after"]) if changes_ else None
        acts = [a for a in data.crm_activities if a["company_id"] in cids]
        before = sum(1 for a in acts if "2025-01-01" <= a["timestamp"][:10] <= "2025-08-31") / 8
        after = sum(1 for a in acts if "2025-11-01" <= a["timestamp"][:10] <= "2026-06-30") / 8
        lost = [d["deal_name"] for d in data.crm_deals if d["company_id"] in cids and d["outcome"] == "lost"
                and d["closed_at"] and d["closed_at"][:10] >= "2025-07-01"]
        trail.append({"customer_number": cnum, "crm_company_ids": cids,
                      "owner_changed_on": changes_[-1]["changed_at"][:10] if changes_ else None,
                      "new_owner_employee_id": new_owner["employee_id"] if new_owner else None,
                      "new_owner_start": new_owner["employment_start"] if new_owner else None,
                      "activities_per_month_before": before, "activities_per_month_after": after,
                      "lost_deals_since_reassignment": lost})
    out["top2_trail"] = trail
    return out


def germany_sales(data, deals):
    """CRM + payroll: pipeline, conversion, and the expansion cohort."""
    owners = rep_cohorts(data)
    new_reps = {u for u, e in owners.items() if e["country"] == "DE" and e["employment_start"] >= "2025-07-01"}
    veterans = {u for u, e in owners.items() if e["country"] == "DE" and u not in new_reps}
    res = {p: pipeline_and_winrate(deals, "DE", PERIODS[p]) for p in ("2025H1", "2026H1")}
    res["pipeline_growth"] = pct_change(res["2025H1"]["pipeline_created"], res["2026H1"]["pipeline_created"])
    res["won_value_change"] = pct_change(res["2025H1"]["won_value"], res["2026H1"]["won_value"])
    res["2026H1_new_reps"] = pipeline_and_winrate(deals, "DE", H1_26, new_reps)
    res["2026H1_veterans"] = pipeline_and_winrate(deals, "DE", H1_26, veterans)
    res["new_rep_share_of_pipeline_2026H1"] = res["2026H1_new_reps"]["pipeline_created"] / res["2026H1"]["pipeline_created"]
    for m in ("DK", "SE"):
        res[f"{m}_win_rate"] = {p: pipeline_and_winrate(deals, m, PERIODS[p])["win_rate"] for p in ("2025H1", "2026H1")}
    return res


def denmark(data, lines, deals):
    """ERP: mix and margin. CRM: service renewals."""
    mc = {p: market_category(lines, PERIODS[p])["DK"] for p in ("2025H1", "2026H1")}
    contract = {p: sum(l["revenue"] for l in lines if l["market"] == "DK" and l["product"] == "SA-STD" and within(l["date"], PERIODS[p]))
                for p in ("2025H1", "2026H1")}
    ren = [d for d in deals if d["mkt"] == "DK" and d["deal_type"] == "Renewal" and d["closed_at"] and within(d["closed_at"], ("2025-07-01", "2025-12-31"))]
    lost = [d for d in ren if d["outcome"] == "lost"]
    rev25, rev26 = mc["2025H1"]["revenue"], mc["2026H1"]["revenue"]
    return {"revenue": {"2025H1": rev25, "2026H1": rev26}, "revenue_change": pct_change(rev25, rev26),
            "gross_profit": {"2025H1": mc["2025H1"]["gross_profit"], "2026H1": mc["2026H1"]["gross_profit"]},
            "gross_margin": {"2025H1": mc["2025H1"]["gross_margin"], "2026H1": mc["2026H1"]["gross_margin"]},
            "service_share": {p: mc[p]["by_category"]["Service"]["share"] for p in mc},
            "equipment_share": {p: mc[p]["by_category"]["Equipment"]["share"] for p in mc},
            "service_revenue_change": pct_change(mc["2025H1"]["by_category"]["Service"]["revenue"], mc["2026H1"]["by_category"]["Service"]["revenue"]),
            "equipment_revenue_change": pct_change(mc["2025H1"]["by_category"]["Equipment"]["revenue"], mc["2026H1"]["by_category"]["Equipment"]["revenue"]),
            "category_margins": {p: {c: v["gross_margin"] for c, v in mc[p]["by_category"].items()} for p in mc},
            "mix_effect_on_gp": rev26 * mc["2025H1"]["gross_margin"] - mc["2026H1"]["gross_profit"],
            "contract_revenue": contract,
            "renewals_2025H2": {"closed": len(ren), "lost": len(lost),
                                "lost_value": sum(d["amount_dkk"] for d in lost),
                                "lost_value_share": sum(d["amount_dkk"] for d in lost) / max(1, sum(d["amount_dkk"] for d in ren))}}


def counterfactual(p_and_l, de_sales, mc26):
    """Q9: 2026 German deals converting at the 2025 win rate."""
    s25, s26 = de_sales["2025H1"], de_sales["2026H1"]
    extra_wins = (s25["win_rate"] - s26["win_rate"]) * s26["deals_closed"]
    extra_bookings = extra_wins * s26["avg_lost_deal"]
    gm = mc26["DE"]["by_category"]["Equipment"]["gross_margin"]
    extra_gp = extra_bookings * gm
    base = p_and_l["2026H1"]
    return {"extra_wins": extra_wins, "extra_bookings": extra_bookings, "de_equipment_gross_margin_2026H1": gm,
            "extra_gross_profit": extra_gp, "profit": base["profit"] + extra_gp,
            "margin": (base["profit"] + extra_gp) / (base["revenue"] + extra_bookings),
            "note": "Upper bound: assumes all extra bookings invoiced within H1 2026; excludes commission."}


def profit_bridge(data, p_and_l, mc25, mc26, pay):
    accounts = {r["account_number"]: r["type"] for r in data.erp_accounts}
    opex = {p: defaultdict(float) for p in ("2025H1", "2026H1")}
    for e in data.erp_ledger_entries:
        for p in opex:
            if within(e["date"], PERIODS[p]) and accounts[e["account_number"]] == "opex":
                opex[p][e["department"] or "(none)"] += num(e["amount_dkk"])
    b = {f"gross_profit_{m}": mc26[m]["gross_profit"] - mc25[m]["gross_profit"] for m in ("DK", "SE", "DE")}
    b["personnel_de_sales"] = -pay["de_sales_increase"]
    b["personnel_other"] = -(pay["increase"] - pay["de_sales_increase"])
    b["opex_de"] = -(opex["2026H1"]["DE"] - opex["2025H1"]["DE"])
    b["opex_other"] = -(sum(opex["2026H1"].values()) - sum(opex["2025H1"].values())) - b["opex_de"]
    b["total"] = sum(b.values())
    b["profit_change"] = p_and_l["2026H1"]["profit"] - p_and_l["2025H1"]["profit"]
    b["germany_total"] = b["gross_profit_DE"] + b["personnel_de_sales"] + b["opex_de"]
    return b


def derived(m):
    """Ratios and differences the checks refer to."""
    p25, p26 = m["pnl"]["2025H1"], m["pnl"]["2026H1"]
    pay, dk, gs, gc = m["payroll"], m["denmark"], m["germany_sales"], m["germany_customers"]
    profit_change = p26["profit"] - p25["profit"]
    de_rev = {p: m["markets"][p]["DE"]["revenue"] for p in ("2025H1", "2026H1")}
    per_rep = {p: de_rev[p] / pay["de_sales_headcount"][d] for p, d in (("2025H1", "2025-06-30"), ("2026H1", "2026-06-30"))}
    return {
        "revenue_growth": pct_change(p25["revenue"], p26["revenue"]),
        "ytd_revenue_growth": pct_change(m["pnl"]["2025YTD"]["revenue"], m["pnl"]["2026YTD"]["revenue"]),
        "ytd_profit_change": pct_change(m["pnl"]["2025YTD"]["profit"], m["pnl"]["2026YTD"]["profit"]),
        "gross_margin_change_pp": (p26["gross_margin"] - p25["gross_margin"]) * 100,
        "profit_change": profit_change,
        "personnel_reconciliation_diff": max(abs(m["pnl"][p]["personnel_ledger"] - pay["total"][p]) for p in ("2025H1", "2026H1")),
        "inflation_share_of_personnel_increase": pay["salary_inflation_effect"] / pay["increase"],
        "inflation_share_of_profit_decline": pay["salary_inflation_effect"] / -profit_change,
        "de_sales_share_of_personnel_increase": pay["de_sales_increase"] / pay["increase"],
        "de_revenue_per_salesperson": per_rep,
        "de_revenue_per_salesperson_change": pct_change(per_rep["2025H1"], per_rep["2026H1"]),
        "new_rep_vs_veteran_win_rate_gap": gs["2026H1_new_reps"]["win_rate"] - gs["2026H1_veterans"]["win_rate"],
        "de_new_customer_revenue_vs_existing_loss": gc["new_customers_revenue_2026H1"] / -gc["existing_customers_change"],
        "top2_names": " | ".join(t["name"] for t in gc["top_decliners"][:2]),
        "top2_lead_over_next_decliner": gc["top_decliners"][2]["change"] - gc["top_decliners"][1]["change"],
        "dk_service_share_change_pp": (dk["service_share"]["2026H1"] - dk["service_share"]["2025H1"]) * 100,
        "dk_equipment_share_change_pp": (dk["equipment_share"]["2026H1"] - dk["equipment_share"]["2025H1"]) * 100,
        "dk_gross_margin_change_pp": (dk["gross_margin"]["2026H1"] - dk["gross_margin"]["2025H1"]) * 100,
        "dk_gross_profit_change": dk["gross_profit"]["2026H1"] - dk["gross_profit"]["2025H1"],
        "dk_contract_revenue_change": pct_change(dk["contract_revenue"]["2025H1"], dk["contract_revenue"]["2026H1"]),
        "germany_share_of_profit_decline": m["bridge"]["germany_total"] / profit_change,
        "bridge_residual": m["bridge"]["total"] - profit_change,
        "counterfactual_margin_gap_pp": (p25["margin"] - m["counterfactual"]["margin"]) * 100,
    }


def compute_all(root):
    data = Data(root)
    lines = erp_lines(data)
    deals = crm_deals(data)
    p_and_l = pnl(data, lines)
    mc25, mc26 = market_category(lines, H1_25), market_category(lines, H1_26)
    pay = payroll(data)
    de_sales = germany_sales(data, deals)
    m = {
        "pnl": p_and_l,
        "markets": {"2025H1": mc25, "2026H1": mc26,
                    "change": {m: pct_change(mc25[m]["revenue"], mc26[m]["revenue"]) for m in ("DK", "SE", "DE")}},
        "payroll": pay,
        "germany_sales": de_sales,
        "germany_customers": germany_customers(data, lines),
        "denmark": denmark(data, lines, deals),
        "counterfactual": counterfactual(p_and_l, de_sales, mc26),
        "bridge": profit_bridge(data, p_and_l, mc25, mc26, pay),
        "_data": data,
    }
    m["derived"] = derived(m)
    return m
