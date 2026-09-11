"""
EVALUATION SIDE ONLY. Builds the reference facts from the Phase 1 answer key
(ground_truth.json + Phase 1 analysis over the frozen dataset). Nothing here is
ever passed to the agent; the runner does not import this package.
"""
import json
import sys
from pathlib import Path

from phase2.runtime.sources import REPO_ROOT

REPORTS = Path(__file__).resolve().parents[1] / "reports"


def build():
    sys.path.insert(0, str(REPO_ROOT / "src"))
    import analysis  # Phase 1 evaluation code (allowed here only)
    m = analysis.compute_all(REPO_ROOT / "data")
    m.pop("_data")
    truth = json.loads((REPO_ROOT / "ground_truth.json").read_text(encoding="utf-8"))
    p25, p26, y25, y26 = (m["pnl"][k] for k in ("2025H1", "2026H1", "2025YTD", "2026YTD"))
    gs, gc, dk, pay, br, cf, dv = (m[k] for k in ("germany_sales", "germany_customers", "denmark", "payroll", "bridge",
                                                   "counterfactual", "derived"))
    mk = m["markets"]
    facts = {
        "company": {"revenue_h1": [p25["revenue"], p26["revenue"]], "operating_profit_h1": [p25["profit"], p26["profit"]],
                    "operating_margin_h1": [p25["margin"], p26["margin"]], "gross_margin_h1": [p25["gross_margin"], p26["gross_margin"]],
                    "revenue_ytd_jan_aug": [y25["revenue"], y26["revenue"]], "profit_ytd_jan_aug": [y25["profit"], y26["profit"]],
                    "other_opex_h1": [p25["other_opex"], p26["other_opex"]]},
        "markets_h1_revenue": {k: [mk["2025H1"][k]["revenue"], mk["2026H1"][k]["revenue"], mk["change"][k]] for k in ("DK", "SE", "DE")},
        "markets_h1_gross_profit": {k: [mk["2025H1"][k]["gross_profit"], mk["2026H1"][k]["gross_profit"]] for k in ("DK", "SE", "DE")},
        "personnel": {"total_h1": [pay["total"]["2025H1"], pay["total"]["2026H1"]], "increase": pay["increase"],
                      "de_sales_increase": pay["de_sales_increase"], "de_sales_share": dv["de_sales_share_of_personnel_increase"],
                      "salary_inflation_pct": pay["salary_inflation_pct"], "salary_inflation_effect": pay["salary_inflation_effect"],
                      "inflation_share_of_profit_decline": dv["inflation_share_of_profit_decline"],
                      "headcount": pay["headcount"], "de_sales_headcount": pay["de_sales_headcount"],
                      "de_expansion_hires": "4 German sales hires Sep 2025 - Jan 2026 (DE0258, DE0261, DE0264, DE0270)"},
        "germany_sales": {"pipeline_h1": [gs["2025H1"]["pipeline_created"], gs["2026H1"]["pipeline_created"]],
                          "pipeline_growth": gs["pipeline_growth"],
                          "win_rate_h1": [gs["2025H1"]["win_rate"], gs["2026H1"]["win_rate"]],
                          "won_value_change": gs["won_value_change"],
                          "new_rep_win_rate_2026H1": gs["2026H1_new_reps"]["win_rate"],
                          "veteran_win_rate_2026H1": gs["2026H1_veterans"]["win_rate"],
                          "revenue_per_salesperson": dv["de_revenue_per_salesperson"],
                          "loss_reasons_2026H1": gs["2026H1"]["loss_reasons"]},
        "germany_customers": {"existing_change": gc["existing_customers_change"], "new_customers_revenue": gc["new_customers_revenue_2026H1"],
                              "new_customers_count": gc["new_customers_count"], "top_decliners": gc["top_decliners"],
                              "top2_change": gc["top2_change"], "top2_trail": gc["top2_trail"]},
        "denmark": {k: dk[k] for k in ("revenue", "revenue_change", "gross_profit", "gross_margin", "service_share", "equipment_share",
                                        "service_revenue_change", "equipment_revenue_change", "contract_revenue", "renewals_2025H2")},
        "counterfactual": cf,
        "bridge": br,
        "story": truth["story"],
    }
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "reference_facts.json").write_text(json.dumps(facts, indent=2, default=str, ensure_ascii=False), encoding="utf-8")
    return facts


if __name__ == "__main__":
    f = build()
    print("reference facts written;", f["company"]["operating_profit_h1"])
