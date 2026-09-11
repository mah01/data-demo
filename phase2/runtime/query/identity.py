"""Cross-system identity resolution backed by data/mappings.

Links come ONLY from the mapping files. Names are looked up in each system's
own master data for display, so the caller can see how differently the same
entity is named in each system.
"""
from ..sources import fold
from .common import envelope


class IdentityQueries:
    def __init__(self, identity, erp, crm, payroll):
        self.ids, self.erp, self.crm, self.pay = identity, erp, crm, payroll

    def _company(self, cid):
        c = self.crm.companies.get(cid)
        return {"crm_company_id": cid, "crm_name": c["name"] if c else None, "crm_market": c["market"] if c else None}

    def _customer(self, num):
        c = self.erp.customers.get(num)
        return {"erp_customer_number": num, "erp_name": c["name"] if c else None, "erp_market": c["market"] if c else None}

    def _user(self, uid):
        u = self.crm.users.get(uid)
        return {"crm_user_id": uid, "crm_user_name": u["full_name"] if u else None,
                "crm_team": u["team"] if u else None, "crm_active": u["active"] if u else None}

    def _employee(self, eid):
        e = self.pay.employees.get(eid) if eid else None
        return {"payroll_employee_id": eid, "employee_name": e["full_name"] if e else None,
                "employee_country": e["country"] if e else None, "employee_department": e["department"] if e else None,
                "employment_start": e["employment_start"] if e else None,
                "employment_end": e["employment_end"] if e else None}

    @staticmethod
    def _status(known, links):
        return "unknown_id" if not known else ("mapped" if links else "not_mapped")

    def identity_crm_companies_to_erp(self, company_ids: list[str]) -> dict:
        """CRM company ids -> linked ERP customers (with match method and note). Several CRM records can
        point to the same ERP customer (duplicates); unmapped companies return status 'not_mapped'."""
        rows = []
        for cid in company_ids:
            links = self.ids.by_crm_company.get(cid, [])
            rows.append({**self._company(cid), "status": self._status(cid in self.crm.companies, links),
                         "links": [{**self._customer(l["erp_customer_number"]), "match_method": l["match_method"],
                                    "note": l["note"]} for l in links]})
        return envelope("identity_crm_companies_to_erp", "mappings", {"company_ids": company_ids}, rows, currency="n/a")

    def identity_erp_customers_to_crm(self, customer_numbers: list[str]) -> dict:
        """ERP customer numbers -> linked CRM company records (possibly several)."""
        rows = []
        for num in [str(n) for n in customer_numbers]:
            links = self.ids.by_erp_customer.get(num, [])
            rows.append({**self._customer(num), "status": self._status(num in self.erp.customers, links),
                         "links": [{**self._company(l["crm_company_id"]), "match_method": l["match_method"],
                                    "note": l["note"]} for l in links]})
        return envelope("identity_erp_customers_to_crm", "mappings", {"customer_numbers": customer_numbers}, rows,
                        currency="n/a")

    def identity_crm_users_to_employees(self, user_ids: list[str]) -> dict:
        """CRM user ids -> payroll employees (with employment dates). Users without a payroll record
        (former staff before the payroll extract, system users) return the mapping note."""
        rows = []
        for uid in user_ids:
            links = [l for l in self.ids.by_crm_user.get(uid, [])]
            mapped = [l for l in links if l["payroll_employee_id"]]
            rows.append({**self._user(uid), "status": self._status(uid in self.crm.users, mapped),
                         "note": "; ".join(l["note"] for l in links if l["note"]) or None,
                         "links": [{**self._employee(l["payroll_employee_id"]), "match_basis": l["match_basis"],
                                    "note": l["note"]} for l in mapped]})
        return envelope("identity_crm_users_to_employees", "mappings", {"user_ids": user_ids}, rows, currency="n/a")

    def identity_employees_to_crm_users(self, employee_ids: list[str]) -> dict:
        """Payroll employee ids -> CRM users. Employees without a CRM seat return status 'not_mapped'."""
        rows = []
        for eid in employee_ids:
            links = self.ids.by_employee.get(eid, [])
            rows.append({**self._employee(eid), "status": self._status(eid in self.pay.employees, links),
                         "links": [{**self._user(l["crm_user_id"]), "match_basis": l["match_basis"],
                                    "note": l["note"]} for l in links]})
        return envelope("identity_employees_to_crm_users", "mappings", {"employee_ids": employee_ids}, rows,
                        currency="n/a")

    def identity_find_company(self, query: str, limit: int = 20) -> dict:
        """Search a company name in BOTH the ERP customer master and the CRM, and show how the hits are
        linked by the mapping file (names often differ between the systems)."""
        words = fold(query).split()
        hit = lambda name: all(w in fold(name) for w in words)
        erp_hits = {n for n, c in self.erp.customers.items() if hit(c["name"])}
        crm_hits = {i for i, c in self.crm.companies.items() if hit(c["name"])}
        for n in list(erp_hits):
            crm_hits |= {l["crm_company_id"] for l in self.ids.by_erp_customer.get(n, [])}
        for i in list(crm_hits):
            erp_hits |= {l["erp_customer_number"] for l in self.ids.by_crm_company.get(i, [])}
        rows, seen = [], set()
        for n in sorted(erp_hits):
            links = self.ids.by_erp_customer.get(n, [])
            seen |= {l["crm_company_id"] for l in links}
            rows.append({**self._customer(n), "crm": [{**self._company(l["crm_company_id"]),
                         "match_method": l["match_method"], "note": l["note"]} for l in links]})
        for i in sorted(crm_hits - seen):
            rows.append({"erp_customer_number": None, "erp_name": None, "erp_market": None,
                         "crm": [{**self._company(i), "match_method": None, "note": "no ERP link in mapping"}]})
        return envelope("identity_find_company", "mappings", {"query": query}, rows[:limit], total_rows=len(rows),
                        currency="n/a")

    def identity_find_person(self, query: str, limit: int = 20) -> dict:
        """Search a person in BOTH payroll and the CRM user list and show mapping links (names can differ,
        e.g. nicknames or married names)."""
        words = fold(query).split()
        hit = lambda name: all(w in fold(name) for w in words)
        emp_hits = {i for i, e in self.pay.employees.items() if hit(e["full_name"])}
        usr_hits = {u for u, x in self.crm.users.items() if hit(x["full_name"])}
        for e in list(emp_hits):
            usr_hits |= {l["crm_user_id"] for l in self.ids.by_employee.get(e, [])}
        for u in list(usr_hits):
            emp_hits |= {l["payroll_employee_id"] for l in self.ids.by_crm_user.get(u, []) if l["payroll_employee_id"]}
        rows, seen = [], set()
        for e in sorted(emp_hits):
            links = self.ids.by_employee.get(e, [])
            seen |= {l["crm_user_id"] for l in links}
            rows.append({**self._employee(e), "crm_users": [{**self._user(l["crm_user_id"]),
                         "match_basis": l["match_basis"], "note": l["note"]} for l in links]})
        for u in sorted(usr_hits - seen):
            note = "; ".join(l["note"] for l in self.ids.by_crm_user.get(u, []) if l["note"]) or "no payroll link"
            rows.append({**self._employee(None), "crm_users": [{**self._user(u), "match_basis": None, "note": note}]})
        return envelope("identity_find_person", "mappings", {"query": query}, rows[:limit], total_rows=len(rows),
                        currency="n/a")
