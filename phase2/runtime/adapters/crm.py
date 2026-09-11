"""CRM adapter: reads data/crm only. Typed records; no aggregation."""
from functools import cached_property

from ..sources import CsvFolder, s, f, d, dt, b, i


class CRMAdapter:
    system = "crm"

    def __init__(self, data_dir, semantics):
        self.src = CsvFolder(data_dir / "crm")
        self.sem = semantics

    @cached_property
    def users(self):
        return {r["user_id"]: {
            "user_id": r["user_id"], "first_name": r["first_name"], "last_name": r["last_name"],
            "full_name": f"{r['first_name']} {r['last_name']}".strip(), "email": s(r["email"]), "team": s(r["team"]),
            "active": b(r["active"]), "created_at": d(r["created_at"]), "archived_at": d(r["archived_at"])}
            for r in self.src.table("owners")}

    def user_name(self, user_id):
        return self.users[user_id]["full_name"] if user_id in self.users else None

    @cached_property
    def companies(self):
        return {r["company_id"]: {
            "company_id": r["company_id"], "name": r["name"], "domain": s(r["domain"]), "country": s(r["country"]),
            "market": self.sem.classify("market", "crm", r["country"]), "city": s(r["city"]),
            "industry": s(r["industry"]), "lifecycle_stage": s(r["lifecycle_stage"]), "owner_id": s(r["owner_id"]),
            "owner_name": self.user_name(s(r["owner_id"])), "created_at": d(r["created_at"]),
            "num_employees": i(r["num_employees"])} for r in self.src.table("companies")}

    def resolve_deal_market(self, deal_market, company_id, currency):
        """market field -> company country -> deal currency (documented fallback chain)."""
        for source, value in (("deal.market", deal_market),
                              ("company.country", self.companies.get(company_id, {}).get("country")),
                              ("deal.currency", currency)):
            code = self.sem.classify("market", "crm", value)
            if code:
                return code, source
        return None, "unknown"

    @cached_property
    def deals(self):
        out = []
        for r in self.src.table("deals"):
            market, source = self.resolve_deal_market(s(r["market"]), r["company_id"], r["deal_currency"])
            comp = self.companies.get(r["company_id"], {})
            out.append({
                "deal_id": r["deal_id"], "deal_name": r["deal_name"], "pipeline": r["pipeline"], "stage": r["stage"],
                "deal_type": r["deal_type"], "is_renewal": r["deal_type"] == "Renewal",
                "company_id": r["company_id"], "company_name": comp.get("name"),
                "owner_id": s(r["owner_id"]), "owner_name": self.user_name(s(r["owner_id"])),
                "market_field": s(r["market"]), "market": market, "market_source": source,
                "product_category_field": s(r["product_category"]),
                "category": self.sem.classify("product_category", "crm", r["product_category"]),
                "amount": f(r["amount"]), "deal_currency": r["deal_currency"],
                "value_dkk": f(r["amount_company_currency"]), "discount_pct": f(r["discount_pct"]),
                "created_at": dt(r["created_at"]), "created_date": d(r["created_at"]),
                "expected_close_date": d(r["expected_close_date"]), "closed_at": dt(r["closed_at"]),
                "closed_date": d(r["closed_at"]), "outcome": r["outcome"], "loss_reason": s(r["loss_reason"])})
        return out

    @cached_property
    def activities(self):
        return [{"activity_id": r["activity_id"], "timestamp": dt(r["timestamp"]), "date": d(r["timestamp"]),
                 "type": r["type"], "owner_id": s(r["owner_id"]), "owner_name": self.user_name(s(r["owner_id"])),
                 "company_id": s(r["company_id"]), "deal_id": s(r["deal_id"]), "subject": s(r["subject"]),
                 "body": s(r["body"])} for r in self.src.table("activities")]

    @cached_property
    def property_history(self):
        out = []
        for r in self.src.table("property_history"):
            owner = r["property"] == "hubspot_owner_id"
            out.append({"object_type": r["object_type"], "object_id": r["object_id"], "property": r["property"],
                        "value_before": s(r["value_before"]), "value_after": s(r["value_after"]),
                        "value_before_name": self.user_name(s(r["value_before"])) if owner else None,
                        "value_after_name": self.user_name(s(r["value_after"])) if owner else None,
                        "changed_at": dt(r["changed_at"]), "date": d(r["changed_at"]), "source": s(r["source"]),
                        "changed_by_user_id": s(r["changed_by_user_id"]),
                        "changed_by_name": self.user_name(s(r["changed_by_user_id"]))})
        return out

    def coverage(self):
        days = [x["created_date"] for x in self.deals] + [x["closed_date"] for x in self.deals if x["closed_date"]] \
            + [a["date"] for a in self.activities]
        return (min(days), max(days)) if days else (None, None)
