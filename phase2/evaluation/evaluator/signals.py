"""
EVALUATION SIDE ONLY. Heuristic discovery signals per run, from the final answer
text (was the item *stated*?) and the tool trace (was it *investigated*?).

These are aids for the human-readable assessment, not the verdict: keyword
matching can miss paraphrases and over-match, so every flag is shown with
the matching snippet for review.
"""
import json
import re

DISCOVERIES = {
    "revenue_up_profit_down": "Overall revenue growth but operating-profit deterioration",
    "germany_major_contributor": "Germany as a major contributor to the profit decline",
    "german_sales_headcount_expansion": "German sales headcount expansion (8 -> 12)",
    "pipeline_up_conversion_down": "Pipeline growth combined with worse conversion (win rate)",
    "new_rep_underperformance": "Poor new-rep performance (new hires convert worse)",
    "key_accounts_named": "Rheinmark / Brandauer identified at customer level",
    "denmark_mix_margin": "Danish revenue growth masking mix / margin deterioration",
    "salary_inflation_insufficient": "Salary inflation insufficient to explain the profit decline",
}

GER = r"(german|germany|\bde\b|dach)"


def _sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text or "") if s.strip()]


def _find(text, *patterns, window=None):
    """First sentence containing all regex patterns (case-insensitive)."""
    for s in _sentences(text):
        if all(re.search(p, s, re.I) for p in patterns):
            return s[:300]
    return None


def _calls(run, tool, **arg_match):
    out = []
    for c in run["tool_calls"]:
        if c["tool"] != tool:
            continue
        args = json.dumps(c["arguments"]).lower()
        if all(str(v).lower() in args for v in arg_match.values()):
            out.append(c["seq"])
    return out


def detect(run):
    a = run.get("final_answer") or ""
    de_market = lambda tool: _calls(run, tool, m="de") + _calls(run, tool, m="germany")
    sig = {
        "revenue_up_profit_down": {
            "stated": _find(a, r"revenue", r"(up|grew|grow|increase|higher|\+\s?\d)") and
                      _find(a, r"(operating profit|profit|ebit|margin)", r"(down|fell|fall|declin|lower|decreas|drop|-\s?\d|−)"),
            "investigated": _calls(run, "erp_financial_summary")},
        "germany_major_contributor": {
            "stated": _find(a, GER, r"(profit|margin|decline|drag|loss|fell|down|deteriorat|biggest|largest|main)"),
            "investigated": sorted(set(de_market("erp_sales_summary") + de_market("crm_win_rate") +
                                       _calls(run, "erp_sales_summary", g="market")))},
        "german_sales_headcount_expansion": {
            "stated": _find(a, GER, r"(sales|salespeople|reps?|headcount|hires?|hired)", r"(\b8\b|\b12\b|four|4 new|expan|added|increase)"),
            "investigated": _calls(run, "payroll_headcount") + _calls(run, "payroll_hires_and_departures")},
        "pipeline_up_conversion_down": {
            "stated": _find(a, r"pipeline", r"(grew|grow|up|increase|\+\s?\d|higher)") and
                      _find(a, r"(win rate|conversion|convert)", r"(fell|fall|declin|down|lower|drop|dropped|worse|\d+%)"),
            "investigated": _calls(run, "crm_pipeline") and _calls(run, "crm_win_rate")},
        "new_rep_underperformance": {
            "stated": _find(a, r"(new|recent|newly)\s+(hire|hires|reps?|sales|salespeople|joiners|recruits|account managers)",
                            r"(win|convert|conversion|lower|worse|weak|below|%)"),
            "investigated": [c["seq"] for c in run["tool_calls"] if c["tool"] == "crm_win_rate" and
                             ("owner_ids" in c["arguments"] or "owner" in json.dumps(c["arguments"].get("group_by", "")))]},
        "key_accounts_named": {
            "stated": _find(a, r"(rheinmark|brandauer)"),
            "investigated": _calls(run, "erp_customer_revenue") + _calls(run, "crm_owner_history")},
        "denmark_mix_margin": {
            "stated": _find(a, r"(denmark|danish|\bdk\b)", r"(service|mix|margin|gross profit|equipment)"),
            "investigated": _calls(run, "erp_sales_summary", m="dk") + _calls(run, "erp_sales_summary", m="denmark")},
        "salary_inflation_insufficient": {
            "stated": _find(a, r"(salary|salaries|raise|pay (rise|increase)|wage|inflation|base pay)",
                            r"(only|small|modest|minor|not the|doesn|does not|limited|fraction|\d+(\.\d)?\s?%)"),
            "investigated": _calls(run, "payroll_base_salary_change")},
    }
    return {k: {"stated": bool(v["stated"]), "snippet": v["stated"] if isinstance(v["stated"], str) else None,
                "investigated": bool(v["investigated"])} for k, v in sig.items()}
