"""Payroll primitives against the fixture dataset."""
import pytest

from .conftest import by, rows

approx = pytest.approx


def test_headcount_point_in_time_boundaries(rt):
    assert rt.people.payroll_headcount(on_date="2026-06-30")["totals"]["headcount"] == 3
    on_last_day = by(rt.people.payroll_headcount(on_date="2026-03-31", group_by=["country"]), "country")
    assert on_last_day["SE"]["headcount"] == 1 and on_last_day["SE"]["part_time_count"] == 1  # end date inclusive
    assert rt.people.payroll_headcount(on_date="2026-01-14", country="DE")["totals"]["headcount"] == 0
    assert rt.people.payroll_headcount(on_date="2026-01-15", country="Germany")["totals"]["headcount"] == 1
    assert rt.people.payroll_headcount(period="2025-H1")["parameters"]["date"] == "2025-06-30"
    with pytest.raises(ValueError):
        rt.people.payroll_headcount(on_date="June 2026")


def test_headcount_average_monthly(rt):
    res = rt.people.payroll_headcount(period="2026-H1", basis="average_monthly")
    assert res["totals"] == {"avg_headcount": 3.0, "months": 2}   # 3 entries in 2026-01, 3 in 2026-06
    with pytest.raises(ValueError):
        rt.people.payroll_headcount(basis="average_monthly")


def test_personnel_costs_totals_and_groups(rt):
    res = rt.people.payroll_personnel_costs("2026-H1", group_by=["country"])
    assert res["totals"]["employer_cost_dkk"] == approx(248975.26, abs=0.01)
    c = by(res, "country")
    assert c["DK"]["employer_cost_dkk"] == approx(44796 + 45296 + 39180)
    assert c["DE"]["employer_cost_dkk"] == approx(29700.42 + 60929.55)
    assert c["DE"]["employee_count"] == 1 and c["DE"]["entry_count"] == 2


def test_personnel_cost_components_in_dkk(rt):
    t = rt.people.payroll_personnel_costs("2026-H1")["totals"]
    assert t["commission_dkk"] == approx(500 + 750 * 7.46)          # EUR commission converted with payroll FX
    assert t["base_salary_dkk"] == approx(41200 * 2 + 3290.32 * 7.46 + 6000 * 7.46 + 31000 * 0.69 + 36000, abs=0.01)


def test_personnel_costs_comparison_and_employee_grouping(rt):
    res = rt.people.payroll_personnel_costs("2026-H1", group_by=["employee"], compare_to="2025-H1")
    e = by(res, "employee")
    assert e["DE0002"]["employer_cost_dkk_compare"] == 0.0 and e["DE0002"]["employee_name"] == "Bernhard Schulz"
    assert e["DK0001"]["employer_cost_dkk_change"] == approx(44796 + 45296 - 44500)
    months = by(rt.people.payroll_personnel_costs("2026", group_by=["month"]), "month")
    assert set(months) == {"2026-01", "2026-06"}
    assert rt.people.payroll_personnel_costs("2026-H1", department="Sales")["totals"]["employee_count"] == 2


def test_hires_and_departures(rt):
    res = rt.people.payroll_hires_and_departures("2026-H1")
    assert res["totals"] == {"hires": 1, "departures": 1}
    events = {(r["event"], r["employee_id"], r["date"]) for r in rows(res)}
    assert events == {("hire", "DE0002", "2026-01-15"), ("departure", "SE0003", "2026-03-31")}
    assert rt.people.payroll_hires_and_departures("2025-07")["totals"]["hires"] == 1


def test_base_salary_change_like_for_like_and_fx_neutral(rt):
    one = rt.people.payroll_base_salary_change("2025-06", "2026-06")["totals"]
    assert one["employee_count"] == 1 and one["change_pct"] == approx(0.03, abs=1e-4)  # only DK0001 employed both months
    two = rt.people.payroll_base_salary_change("2025-06", "2026-01", group_by=["country"])
    assert two["totals"]["employee_count"] == 2
    expected = (41200 + 31000 * 0.66) / (40000 + 30000 * 0.66) - 1                      # SEK at the from-month rate
    assert two["totals"]["change_pct"] == approx(expected, abs=1e-4)
    assert by(two, "country")["SE"]["change_pct"] == approx(31000 / 30000 - 1, abs=1e-4)


def test_employee_lookup_and_entries(rt):
    assert rows(rt.people.payroll_find_employees("cecilia"))[0]["status"] == "terminated"
    assert rt.people.payroll_find_employees(status="active", country="DK")["row_count"] == 2
    assert rows(rt.people.payroll_find_employees(employee_id="DE0002"))[0]["work_email"] is None
    ent = rows(rt.people.payroll_entries(employee_id="SE0003"))
    assert [e["pay_period"] for e in ent] == ["2025-06", "2026-01"]
    assert ent[1]["currency"] == "SEK" and ent[1]["employer_cost_dkk"] == approx(29073.29)
