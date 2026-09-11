"""
Generic integration checks on the frozen dataset: aggregations reconcile, every
operation returns JSON, mappings resolve. These test the query layer's
mechanics, NOT any business conclusion about the scenario.
"""
import json

import pytest

from .conftest import by, rows
from .examples import EXAMPLES

approx = pytest.approx
PERIOD = "2026-H1"


def test_every_operation_runs_and_is_json(real):
    ops = real.operations()
    for name, kwargs in EXAMPLES.items():
        out = ops[name](**kwargs)
        json.dumps(out)
        assert out["operation"] == name and "rows" in out


def test_revenue_reconciles_across_groupings(real):
    total = rows(real.finance.erp_financial_summary(PERIOD))[0]["revenue_dkk"]
    for group in (["market"], ["category"], ["month"], ["currency"], ["market", "category"], ["document_type"]):
        res = real.finance.erp_sales_summary(PERIOD, group_by=group, limit=None)
        assert sum(r["revenue_dkk"] for r in rows(res)) == approx(total, abs=1.0), group
        assert res["totals"]["revenue_dkk"] == approx(total, abs=0.01)


def test_customer_revenue_sums_to_total(real):
    total = real.finance.erp_sales_summary(PERIOD)["totals"]["revenue_dkk"]
    res = real.finance.erp_customer_revenue(PERIOD, limit=None)
    assert sum(r["revenue_dkk"] for r in rows(res)) == approx(total, abs=1.0)


def test_cost_ledger_reconciles(real):
    fin = rows(real.finance.erp_financial_summary(PERIOD))[0]
    types = by(real.finance.erp_operating_costs(PERIOD, group_by=["account_type"]), "account_type")
    assert types["personnel"]["amount_dkk"] == approx(fin["personnel_costs_dkk"], abs=0.01)
    assert types["opex"]["amount_dkk"] == approx(fin["other_operating_costs_dkk"], abs=0.01)


def test_payroll_matches_erp_payroll_journal(real):
    """Cross-system consistency of the exports: payroll employer cost = ERP payroll journal."""
    for period in ("2025-H1", "2026-H1", "2025-07"):
        pay = real.people.payroll_personnel_costs(period)["totals"]["employer_cost_dkk"]
        erp = rows(real.finance.erp_financial_summary(period))[0]["personnel_costs_dkk"]
        assert pay == approx(erp, abs=1.0)


def test_crm_aggregations_reconcile(real):
    t = real.sales.crm_win_rate(PERIOD)["totals"]
    assert t["closed_count"] == t["won_count"] + t["lost_count"]
    m = rows(real.sales.crm_win_rate(PERIOD, group_by=["market"]))
    assert sum(r["closed_count"] for r in m) == t["closed_count"]
    p = real.sales.crm_pipeline(PERIOD, group_by=["market"])
    assert sum(r["value_dkk"] for r in rows(p)) == approx(p["totals"]["value_dkk"], abs=1.0)
    reasons = real.sales.crm_loss_reasons(PERIOD)
    assert sum(r["lost_count"] for r in rows(reasons)) == t["lost_count"]


def test_every_deal_gets_a_market_via_documented_fallback(real):
    deals = rows(real.sales.crm_deals(limit=None))
    assert all(d["market"] in ("DK", "SE", "DE") for d in deals)
    assert {d["market_source"] for d in deals} <= {"deal.market", "company.country", "deal.currency"}


def test_headcount_groups_sum(real):
    res = real.people.payroll_headcount(on_date="2026-06-30", group_by=["country", "department"])
    assert sum(r["headcount"] for r in rows(res)) == res["totals"]["headcount"]


def test_mappings_resolve_in_both_directions(real):
    links = real.identity.company_links
    res = rows(real.links.identity_crm_companies_to_erp([l["crm_company_id"] for l in links]))
    assert all(r["status"] == "mapped" and r["crm_name"] and r["links"][0]["erp_name"] for r in res)
    back = rows(real.links.identity_erp_customers_to_crm(sorted({l["erp_customer_number"] for l in links})))
    assert all(r["status"] == "mapped" for r in back)
    people = [l for l in real.identity.person_links if l["payroll_employee_id"]]
    res = rows(real.links.identity_employees_to_crm_users([l["payroll_employee_id"] for l in people]))
    assert all(r["status"] == "mapped" and r["employee_name"] for r in res)


def test_partial_period_is_flagged(real):
    notes = real.finance.erp_financial_summary("2026")["notes"]
    assert any("only partly covered" in n for n in notes)
