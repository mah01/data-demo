"""
Story parameters for the NordFlow A/S synthetic dataset.

Everything that shapes the business story lives here. The generator modules
read these values; the validator does NOT (it reads ground_truth.json and the
raw generated records only).

Money is DKK unless stated otherwise. Revenue targets are in DKK millions.
"""
import os
from datetime import date

SEED = int(os.environ.get("NORDFLOW_SEED", "4217"))  # env override is used by src/robustness.py

DATA_START = date(2025, 1, 1)
DATA_END = date(2026, 8, 31)
CRM_HISTORY_START = date(2024, 9, 1)  # CRM holds some history before the reporting window

MARKETS = ["DK", "SE", "DE"]
CURRENCY = {"DK": "DKK", "SE": "SEK", "DE": "EUR"}
CATEGORIES = ["Equipment", "Components", "Service"]

# Month-of-year seasonality for transactional revenue (summer dip, strong Q4).
SEASONALITY = {1: 0.88, 2: 0.92, 3: 1.06, 4: 1.00, 5: 1.04, 6: 1.10,
               7: 0.72, 8: 0.90, 9: 1.08, 10: 1.10, 11: 1.12, 12: 1.08}

# ---------------------------------------------------------------------------
# Revenue plan: (market, category) -> DKK m per half year.
# 2026H2 is only used for Jul-Aug 2026.
# ---------------------------------------------------------------------------
HALVES = ["2025H1", "2025H2", "2026H1", "2026H2"]
REVENUE_TARGETS = {
    ("DK", "Equipment"):  [22.00, 26.50, 29.20, 30.50],
    ("DK", "Components"): [11.00, 11.60, 11.46, 11.90],
    ("DK", "Service"):    [14.00, 13.40, 10.80, 10.50],
    ("SE", "Equipment"):  [8.00, 8.60, 8.10, 8.70],
    ("SE", "Components"): [5.00, 5.30, 5.10, 5.40],
    ("SE", "Service"):    [4.00, 4.10, 4.10, 4.20],
    ("DE", "Equipment"):  [11.00, 11.80, 10.50, 10.90],
    ("DE", "Components"): [6.50, 6.20, 5.44, 5.40],
    ("DE", "Service"):    [4.50, 4.40, 4.30, 4.30],
}
MONTHLY_TARGET_NOISE = 0.025  # +/- relative noise on each month x market x category cell

# Average product cost as share of list price, per category.
COST_RATIO = {"Equipment": 0.67, "Components": 0.55, "Service": 0.39}

# Mean discount on run-rate (non-CRM) invoice lines. Overrides by (market, category, half).
DEFAULT_DISCOUNT = {"Equipment": 0.07, "Components": 0.05, "Service": 0.02}
DISCOUNT_OVERRIDES = {
    ("DK", "Equipment", "2026H1"): 0.11,   # bigger, more competitive project sales in DK
    ("DK", "Equipment", "2026H2"): 0.11,
    ("DE", "Equipment", "2025H2"): 0.09,
    ("DE", "Equipment", "2026H1"): 0.14,   # price pressure in DE
    ("DE", "Equipment", "2026H2"): 0.14,
}

# FX (units of DKK per 1 unit of currency). EUR is pegged; SEK drifts slightly.
EUR_DKK = 7.4600
SEK_DKK_START = 0.6520
SEK_DKK_MONTHLY_DRIFT = 0.0011
# Fixed price lists per currency (list price in DKK divided by these).
PRICE_LIST_FX = {"DKK": 1.0, "EUR": 7.45, "SEK": 0.66}

# ---------------------------------------------------------------------------
# CRM
# ---------------------------------------------------------------------------
# New (non-renewal) deals created per month, by market and half.
DEAL_RATE = {
    "DK": {"2024H2": 14, "2025H1": 15, "2025H2": 15, "2026H1": 16, "2026H2": 16},
    "SE": {"2024H2": 8, "2025H1": 8, "2025H2": 8, "2026H1": 8, "2026H2": 8},
    "DE": {"2024H2": 15, "2025H1": 16, "2025H2": 18, "2026H1": 21.7, "2026H2": 22},
}
# Win rate (by count, non-renewal deals) by close half.
WIN_RATE = {
    "DK": {"2024H2": 0.34, "2025H1": 0.34, "2025H2": 0.34, "2026H1": 0.35, "2026H2": 0.34},
    "SE": {"2024H2": 0.30, "2025H1": 0.30, "2025H2": 0.30, "2026H1": 0.30, "2026H2": 0.30},
    "DE": {"2024H2": 0.32, "2025H1": 0.31, "2025H2": 0.26, "2026H1": 0.19, "2026H2": 0.18},
}
# New pipeline created (sum of deal amounts, DKK, non-renewal) the generator calibrates to.
PIPELINE_TARGET = {
    ("DK", "2025H1"): 33.0e6, ("DK", "2026H1"): 37.5e6,
    ("SE", "2025H1"): 11.0e6, ("SE", "2026H1"): 11.3e6,
    ("DE", "2025H1"): 26.0e6, ("DE", "2026H1"): 35.1e6,  # +35%
}
DEAL_CATEGORY_MIX = {"Equipment": 0.72, "Components": 0.13, "Service": 0.15}
# Danish sellers focus on equipment projects from 2025 (commission plan rewards equipment).
DEAL_CATEGORY_MIX_DK_FROM_2025 = {"Equipment": 0.82, "Components": 0.12, "Service": 0.06}
DEAL_MEDIAN_DKK = {"Equipment": 230_000, "Components": 110_000, "Service": 150_000}
DEAL_MAX_MULTIPLE = 3.0  # cap on single-deal size vs. median
DEAL_DISCOUNT = {"default": 0.07, ("DK", "2026"): 0.11, ("DE", "2025H2"): 0.10, ("DE", "2026"): 0.17}
COMMISSION_RATE = {"DK": 0.015, "SE": 0.015, "DE": 0.02}

LOSS_REASONS = {
    "normal": [("Price too high", 25), ("Lost to competitor", 25), ("No decision / project postponed", 22),
               ("Budget", 10), ("Technical fit", 8), ("Timing", 10)],
    "de_2026": [("Price too high", 26), ("Lost to competitor", 22), ("No decision / project postponed", 16),
                ("Not qualified", 18), ("No response", 12), ("Technical fit", 6)],
    "renewal": [("Customer insourced maintenance", 30), ("Price too high", 30), ("Lost to competitor", 25),
                ("Budget cuts", 15)],
}

# ---------------------------------------------------------------------------
# Service contracts (annual, invoiced quarterly in advance)
# ---------------------------------------------------------------------------
CONTRACTS = {
    # market: (number of contracts active 1 Jan 2025, target total annual value DKK)
    "DK": (52, 11.6e6),
    "SE": (10, 1.6e6),
    "DE": (11, 2.0e6),  # plus the Rheinmark key account contract
}
# Share of contract value NOT renewed at each term end (by market, end date).
CONTRACT_LOSS_SHARE = {
    ("DK", date(2025, 6, 30)): 0.25, ("DK", date(2025, 12, 31)): 0.33, ("DK", date(2026, 6, 30)): 0.20,
    ("SE", date(2025, 6, 30)): 0.08, ("SE", date(2025, 12, 31)): 0.08, ("SE", date(2026, 6, 30)): 0.08,
    ("DE", date(2025, 6, 30)): 0.10, ("DE", date(2025, 12, 31)): 0.10, ("DE", date(2026, 6, 30)): 0.10,
}
CONTRACT_PRICE_INDEX = 0.03  # uplift on renewal

# ---------------------------------------------------------------------------
# German key accounts (the "reassignment" story)
# ---------------------------------------------------------------------------
KEY_ACCOUNTS = {
    "rheinmark": {
        "erp_name": "Rheinmark Chemie GmbH & Co. KG", "crm_name": "Rheinmark Chemie",
        "city": "Ludwigshafen", "industry": "CHEMICALS", "domain": "rheinmark-chemie.de",
        # run-rate (non-deal, non-contract) revenue DKK per half at 2025 level
        "components_per_half": 1.90e6, "service_adhoc_per_half": 0.35e6, "floor": 0.55,
        "contract_annual_dkk": 1.00e6,
        "owner_before": "de_stefan", "owner_after": "de_lukas", "reassigned_on": date(2025, 9, 15),
    },
    "brandauer": {
        "erp_name": "Brandauer Papierwerke AG", "crm_name": "Brandauer Papier",
        "city": "Aschaffenburg", "industry": "PAPER_FOREST_PRODUCTS", "domain": "brandauer-papier.de",
        "components_per_half": 2.00e6, "service_adhoc_per_half": 0.45e6, "floor": 0.30,
        "contract_annual_dkk": None,
        "owner_before": "de_stefan", "owner_after": "de_jana", "reassigned_on": date(2025, 10, 6),
    },
}
# Progress of the key-account decline by month (0 = 2025 level, 1 = account's floor reached).
# Monthly purchase multiplier = 1 - (1 - floor) * progress.
KEY_ACCOUNT_TREND = {"2025-11": 0.35, "2025-12": 0.60, "2026-01": 0.85}
# Hand-written key account deals: (account, name, category, amount EUR, created, closed, outcome, owner, loss reason)
KEY_ACCOUNT_DEALS = [
    ("rheinmark", "Kühlwasserpumpen Linie 3", "Equipment", 62_000, date(2024, 11, 20), date(2025, 2, 14), "won", "de_stefan", None),
    ("rheinmark", "Dosierpumpen Erweiterung", "Equipment", 28_000, date(2025, 3, 10), date(2025, 5, 22), "won", "de_stefan", None),
    ("rheinmark", "Pumpentausch Tanklager Nord", "Equipment", 55_000, date(2025, 11, 12), date(2026, 2, 20), "lost", "de_lukas", "Lost to competitor"),
    ("rheinmark", "Ersatzteil-Rahmenvertrag 2026", "Components", 105_000, date(2025, 11, 28), date(2026, 1, 30), "lost", "de_lukas", "Price too high"),
    ("brandauer", "Stoffpumpen PM2", "Equipment", 48_000, date(2025, 1, 20), date(2025, 4, 8), "won", "de_stefan", None),
    ("brandauer", "Ersatzteile Rahmen 2026", "Components", 90_000, date(2025, 11, 3), date(2026, 1, 22), "lost", "de_jana", "Lost to competitor"),
    ("brandauer", "Vakuumpumpe PM3", "Equipment", 26_000, date(2026, 1, 12), date(2026, 3, 18), "won", "de_jana", None),
]
# Rheinmark service contract renewal (created, closed) - lost.
RHEINMARK_RENEWAL = (date(2025, 10, 1), date(2025, 12, 9), "Lost to competitor")

# ---------------------------------------------------------------------------
# Scenario invariants: story-critical outcomes enforced by construction (not
# left to random draws), so they hold for any seed. Verified by validate.py
# and src/robustness.py.
# ---------------------------------------------------------------------------
# 1. Danish service-contract billing, H1 2026 vs H1 2025. The end-2025 renewal
#    decisions are chosen to hit this after new contracts and mid-year renewals.
DK_CONTRACT_INVARIANT = {"market": "DK", "decision": date(2025, 12, 31), "base_year": 2025, "change": -0.25}
# 2. Win rate of the German expansion hires (count, deals closed in the half).
#    Veterans get the remainder, so the overall German rate in WIN_RATE is unchanged.
DE_NEW_REP_WIN_RATE = {"2025H2": 0.15, "2026H1": 0.12, "2026H2": 0.12}
# 3. No non-key German customer may win more than this much equipment (DKK)
#    within any 12-month window, so one-off projects cannot outrank the key accounts.
DE_OTHER_CUSTOMER_MAX_EQUIPMENT_WON_12M = 0.8e6
# 4. German won value (non-renewal deals closed in the half) vs the base half: more
#    pipeline, fewer and smaller wins. Winners are swapped within each rep stratum
#    (win counts unchanged) until the value lands on target.
DE_WON_VALUE_INVARIANT = {"half": "2026H1", "base_half": "2025H1", "change": -0.25}
