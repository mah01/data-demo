"""
CRM generator (HubSpot-like).

Produces owners (users), companies, deals, activities and property history.
Also returns in-memory deal objects that the ERP and payroll generators use
(won deals become invoices and commissions).
"""
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Optional

import config
import roster
from common import rng, months_between, month_start, month_end, half_of, fx, to_weekday, business_day
from world import Contract, resolve_renewals, strip_suffix

CRM_CATEGORY = {"Equipment": "Pumps & Systems", "Components": "Spare Parts Agreement", "Service": "Service Contract"}
MARKET_LABEL = {"DK": "Denmark", "SE": "Sweden", "DE": "Germany"}
PIPELINE = {"DK": "Nordics Sales", "SE": "Nordics Sales", "DE": "DACH Sales"}
OPEN_STAGES = ["Qualification", "Needs Analysis", "Proposal Sent", "Negotiation"]

PHRASES = {
    "DK": {"Equipment": ["Pumpeudskiftning", "Nyt trykforøgeranlæg", "Spildevandspumper", "Procespumper", "Doseringsanlæg"],
           "Components": ["Reservedelsaftale"], "Service": ["Serviceaftale"]},
    "SE": {"Equipment": ["Pumpbyte", "Tryckstegringsanläggning", "Avloppspumpar", "Processpumpar"],
           "Components": ["Reservdelsavtal"], "Service": ["Serviceavtal"]},
    "DE": {"Equipment": ["Pumpentausch", "Neuanlage Druckerhöhung", "Abwasserpumpen", "Prozesspumpen", "Dosiertechnik"],
           "Components": ["Ersatzteilvertrag"], "Service": ["Servicevertrag"]},
}


@dataclass
class Deal:
    market: str
    customer_key: str
    owner: str
    category: str
    deal_type: str
    created: date
    close_date: date
    amount_dkk: float
    name: str
    outcome: str = "open"
    discount: Optional[float] = None
    loss_reason: Optional[str] = None
    fixed: bool = False
    contract_id: Optional[int] = None
    on_duplicate: bool = False
    deal_id: str = ""
    amount_local: float = 0.0

    @property
    def currency(self):
        return config.CURRENCY[self.market]


class CRMGenerator:
    def __init__(self, customers, contracts):
        self.r = rng("crm")
        self.customers = {c.key: c for c in customers}
        self.contracts = contracts
        self.emp = {row[0]: {"start": row[7], "end": row[8], "country": row[4]} for row in roster.ROSTER}
        self.emp["crm_heinz"] = {"start": date(2019, 3, 4), "end": date(2024, 10, 31), "country": "DE"}
        self.owner_tl = {}          # customer key -> [(date, owner key, changed_by, source)]
        self.deals = []
        self.activities = []
        self.users = {}             # owner key -> user row
        self.prospect_claims = {}   # prospect key -> owner

    # ------------------------------------------------------------------ helpers
    def active(self, key, d):
        e = self.emp[key]
        return e["start"] <= d and (e["end"] is None or d <= e["end"])

    def seller_weight(self, key, d):
        if key in ("de_cm", "se_cm"):
            return 0.45
        if key == "dk_salesdir":
            return 0.3
        if key == "de_sabine":
            return 0.5
        if key in roster.NEW_DE_REPS:
            s = self.emp[key]["start"]
            months = (d.year - s.year) * 12 + d.month - s.month
            return 0.5 if months < 1 else 0.9 if months < 2 else 1.6
        return 1.0

    def sellers(self, market, d):
        pool = list(roster.SELLERS[market]) + (["crm_heinz"] if market == "DE" else [])
        return [k for k in pool if self.active(k, d)]

    def owner_at(self, ckey, d):
        tl = self.owner_tl.get(ckey)
        if not tl:
            return None
        cur = tl[0][1]
        for when, who, *_ in tl:
            if when <= d:
                cur = who
        return cur

    # ------------------------------------------------------------------ owners
    def assign_owners(self):
        r = self.r
        start = config.CRM_HISTORY_START
        for c in self.customers.values():
            if not c.crm_name or c.prospect:
                continue
            if c.is_key:
                ka = config.KEY_ACCOUNTS[c.key]
                self.owner_tl[c.key] = [(start, ka["owner_before"], None, None),
                                        (ka["reassigned_on"], ka["owner_after"], "de_cm", "BULK_ASSIGN")]
                continue
            pool = [k for k in self.sellers(c.market, start) if k != "crm_heinz"]
            owner = r.choices(pool, weights=[self.seller_weight(k, start) for k in pool])[0]
            self.owner_tl[c.key] = [(start, owner, None, None)]
        de = [c for c in self.customers.values() if c.market == "DE" and c.key in self.owner_tl and not c.is_key]
        for c in r.sample(de, 6):  # former rep's accounts, reassigned after he left
            self.owner_tl[c.key] = [(start, "crm_heinz", None, None), (date(2024, 11, 4), "de_florian", "de_cm", "CRM_UI")]
        for c in self.customers.values():  # Johan left SE in March 2025
            if self.owner_tl.get(c.key, [(0, None)])[-1][1] == "se_johan":
                self.owner_tl[c.key].append((date(2025, 5, 14), "se_sara", "se_cm", "BULK_ASSIGN"))
        # DACH territory re-cut in autumn 2025 (besides the two key accounts)
        cands = sorted([c for c in de if self.owner_tl[c.key][-1][1] in
                        ("de_stefan", "de_monika", "de_tobias", "de_markus", "de_florian")],
                       key=lambda c: -c.weight)[:20]
        moved = r.sample(cands, 11)
        plan = [("de_lukas", date(2025, 9, 15))] * 4 + [("de_jana", date(2025, 10, 6))] * 4 + [("de_timo", date(2025, 11, 10))] * 3
        for c, (who, when) in zip(moved, plan):
            self.owner_tl[c.key].append((when, who, "de_cm", "BULK_ASSIGN"))

    # ------------------------------------------------------------------ deals
    def _amount(self, market, category, d):
        med = config.DEAL_MEDIAN_DKK[category] * {"DK": 1.0, "SE": 0.85, "DE": 1.05}[market]
        if market == "DK" and category == "Equipment" and d.year == 2026:
            med *= 1.15
        return med * min(config.DEAL_MAX_MULTIPLE, self.r.lognormvariate(0, 0.62))

    def _cycle(self, category, new_business):
        lo, hi, mode = {"Equipment": (35, 170, 75), "Components": (20, 100, 45), "Service": (25, 120, 60)}[category]
        days = self.r.triangular(lo, hi, mode) * (1.2 if new_business else 1.0)
        return timedelta(days=int(days))

    def _name(self, c, category, created):
        base = strip_suffix(c.crm_name or c.legal_name)
        phrase = self.r.choice(PHRASES[c.market][category])
        if category in ("Service", "Components"):
            phrase += f" {created.year + (1 if created.month >= 9 else 0)}"
        return f"{base} - {phrase}"

    def generate_deals(self):
        r = self.r
        by_market = defaultdict(lambda: {"cust": [], "prosp": []})
        for c in self.customers.values():
            if c.is_key or not c.crm_name:
                continue
            by_market[c.market]["prosp" if c.prospect else "cust"].append(c)
        for key in months_between(config.CRM_HISTORY_START, config.DATA_END):
            half = half_of(month_start(key))
            for market in config.MARKETS:
                rate = config.DEAL_RATE[market][half] * (0.75 if key.endswith("-07") else 1.0)
                for _ in range(max(0, round(rate * r.uniform(0.88, 1.12)))):
                    created = business_day(r, key)
                    pool = self.sellers(market, created)
                    owner = r.choices(pool, weights=[self.seller_weight(k, created) for k in pool])[0]
                    nb_share = 0.8 if owner in roster.NEW_DE_REPS else 0.45 if market == "DE" else 0.38
                    new_business = r.random() < nb_share
                    if new_business:
                        free = [p for p in by_market[market]["prosp"] if p.key not in self.prospect_claims]
                        mine = [p for p in by_market[market]["prosp"] if self.prospect_claims.get(p.key) == owner]
                        c = r.choice(free) if free and (not mine or r.random() < 0.95) else r.choice(mine or by_market[market]["prosp"])
                        if c.key not in self.prospect_claims:
                            self.prospect_claims[c.key] = owner
                            c.crm_created = created - timedelta(days=r.randint(0, 20))
                            self.owner_tl[c.key] = [(c.crm_created, owner, owner, "CRM_UI")]
                        owner = self.prospect_claims[c.key] if self.active(self.prospect_claims[c.key], created) else owner
                        mix = {"Equipment": 0.80, "Components": 0.08, "Service": 0.12}
                    else:
                        own = [x for x in by_market[market]["cust"] if self.owner_at(x.key, created) == owner]
                        pick_from = own if own and r.random() < 0.85 else by_market[market]["cust"]
                        c = r.choices(pick_from, weights=[x.weight + 0.5 for x in pick_from])[0]
                        mix = config.DEAL_CATEGORY_MIX_DK_FROM_2025 if market == "DK" and created.year >= 2025 \
                            else config.DEAL_CATEGORY_MIX
                    cat = r.choices(list(mix), weights=list(mix.values()))[0]
                    d = Deal(market, c.key, owner, cat, "New Business" if new_business else "Existing Business",
                             created, created + self._cycle(cat, new_business), self._amount(market, cat, created),
                             self._name(c, cat, created))
                    d.on_duplicate = bool(c.crm_dup_id) and created.year >= 2025 and r.random() < 0.3
                    self.deals.append(d)
        for acc, nm, cat, eur, created, closed, outcome, owner, reason in config.KEY_ACCOUNT_DEALS:
            c = self.customers[acc]
            self.deals.append(Deal("DE", acc, owner, cat, "Existing Business", created, closed,
                                   eur * fx("EUR", created.strftime("%Y-%m")), f"{c.crm_name} - {nm}",
                                   outcome=outcome, loss_reason=reason, fixed=True))

    def calibrate_pipeline(self):
        def created_sum(market, half, fixed):
            return sum(d.amount_dkk for d in self.deals if d.market == market and d.fixed == fixed
                       and d.deal_type != "Renewal" and half_of(d.created) == half)
        for market in config.MARKETS:
            f = (config.PIPELINE_TARGET[(market, "2025H1")] - created_sum(market, "2025H1", True)) / created_sum(market, "2025H1", False)
            for d in self.deals:
                if d.market == market and not d.fixed:
                    d.amount_dkk *= f
            g = (config.PIPELINE_TARGET[(market, "2026H1")] - created_sum(market, "2026H1", True)) / created_sum(market, "2026H1", False)
            for d in self.deals:
                if d.market == market and not d.fixed and half_of(d.created) == "2026H1":
                    d.amount_dkk *= g

    def assign_outcomes(self):
        r = rng("crm-outcomes")
        groups = defaultdict(list)
        for d in self.deals:
            if d.deal_type != "Renewal" and d.close_date <= config.DATA_END:
                groups[(d.market, half_of(d.close_date))].append(d)
        won_equipment = defaultdict(list)  # customer key -> [(close date, DKK)] for invariant 3
        for d in self.deals:
            if d.fixed and d.outcome == "won" and d.category == "Equipment":
                won_equipment[d.customer_key].append((d.close_date, d.amount_dkk))

        def may_win(d):
            """Invariant 3: cap equipment wins per non-key German customer in any 12-month window."""
            if d.market != "DE" or d.category != "Equipment" or self.customers[d.customer_key].is_key:
                return True
            recent = sum(a for when, a in won_equipment[d.customer_key] if abs((when - d.close_date).days) <= 365)
            return recent + d.amount_dkk <= config.DE_OTHER_CUSTOMER_MAX_EQUIPMENT_WON_12M

        for market, half in sorted(groups):  # chronological, so the 12-month window looks back correctly
            g = groups[(market, half)]
            target = round(config.WIN_RATE[market][half] * len(g))
            new_rate = config.DE_NEW_REP_WIN_RATE.get(half) if market == "DE" else None
            if new_rate is None:
                strata = [(g, target)]
            else:  # invariant 2: expansion hires convert at their own planned rate, veterans take the rest
                new = [d for d in g if d.owner in roster.NEW_DE_REPS]
                vet = [d for d in g if d.owner not in roster.NEW_DE_REPS]
                strata = [(new, round(new_rate * len(new))), (vet, target - round(new_rate * len(new)))]
            for deals, t in strata:
                free = [d for d in deals if not d.fixed]
                k = max(0, t - sum(1 for d in deals if d.fixed and d.outcome == "won"))
                scores = [r.random() + (0.08 if d.deal_type == "Existing Business" else 0.0) for d in free]
                won = 0
                for _, i in sorted(((s, i) for i, s in enumerate(scores)), reverse=True):
                    d = free[i]
                    if won < k and may_win(d):
                        d.outcome, won = "won", won + 1
                        if d.category == "Equipment":
                            won_equipment[d.customer_key].append((d.close_date, d.amount_dkk))
                    else:
                        d.outcome = "lost"
            if market == "DE" and half == config.DE_WON_VALUE_INVARIANT["half"]:
                self._tune_won_value(g, strata, won_equipment, may_win)
        for d in self.deals:
            if d.fixed:
                continue
            if d.outcome == "lost":
                late_de = d.market == "DE" and d.close_date.year == 2026
                reasons = config.LOSS_REASONS["de_2026" if late_de else "normal"]
                d.loss_reason = r.choices([x for x, _ in reasons], weights=[w for _, w in reasons])[0] if r.random() > 0.14 else None
            if d.outcome in ("won", "lost"):
                y, h = d.close_date.year, half_of(d.close_date)
                base = config.DEAL_DISCOUNT.get((d.market, h), config.DEAL_DISCOUNT.get((d.market, str(y)), config.DEAL_DISCOUNT["default"]))
                disc = max(0.0, base + r.uniform(-0.03, 0.03)) if d.category == "Equipment" else max(0.0, base / 2 + r.uniform(-0.02, 0.02))
                d.discount = round(disc, 3) if d.outcome == "won" or r.random() < 0.5 else None
        for d in self.deals:
            if d.fixed and d.outcome == "won":
                d.discount = 0.06 if d.close_date.year == 2025 else 0.15

    def _tune_won_value(self, group, strata, won_equipment, may_win):
        """Invariant 4: swap winners and losers inside each rep stratum (win counts
        unchanged) until German won value lands on DE_WON_VALUE_INVARIANT."""
        inv = config.DE_WON_VALUE_INVARIANT
        base = sum(d.amount_dkk for d in self.deals if d.market == "DE" and d.deal_type != "Renewal"
                   and d.outcome == "won" and half_of(d.close_date) == inv["base_half"])
        target = base * (1 + inv["change"])
        current = sum(d.amount_dkk for d in group if d.outcome == "won")
        for _ in range(300):
            diff = current - target
            best, move = abs(diff), None
            for deals, _ in strata:
                free = [d for d in deals if not d.fixed]
                for w in (d for d in free if d.outcome == "won"):
                    for l in (d for d in free if d.outcome == "lost"):
                        nd = diff - w.amount_dkk + l.amount_dkk
                        if abs(nd) < best and (l.customer_key == w.customer_key or may_win(l)):
                            best, move = abs(nd), (w, l)
            if move is None:
                return
            w, l = move
            w.outcome, l.outcome = "lost", "won"
            current += l.amount_dkk - w.amount_dkk
            if w.category == "Equipment":
                won_equipment[w.customer_key].remove((w.close_date, w.amount_dkk))
            if l.category == "Equipment":
                won_equipment[l.customer_key].append((l.close_date, l.amount_dkk))

    # ------------------------------------------------------------------ contracts / renewals
    def add_new_contracts(self):
        for d in self.deals:
            if d.outcome == "won" and d.category == "Service" and d.deal_type != "Renewal":
                q = (d.close_date.month - 1) // 3 + 1
                start = date(d.close_date.year + (q == 4), (q % 4) * 3 + 1, 1)
                end = date(start.year + 1, start.month, 1) - timedelta(days=1)
                c = Contract(len(self.contracts) + 1, d.customer_key, d.market, round(d.amount_dkk, -3), start, end, "new")
                self.contracts.append(c)
                d.contract_id = c.cid
        resolve_renewals(self.contracts)

    def renewal_deals(self):
        r = rng("crm-renewals")
        successors = {c.predecessor: c for c in self.contracts if c.predecessor}
        owner_for = lambda c, d: roster.SERVICE_RENEWAL_OWNER[c.market] or self.owner_at(c.customer_key, d) or "de_cm"
        for c in self.contracts:
            cust = self.customers[c.customer_key]
            if not cust.crm_name:
                continue
            if c.origin == "initial" and c.start == date(2025, 1, 1):  # renewal of the 2024 term, won in Q4 2024
                created, closed = to_weekday(date(2024, 10, r.randint(1, 28))), to_weekday(date(2024, 12, r.randint(1, 18)))
                self._renewal(cust, c, created, closed, "won", c.annual_dkk, owner_for(c, created), r)
            if c.renewed is None or c.end > config.DATA_END:
                continue
            if c.customer_key == "rheinmark":
                created, closed, reason = config.RHEINMARK_RENEWAL
                self._renewal(cust, c, created, closed, "lost", c.annual_dkk * 1.03, "de_lukas", r, reason)
                continue
            created = to_weekday(c.end - timedelta(days=r.randint(55, 85)))
            closed = to_weekday(c.end - timedelta(days=r.randint(5, 25)))
            amount = successors[c.cid].annual_dkk if c.renewed else c.annual_dkk * (1 + config.CONTRACT_PRICE_INDEX)
            self._renewal(cust, c, created, closed, "won" if c.renewed else "lost", amount, owner_for(c, created), r)
        # Renewals lost in Q4 2024 (customers without a 2025 contract)
        with_contract = {c.customer_key for c in self.contracts}
        for market, n in (("DK", 7), ("SE", 1), ("DE", 1)):
            pool = [c for c in self.customers.values() if c.market == market and c.crm_name and not c.prospect
                    and not c.is_key and c.key not in with_contract]
            for cust in r.sample(pool, n):
                created, closed = to_weekday(date(2024, 10, r.randint(1, 25))), to_weekday(date(2024, 12, r.randint(1, 18)))
                fake = Contract(0, cust.key, market, round(r.uniform(60, 260)) * 1000, date(2024, 1, 1), date(2024, 12, 31), "initial")
                self._renewal(cust, fake, created, closed, "lost", fake.annual_dkk, owner_for(fake, created), r)

    def _renewal(self, cust, contract, created, closed, outcome, amount, owner, r, reason=None):
        if outcome == "lost" and reason is None:
            reasons = config.LOSS_REASONS["renewal"]
            reason = r.choices([x for x, _ in reasons], weights=[w for _, w in reasons])[0] if r.random() > 0.1 else None
        year = contract.end.year + 1
        label = {"DK": "Serviceaftale fornyelse", "SE": "Serviceavtal förnyelse", "DE": "Servicevertrag Verlängerung"}[cust.market]
        d = Deal(cust.market, cust.key, owner, "Service", "Renewal", created, closed, amount,
                 f"{strip_suffix(cust.crm_name)} - {label} {year}", outcome=outcome, loss_reason=reason,
                 contract_id=contract.cid or None)
        d.discount = round(r.uniform(0, 0.03), 3) if outcome == "won" else None
        self.deals.append(d)

    # ------------------------------------------------------------------ finalize
    def finalize_deals(self):
        r = rng("crm-ids")
        self.deals.sort(key=lambda d: (d.created, d.customer_key, d.name))
        next_id = 9_214_300_000
        for d in self.deals:
            next_id += r.randint(1_000, 400_000)
            d.deal_id = str(next_id)
            step = 100 if d.currency == "EUR" else 1000
            d.amount_local = round(d.amount_dkk / fx(d.currency, d.created.strftime("%Y-%m")) / step) * step
            d.amount_dkk = round(d.amount_local * fx(d.currency, d.created.strftime("%Y-%m")), 2)

    def run(self):
        self.assign_owners()
        self.generate_deals()
        self.calibrate_pipeline()
        self.assign_outcomes()
        self.add_new_contracts()
        self.renewal_deals()
        self.finalize_deals()
        return self
