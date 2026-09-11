"""
Payroll generator (Danløn-like group payroll export).

Base salaries are scaled by one factor so that H1 2025 employer cost hits
roster.PERSONNEL_TARGET_H1_2025. Everything after that (raises, new German
reps, commissions from CRM wins, bonuses) is story-driven, not calibrated.
"""
import calendar
from collections import defaultdict
from datetime import timedelta

import config
import roster
from common import rng, DATA_MONTHS, month_start, month_end, last_banking_day, fx

MANAGER = {"dk_cfo": "dk_ceo", "dk_coo": "dk_ceo", "dk_salesdir": "dk_ceo", "de_cm": "dk_ceo", "dk_mktmgr": "dk_ceo",
           "se_cm": "dk_salesdir", "dk_it": "dk_cfo", "dk_opsmgr": "dk_coo", "dk_tech1": "dk_coo"}
DEPT_MANAGER = {("DK", "Finance & Admin"): "dk_cfo", ("DK", "Sales"): "dk_salesdir", ("DK", "Customer Service"): "dk_salesdir",
                ("DK", "Service"): "dk_tech1", ("DK", "Operations"): "dk_opsmgr", ("DK", "Marketing"): "dk_mktmgr",
                ("SE", "Sales"): "se_cm", ("SE", "Service"): "se_cm", ("DE", "Sales"): "de_cm", ("DE", "Service"): "de_cm"}
COST_CENTER = {"Management": "100", "Finance & Admin": "110", "IT": "120", "Sales": "200", "Customer Service": "210",
               "Marketing": "220", "Service": "300", "Operations": "400"}
RENEWAL_COMMISSION = 0.01


class PayrollGenerator:
    def __init__(self, crm):
        self.crm = crm
        self.emps = [dict(zip(["key", "id", "first", "last", "country", "dept", "title", "start", "end", "base",
                               "hours", "bonus_pct", "crm"], row)) for row in roster.ROSTER]
        self.by_key = {e["key"]: e for e in self.emps}
        self.commission_due = self._commissions()

    def _commissions(self):
        due = defaultdict(float)  # (emp key, month) -> DKK
        for d in self.crm.deals:
            if d.outcome != "won" or d.owner not in self.by_key or d.close_date > config.DATA_END:
                continue
            pay_month = (d.close_date.replace(day=28) + timedelta(days=5)).strftime("%Y-%m")
            rate = RENEWAL_COMMISSION if d.deal_type == "Renewal" else config.COMMISSION_RATE[d.market]
            if self.by_key[d.owner]["key"] == "dk_salesdir":
                continue
            due[(d.owner, pay_month)] += rate * d.amount_dkk
        return due

    def _base(self, e, key, scale):
        cur = config.CURRENCY[e["country"]]
        step = 10 if cur == "EUR" else 100
        base = round(e["base"] * scale / step) * step
        for k, when, pct in roster.INDIVIDUAL_RAISES:
            if k == e["key"] and key >= when:
                base = round(base * (1 + pct) / step) * step
        if key >= "2026-01" and e["start"] < month_start("2025-10"):
            base = round(base * (1 + roster.GENERAL_RAISE[e["country"]]) / step) * step
        return base

    def compute(self, scale, with_noise=True):
        r = rng("payroll")
        rows = []
        for key in DATA_MONTHS:
            ms, me = month_start(key), month_end(key)
            days = calendar.monthrange(ms.year, ms.month)[1]
            rate = None
            for e in self.emps:
                if e["start"] > me or (e["end"] and e["end"] < ms):
                    continue
                cur = config.CURRENCY[e["country"]]
                rate = fx(cur, key)
                first, last = max(ms, e["start"]), min(me, e["end"] or me)
                share = ((last - first).days + 1) / days
                full_base = self._base(e, key, scale)
                base = round(full_base * share, 2)
                overtime = 0.0
                if e["dept"] == "Service" and with_noise:
                    winter = ms.month in (11, 12, 1, 2)
                    overtime = round(full_base * r.uniform(0.0, 0.07 if winter else 0.035) * share, 2)
                commission = round(self.commission_due.get((e["key"], key), 0.0) / rate, 2)
                if e["key"] in roster.NEW_DE_REPS:
                    months_in = (ms.year - e["start"].year) * 12 + ms.month - e["start"].month
                    if 1 <= months_in <= 6:
                        commission = max(commission, float(roster.DE_RAMP_GUARANTEE_EUR))
                bonus = 0.0
                if ms.month == roster.BONUS_MONTH and e["bonus_pct"] and e["start"].year < ms.year:
                    bonus = round(full_base * 12 * e["bonus_pct"] * roster.BONUS_FACTOR[ms.year], 2)
                gross = round(base + overtime + commission + bonus, 2)
                s = roster.SOCIAL[e["country"]]
                pension = round(base * s["pension_pct"], 2)
                if e["country"] == "DE":
                    social = min(gross, s["social_cap"]) * s["social_pct"] + gross * s["social_uncapped_pct"]
                else:
                    social = s["social_fixed"] * share + gross * s["social_pct"]
                social = round(social, 2)
                cost = round(gross + pension + social, 2)
                rows.append({"pay_period": key, "payment_date": last_banking_day(key), "employee_id": e["id"],
                             "emp_key": e["key"], "country": e["country"], "currency": cur, "base_salary": base,
                             "overtime_pay": overtime, "commission": commission, "bonus": bonus, "gross_pay": gross,
                             "pension_employer": pension, "social_contributions_employer": social,
                             "employer_cost": cost, "fx_rate_to_dkk": rate, "employer_cost_dkk": round(cost * rate, 2)})
        return rows

    def run(self):
        target = roster.PERSONNEL_TARGET_H1_2025 * (1 + rng("payroll-anchor").uniform(-0.004, 0.004))
        scale = 1.0
        for _ in range(8):
            rows = self.compute(scale)
            h1 = sum(x["employer_cost_dkk"] for x in rows if "2025-01" <= x["pay_period"] <= "2025-06")
            scale *= target / h1
        self.scale = scale
        self.rows = self.compute(scale)
        return self

    # ------------------------------------------------------------------ outputs
    def employee_rows(self):
        r = rng("payroll-employees")
        last_base = {}
        for x in self.rows:
            last_base[x["emp_key"]] = self._base(self.by_key[x["emp_key"]], x["pay_period"], self.scale)
        out = []
        for e in self.emps:
            mgr = MANAGER.get(e["key"]) or DEPT_MANAGER.get((e["country"], e["dept"]))
            if e["key"] == mgr:
                mgr = MANAGER.get(e["key"])
            email = f"{e['first'].split()[0].lower()}.{e['last'].lower()}@nordflow.{e['country'].lower()}"
            out.append({"employee_id": e["id"], "first_name": e["first"], "last_name": e["last"],
                        "work_email": email.replace("ø", "oe").replace("å", "aa").replace("æ", "ae").replace("ö", "oe")
                        .replace("ä", "ae").replace("ü", "ue").replace("ı", "i") if r.random() < 0.6 else None,
                        "country": e["country"], "department": e["dept"], "job_title": e["title"],
                        "employment_type": "part-time" if e["hours"] < 37 else "full-time", "weekly_hours": e["hours"],
                        "employment_start": e["start"], "employment_end": e["end"],
                        "status": "terminated" if e["end"] and e["end"] <= config.DATA_END else "active",
                        "cost_center": f"{e['country']}-{COST_CENTER[e['dept']]}",
                        "manager_employee_id": self.by_key[mgr]["id"] if mgr and mgr != e["key"] else None,
                        "current_base_salary": float(last_base.get(e["key"], 0)), "currency": config.CURRENCY[e["country"]]})
        return out

    def journal_totals(self):
        """Monthly DKK totals as posted to the ERP general ledger."""
        tot = defaultdict(lambda: [0.0, 0.0, 0.0])
        for x in self.rows:
            t = tot[x["pay_period"]]
            t[0] += x["gross_pay"] * x["fx_rate_to_dkk"]
            t[1] += x["pension_employer"] * x["fx_rate_to_dkk"]
            t[2] += x["social_contributions_employer"] * x["fx_rate_to_dkk"]
        return tot
