"""Identity adapter: reads data/mappings only (cross-system id links)."""
from collections import defaultdict
from functools import cached_property

from ..sources import CsvFolder, s


class IdentityAdapter:
    system = "mappings"

    def __init__(self, data_dir):
        self.src = CsvFolder(data_dir / "mappings")

    @cached_property
    def company_links(self):
        return [{"crm_company_id": r["crm_company_id"], "erp_customer_number": r["erp_customer_number"],
                 "match_method": s(r["match_method"]), "note": s(r["note"])}
                for r in self.src.table("crm_company_erp_customer")]

    @cached_property
    def person_links(self):
        return [{"payroll_employee_id": s(r["payroll_employee_id"]), "crm_user_id": r["crm_user_id"],
                 "match_basis": s(r["match_basis"]), "note": s(r["note"])}
                for r in self.src.table("employee_crm_user")]

    def _index(self, rows, key):
        idx = defaultdict(list)
        for r in rows:
            if r[key]:
                idx[r[key]].append(r)
        return idx

    @cached_property
    def by_crm_company(self):
        return self._index(self.company_links, "crm_company_id")

    @cached_property
    def by_erp_customer(self):
        return self._index(self.company_links, "erp_customer_number")

    @cached_property
    def by_crm_user(self):
        return self._index(self.person_links, "crm_user_id")

    @cached_property
    def by_employee(self):
        return self._index(self.person_links, "payroll_employee_id")
