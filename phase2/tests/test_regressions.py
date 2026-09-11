"""Regression tests for defects found by the Phase 2B agent evaluation (fixed on the phase3-demo line)."""
from datetime import date

import pytest

from phase2.runtime.periods import parse_period
from phase2.runtime.query.common import compare_rows

from .conftest import by, rows


# --- Defect 1: comparison crashed when a nullable measure was null now but set in the comparison period -------------
def test_compare_rows_tolerates_null_current_value():
    cur = [{"owner": "a", "won_count": 0, "avg_won_value_dkk": None}]
    prev = [{"owner": "a", "won_count": 2, "avg_won_value_dkk": 50000.0}]
    row = compare_rows(cur, prev, ["owner"], ["won_count", "avg_won_value_dkk"])[0]
    assert row["avg_won_value_dkk_compare"] == 50000.0
    assert row["avg_won_value_dkk_change"] is None and row["avg_won_value_dkk_change_pct"] is None
    assert row["won_count_change"] == -2 and row["won_count_change_pct"] == -1.0


def test_win_rate_comparison_with_group_that_only_won_in_comparison_period(rt):
    """Before the fix this raised TypeError (Phase 2B runs Q06/Q09): usr_000001 won a deal in 2025-H1
    but only lost (a renewal) in 2025-H2, so avg_won_value_dkk is null in the current period."""
    res = rt.sales.crm_win_rate("2025-H2", compare_to="2025-H1", group_by=["owner"], include_renewals=True)
    anna = by(res, "owner")["usr_000001"]
    assert anna["won_count"] == 0 and anna["avg_won_value_dkk"] is None
    assert anna["avg_won_value_dkk_compare"] == pytest.approx(100000.0)
    assert anna["avg_won_value_dkk_change_pct"] is None


def test_win_rate_comparison_by_deal_type_and_category(rt):
    res = rt.sales.crm_win_rate("2026-H1", compare_to="2025", group_by=["deal_type", "category"])
    assert res["row_count"] >= 2


# --- Defect 2: single dates were rejected where a period is expected -------------------------------------------------
def test_single_date_is_a_one_day_period():
    p = parse_period("2025-09-01")
    assert (p.start, p.end, p.label) == (date(2025, 9, 1), date(2025, 9, 1), "2025-09-01")
    with pytest.raises(ValueError):
        parse_period("2025-13-01")


def test_first_invoice_filters_accept_single_dates(rt):
    got = {r["customer_number"] for r in rows(rt.finance.erp_customer_revenue("2026-H1", first_invoice_from="2025-07-01"))}
    assert got == {"20002", "30003"}          # first invoiced 2025-07-01 (boundary included) and 2026-02-15
    only = rt.finance.erp_customer_revenue("2026-H1", first_invoice_from="2025-07-02", first_invoice_to="2026-12-31")
    assert {r["customer_number"] for r in rows(only)} == {"30003"}


def test_open_pipeline_on_a_single_day(rt):
    res = rt.sales.crm_pipeline("2025-12-31", basis="open_at_end")
    assert res["totals"]["deal_count"] == 1 and res["period"] == {"label": "2025-12-31", "start": "2025-12-31",
                                                                     "end": "2025-12-31"}


def test_single_day_sales(rt):
    assert rt.finance.erp_sales_summary("2025-06-30")["totals"]["revenue_dkk"] == pytest.approx(11000.0)
