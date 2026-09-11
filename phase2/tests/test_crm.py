"""CRM primitives against the fixture dataset."""
import pytest

from .conftest import by, rows

approx = pytest.approx


def test_market_fallback_chain(rt):
    deals = {d["deal_id"]: d for d in rows(rt.sales.crm_deals(limit=None))}
    assert (deals["1000000001"]["market"], deals["1000000001"]["market_source"]) == ("DK", "deal.market")
    assert (deals["1000000002"]["market"], deals["1000000002"]["market_source"]) == ("DE", "company.country")
    assert (deals["1000000003"]["market"], deals["1000000003"]["market_source"]) == ("DE", "deal.currency")
    assert deals["1000000003"]["category"] is None      # blank product_category stays null


def test_pipeline_created(rt):
    res = rt.sales.crm_pipeline("2026-H1")
    assert res["totals"]["deal_count"] == 3              # deals 3, 4, 6 (renewal 7 excluded)
    assert res["totals"]["value_dkk"] == approx(149200 + 37300 + 7460)
    h1_25 = rt.sales.crm_pipeline("2025-H1")["totals"]
    assert h1_25["deal_count"] == 2 and h1_25["value_dkk"] == approx(174600.0)  # created 2025-06-30 is inside H1


def test_pipeline_grouping_and_comparison(rt):
    m = by(rt.sales.crm_pipeline("2026-H1", group_by=["market"], compare_to="2025-H1"), "market")
    assert m["DE"]["deal_count"] == 3 and m["DE"]["deal_count_compare"] == 1
    assert m["DK"]["deal_count"] == 0 and m["DK"]["value_dkk_compare"] == approx(100000.0)
    src = by(rt.sales.crm_pipeline("2026-H1", group_by=["market_source"]), "market_source")
    assert src["deal.currency"]["deal_count"] == 1


def test_pipeline_open_at_end(rt):
    res = rt.sales.crm_pipeline("2025-H2", basis="open_at_end")
    assert res["totals"]["deal_count"] == 1 and res["totals"]["value_dkk"] == approx(74600.0)  # deal 2 closes 2026-01-15
    assert any("not recorded" in n for n in res["notes"])
    with pytest.raises(ValueError):
        rt.sales.crm_pipeline("2026-H1", basis="forecast")


def test_pipeline_renewal_switch(rt):
    assert rt.sales.crm_pipeline("2026-H1", include_renewals=True)["totals"]["deal_count"] == 4
    assert rt.sales.crm_pipeline("2026-H1", deal_type="Renewal")["totals"]["deal_count"] == 1


def test_win_rate(rt):
    t = rt.sales.crm_win_rate("2026-H1")["totals"]
    assert (t["closed_count"], t["won_count"], t["lost_count"]) == (3, 1, 2)   # 2 lost (1-15, 5-1), 1 won (6-30 23:00)
    assert t["win_rate"] == approx(1 / 3, abs=1e-4)
    assert t["won_value_dkk"] == approx(149200.0) and t["lost_value_dkk"] == approx(82060.0)
    assert t["value_win_rate"] == approx(149200 / 231260, abs=1e-4)
    assert rt.sales.crm_win_rate("2026-H1", include_renewals=True)["totals"]["won_count"] == 2
    assert rt.sales.crm_win_rate("2025-H1")["totals"]["win_rate"] == 1.0      # closed 2025-06-30 16:00 inside H1


def test_win_rate_by_owner_and_filter(rt):
    owners = by(rt.sales.crm_win_rate("2026-H1", group_by=["owner"]), "owner")
    assert owners["usr_000003"]["owner_name"] == "Carl Alt" and owners["usr_000003"]["lost_count"] == 1
    only = rt.sales.crm_win_rate("2026-H1", owner_ids=["usr_000002"])["totals"]
    assert (only["closed_count"], only["won_count"]) == (2, 1)
    cmp = rows(rt.sales.crm_win_rate("2026-H1", compare_to="2025-H1", group_by=["market"]))
    de = next(r for r in cmp if r["market"] == "DE")
    assert de["win_rate_compare"] is None and de["win_rate_change"] is None   # no DE deals closed in H1 2025


def test_loss_reasons_blank_reported(rt):
    res = by(rt.sales.crm_loss_reasons("2026-H1"), "loss_reason")
    assert res["Price too high"]["lost_count"] == 1
    assert res["(not recorded)"]["lost_count"] == 1 and res["(not recorded)"]["share_of_lost"] == 0.5


def test_deals_listing(rt):
    assert rt.sales.crm_deals(outcome="open")["row_count"] == 1
    closed = rt.sales.crm_deals(period="2026-H1", date_field="closed")
    assert {d["deal_id"] for d in rows(closed)} == {"1000000002", "1000000003", "1000000006", "1000000007"}
    assert rt.sales.crm_deals(company_id="cmp_00004")["row_count"] == 2
    assert rt.sales.crm_deals(name_contains="pumpen")["row_count"] == 1
    assert rt.sales.crm_deals(market="Germany", min_value_dkk=50000)["row_count"] == 3
    with pytest.raises(ValueError):
        rt.sales.crm_deals(date_field="updated")


def test_renewals(rt):
    res = rt.sales.crm_renewals("2025-H2")
    assert res["totals"]["lost_count"] == 1 and res["totals"]["lost_value_share"] == 1.0
    assert rt.sales.crm_renewals("2026-H1")["totals"]["renewal_rate"] == 1.0


def test_companies_activities_history_users(rt):
    comps = rows(rt.sales.crm_find_companies("beta chemie"))
    assert {c["company_id"] for c in comps} == {"cmp_00002", "cmp_00003"}   # duplicate record found by name
    assert rows(rt.sales.crm_find_companies(company_id="cmp_00003"))[0]["market"] is None  # blank country
    acts = rt.sales.crm_activities(text_contains="rabatt")
    assert acts["row_count"] == 1 and rows(acts)[0]["owner_name"] == "Bernd Schulz"
    summary = by(rt.sales.crm_activity_summary("2025-01..2026-06"), "month")
    assert summary["2026-01"]["activity_count"] == 2
    types = by(rt.sales.crm_activity_summary("2026", group_by=["type"], market="DE"), "type")
    assert set(types) == {"EMAIL"}                    # cmp_00004 has no country, so its note has no market
    hist = rows(rt.sales.crm_owner_history(company_id="cmp_00002"))
    assert hist[0]["value_before_name"] == "Carl Alt" and hist[0]["value_after_name"] == "Bernd Schulz"
    assert rt.sales.crm_owner_history(owner_id="usr_000002")["row_count"] == 2
    assert rt.sales.crm_owner_history(property=None)["row_count"] == 3
    assert {u["user_id"] for u in rows(rt.sales.crm_users(active=False))} == {"usr_000003"}
