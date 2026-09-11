"""Generic finance operations over the ERP adapter. Values in DKK."""
from ..periods import coverage_note, parse_period
from ..sources import fold
from .common import (aggregate, calendar_dims, check_dims, compare_rows, envelope, periods, ratio, sort_limit)

SALES_SUMS = ["revenue_dkk", "cost_dkk", "gross_profit_dkk", "list_value_dkk", "net_amount", "quantity"]
SALES_MEASURES = ["revenue_dkk", "cost_dkk", "gross_profit_dkk", "gross_margin", "avg_discount_pct"]


class FinanceQueries:
    def __init__(self, erp, semantics):
        self.erp, self.sem = erp, semantics
        self.sales_dims = {
            "market": lambda r: r["market"], "category": lambda r: r["category"],
            "customer": lambda r: r["customer_number"], "product": lambda r: r["product_number"],
            "product_group": lambda r: r["product_group_number"], "currency": lambda r: r["currency"],
            "document_type": lambda r: r["document_type"], **calendar_dims("invoice_date")}
        self.cost_dims = {
            "account": lambda r: r["account_number"], "account_type": lambda r: r["account_type"],
            "department": lambda r: r["department"], **calendar_dims("date")}

    # ------------------------------------------------------------------ helpers
    def _note(self, p):
        return coverage_note(p, *self.erp.coverage(), "ERP")

    def _lines(self, p, market=None, category=None, customer_number=None, product_number=None, document_type=None):
        market, category = self.sem.normalize_market(market), self.sem.normalize_category(category)
        return [l for l in self.erp.sales_lines if p.contains(l["invoice_date"])
                and (market is None or l["market"] == market) and (category is None or l["category"] == category)
                and (customer_number is None or l["customer_number"] == str(customer_number))
                and (product_number is None or l["product_number"] == product_number)
                and (document_type is None or l["document_type"] == document_type)]

    @staticmethod
    def _finish_sales(row, keep_currency, keep_qty):
        row["gross_margin"] = ratio(row["gross_profit_dkk"], row["revenue_dkk"])
        row["avg_discount_pct"] = (1 - row["revenue_dkk"] / row["list_value_dkk"]) if row["list_value_dkk"] > 0 else None
        amount = row.pop("net_amount")
        if keep_currency:
            row["revenue_source_currency"] = amount
        qty = row.pop("quantity")
        if keep_qty:
            row["quantity"] = qty
        row.pop("list_value_dkk")
        row["line_count"] = row.pop("record_count")
        return row

    def _sales_rows(self, lines, group_by):
        rows = aggregate(lines, group_by, self.sales_dims, SALES_SUMS,
                         {"invoice_count": lambda r: r["invoice_number"], "customer_count": lambda r: r["customer_number"]})
        for r in rows:
            self._finish_sales(r, "currency" in group_by, "product" in group_by)
            if "customer" in group_by:
                c = self.erp.customers.get(r["customer"], {})
                r["customer_name"], r["customer_market"] = c.get("name"), c.get("market")
            if "product" in group_by:
                r["product_name"] = self.erp.products.get(r["product"], {}).get("name")
        return rows

    def _period_totals(self, p):
        lines = self._lines(p)
        revenue = sum(l["revenue_dkk"] for l in lines)
        cost = sum(l["cost_dkk"] for l in lines)
        ledger = [e for e in self.erp.ledger if p.contains(e["date"])]
        personnel = sum(e["amount_dkk"] for e in ledger if e["account_type"] == "personnel")
        opex = sum(e["amount_dkk"] for e in ledger if e["account_type"] == "opex")
        invoices = {l["invoice_number"] for l in lines}
        profit = revenue - cost - personnel - opex
        return {"revenue_dkk": revenue, "cost_of_sales_dkk": cost, "gross_profit_dkk": revenue - cost,
                "gross_margin": ratio(revenue - cost, revenue), "personnel_costs_dkk": personnel,
                "other_operating_costs_dkk": opex, "operating_profit_dkk": profit,
                "operating_margin": ratio(profit, revenue),
                "invoice_count": sum(1 for n in invoices if self.erp.invoices[n]["document_type"] == "invoice"),
                "credit_note_count": sum(1 for n in invoices if self.erp.invoices[n]["document_type"] == "credit_note")}

    # ------------------------------------------------------------------ operations
    def erp_financial_summary(self, period: str, compare_to: str | None = None) -> dict:
        """Company P&L from the ERP for a period: revenue, cost of sales, gross profit and margin, personnel
        costs (payroll journal), other operating costs, operating profit and margin. Optional comparison period."""
        p, c = periods(period, compare_to)
        measures = ["revenue_dkk", "cost_of_sales_dkk", "gross_profit_dkk", "gross_margin", "personnel_costs_dkk",
                    "other_operating_costs_dkk", "operating_profit_dkk", "operating_margin"]
        rows = [self._period_totals(p)]
        if c:
            rows = compare_rows(rows, [self._period_totals(c)], [], measures)
        return envelope("erp_financial_summary", "erp", {"period": period, "compare_to": compare_to}, rows,
                        period=p, compare=c, notes=[self._note(p), c and self._note(c),
                        "Operating costs are company-level; the payroll journal is not split by market."])

    def erp_sales_summary(self, period: str, group_by: list[str] | None = None, market: str | None = None,
                          category: str | None = None, customer_number: str | None = None,
                          product_number: str | None = None, document_type: str | None = None,
                          compare_to: str | None = None, sort_by: str | None = "revenue_dkk",
                          ascending: bool = False, limit: int = 100) -> dict:
        """Revenue, cost of sales, gross profit, gross margin and average discount from invoice lines, grouped by
        any of: market, category, customer, product, product_group, currency, document_type, month, quarter,
        half, year. Filters narrow the lines first. Optional comparison period adds _compare/_change columns."""
        group_by = check_dims(group_by, self.sales_dims)
        p, c = periods(period, compare_to)
        f = dict(market=market, category=category, customer_number=customer_number, product_number=product_number,
                 document_type=document_type)
        rows = self._sales_rows(self._lines(p, **f), group_by)
        totals = self._sales_rows(self._lines(p, **f), [])
        if c:
            rows = compare_rows(rows, self._sales_rows(self._lines(c, **f), group_by), group_by, SALES_MEASURES)
            totals = compare_rows(totals, self._sales_rows(self._lines(c, **f), []), [], SALES_MEASURES)
        rows, n = sort_limit(rows, sort_by, ascending, limit)
        return envelope("erp_sales_summary", "erp", {"period": period, "group_by": group_by, **f,
                        "compare_to": compare_to}, rows, period=p, compare=c, totals=totals[0] if totals else None,
                        total_rows=n, notes=[self._note(p), c and self._note(c)])

    def erp_customer_revenue(self, period: str, compare_to: str | None = None, market: str | None = None,
                             category: str | None = None, first_invoice_from: str | None = None,
                             first_invoice_to: str | None = None, min_revenue_dkk: float | None = None,
                             sort_by: str | None = "revenue_dkk", ascending: bool = False, limit: int = 50) -> dict:
        """Revenue and gross profit per ERP customer, with each customer's first and last invoice date in the
        whole export. With compare_to, customers active in either period are included with change columns
        (sort_by='revenue_dkk_change' ascending lists the largest decreases). first_invoice_from/to filter
        customers by when they were first invoiced (e.g. to separate new from existing customers)."""
        p, c = periods(period, compare_to)
        first, last = {}, {}
        for l in self.erp.sales_lines:
            n = l["customer_number"]
            first[n] = min(first.get(n, l["invoice_date"]), l["invoice_date"])
            last[n] = max(last.get(n, l["invoice_date"]), l["invoice_date"])
        f = dict(market=market, category=category)
        measures = ["revenue_dkk", "gross_profit_dkk", "gross_margin"]
        rows = self._sales_rows(self._lines(p, **f), ["customer"])
        if c:
            rows = compare_rows(rows, self._sales_rows(self._lines(c, **f), ["customer"]), ["customer"], measures)
        lo = parse_period(first_invoice_from).start if first_invoice_from else None
        hi = parse_period(first_invoice_to).end if first_invoice_to else None
        out = []
        for r in rows:
            n = r["customer"]
            if (lo and first[n] < lo) or (hi and first[n] > hi):
                continue
            size = max(abs(r.get("revenue_dkk") or 0), abs(r.get("revenue_dkk_compare") or 0))
            if min_revenue_dkk is not None and size < min_revenue_dkk:
                continue
            cust = self.erp.customers.get(n, {})
            keep = {k: v for k, v in r.items() if k in ("revenue_dkk", "gross_profit_dkk", "gross_margin", "invoice_count")
                    or k.endswith(("_compare", "_change", "_change_pct"))}
            out.append({"customer_number": n, "customer_name": cust.get("name"), "market": cust.get("market"),
                        "first_invoice_date": first[n], "last_invoice_date": last[n], **keep})
        out, total = sort_limit(out, sort_by, ascending, limit)
        return envelope("erp_customer_revenue", "erp", {"period": period, "compare_to": compare_to, **f,
                        "first_invoice_from": first_invoice_from, "first_invoice_to": first_invoice_to,
                        "min_revenue_dkk": min_revenue_dkk}, out, period=p, compare=c, total_rows=total,
                        notes=[self._note(p), c and self._note(c)])

    def erp_operating_costs(self, period: str, group_by: list[str] | None = None, account_type: str | None = None,
                            department: str | None = None, compare_to: str | None = None,
                            sort_by: str | None = "amount_dkk", ascending: bool = False, limit: int = 100) -> dict:
        """Cost ledger (payroll journal + operating expenses) in DKK, grouped by any of: account, account_type,
        department, month, quarter, half, year (default: account). account_type: 'personnel' or 'opex'.
        department: DK/SE/DE or 'unassigned' (entries without department, incl. the payroll journal)."""
        group_by = check_dims(group_by or ["account"], self.cost_dims)
        p, c = periods(period, compare_to)
        dept = None if department is None else ("__none__" if department.lower() == "unassigned"
                                                 else self.sem.normalize_market(department))

        def rows_for(per, dims):
            entries = [e for e in self.erp.ledger if per.contains(e["date"])
                       and e["account_type"] in ("personnel", "opex")
                       and (account_type is None or e["account_type"] == account_type)
                       and (dept is None or e["department"] == (None if dept == "__none__" else dept))]
            rows = aggregate(entries, dims, self.cost_dims, ["amount_dkk"])
            for r in rows:
                r["entry_count"] = r.pop("record_count")
                if "account" in dims:
                    acc = self.erp.accounts.get(r["account"], {})
                    r["account_name"], r["account_type"] = acc.get("name"), acc.get("type")
            return rows
        rows, totals = rows_for(p, group_by), rows_for(p, [])
        if c:
            rows = compare_rows(rows, rows_for(c, group_by), group_by, ["amount_dkk"])
            totals = compare_rows(totals, rows_for(c, []), [], ["amount_dkk"])
        rows, n = sort_limit(rows, sort_by, ascending, limit)
        return envelope("erp_operating_costs", "erp", {"period": period, "group_by": group_by,
                        "account_type": account_type, "department": department, "compare_to": compare_to}, rows,
                        period=p, compare=c, totals=totals[0] if totals else {"amount_dkk": 0.0}, total_rows=n,
                        notes=[self._note(p), c and self._note(c)])

    def erp_ledger_entries(self, period: str | None = None, account_number: str | None = None,
                           account_type: str | None = None, department: str | None = None,
                           text_contains: str | None = None, limit: int = 100) -> dict:
        """Individual cost ledger entries (date, voucher, account, department, DKK amount, text)."""
        p = parse_period(period) if period else None
        dept = self.sem.normalize_market(department) if department else None
        rows = [e for e in self.erp.ledger if (p is None or p.contains(e["date"]))
                and (account_number is None or e["account_number"] == str(account_number))
                and (account_type is None or e["account_type"] == account_type)
                and (dept is None or e["department"] == dept)
                and (text_contains is None or fold(text_contains) in fold(e["text"]))]
        rows, n = sort_limit(rows, "date", False, limit)
        return envelope("erp_ledger_entries", "erp", {"period": period, "account_number": account_number,
                        "account_type": account_type, "department": department, "text_contains": text_contains},
                        rows, period=p, total_rows=n)

    def erp_find_customers(self, query: str | None = None, customer_number: str | None = None,
                           market: str | None = None, limit: int = 20) -> dict:
        """ERP customer master records by customer number or (accent/case-insensitive) name search."""
        mkt = self.sem.normalize_market(market)
        words = fold(query).split() if query else []
        rows = [c for c in self.erp.customers.values()
                if (customer_number is None or c["customer_number"] == str(customer_number))
                and (mkt is None or c["market"] == mkt) and all(w in fold(c["name"]) for w in words)]
        rows, n = sort_limit(rows, "name", True, limit)
        return envelope("erp_find_customers", "erp", {"query": query, "customer_number": customer_number,
                        "market": market}, rows, total_rows=n)

    def erp_invoices(self, period: str | None = None, customer_number: str | None = None,
                     document_type: str | None = None, market: str | None = None,
                     min_amount_dkk: float | None = None, reference_contains: str | None = None,
                     sort_by: str | None = "invoice_date", ascending: bool = False, limit: int = 50) -> dict:
        """Invoice headers (source currency, exchange rate and DKK amount). document_type: invoice | credit_note."""
        p = parse_period(period) if period else None
        mkt = self.sem.normalize_market(market)
        rows = [v for v in self.erp.invoices.values() if (p is None or p.contains(v["invoice_date"]))
                and (customer_number is None or v["customer_number"] == str(customer_number))
                and (document_type is None or v["document_type"] == document_type)
                and (mkt is None or v["market"] == mkt)
                and (min_amount_dkk is None or abs(v["net_amount_dkk"]) >= min_amount_dkk)
                and (reference_contains is None or fold(reference_contains) in fold(v["your_reference"]))]
        rows, n = sort_limit(rows, sort_by, ascending, limit)
        return envelope("erp_invoices", "erp", {"period": period, "customer_number": customer_number,
                        "document_type": document_type, "market": market, "min_amount_dkk": min_amount_dkk,
                        "reference_contains": reference_contains}, rows, period=p, total_rows=n)

    def erp_invoice_lines(self, invoice_number: str | None = None, period: str | None = None,
                          customer_number: str | None = None, product_number: str | None = None,
                          category: str | None = None, market: str | None = None, limit: int = 100) -> dict:
        """Invoice lines with product category, source-currency amounts and DKK revenue/cost/gross profit."""
        p = parse_period(period) if period else None
        cat, mkt = self.sem.normalize_category(category), self.sem.normalize_market(market)
        rows = [l for l in self.erp.sales_lines if (invoice_number is None or l["invoice_number"] == str(invoice_number))
                and (p is None or p.contains(l["invoice_date"]))
                and (customer_number is None or l["customer_number"] == str(customer_number))
                and (product_number is None or l["product_number"] == product_number)
                and (cat is None or l["category"] == cat) and (mkt is None or l["market"] == mkt)]
        rows = [{k: v for k, v in l.items() if k != "list_value_dkk"} for l in rows]
        rows, n = sort_limit(rows, "invoice_date", False, limit)
        return envelope("erp_invoice_lines", "erp", {"invoice_number": invoice_number, "period": period,
                        "customer_number": customer_number, "product_number": product_number, "category": category,
                        "market": market}, rows, period=p, total_rows=n)

    def erp_products(self, category: str | None = None) -> dict:
        """Product catalogue with category, list price and standard cost (DKK)."""
        cat = self.sem.normalize_category(category)
        rows = [v for v in self.erp.products.values() if cat is None or v["category"] == cat]
        return envelope("erp_products", "erp", {"category": category}, rows)
