"""
The hidden "real world" behind the three systems: products, customers,
prospects and service contracts.

Each system generator renders its own view of this world with its own IDs,
naming conventions, granularity and gaps. Nothing in this module is written
to disk directly.
"""
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional

import config
from common import rng, ascii_fold, slug, add_months


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------
@dataclass
class Product:
    number: str
    name: str
    category: str
    list_dkk: float
    cost_dkk: float
    unit: str = "stk"


PRODUCT_GROUPS = {"Equipment": (10, "Pumper og anlæg"),
                  "Components": (20, "Reservedele og komponenter"),
                  "Service": (30, "Service og vedligehold")}

_EQUIPMENT = [
    ("NF-C32", "Centrifugalpumpe NF-C 32/160", 28000), ("NF-C40", "Centrifugalpumpe NF-C 40/200", 39000),
    ("NF-C50", "Centrifugalpumpe NF-C 50/250", 56000), ("NF-C65", "Centrifugalpumpe NF-C 65/315", 84000),
    ("NF-C80", "Centrifugalpumpe NF-C 80/400", 128000), ("NF-M10", "Flertrinspumpe NF-M 10", 46000),
    ("NF-M20", "Flertrinspumpe NF-M 20", 68000), ("NF-M45", "Flertrinspumpe NF-M 45", 115000),
    ("NF-S7", "Dykpumpe NF-S 7.5 kW", 32000), ("NF-S15", "Dykpumpe NF-S 15 kW", 52000),
    ("NF-S30", "Dykpumpe NF-S 30 kW", 95000), ("NF-D01", "Doseringspumpe NF-D mini", 14000),
    ("NF-D60", "Doseringspumpe NF-D 60", 22000), ("NF-D200", "Doseringspumpe NF-D 200", 36000),
    ("BS-2", "Trykforøgeranlæg BS-2", 145000), ("BS-3", "Trykforøgeranlæg BS-3", 210000),
    ("BS-4", "Trykforøgeranlæg BS-4", 320000), ("LS-2", "Pumpestation spildevand LS-2", 260000),
    ("HX-500", "Pumpeskid HX-500", 420000), ("CP-PRO", "Styretavle CP-PRO", 48000),
    ("VFD-22", "Frekvensomformerpakke 22 kW", 38000), ("VFD-55", "Frekvensomformerpakke 55 kW", 72000),
    ("NF-ACC", "Tilbehør og montagemateriel iht. tilbud", 0),  # priced per quote
]
VARIABLE_COST_RATIO = {"NF-ACC": 0.67, "SA-STD": 0.40}
_COMPONENTS = [
    ("RS-SEAL-S", "Akseltætningssæt S", 1200), ("RS-SEAL-M", "Akseltætningssæt M", 2900),
    ("RS-SEAL-L", "Akseltætningssæt L", 6500), ("RS-IMP-S", "Løbehjul S", 3100),
    ("RS-IMP-M", "Løbehjul M", 7800), ("RS-IMP-L", "Løbehjul L", 17500),
    ("RS-BRG-S", "Lejesæt S", 1500), ("RS-BRG-L", "Lejesæt L", 3900),
    ("RS-MOT-7", "Motor 7.5 kW IE3", 14000), ("RS-MOT-15", "Motor 15 kW IE3", 24000),
    ("RS-MOT-30", "Motor 30 kW IE3", 41000), ("RS-PT", "Tryktransmitter", 4200),
    ("RS-FLOW", "Flowmåler DN80", 11000), ("RS-GSK", "Pakningssæt", 650),
    ("RS-WEAR", "Slidringssæt", 2200), ("RS-SLV", "Akselbøsning", 3100),
    ("RS-CTRL", "Styreprint CP-PRO", 6800), ("RS-CPL", "Kobling", 2900),
    ("RS-CHK", "Kontraventil DN80", 5400), ("RS-FLT", "Filterindsats", 890),
]
_SERVICE = [
    ("SVC-HOUR", "Servicetime tekniker", 1050, "time"), ("SVC-CALL", "Udkørselsgebyr", 1450, "stk"),
    ("SVC-COMM", "Idriftsættelse", 12500, "stk"), ("SVC-INSP", "Inspektion og tilstandsrapport", 4800, "stk"),
    ("SVC-WS", "Værkstedsreparation", 6500, "stk"),
    ("SA-STD", "Serviceaftale - kvartalsvis fakturering", 0, "stk"),
]


def build_products():
    r = rng("products")
    out = []
    for num, name, price in _EQUIPMENT:
        if price == 0:
            out.append(Product(num, name, "Equipment", 0, 0))
            continue
        out.append(Product(num, name, "Equipment", price, round(price * (config.COST_RATIO["Equipment"] + r.uniform(-.035, .035)))))
    for num, name, price in _COMPONENTS:
        out.append(Product(num, name, "Components", price, round(price * (config.COST_RATIO["Components"] + r.uniform(-.05, .05)))))
    for num, name, price, unit in _SERVICE:
        out.append(Product(num, name, "Service", price, round(price * (config.COST_RATIO["Service"] + r.uniform(-.03, .03))), unit))
    return out


# ---------------------------------------------------------------------------
# Customers and prospects
# ---------------------------------------------------------------------------
@dataclass
class Customer:
    key: str
    market: str
    legal_name: str
    city: str
    industry: str
    weight: float
    prospect: bool                      # True = CRM only until a deal is won
    erp_since: Optional[date] = None    # first ERP existence (None for unconverted prospects)
    crm_name: Optional[str] = None      # None = not in CRM
    crm_duplicate_name: Optional[str] = None
    crm_created: Optional[date] = None
    domain: Optional[str] = None
    vat: Optional[str] = None
    trend_2026: float = 1.0             # multiplier on run-rate purchases from 2026
    is_key: bool = False
    erp_number: Optional[int] = None
    crm_id: Optional[str] = None
    crm_dup_id: Optional[str] = None
    first_invoice: Optional[date] = None
    tags: list = field(default_factory=list)


_NAMES = {
    "DK": (["Nordjysk", "Vestjysk", "Sydfyns", "Midtjysk", "Himmerlands", "Limfjords", "Kalundborg", "Esbjerg",
            "Horsens", "Silkeborg", "Roskilde", "Holbæk", "Vejle", "Herning", "Thy", "Djurs", "Sjællands",
            "Bornholms", "Køge", "Odense", "Randers", "Skive", "Viborg", "Fredericia", "Svendborg", "Næstved",
            "Hjørring", "Aabenraa", "Fjord", "Kyst", "Østjysk", "Lolland"],
           ["Vand", "Varmeværk", "Fødevarer", "Mejeri", "Slagteri", "Køleteknik", "Kemi", "Fjernvarme",
            "Spildevand", "Akvakultur", "Maskinfabrik", "Bryggeri", "Plast", "Energi", "Rensningsanlæg",
            "Stålindustri", "Emballage", "Bygningsservice", "VVS", "Foder"],
           ["A/S", "A/S", "A/S", "ApS", "ApS", "A.m.b.a."],
           ["Aarhus", "Odense", "Aalborg", "Esbjerg", "Vejle", "Horsens", "Randers", "Kolding", "Herning",
            "Silkeborg", "Roskilde", "Næstved", "Viborg", "Holstebro", "Fredericia", "Skive", "Køge"]),
    "SE": (["Mälardalens", "Norrlands", "Skånska", "Värmlands", "Göteborgs", "Dalarnas", "Upplands", "Smålands",
            "Hallands", "Västerbottens", "Gävle", "Örebro", "Jönköpings", "Kalmar", "Blekinge", "Östgöta"],
           ["Vatten", "Massa", "Kyl", "Livsmedel", "Energi", "Kemi", "Pappersbruk", "Fjärrvärme", "Mejeri",
            "Industriservice", "Reningsverk"],
           ["AB"],
           ["Göteborg", "Malmö", "Västerås", "Örebro", "Linköping", "Jönköping", "Helsingborg", "Norrköping",
            "Karlstad", "Gävle", "Sundsvall", "Umeå", "Kalmar", "Halmstad"]),
    "DE": (["Weserland", "Elbtal", "Mainfranken", "Mosel", "Ruhrtal", "Saarland", "Harz", "Eifel", "Allgäu",
            "Lausitz", "Emsland", "Sauerland", "Oderland", "Havelland", "Spreewald", "Donautal", "Neckartal",
            "Isartal", "Fuldatal", "Lahntal", "Werratal", "Nahetal", "Altmark", "Uckermark", "Vogtland",
            "Hunsrück", "Westerwald", "Wetterau", "Kraichgau", "Ostalb"],
           ["Chemie", "Papier", "Wasserwerke", "Lebensmittel", "Kältetechnik", "Stahl", "Brauerei", "Energie",
            "Umwelttechnik", "Klärtechnik", "Molkerei", "Kunststoffe", "Anlagenbau", "Fleischwaren",
            "Gebäudetechnik", "Galvanik"],
           ["GmbH", "GmbH", "GmbH", "GmbH & Co. KG", "AG"],
           ["Köln", "Hamburg", "Hannover", "Bremen", "Dortmund", "Essen", "Kassel", "Würzburg", "Stuttgart",
            "Nürnberg", "Augsburg", "Regensburg", "Mannheim", "Karlsruhe", "Bielefeld", "Münster", "Leipzig",
            "Magdeburg", "Osnabrück", "Paderborn", "Ulm", "Freiburg"]),
}
_INDUSTRY_BY_WORD = {
    "UTILITIES": ["Vand", "Varmeværk", "Fjernvarme", "Spildevand", "Rensningsanlæg", "Vatten", "Fjärrvärme",
                  "Reningsverk", "Wasserwerke", "Klärtechnik", "Energi", "Energie"],
    "FOOD_BEVERAGES": ["Fødevarer", "Mejeri", "Slagteri", "Bryggeri", "Livsmedel", "Lebensmittel", "Molkerei",
                       "Brauerei", "Fleischwaren", "Foder", "Akvakultur"],
    "CHEMICALS": ["Kemi", "Chemie", "Galvanik", "Plast", "Kunststoffe"],
    "PAPER_FOREST_PRODUCTS": ["Massa", "Pappersbruk", "Papier", "Emballage"],
    "MACHINERY": ["Maskinfabrik", "Anlagenbau", "Stålindustri", "Stahl", "Industriservice", "Kältetechnik",
                  "Køleteknik", "Kyl"],
    "BUILDING_MATERIALS": ["Bygningsservice", "VVS", "Gebäudetechnik"],
}
_SUFFIXES = ("A/S", "ApS", "A.m.b.a.", "AB", "GmbH & Co. KG", "GmbH", "AG", "I/S")

COUNTS = {  # existing ERP customers (excl. key accounts), CRM-only prospects
    "DK": (125, 70), "SE": (50, 35), "DE": (70, 190),
}
WEIGHT_CAP = {"DK": 22.0, "SE": 16.0, "DE": 9.0}  # keeps German run-rate customers below the key accounts


def _industry(word):
    for ind, words in _INDUSTRY_BY_WORD.items():
        if word in words:
            return ind
    return "MACHINERY"


def strip_suffix(name):
    for s in _SUFFIXES:
        if name.endswith(" " + s):
            return name[: -len(s) - 1]
    return name


def _crm_variant(r, legal):
    """How a sales rep typed the company into the CRM."""
    x = r.random()
    base = strip_suffix(legal)
    if x < 0.50:
        return base
    if x < 0.68:
        return legal
    if x < 0.80:
        return ascii_fold(base)
    if x < 0.88:
        return base + r.choice([" (HQ)", " - Hovedkontor", " Group", " Produktion"]) if legal.endswith(("A/S", "ApS")) \
            else base + r.choice([" (HQ)", " Group", " Werk 1", " Produktion"])
    if x < 0.94:
        return legal.upper()
    words = base.split()
    return " ".join(words[:-1] + [words[-1][:-1]]) if len(words[-1]) > 5 else base + "s"


def _vat(r, market):
    if market == "DK":
        return f"DK{r.randint(10000000, 45999999)}"
    if market == "SE":
        return f"SE55{r.randint(10000000, 69999999)}01"
    return f"DE{r.randint(100000000, 349999999)}"


def build_customers():
    r = rng("customers")
    customers, used = [], set()
    tld = {"DK": "dk", "SE": "se", "DE": "de"}
    for market in config.MARKETS:
        prefixes, words, suffixes, cities = _NAMES[market]
        n_cust, n_prosp = COUNTS[market]
        for i in range(n_cust + n_prosp):
            while True:
                p, w = r.choice(prefixes), r.choice(words)
                name = f"{p} {w} {r.choice(suffixes)}" if market != "DE" or r.random() > 0.15 else f"{w} {p} {r.choice(suffixes)}"
                if strip_suffix(name) not in used:
                    used.add(strip_suffix(name))
                    break
            prospect = i >= n_cust
            c = Customer(key=f"{market.lower()}-{i:03d}", market=market, legal_name=name, city=r.choice(cities),
                         industry=_industry(w), weight=min(r.paretovariate(1.25), WEIGHT_CAP[market]), prospect=prospect)
            c.domain = slug(strip_suffix(name)) + "." + tld[market] if r.random() > 0.12 else None
            c.vat = _vat(r, market) if r.random() > 0.08 else None
            if not prospect:
                c.erp_since = date(r.randint(2006, 2024), r.randint(1, 12), r.randint(1, 28))
                in_crm = c.weight > 1.6 or r.random() < 0.80
                c.crm_name = _crm_variant(r, name) if in_crm else None
            else:
                c.crm_name = _crm_variant(r, name)
            customers.append(c)

    # A few customers buying noticeably less in 2026 (normal churn / competition).
    de_existing = [c for c in customers if c.market == "DE" and not c.prospect and c.weight < 2.5]
    for c in r.sample(de_existing, 7):
        c.trend_2026 = 0.35
        c.tags.append("declining")
    dk_existing = [c for c in customers if c.market == "DK" and not c.prospect]
    for c in r.sample(dk_existing, 5):
        c.trend_2026 = 0.6
    # Duplicate CRM records for three Danish customers.
    for c in r.sample([c for c in dk_existing if c.crm_name], 3):
        c.crm_duplicate_name = strip_suffix(c.legal_name) if c.crm_name != strip_suffix(c.legal_name) else c.legal_name

    for key, ka in config.KEY_ACCOUNTS.items():
        customers.append(Customer(key=key, market="DE", legal_name=ka["erp_name"], crm_name=ka["crm_name"],
                                  city=ka["city"], industry=ka["industry"], weight=0.0, prospect=False,
                                  erp_since=date(2014 if key == "rheinmark" else 2016, 3, 11), domain=ka["domain"],
                                  vat=_vat(r, "DE"), is_key=True))

    # ERP customer numbers (existing customers only; new ones are numbered on first invoice).
    nums = r.sample(range(10100, 69999), len(customers))
    for c, n in zip(customers, nums):
        if not c.prospect:
            c.erp_number = n
    ids = r.sample(range(10000, 99999), len(customers) + 10)
    for c, n in zip(customers, ids):
        if c.crm_name:
            c.crm_id = f"cmp_{n}"
            c.crm_created = date(r.randint(2019, 2024), r.randint(1, 12), r.randint(1, 28)) if not c.prospect else None
    for c, n in zip([c for c in customers if c.crm_duplicate_name], ids[-10:]):
        c.crm_dup_id = f"cmp_{n}"
    return customers


# ---------------------------------------------------------------------------
# Service contracts
# ---------------------------------------------------------------------------
@dataclass
class Contract:
    cid: int
    customer_key: str
    market: str
    annual_dkk: float
    start: date
    end: date
    origin: str                   # initial | renewal | new
    renewed: Optional[bool] = None
    predecessor: Optional[int] = None


def build_initial_contracts(customers):
    r = rng("contracts")
    contracts = []
    for market in config.MARKETS:
        n, total = config.CONTRACTS[market]
        pool = [c for c in customers if c.market == market and not c.prospect and not c.is_key]
        chosen = []
        while len(chosen) < n:
            c = r.choices(pool, weights=[p.weight + 0.8 for p in pool])[0]
            if c not in chosen:
                chosen.append(c)
        raw = [r.lognormvariate(0, 0.55) * (1 + c.weight / 10) for c in chosen]
        scale = total / sum(raw)
        for c, v in zip(chosen, raw):
            if r.random() < 0.8:
                start, end = date(2025, 1, 1), date(2025, 12, 31)
            else:
                start, end = date(2024, 7, 1), date(2025, 6, 30)
            contracts.append(Contract(len(contracts) + 1, c.key, market, round(v * scale, -3), start, end, "initial"))
    ka = config.KEY_ACCOUNTS["rheinmark"]
    contracts.append(Contract(len(contracts) + 1, "rheinmark", "DE", ka["contract_annual_dkk"],
                              date(2025, 1, 1), date(2025, 12, 31), "initial"))
    return contracts


def successor(c, cid=0):
    """The next 12-month term of a renewed contract, with the price index applied."""
    return Contract(cid, c.customer_key, c.market, round(c.annual_dkk * (1 + config.CONTRACT_PRICE_INDEX), -3),
                    c.end + timedelta(days=1), date(c.end.year + 1, c.end.month, c.end.day), "renewal", predecessor=c.cid)


def h1_billing(c, year):
    """DKK billed Jan-Jun of `year` by one contract term (quarterly in advance)."""
    starts = [add_months(c.start, 3 * q) for q in range(4)]
    return sum(1 for d in starts if d.year == year and d.month <= 6) * round(c.annual_dkk / 4)


def _renew_by_loss_share(contracts, group, share, r):
    target_loss = share * sum(c.annual_dkk for c in group)
    lost = 0.0
    for c in sorted(group, key=lambda c: r.random()):
        if c.customer_key == "rheinmark":
            c.renewed = False
            continue
        if lost + c.annual_dkk * 0.5 < target_loss:
            c.renewed, lost = False, lost + c.annual_dkk
        else:
            c.renewed = True
    for c in group:
        if c.renewed:
            contracts.append(successor(c, len(contracts) + 1))


def _renew_to_billing_target(contracts, group, r):
    """Invariant 1: pick which contracts in `group` renew so that next year's H1
    contract billing lands on DK_CONTRACT_INVARIANT['change'] vs the base year.
    Which customers churn stays random; how much value churns does not."""
    inv = config.DK_CONTRACT_INVARIANT
    # Terms ending between this decision and May next year renew INTO next year's H1:
    # decide them first (normal loss share) so their successors are known.
    early = [c for c in contracts if c.market == inv["market"] and c.renewed is None
             and inv["decision"] < c.end < date(inv["base_year"] + 1, 6, 1)]
    for end in sorted({c.end for c in early}):
        _renew_by_loss_share(contracts, [c for c in early if c.end == end],
                             config.CONTRACT_LOSS_SHARE.get((inv["market"], end), 0.10), r)
    in_group = {c.cid for c in group}
    market = [c for c in contracts if c.market == inv["market"]]
    base = sum(h1_billing(c, inv["base_year"]) for c in market)
    other = sum(h1_billing(c, inv["base_year"] + 1) for c in market if c.cid not in in_group)
    need = base * (1 + inv["change"]) - other
    value = {c.cid: h1_billing(successor(c), inv["base_year"] + 1) for c in group}
    renewed = 0.0
    for c in sorted(group, key=lambda c: r.random()):  # random first pass: who churns is random
        c.renewed = renewed + value[c.cid] / 2 <= need
        renewed += value[c.cid] if c.renewed else 0.0
    # Local search: flip one contract or swap a renewed/lost pair while it brings the total closer.
    for _ in range(200):
        diff = renewed - need
        best, move = abs(diff), None
        for a in group:
            flip = diff + (-value[a.cid] if a.renewed else value[a.cid])
            if abs(flip) < best:
                best, move = abs(flip), (a, None)
            for b in group:
                if a.renewed and not b.renewed and abs(diff - value[a.cid] + value[b.cid]) < best:
                    best, move = abs(diff - value[a.cid] + value[b.cid]), (a, b)
        if move is None:
            break
        a, b = move
        renewed += -value[a.cid] if a.renewed else value[a.cid]
        a.renewed = not a.renewed
        if b is not None:
            b.renewed, renewed = True, renewed + value[b.cid]


def resolve_renewals(contracts):
    """Decide renewal for every contract term ending inside the data window and
    create successor terms. Losses are chosen to hit the planned lost-value share
    (or, for the invariant decision, the planned billing change)."""
    r = rng("renewals")
    inv = config.DK_CONTRACT_INVARIANT
    while True:
        pending = [c for c in contracts if c.renewed is None and c.end <= config.DATA_END]
        if not pending:
            return contracts
        end = min(c.end for c in pending)
        for market in config.MARKETS:
            group = [c for c in pending if c.end == end and c.market == market]
            if not group:
                continue
            if (market, end) == (inv["market"], inv["decision"]):
                _renew_to_billing_target(contracts, group, r)
                for c in group:
                    if c.renewed:
                        contracts.append(successor(c, len(contracts) + 1))
            else:
                _renew_by_loss_share(contracts, group, config.CONTRACT_LOSS_SHARE.get((market, end), 0.10), r)
        for c in pending:
            if c.end == end and c.renewed is None:
                c.renewed = True
