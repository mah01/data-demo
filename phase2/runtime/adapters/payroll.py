"""Payroll adapter: reads data/payroll only. Typed records; no aggregation."""
from functools import cached_property

from ..sources import CsvFolder, s, f, d, i

COMPONENTS = {"base_salary": "base_salary", "overtime": "overtime_pay", "commission": "commission", "bonus": "bonus",
              "gross_pay": "gross_pay", "pension_employer": "pension_employer",
              "social_contributions_employer": "social_contributions_employer"}


class PayrollAdapter:
    system = "payroll"

    def __init__(self, data_dir, semantics):
        self.src = CsvFolder(data_dir / "payroll")
        self.sem = semantics

    @cached_property
    def employees(self):
        return {r["employee_id"]: {
            "employee_id": r["employee_id"], "first_name": r["first_name"], "last_name": r["last_name"],
            "full_name": f"{r['first_name']} {r['last_name']}", "work_email": s(r["work_email"]),
            "country": r["country"], "market": self.sem.classify("market", "payroll", r["country"]),
            "department": r["department"], "job_title": r["job_title"], "employment_type": r["employment_type"],
            "weekly_hours": f(r["weekly_hours"]), "employment_start": d(r["employment_start"]),
            "employment_end": d(r["employment_end"]), "status": r["status"], "cost_center": s(r["cost_center"]),
            "manager_employee_id": s(r["manager_employee_id"]), "current_base_salary": f(r["current_base_salary"]),
            "currency": r["currency"]} for r in self.src.table("employees")}

    @cached_property
    def entries(self):
        out = []
        for r in self.src.table("payroll_entries"):
            e = self.employees.get(r["employee_id"], {})
            rate = f(r["fx_rate_to_dkk"])
            row = {"pay_period": r["pay_period"], "period_start": d(r["pay_period"] + "-01"),
                   "payment_date": d(r["payment_date"]), "employee_id": r["employee_id"],
                   "employee_name": e.get("full_name"), "country": e.get("country"), "department": e.get("department"),
                   "job_title": e.get("job_title"), "cost_center": e.get("cost_center"), "currency": r["currency"],
                   "fx_rate_to_dkk": rate, "employer_cost": f(r["employer_cost"]),
                   "employer_cost_dkk": f(r["employer_cost_dkk"])}
            for name, col in COMPONENTS.items():
                row[name] = f(r[col])
                row[f"{name}_dkk"] = f(r[col]) * rate
            out.append(row)
        return out

    def employed_on(self, emp, day):
        return emp["employment_start"] <= day and (emp["employment_end"] is None or day <= emp["employment_end"])

    def coverage(self):
        months = sorted({e["pay_period"] for e in self.entries})
        if not months:
            return None, None
        first, last = months[0], months[-1]
        return d(first + "-01"), max(e["payment_date"] for e in self.entries if e["pay_period"] == last)
