"""
Runtime facade: builds the four adapters and the query layer, and lists the
read-only operations that can be exposed to an agent.

The runtime reads only the system exports under the data folder
(erp/, crm/, payroll/, mappings/). It has no access to evaluation material.
"""
from pathlib import Path

from .adapters.crm import CRMAdapter
from .adapters.erp import ERPAdapter
from .adapters.identity import IdentityAdapter
from .adapters.payroll import PayrollAdapter
from .query.common import envelope
from .query.crm import SalesQueries
from .query.erp import FinanceQueries
from .query.identity import IdentityQueries
from .query.payroll import PeopleQueries
from .semantics import Semantics, semantics_topic
from .sources import CsvFolder, default_data_dir

SYSTEM_FOLDERS = ("erp", "crm", "payroll", "mappings")


class Runtime:
    def __init__(self, data_dir=None):
        self.data_dir = Path(data_dir) if data_dir else default_data_dir()
        self.semantics = Semantics(CsvFolder(self.data_dir / "mappings"))
        self.erp = ERPAdapter(self.data_dir, self.semantics)
        self.crm = CRMAdapter(self.data_dir, self.semantics)
        self.payroll = PayrollAdapter(self.data_dir, self.semantics)
        self.identity = IdentityAdapter(self.data_dir)
        self.finance = FinanceQueries(self.erp, self.semantics)
        self.sales = SalesQueries(self.crm, self.semantics)
        self.people = PeopleQueries(self.payroll, self.semantics)
        self.links = IdentityQueries(self.identity, self.erp, self.crm, self.payroll)

    # ------------------------------------------------------------------ metadata operations
    def meta_describe_sources(self) -> dict:
        """The four source systems: tables, row counts, date coverage and field descriptions."""
        rows = []
        for system, adapter in (("erp", self.erp), ("crm", self.crm), ("payroll", self.payroll)):
            first, last = adapter.coverage()
            rows.append({"system": system, "coverage": {"first": first, "last": last},
                         "tables": {t: len(adapter.src.table(t)) for t in adapter.src.tables()}})
        rows.append({"system": "mappings", "coverage": None,
                     "tables": {t: len(self.identity.src.table(t)) for t in self.identity.src.tables()}})
        return envelope("meta_describe_sources", "all", {}, rows, currency="n/a",
                        totals=None, notes=["Field-level descriptions: meta_get_semantics(topic='systems')."])

    def meta_get_semantics(self, topic: str | None = None) -> dict:
        """Definitions of fields, dates, currencies, markets (incl. fallback rules), product categories, CRM
        stages, metric definitions and known data-quality caveats. topic: systems | currencies | dates |
        markets | product_categories | crm_stages | metrics | data_quality (omit for all)."""
        return envelope("meta_get_semantics", "metadata", {"topic": topic}, [semantics_topic(topic)], currency="n/a")

    # ------------------------------------------------------------------ registry
    def operations(self):
        """name -> bound method, for every read-only operation (used by the MCP server)."""
        ops = {}
        for obj in (self, self.finance, self.sales, self.people, self.links):
            for name in dir(obj):
                if name.startswith(("erp_", "crm_", "payroll_", "identity_", "meta_")) and callable(getattr(obj, name)):
                    ops[name] = getattr(obj, name)
        return dict(sorted(ops.items()))
