"""Generic people operations over the payroll adapter. Costs in DKK (payroll's own conversion)."""
import calendar
from datetime import date

from ..periods import coverage_note, parse_period
from ..sources import fold
from .common import aggregate, calendar_dims, check_dims, compare_rows, envelope, periods, ratio, sort_limit

COST_SUMS = ["employer_cost_dkk", "base_salary_dkk", "overtime_dkk", "commission_dkk", "bonus_dkk", "gross_pay_dkk",
             "pension_employer_dkk", "social_contributions_employer_dkk"]
EMPLOYEE_FIELDS = ["employee_id", "full_name", "country", "department", "job_title", "employment_type", "weekly_hours",
                   "employment_start", "employment_end", "status", "cost_center", "manager_employee_id",
                   "current_base_salary", "currency", "work_email"]


def _month_bounds(key):
    y, m = int(key[:4]), int(key[5:7])
    return date(y, m, 1), date(y, m, calendar.monthrange(y, m)[1])


class PeopleQueries:
    def __init__(self, payroll, semantics):
        self.pay, self.sem = payroll, semantics
        self.static_dims = {"country": lambda r: r["country"], "department": lambda r: r["department"],
                            "cost_center": lambda r: r["cost_center"], "job_title": lambda r: r["job_title"],
                            "employment_type": lambda r: r.get("employment_type")}
        self.cost_dims = {**self.static_dims, "employee": lambda r: r["employee_id"], **calendar_dims("period_start")}

    def _note(self, p):
        return coverage_note(p, *self.pay.coverage(), "payroll")

    def _emp_filter(self, e, country, department):
        c = self.sem.normalize_market(country)
        return (c is None or e["country"] == c) and (department is None or e["department"] == department)

    def _decorate(self, rows, group_by):
        if "employee" in group_by:
            for r in rows:
                e = self.pay.employees.get(r["employee"], {})
                r.update(employee_name=e.get("full_name"), employee_country=e.get("country"),
                         employee_department=e.get("department"), employee_job_title=e.get("job_title"))
        return rows

    # ------------------------------------------------------------------ headcount
    def payroll_headcount(self, on_date: str | None = None, period: str | None = None,
                          group_by: list[str] | None = None, country: str | None = None,
                          department: str | None = None, basis: str = "point_in_time") -> dict:
        """Headcount grouped by any of: country, department, cost_center, job_title, employment_type.
        basis='point_in_time': employees employed on `on_date` (YYYY-MM-DD; default: end of `period`, else the
        last payroll date). basis='average_monthly': average number of employees with a payroll entry per month
        in `period`."""
        group_by = check_dims(group_by, self.static_dims)
        emps = [e for e in self.pay.employees.values() if self._emp_filter(e, country, department)]
        if basis == "point_in_time":
            if on_date:
                try:
                    day = date.fromisoformat(on_date)
                except ValueError:
                    raise ValueError("on_date must be YYYY-MM-DD") from None
            else:
                day = parse_period(period).end if period else self.pay.coverage()[1]
            sel = [e for e in emps if self.pay.employed_on(e, day)]
            rows = aggregate(sel, group_by, self.static_dims, [], {"part_time_count": lambda r: r["employee_id"]
                             if r["employment_type"] == "part-time" else None})
            for r in rows:
                r["headcount"] = r.pop("record_count")
            rows, n = sort_limit(rows, "headcount", False, None)
            return envelope("payroll_headcount", "payroll", {"date": day.isoformat(), "group_by": group_by,
                            "country": country, "department": department, "basis": basis}, rows,
                            totals={"headcount": len(sel)}, total_rows=n, currency="n/a")
        if basis != "average_monthly" or not period:
            raise ValueError("basis must be 'point_in_time' or 'average_monthly' (the latter requires period)")
        p = parse_period(period)
        ids = {e["employee_id"] for e in emps}
        entries = [x for x in self.pay.entries if p.contains(x["period_start"]) and x["employee_id"] in ids]
        months = sorted({x["pay_period"] for x in entries})
        rows = aggregate(entries, group_by, self.static_dims, [])
        for r in rows:
            r["avg_headcount"] = r.pop("record_count") / len(months)
        rows, n = sort_limit(rows, "avg_headcount", False, None)
        return envelope("payroll_headcount", "payroll", {"period": period, "group_by": group_by, "country": country,
                        "department": department, "basis": basis}, rows, period=p,
                        totals={"avg_headcount": len(entries) / len(months) if months else 0.0, "months": len(months)},
                        total_rows=n, notes=[self._note(p)], currency="n/a")

    # ------------------------------------------------------------------ costs
    def _cost_rows(self, p, group_by, country, department, employee_id):
        entries = [x for x in self.pay.entries if p.contains(x["period_start"])
                   and self._emp_filter(self.pay.employees[x["employee_id"]], country, department)
                   and (employee_id is None or x["employee_id"] == employee_id)]
        rows = aggregate(entries, group_by, self.cost_dims, COST_SUMS, {"employee_count": lambda r: r["employee_id"],
                                                                        "months": lambda r: r["pay_period"]})
        for r in rows:
            r["entry_count"] = r.pop("record_count")
        return self._decorate(rows, group_by)

    def payroll_personnel_costs(self, period: str, group_by: list[str] | None = None, country: str | None = None,
                                department: str | None = None, employee_id: str | None = None,
                                compare_to: str | None = None, sort_by: str | None = "employer_cost_dkk",
                                ascending: bool = False, limit: int = 100) -> dict:
        """Employer cost in DKK with components (base salary, overtime, commission, bonus, gross pay, employer
        pension, employer social contributions), grouped by any of: country, department, cost_center,
        job_title, employment_type, employee, month, quarter, half, year (by pay period)."""
        group_by = check_dims(group_by, self.cost_dims)
        p, c = periods(period, compare_to)
        args = (country, department, employee_id)
        rows, totals = self._cost_rows(p, group_by, *args), self._cost_rows(p, [], *args)
        if c:
            rows = compare_rows(rows, self._cost_rows(c, group_by, *args), group_by, COST_SUMS + ["employee_count"])
            totals = compare_rows(totals, self._cost_rows(c, [], *args), [], COST_SUMS + ["employee_count"])
        rows, n = sort_limit(rows, sort_by, ascending, limit)
        return envelope("payroll_personnel_costs", "payroll", {"period": period, "group_by": group_by,
                        "country": country, "department": department, "employee_id": employee_id,
                        "compare_to": compare_to}, rows, period=p, compare=c, totals=totals[0] if totals else None,
                        total_rows=n, notes=[self._note(p), c and self._note(c)])

    def payroll_base_salary_change(self, from_month: str, to_month: str, group_by: list[str] | None = None,
                                   country: str | None = None, department: str | None = None) -> dict:
        """Like-for-like monthly base salary change between two months for employees employed the whole of both
        months. Change measured in LOCAL currency (no FX effect), weighted by from-month DKK base. group_by any
        of: country, department, cost_center, job_title, employment_type, employee."""
        dims = {**self.static_dims, "employee": lambda r: r["employee_id"]}
        group_by = check_dims(group_by, dims)
        (f0, f1), (t0, t1) = _month_bounds(from_month), _month_bounds(to_month)
        base = {(x["employee_id"], x["pay_period"]): x for x in self.pay.entries}
        rows_in = []
        for e in self.pay.employees.values():
            if not self._emp_filter(e, country, department):
                continue
            if not (self.pay.employed_on(e, f0) and self.pay.employed_on(e, f1) and self.pay.employed_on(e, t0)
                    and self.pay.employed_on(e, t1)):
                continue
            a, b = base.get((e["employee_id"], from_month)), base.get((e["employee_id"], to_month))
            if not a or not b:
                continue
            rows_in.append({**e, "from_base_dkk": a["base_salary"] * a["fx_rate_to_dkk"],
                            "to_base_at_from_fx_dkk": b["base_salary"] * a["fx_rate_to_dkk"]})
        rows = aggregate(rows_in, group_by, dims, ["from_base_dkk", "to_base_at_from_fx_dkk"])
        for r in rows:
            r["employee_count"] = r.pop("record_count")
            r["change_pct"] = ratio(r["to_base_at_from_fx_dkk"] - r["from_base_dkk"], r["from_base_dkk"])
        totals = aggregate(rows_in, [], dims, ["from_base_dkk", "to_base_at_from_fx_dkk"])
        for t in totals:
            t["employee_count"] = t.pop("record_count")
            t["change_pct"] = ratio(t["to_base_at_from_fx_dkk"] - t["from_base_dkk"], t["from_base_dkk"])
        rows = self._decorate(rows, group_by)
        rows, n = sort_limit(rows, "from_base_dkk", False, None)
        return envelope("payroll_base_salary_change", "payroll", {"from_month": from_month, "to_month": to_month,
                        "group_by": group_by, "country": country, "department": department}, rows,
                        totals=totals[0] if totals else None, total_rows=n,
                        notes=["Monthly base salary only; excludes variable pay and employer contributions."])

    # ------------------------------------------------------------------ records
    def payroll_find_employees(self, query: str | None = None, employee_id: str | None = None,
                               country: str | None = None, department: str | None = None,
                               status: str | None = None, limit: int = 50) -> dict:
        """Employee master records by id or (accent/case-insensitive) name search. status: active | terminated."""
        words = fold(query).split() if query else []
        rows = [{k: e[k] for k in EMPLOYEE_FIELDS} for e in self.pay.employees.values()
                if (employee_id is None or e["employee_id"] == employee_id) and self._emp_filter(e, country, department)
                and (status is None or e["status"] == status) and all(w in fold(e["full_name"]) for w in words)]
        rows, n = sort_limit(rows, "employee_id", True, limit)
        return envelope("payroll_find_employees", "payroll", {"query": query, "employee_id": employee_id,
                        "country": country, "department": department, "status": status}, rows, total_rows=n,
                        currency="local (see currency field)")

    def payroll_entries(self, employee_id: str | None = None, period: str | None = None, country: str | None = None,
                        department: str | None = None, limit: int = 100) -> dict:
        """Monthly pay slips: local-currency amounts, FX rate and DKK conversions."""
        p = parse_period(period) if period else None
        rows = [x for x in self.pay.entries if (employee_id is None or x["employee_id"] == employee_id)
                and (p is None or p.contains(x["period_start"]))
                and self._emp_filter(self.pay.employees[x["employee_id"]], country, department)]
        rows, n = sort_limit(rows, "pay_period", True, limit)
        return envelope("payroll_entries", "payroll", {"employee_id": employee_id, "period": period,
                        "country": country, "department": department}, rows, period=p, total_rows=n,
                        currency="local + DKK (*_dkk fields)")

    def payroll_hires_and_departures(self, period: str, country: str | None = None,
                                     department: str | None = None) -> dict:
        """Employees whose employment started (hire) or ended (departure) within the period."""
        p = parse_period(period)
        rows = []
        for e in self.pay.employees.values():
            if not self._emp_filter(e, country, department):
                continue
            for event, day in (("hire", e["employment_start"]), ("departure", e["employment_end"])):
                if p.contains(day):
                    rows.append({"event": event, "date": day, **{k: e[k] for k in EMPLOYEE_FIELDS}})
        rows, n = sort_limit(rows, "date", True, None)
        return envelope("payroll_hires_and_departures", "payroll", {"period": period, "country": country,
                        "department": department}, rows, period=p, total_rows=n,
                        totals={"hires": sum(r["event"] == "hire" for r in rows),
                                "departures": sum(r["event"] == "departure" for r in rows)},
                        notes=[self._note(p)], currency="n/a")
