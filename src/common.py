"""Small helpers shared by the generator modules (not used by the validator)."""
import calendar
import csv
import os
import random
import unicodedata
from datetime import date, timedelta
from pathlib import Path

import config

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("NORDFLOW_DATA_DIR", ROOT / "data"))  # env override is used by src/robustness.py


def rng(label):
    """Independent deterministic RNG stream per purpose, so changing one part
    of the generator does not reshuffle every other part."""
    return random.Random(f"{config.SEED}:{label}")


# ---------------------------------------------------------------------------
# Dates
# ---------------------------------------------------------------------------
def month_key(d):
    return f"{d.year}-{d.month:02d}"


def month_start(key):
    y, m = map(int, key.split("-"))
    return date(y, m, 1)


def month_end(key):
    y, m = map(int, key.split("-"))
    return date(y, m, calendar.monthrange(y, m)[1])


def months_between(start, end):
    """Month keys from start to end inclusive (dates)."""
    keys, y, m = [], start.year, start.month
    while (y, m) <= (end.year, end.month):
        keys.append(f"{y}-{m:02d}")
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return keys


DATA_MONTHS = months_between(config.DATA_START, config.DATA_END)


def half_of(d):
    return f"{d.year}H{1 if d.month <= 6 else 2}"


def half_of_key(key):
    return half_of(month_start(key))


def add_months(d, n):
    y, m = d.year + (d.month - 1 + n) // 12, (d.month - 1 + n) % 12 + 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def business_day(r, key, lo=1, hi=None):
    """Random weekday within a month."""
    last = month_end(key).day
    hi = min(hi or last, last)
    for _ in range(20):
        d = month_start(key).replace(day=r.randint(lo, hi))
        if d.weekday() < 5:
            return d
    return month_start(key).replace(day=lo)


def to_weekday(d):
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


def last_banking_day(key):
    d = month_end(key)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d


# ---------------------------------------------------------------------------
# FX
# ---------------------------------------------------------------------------
def _sek_rate(key):
    i = (month_start(key).year - 2024) * 12 + month_start(key).month - 1
    wobble = ((i * 7919) % 13 - 6) * 0.0006
    return round(config.SEK_DKK_START + config.SEK_DKK_MONTHLY_DRIFT * (i - 12) + wobble, 4)


def _eur_rate(key):
    i = month_start(key).month + month_start(key).year
    return round(config.EUR_DKK + ((i * 31) % 7 - 3) * 0.0012, 4)


def fx(currency, key):
    if currency == "DKK":
        return 1.0
    return _eur_rate(key) if currency == "EUR" else _sek_rate(key)


# ---------------------------------------------------------------------------
# Text
# ---------------------------------------------------------------------------
_FOLD = str.maketrans({"ø": "o", "Ø": "O", "æ": "ae", "Æ": "Ae", "å": "aa", "Å": "Aa",
                       "ä": "a", "Ä": "A", "ö": "o", "Ö": "O", "ü": "ue", "Ü": "Ue", "ß": "ss"})


def ascii_fold(s):
    s = s.translate(_FOLD)
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()


def slug(s):
    return "".join(c if c.isalnum() else "-" for c in ascii_fold(s).lower()).strip("-").replace("--", "-")


def weighted_choice(r, items, weights):
    return r.choices(items, weights=weights, k=1)[0]


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------
def write_csv(rel_path, rows, fields):
    path = DATA_DIR / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow({k: _fmt(row.get(k)) for k in fields})
    return len(rows)


def _fmt(v):
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        return f"{v:.2f}"
    if isinstance(v, date):
        return v.isoformat()
    return v
