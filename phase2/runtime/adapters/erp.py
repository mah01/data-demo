"""ERP adapter: reads data/erp only. Typed records; no aggregation."""
from functools import cached_property

from ..sources import CsvFolder, s, f, i, d, b

ACCOUNT_TYPES = {"personnel": "personnel", "opex": "opex"}


def _account_type(raw):
    raw = (raw or "").lower()
    if raw.startswith("revenue"):
        return "revenue"
    if raw.startswith("cost of sales"):
        return "cost_of_sales"
    return ACCOUNT_TYPES.get(raw, raw)


class ERPAdapter:
    system = "erp"

    def __init__(self, data_dir, semantics):
        self.src = CsvFolder(data_dir / "erp")
        self.sem = semantics

    @cached_property
    def customers(self):
        out = {}
        for r in self.src.table("customers"):
            out[r["customer_number"]] = {
                "customer_number": r["customer_number"], "name": r["name"],
                "customer_group": s(r["customer_group_name"]), "country": s(r["country"]),
                "market": self.sem.classify("market", "erp", r["country"]), "city": s(r["city"]),
                "currency": r["currency"], "vat_number": s(r["vat_number"]), "payment_terms": s(r["payment_terms"]),
                "created_date": d(r["created_date"]), "barred": b(r["barred"])}
        return out

    @cached_property
    def products(self):
        return {r["product_number"]: {
            "product_number": r["product_number"], "name": r["name"],
            "product_group_number": r["product_group_number"], "product_group_name": r["product_group_name"],
            "category": self.sem.classify("product_category", "erp", r["product_group_number"]),
            "sales_price_dkk": f(r["sales_price_dkk"]), "cost_price_dkk": f(r["cost_price_dkk"]), "unit": r["unit"]}
            for r in self.src.table("products")}

    @cached_property
    def invoices(self):
        out = {}
        for r in self.src.table("invoices"):
            c = self.customers.get(r["customer_number"], {})
            out[r["invoice_number"]] = {
                "invoice_number": r["invoice_number"], "invoice_date": d(r["invoice_date"]), "due_date": d(r["due_date"]),
                "customer_number": r["customer_number"], "customer_name": r["customer_name"], "market": c.get("market"),
                "currency": r["currency"], "exchange_rate": f(r["exchange_rate"]), "net_amount": f(r["net_amount"]),
                "vat_amount": f(r["vat_amount"]), "gross_amount": f(r["gross_amount"]),
                "net_amount_dkk": f(r["net_amount_dkk"]), "document_type": r["document_type"],
                "your_reference": s(r["your_reference"]), "credited_invoice_number": s(r["credited_invoice_number"])}
        return out

    @cached_property
    def sales_lines(self):
        """Invoice lines joined to their invoice header, customer market and product category (all ERP)."""
        out = []
        for r in self.src.table("invoice_lines"):
            inv = self.invoices[r["invoice_number"]]
            prod = self.products.get(r["product_number"], {})
            rate, qty, price = inv["exchange_rate"], f(r["quantity"]), f(r["unit_price"])
            revenue = f(r["net_amount"]) * rate
            cost = f(r["total_cost_dkk"])
            out.append({
                "invoice_number": r["invoice_number"], "line_number": i(r["line_number"]),
                "invoice_date": inv["invoice_date"], "document_type": inv["document_type"],
                "customer_number": inv["customer_number"], "market": inv["market"], "currency": inv["currency"],
                "exchange_rate": rate, "product_number": r["product_number"], "category": prod.get("category"),
                "product_group_number": prod.get("product_group_number"), "description": r["description"],
                "quantity": qty, "unit": r["unit"], "unit_price": price, "discount_pct": f(r["discount_pct"]),
                "net_amount": f(r["net_amount"]), "revenue_dkk": revenue, "list_value_dkk": qty * price * rate,
                "cost_dkk": cost, "gross_profit_dkk": revenue - cost})
        return out

    @cached_property
    def accounts(self):
        return {r["account_number"]: {"account_number": r["account_number"], "name": r["name"],
                                      "type": _account_type(r["type"])} for r in self.src.table("accounts")}

    @cached_property
    def ledger(self):
        out = []
        for r in self.src.table("ledger_entries"):
            acc = self.accounts.get(r["account_number"], {})
            out.append({"entry_number": i(r["entry_number"]), "date": d(r["date"]), "voucher": r["voucher"],
                        "account_number": r["account_number"], "account_name": acc.get("name"),
                        "account_type": acc.get("type"), "department": s(r["department"]),
                        "amount_dkk": f(r["amount_dkk"]), "text": s(r["text"])})
        return out

    @cached_property
    def exchange_rates(self):
        return [{"month": r["month"], "currency": r["currency"], "rate_to_dkk": f(r["rate_to_dkk"])}
                for r in self.src.table("exchange_rates")]

    def coverage(self):
        days = [inv["invoice_date"] for inv in self.invoices.values()] + [e["date"] for e in self.ledger]
        return (min(days), max(days)) if days else (None, None)
