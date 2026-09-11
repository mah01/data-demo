"""
ERP general-ledger entries for costs that do not come from sales invoices:
the monthly payroll journal and operating expenses.

Calibration: the recurring (non-story) cost base is scaled by ONE factor so
that H1 2025 operating profit matches roster.PROFIT_TARGET_H1_2025. The same
factor applies to every month, so the 2026 result is a consequence of the
story drivers, not a second calibration.
"""
from collections import defaultdict
from datetime import timedelta

import config
import roster
from common import rng, DATA_MONTHS, month_key, month_start, month_end, business_day, last_banking_day

OFFICE = {"DK": "Kolding", "SE": "Göteborg", "DE": "Frankfurt"}
TEXT = {2710: "Husleje {office}", 2720: "El/vand/varme {office}", 2810: "Leasing og brændstof",
        2820: "Rejser {m}", 2910: "Annoncering og kampagner", 2920: "Softwarelicenser og hosting",
        2940: "Forsikringspræmie", 2950: "Kontorhold og gebyrer", 2960: "Garantisager", 2990: "Diverse",
        3510: "Afskrivninger driftsmidler"}


def _season(account, month):
    if account == 2720:
        return 1.35 if month in (11, 12, 1, 2) else 0.7 if month in (5, 6, 7, 8) else 1.0
    if account == 2820:
        return {7: 0.45, 8: 0.8, 12: 0.8}.get(month, 1.05)
    return 1.0


class LedgerGenerator:
    def __init__(self, erp, payroll, crm_users):
        self.erp, self.payroll, self.users = erp, payroll, crm_users

    def _revenue_by(self):
        rev, cogs = defaultdict(float), defaultdict(float)
        for inv in self.erp.invoices:
            key = month_key(inv["date"])
            for ln in inv["lines"]:
                rev[(inv["cust"].market, key)] += ln["dkk"]
                cogs[key] += ln["qty"] * ln["unit_cost"]
        return rev, cogs

    def run(self):
        r = rng("ledger")
        rev, cogs = self._revenue_by()
        items = []  # [date, account, dept, amount, text, scalable, voucher_prefix]
        for key in DATA_MONTHS:
            ms, me = month_start(key), month_end(key)
            for acct, dept, amount, start, end, seasonal in roster.RECURRING_COSTS:
                if (start and start > me) or (end and end < ms):
                    continue
                value = amount * (_season(acct, ms.month) if seasonal else 1.0) * r.uniform(0.95, 1.05)
                if ms.year >= 2026:
                    value *= 1 + roster.COST_INFLATION_2026
                d = ms if acct in (2710, 3510) else business_day(r, key)
                if acct == 3510:
                    d = me
                items.append([d, acct, dept, value, TEXT[acct].format(office=OFFICE.get(dept, ""), m=key), True, "K"])
            for market in config.MARKETS:
                value = rev[(market, key)] * roster.FREIGHT_PCT[market] * r.uniform(0.9, 1.1)
                items.append([business_day(r, key, 20), 2830, market, value, "Fragt udgående", False, "K"])
            seats = sum(1 for u in self.users if u["created_at"] <= me and (u["archived_at"] is None or u["archived_at"] >= ms))
            items.append([business_day(r, key, 1, 10), 2920, None, seats * roster.CRM_SEAT_COST, f"HubSpot licenser ({seats} brugere)", False, "K"])
            cars = sum(1 for k in roster.NEW_DE_REPS if roster_start(k) <= me)
            if cars:
                items.append([business_day(r, key, 1, 10), 2810, "DE", cars * roster.DE_CAR_PER_REP, f"Firmenwagen Leasing ({cars})", False, "K"])
        for d, acct, dept, amount, text in roster.ONE_OFF_COSTS:
            items.append([d, acct, dept, float(amount), text, False, "K"])
        items.append([month_start("2025-05") + timedelta(days=12), 2940, None, -18500.0, "Præmierefusion skadefri", False, "K"])
        items.append([month_start("2026-02") + timedelta(days=9), 2990, "DE", -6200.0, "Gutschrift Lieferant", False, "K"])

        # --- calibrate recurring base on H1 2025 --------------------------------------
        in_h1 = lambda d: "2025-01" <= month_key(d) <= "2025-06"
        revenue = sum(v for (m, k), v in rev.items() if "2025-01" <= k <= "2025-06")
        gross_profit = revenue - sum(v for k, v in cogs.items() if "2025-01" <= k <= "2025-06")
        journal = self.payroll.journal_totals()
        personnel = sum(sum(v) for k, v in journal.items() if "2025-01" <= k <= "2025-06")
        target = roster.PROFIT_TARGET_H1_2025 * (1 + r.uniform(-0.004, 0.004))
        fixed = sum(i[3] for i in items if in_h1(i[0]) and not i[5])
        scalable = sum(i[3] for i in items if in_h1(i[0]) and i[5])
        self.scale = (gross_profit - personnel - target - fixed) / scalable
        for i in items:
            if i[5]:
                i[3] *= self.scale

        entries = []
        for key, (gross, pension, social) in journal.items():
            d = last_banking_day(key)
            for acct, value, label in ((2210, gross, "Løn"), (2220, pension, "Pension"), (2230, social, "Sociale bidrag")):
                entries.append({"date": d, "account_number": acct, "department": None, "amount_dkk": round(value, 2),
                                "text": f"Lønkørsel {key} - {label}", "voucher": f"LØN-{key}"})
        for d, acct, dept, amount, text, _, prefix in items:
            entries.append({"date": d, "account_number": acct, "department": dept if r.random() > 0.04 else None,
                            "amount_dkk": round(amount, 2), "text": text, "voucher": None})
        entries.sort(key=lambda e: (e["date"], e["account_number"]))
        vno = 1
        for n, e in enumerate(entries, start=1):
            e["entry_number"] = n
            if e["voucher"] is None:
                e["voucher"] = f"K{e['date'].year}-{vno:05d}"
                vno += 1
        self.entries = entries
        return self


def roster_start(key):
    return next(row[7] for row in roster.ROSTER if row[0] == key)
