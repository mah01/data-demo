"""
ERP generator (e-conomic-like): customers, products, invoices, invoice lines.

Revenue is booked in this order:
  1. won CRM deals (equipment deliveries, spare-parts frameworks)
  2. service contracts (quarterly in advance)
  3. German key-account run-rate purchases
  4. run-rate "filler" orders, sized so each market x category x half lands on
     the revenue plan in config.REVENUE_TARGETS (spread by seasonality).
Credit notes are added last.
"""
from collections import defaultdict
from datetime import date, timedelta

import config
from common import (rng, DATA_MONTHS, month_key, month_start, month_end, half_of_key, add_months,
                    business_day, to_weekday, fx)
from world import PRODUCT_GROUPS, VARIABLE_COST_RATIO

TYPICAL_INVOICE = {"Equipment": 70_000, "Components": 16_000, "Service": 13_000}
MIN_LINE = {"Equipment": 12_000, "Components": 700, "Service": 1_200}
COUNTRY_DA = {"DK": "Danmark", "SE": "Sverige", "DE": "Tyskland"}
CUSTOMER_GROUP = {"DK": (1, "Kunder Danmark"), "SE": (2, "Kunder Sverige"), "DE": (3, "Kunder Tyskland")}
VAT_RATE = {"DK": 0.25, "SE": 0.0, "DE": 0.0}


class ERPGenerator:
    def __init__(self, customers, products, crm):
        self.r = rng("erp")
        self.customers = {c.key: c for c in customers}
        self.products = {p.number: p for p in products}
        self.by_cat = defaultdict(list)
        for p in products:
            if p.list_dkk > 0:
                self.by_cat[p.category].append(p)
        self.crm = crm
        self.invoices = []
        self.booked = defaultdict(float)  # (market, category, month) -> DKK

    # ------------------------------------------------------------------ lines
    def _line(self, product, qty, unit_price, disc, cur, key, desc=None):
        net = round(qty * unit_price * (1 - disc), 2)
        if product.number in VARIABLE_COST_RATIO:
            unit_cost = round(unit_price * config.PRICE_LIST_FX[cur] * VARIABLE_COST_RATIO[product.number], 2)
        else:
            unit_cost = float(product.cost_dkk)
        return {"product": product, "qty": qty, "unit_price": unit_price, "disc": disc, "net": net,
                "unit_cost": unit_cost, "desc": desc or product.name, "dkk": net * fx(cur, key),
                "category": product.category}

    def _list_local(self, product, cur):
        return float(round(product.list_dkk / config.PRICE_LIST_FX[cur]))

    def _disc(self, mean):
        if mean <= 0.03 and self.r.random() < 0.55:
            return 0.0
        return round(max(0.0, min(0.35, self.r.gauss(mean, 0.025))) * 200) / 200

    def discount_mean(self, market, cat, key):
        return config.DISCOUNT_OVERRIDES.get((market, cat, half_of_key(key)), config.DEFAULT_DISCOUNT[cat])

    def make_lines(self, cat, target_dkk, market, key, disc_mean=None):
        r, cur = self.r, config.CURRENCY[market]
        rate = fx(cur, key)
        disc_mean = self.discount_mean(market, cat, key) if disc_mean is None else disc_mean
        lines, total = [], 0.0
        if cat == "Service":
            hours = max(2, min(80, round(target_dkk * 0.72 / (1050 * (1 - disc_mean)))))
            svc = self.products["SVC-HOUR"]
            lines.append(self._line(svc, hours, self._list_local(svc, cur), self._disc(disc_mean), cur, key))
            lines.append(self._line(self.products["SVC-CALL"], r.randint(1, 3), self._list_local(self.products["SVC-CALL"], cur), 0.0, cur, key))
            if r.random() < 0.35:
                extra = self.products[r.choice(["SVC-INSP", "SVC-WS"])]
                lines.append(self._line(extra, 1, self._list_local(extra, cur), self._disc(disc_mean), cur, key))
            return lines
        pool = self.by_cat[cat]
        max_lines = 3 if cat == "Equipment" else 10
        while total < target_dkk * 0.9 and len(lines) < max_lines:
            remaining = target_dkk - total
            fits = [p for p in pool if p.list_dkk * (1 - disc_mean) <= remaining]
            if not fits:
                if lines:
                    break
                fits = [min(pool, key=lambda x: x.list_dkk)]
            p = r.choice(fits)
            unit = self._list_local(p, cur)
            qmax = max(1, int(remaining / (unit * rate * (1 - disc_mean))))
            cap = 2 if cat == "Equipment" else 40 if p.list_dkk < 2000 else 12 if p.list_dkk < 10000 else 6
            qty = r.randint(max(1, min(qmax, cap) // 3), min(qmax, cap))
            ln = self._line(p, qty, unit, self._disc(disc_mean), cur, key)
            lines.append(ln)
            total += ln["dkk"]
        return lines

    # ------------------------------------------------------------------ invoices
    def add_invoice(self, cust, d, lines, source, kind="invoice", ref=None):
        if not lines or d < config.DATA_START or d > config.DATA_END:
            return None
        inv = {"cust": cust, "date": d, "currency": config.CURRENCY[cust.market], "lines": lines,
               "source": source, "kind": kind, "ref": ref}
        self.invoices.append(inv)
        key = month_key(d)
        for ln in lines:
            self.booked[(cust.market, ln["category"], key)] += ln["dkk"]
        if cust.first_invoice is None or d < cust.first_invoice:
            cust.first_invoice = d
        return inv

    def book_deals(self):
        r = self.r
        for dl in self.crm.deals:
            if dl.outcome != "won" or dl.deal_type == "Renewal" or dl.close_date > config.DATA_END:
                continue
            cust = self.customers[dl.customer_key]
            if cust.prospect and cust.erp_since is None:
                cust.erp_since = dl.close_date + timedelta(days=r.randint(1, 7))
            cur, disc = dl.currency, dl.discount or 0.0
            if dl.category == "Components":  # framework: monthly call-offs for 12 months
                for i in range(1, 13):
                    d = business_day(r, month_key(add_months(dl.close_date, i)))
                    key = month_key(d)
                    value = dl.amount_local / 12 * r.uniform(0.7, 1.3) * fx(cur, key)
                    self.add_invoice(cust, d, self.make_lines("Components", value, cust.market, key, disc), "deal",
                                     ref=f"Rammeaftale {dl.deal_id[-6:]}")
                continue
            if dl.category != "Equipment":
                continue  # service deals become contracts
            d1 = to_weekday(dl.close_date + timedelta(days=r.randint(20, 55)))
            key = month_key(d1)
            remaining = dl.amount_local / (1 - disc)
            lines = []
            pumps = sorted(self.by_cat["Equipment"], key=lambda p: p.list_dkk)
            while len(lines) < 4:
                fits = [p for p in pumps if self._list_local(p, cur) <= remaining * 0.9]
                if not fits:
                    break
                p = r.choice(fits[-6:])
                qty = r.randint(1, max(1, min(3, int(remaining * 0.9 // self._list_local(p, cur)))))
                lines.append(self._line(p, qty, self._list_local(p, cur), disc, cur, key))
                remaining -= qty * self._list_local(p, cur)
            if remaining > 50:
                lines.append(self._line(self.products["NF-ACC"], 1, float(round(remaining)), disc, cur, key))
            ref = r.choice([f"Ordre {dl.deal_id[-5:]}", f"PO-{r.randint(4500000000, 4509999999)}", None])
            if dl.amount_dkk > 150_000 and len(lines) > 1:
                cut = max(1, len(lines) // 2)
                self.add_invoice(cust, d1, lines[:cut], "deal", ref=ref)
                d2 = to_weekday(d1 + timedelta(days=r.randint(25, 50)))
                comm = self.products["SVC-COMM"]
                rest = [dict(ln, dkk=ln["net"] * fx(cur, month_key(d2))) for ln in lines[cut:]]
                rest.append(self._line(comm, 1, self._list_local(comm, cur), 0.0, cur, month_key(d2)))
                self.add_invoice(cust, d2, rest, "deal", ref=ref)
            else:
                if r.random() < 0.4:
                    comm = self.products["SVC-COMM"]
                    lines.append(self._line(comm, 1, self._list_local(comm, cur), 0.0, cur, key))
                self.add_invoice(cust, d1, lines, "deal", ref=ref)

    def book_contracts(self):
        sa = self.products["SA-STD"]
        label = {"DK": "Serviceaftale", "SE": "Serviceavtal", "DE": "Servicevertrag"}
        for c in self.crm.contracts:
            cust = self.customers[c.customer_key]
            cur = config.CURRENCY[c.market]
            for q in range(4):
                d = to_weekday(add_months(c.start, 3 * q) + timedelta(days=1))
                price = float(round(c.annual_dkk / 4 / config.PRICE_LIST_FX[cur]))
                desc = f"{label[c.market]} {c.start:%m/%Y}-{c.end:%m/%Y}, kvartal {q + 1}"
                self.add_invoice(cust, d, [self._line(sa, 1, price, 0.0, cur, month_key(d), desc)], "contract")

    def book_key_accounts(self):
        r = self.r
        for acc, ka in config.KEY_ACCOUNTS.items():
            cust = self.customers[acc]
            for key in DATA_MONTHS:
                progress = config.KEY_ACCOUNT_TREND.get(key, 0.0 if key < "2025-11" else 1.0)
                trend = 1 - (1 - ka["floor"]) * progress
                for cat, per_half in (("Components", ka["components_per_half"]), ("Service", ka["service_adhoc_per_half"])):
                    value = per_half / 6 * config.SEASONALITY[month_start(key).month] * trend * r.uniform(0.9, 1.1)
                    n = r.randint(2, 4) if cat == "Components" else r.randint(1, 2)
                    for _ in range(n):
                        self.add_invoice(cust, business_day(r, key), self.make_lines(cat, value / n, "DE", key), "key_account",
                                         ref=r.choice([f"PO-{r.randint(4500000000, 4509999999)}", None]))

    # ------------------------------------------------------------------ filler
    def book_filler(self):
        r = rng("erp-filler")
        noise = rng("erp-cells")
        by_half = defaultdict(list)
        for key in DATA_MONTHS:
            by_half[half_of_key(key)].append(key)
        self.shortfalls = []
        plan = {}
        for (market, cat), targets in config.REVENUE_TARGETS.items():
            for half, t in zip(config.HALVES, targets):
                months = by_half[half]
                all_w = sum(config.SEASONALITY[m] for m in (range(1, 7) if half.endswith("H1") else range(7, 13)))
                w = [config.SEASONALITY[month_start(k).month] for k in months]
                effective = t * 1e6 * sum(w) / all_w
                fixed = sum(self.booked[(market, cat, k)] for k in months)
                gap = effective - fixed
                if gap < 0 and len(months) == 6:
                    self.shortfalls.append((market, cat, half, gap))
                for k, wk in zip(months, w):
                    jitter = 1 + noise.uniform(-1, 1) * config.MONTHLY_TARGET_NOISE
                    if len(months) < 6:  # partial half: same months last year (all sources), scaled by the plan
                        pk = (market, cat, f"{int(k[:4]) - 1}{k[4:]}")
                        total_prior = self.booked[pk] + plan[pk]
                        ratio = t / targets[config.HALVES.index(half) - 2]
                        plan[(market, cat, k)] = max(0.0, total_prior * ratio * jitter - self.booked[(market, cat, k)])
                    else:
                        plan[(market, cat, k)] = max(0.0, gap * wk / sum(w) * jitter)
        for key in DATA_MONTHS:
            for market in config.MARKETS:
                resid = {cat: plan[(market, cat, key)] for cat in config.CATEGORIES}
                pool = [c for c in self.customers.values() if c.market == market and not c.is_key
                        and c.erp_since and c.erp_since <= month_end(key)]
                weights = [(c.weight if not c.prospect else 0.25) * (c.trend_2026 if key >= "2026-01" else 1.0) for c in pool]
                for _ in range(3000):
                    open_cats = [c for c in config.CATEGORIES if resid[c] > MIN_LINE[c]]
                    if not open_cats:
                        break
                    cat = r.choices(open_cats, weights=[resid[c] for c in open_cats])[0]
                    size = max(MIN_LINE[cat], min(resid[cat], TYPICAL_INVOICE[cat] * r.lognormvariate(0, 0.7)))
                    cust = r.choices(pool, weights=weights)[0]
                    lines = self.make_lines(cat, size, market, key)
                    if cat == "Service" and resid["Components"] > 5000 and r.random() < 0.3:
                        lines += self.make_lines("Components", min(resid["Components"], r.uniform(2000, 12000)), market, key)
                    for ln in lines:
                        resid[ln["category"]] -= ln["dkk"]
                    self.add_invoice(cust, business_day(r, key), lines, "run_rate",
                                     ref=r.choice([f"Rekv. {r.randint(1000, 99999)}", None, None]) if market == "DK" else
                                     r.choice([f"PO-{r.randint(4500000000, 4509999999)}", None]))

    # ------------------------------------------------------------------ credits
    def book_credit_notes(self):
        r = rng("erp-credits")
        candidates = [i for i in self.invoices if i["source"] in ("run_rate", "key_account")]
        for inv in r.sample(candidates, int(len(candidates) * 0.012)):
            d = to_weekday(inv["date"] + timedelta(days=r.randint(6, 40)))
            key = month_key(d)
            parts = [ln for ln in inv["lines"] if ln["category"] == "Components"]
            if parts and r.random() < 0.6:  # return of spare parts
                ln = r.choice(parts)
                qty = -max(1, int(ln["qty"] * r.uniform(0.2, 0.6)))
                line = dict(ln, qty=qty, net=round(qty * ln["unit_price"] * (1 - ln["disc"]), 2),
                            desc="Retur: " + ln["desc"])
            else:  # price correction, no cost impact
                ln = inv["lines"][0]
                amount = -round(min(sum(x["net"] for x in inv["lines"]) * r.choice([0.03, 0.05, 0.1]),
                                    15000 / config.PRICE_LIST_FX[inv["currency"]]), 2)
                line = dict(ln, qty=1, unit_price=amount, disc=0.0, net=amount, unit_cost=0.0,
                            desc="Prisregulering jf. aftale")
            line["dkk"] = line["net"] * fx(inv["currency"], key)
            credit = self.add_invoice(inv["cust"], d, [line], "credit", kind="credit_note")
            if credit:
                credit["credits"] = inv

    def run(self):
        self.book_deals()
        self.book_contracts()
        self.book_key_accounts()
        self.book_filler()
        self.book_credit_notes()
        return self
