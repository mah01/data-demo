"""ERP primitives against the fixture dataset (expected values derived by hand from the CSVs)."""
import pytest

from .conftest import by, rows

approx = pytest.approx


def test_financial_summary_h1_2026(rt):
    r = rows(rt.finance.erp_financial_summary("2026-H1"))[0]
    assert r["revenue_dkk"] == approx(22860.0)            # 10360 (EUR 1400*7.40) + 10500 (SEK 15000*0.70) - 2000 + 4000
    assert r["cost_of_sales_dkk"] == approx(12650.0)
    assert r["gross_profit_dkk"] == approx(10210.0)
    assert r["personnel_costs_dkk"] == approx(1200.0)      # payroll journal only
    assert r["other_operating_costs_dkk"] == approx(750.0)  # 500 + 300 - 50; the 2026-07-01 entry is outside H1
    assert r["operating_profit_dkk"] == approx(8260.0)
    assert r["operating_margin"] == approx(8260 / 22860, abs=1e-4)
    assert (r["invoice_count"], r["credit_note_count"]) == (3, 1)


def test_financial_summary_comparison_and_boundaries(rt):
    r = rows(rt.finance.erp_financial_summary("2026-H1", compare_to="2025-H1"))[0]
    assert r["revenue_dkk_compare"] == approx(11000.0)    # invoice dated 2025-06-30 is inside H1 2025
    assert r["revenue_dkk_change"] == approx(11860.0)
    assert r["revenue_dkk_change_pct"] == approx(11860 / 11000, abs=1e-4)
    assert r["operating_profit_dkk_compare"] == approx(11000 - 7800 - 1000)
    assert r["gross_margin_change"] == approx(10210 / 22860 - 3200 / 11000, abs=1e-4)  # ratio -> points, no _pct
    assert "gross_margin_change_pct" not in r
    h2 = rows(rt.finance.erp_financial_summary("2025-H2"))[0]
    assert h2["revenue_dkk"] == approx(7500.0)            # 2025-07-01 belongs to H2


def test_sales_by_market_converts_currency(rt):
    res = rt.finance.erp_sales_summary("2026-H1", group_by=["market"])
    m = by(res, "market")
    assert m["DE"]["revenue_dkk"] == approx(10360.0) and m["SE"]["revenue_dkk"] == approx(10500.0)
    assert m["DK"]["revenue_dkk"] == approx(2000.0)       # credit note -2000 included
    assert m["DK"]["cost_dkk"] == approx(1650.0)
    assert res["totals"]["revenue_dkk"] == approx(22860.0)
    assert res["currency"] == "DKK"


def test_sales_source_currency_kept_when_grouped_by_currency(rt):
    c = by(rt.finance.erp_sales_summary("2026-H1", group_by=["currency"]), "currency")
    assert c["EUR"]["revenue_source_currency"] == approx(1400.0) and c["EUR"]["revenue_dkk"] == approx(10360.0)
    assert c["SEK"]["revenue_source_currency"] == approx(15000.0)
    assert "revenue_source_currency" not in rows(rt.finance.erp_sales_summary("2026-H1"))[0]


def test_sales_by_category_and_discount(rt):
    res = rt.finance.erp_sales_summary("2026-H1", group_by=["category"])
    c = by(res, "category")
    assert c["Equipment"]["revenue_dkk"] == approx(10360.0)
    assert c["Components"]["revenue_dkk"] == approx(2000.0)
    assert c["Components"]["avg_discount_pct"] == approx(1 - 2000 / 3000, abs=1e-4)  # list 5*1000 - 2*1000
    assert res["totals"]["avg_discount_pct"] == approx(1 - 22860 / 23860, abs=1e-4)


def test_sales_filters_and_labels(rt):
    a = rt.finance.erp_sales_summary("2026-H1", market="Tyskland")["totals"]["revenue_dkk"]
    b = rt.finance.erp_sales_summary("2026-H1", market="DE")["totals"]["revenue_dkk"]
    assert a == b == approx(10360.0)
    only_credit = rt.finance.erp_sales_summary("2026-H1", document_type="credit_note")["totals"]
    assert only_credit["revenue_dkk"] == approx(-2000.0)
    assert rt.finance.erp_sales_summary("2026-H1", category="Service", customer_number="30003")["totals"]["revenue_dkk"] \
        == approx(10500.0)


def test_sales_calendar_grouping_and_comparison(rt):
    months = by(rt.finance.erp_sales_summary("2026-H1", group_by=["month"]), "month")
    assert set(months) == {"2026-01", "2026-02", "2026-03", "2026-06"}
    assert months["2026-03"]["revenue_dkk"] == approx(-2000.0)
    cmp = by(rt.finance.erp_sales_summary("2026-H1", group_by=["market"], compare_to="2025-H1"), "market")
    assert cmp["DK"]["revenue_dkk_compare"] == approx(11000.0) and cmp["DK"]["revenue_dkk_change"] == approx(-9000.0)
    assert cmp["DE"]["revenue_dkk_compare"] == 0.0 and cmp["DE"]["revenue_dkk_change_pct"] is None


def test_sales_rejects_unknown_dimension(rt):
    with pytest.raises(ValueError):
        rt.finance.erp_sales_summary("2026-H1", group_by=["region"])


def test_customer_revenue_change_and_first_invoice(rt):
    res = rt.finance.erp_customer_revenue("2026-H1", compare_to="2025-H1", sort_by="revenue_dkk_change", ascending=True)
    first = rows(res)[0]
    assert first["customer_number"] == "10001" and first["revenue_dkk_change"] == approx(-9000.0)
    assert {r["customer_number"] for r in rows(res)} == {"10001", "20002", "30003"}  # union of both periods
    new = rt.finance.erp_customer_revenue("2026-H1", first_invoice_from="2025-07")
    assert {r["customer_number"] for r in rows(new)} == {"20002", "30003"}
    assert by(new, "customer_number")["20002"]["first_invoice_date"] == "2025-07-01"


def test_operating_costs(rt):
    acc = by(rt.finance.erp_operating_costs("2026-H1"), "account")
    assert acc["2210"]["amount_dkk"] == approx(1200.0) and acc["2210"]["account_type"] == "personnel"
    assert acc["2710"]["amount_dkk"] == approx(450.0)     # includes the -50 refund
    assert rt.finance.erp_operating_costs("2026-H1", account_type="opex")["totals"]["amount_dkk"] == approx(750.0)
    assert rt.finance.erp_operating_costs("2026-H1", department="Germany")["totals"]["amount_dkk"] == approx(300.0)
    assert rt.finance.erp_operating_costs("2026-H1", department="unassigned")["totals"]["amount_dkk"] == approx(1150.0)
    by_dept = by(rt.finance.erp_operating_costs("2026", group_by=["department"]), "department")
    assert by_dept[None]["amount_dkk"] == approx(1150.0)  # blank department kept as null
    assert "only partly covered" in " ".join(rt.finance.erp_operating_costs("2026")["notes"])


def test_ledger_entries_search(rt):
    res = rt.finance.erp_ledger_entries(text_contains="reise")
    assert res["row_count"] == 2
    assert rt.finance.erp_ledger_entries(period="2026-H1", department="DE")["row_count"] == 1


def test_find_customers(rt):
    assert rows(rt.finance.erp_find_customers("beta"))[0]["customer_number"] == "20002"
    assert rows(rt.finance.erp_find_customers("malmo"))== [] and rt.finance.erp_find_customers(market="SE")["row_count"] == 1
    c = rows(rt.finance.erp_find_customers(customer_number="20002"))[0]
    assert c["market"] == "DE" and c["vat_number"] is None  # missing optional field stays null


def test_invoices_and_lines(rt):
    credit = rows(rt.finance.erp_invoices(document_type="credit_note"))[0]
    assert credit["credited_invoice_number"] == "1" and credit["net_amount_dkk"] == approx(-2000.0)
    assert rt.finance.erp_invoices(min_amount_dkk=10000)["row_count"] == 3   # |amount| >= 10000 DKK
    assert rt.finance.erp_invoices(reference_contains="po-45")["row_count"] == 1
    lines = rows(rt.finance.erp_invoice_lines(invoice_number="3"))
    assert lines[0]["net_amount"] == approx(1400.0) and lines[0]["revenue_dkk"] == approx(10360.0)
    assert lines[0]["currency"] == "EUR" and lines[0]["category"] == "Equipment"
    assert rt.finance.erp_invoice_lines(invoice_number="1")["row_count"] == 2


def test_products(rt):
    assert {p["product_number"] for p in rows(rt.finance.erp_products("Components"))} == {"P-CO"}
    assert rt.finance.erp_products()["row_count"] == 3
