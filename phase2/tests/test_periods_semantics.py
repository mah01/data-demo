from datetime import date

import pytest

from phase2.runtime.periods import parse_period, coverage_note
from phase2.runtime.semantics import semantics_topic


@pytest.mark.parametrize("text,start,end,label", [
    ("2026", date(2026, 1, 1), date(2026, 12, 31), "2026"),
    ("2026-H1", date(2026, 1, 1), date(2026, 6, 30), "2026-H1"),
    ("H2 2025", date(2025, 7, 1), date(2025, 12, 31), "2025-H2"),
    ("2026h1", date(2026, 1, 1), date(2026, 6, 30), "2026-H1"),
    ("2026-Q1", date(2026, 1, 1), date(2026, 3, 31), "2026-Q1"),
    ("Q4 2025", date(2025, 10, 1), date(2025, 12, 31), "2025-Q4"),
    ("2024-02", date(2024, 2, 1), date(2024, 2, 29), "2024-02"),
    ("2026-01..2026-08", date(2026, 1, 1), date(2026, 8, 31), "2026-01-01..2026-08-31"),
    ("2025-01-15..2025-02-10", date(2025, 1, 15), date(2025, 2, 10), "2025-01-15..2025-02-10"),
])
def test_period_formats(text, start, end, label):
    p = parse_period(text)
    assert (p.start, p.end, p.label) == (start, end, label)


def test_period_boundaries_inclusive():
    p = parse_period("2025-H1")
    assert p.contains(date(2025, 1, 1)) and p.contains(date(2025, 6, 30))
    assert not p.contains(date(2025, 7, 1)) and not p.contains(None)


@pytest.mark.parametrize("bad", ["", None, "2026-H3", "last year", "2026-06..2026-01"])
def test_period_errors(bad):
    with pytest.raises(ValueError):
        parse_period(bad)


def test_coverage_note():
    assert coverage_note(parse_period("2026"), date(2025, 1, 1), date(2026, 8, 31), "ERP").startswith("Period 2026 is only partly")
    assert coverage_note(parse_period("2026-H1"), date(2025, 1, 1), date(2026, 8, 31), "ERP") is None


@pytest.mark.parametrize("value,code", [("DK", "DK"), ("de", "DE"), ("Germany", "DE"), ("germany", "DE"),
                                        ("Tyskland", "DE"), ("Sverige", "SE"), ("Denmark", "DK")])
def test_market_normalisation(rt, value, code):
    assert rt.semantics.normalize_market(value) == code


def test_unknown_market_and_category_raise(rt):
    with pytest.raises(ValueError):
        rt.semantics.normalize_market("France")
    with pytest.raises(ValueError):
        rt.semantics.normalize_category("Software")


@pytest.mark.parametrize("value,cat", [("Equipment", "Equipment"), ("pumps & systems", "Equipment"), ("10", "Equipment"),
                                       ("Spare Parts Agreement", "Components"), ("30", "Service")])
def test_category_normalisation(rt, value, cat):
    assert rt.semantics.normalize_category(value) == cat


def test_semantics_topics(rt):
    everything = semantics_topic()
    for topic in ("systems", "currencies", "dates", "markets", "product_categories", "crm_stages", "metrics", "data_quality"):
        assert topic in everything
    assert "deal.currency" in rt.meta_get_semantics("markets")["rows"][0]["markets"]["crm_deals_fallback"] or \
        "currency" in rt.meta_get_semantics("markets")["rows"][0]["markets"]["crm_deals_fallback"]
    with pytest.raises(ValueError):
        semantics_topic("nonsense")


def test_describe_sources(rt):
    res = rt.meta_describe_sources()
    systems = {r["system"]: r for r in res["rows"]}
    assert set(systems) == {"erp", "crm", "payroll", "mappings"}
    assert systems["erp"]["tables"]["invoices"] == 6
    assert systems["erp"]["coverage"] == {"first": "2025-06-30", "last": "2026-07-01"}
