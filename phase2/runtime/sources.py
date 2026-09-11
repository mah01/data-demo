"""
Low-level, read-only access to one system's CSV export folder.

Each adapter owns exactly one folder (data/erp, data/crm, data/payroll,
data/mappings). Nothing here knows about other systems.
"""
import csv
import os
import unicodedata
from datetime import date, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def default_data_dir():
    """Runtime data root: $NORDFLOW_DATA_DIR or <repo>/data."""
    return Path(os.environ.get("NORDFLOW_DATA_DIR", REPO_ROOT / "data"))


class CsvFolder:
    """Read-only, cached CSV tables of a single system folder."""

    def __init__(self, folder):
        self.folder = Path(folder)
        if not self.folder.is_dir():
            raise FileNotFoundError(f"System export folder not found: {self.folder}")
        self._cache = {}

    def table(self, name):
        if name not in self._cache:
            path = self.folder / f"{name}.csv"
            with open(path, newline="", encoding="utf-8") as f:
                self._cache[name] = [dict(r) for r in csv.DictReader(f)]
        return self._cache[name]

    def tables(self):
        return sorted(p.stem for p in self.folder.glob("*.csv"))


# ---------------------------------------------------------------------------
# Typed parsing of CSV strings (blank -> None)
# ---------------------------------------------------------------------------
def s(v):
    return v if v not in (None, "") else None


def f(v):
    return float(v) if v not in (None, "") else None


def i(v):
    return int(float(v)) if v not in (None, "") else None


def d(v):
    return date.fromisoformat(v[:10]) if v not in (None, "") else None


def dt(v):
    return datetime.fromisoformat(v) if v not in (None, "") else None


def b(v):
    return None if v in (None, "") else v.strip().lower() in ("true", "1", "yes")


_FOLD = str.maketrans({"ø": "o", "æ": "ae", "å": "aa", "ä": "a", "ö": "o", "ü": "u", "ß": "ss", "ı": "i"})


def fold(text):
    """Case- and accent-insensitive form used for name search."""
    text = (text or "").lower().translate(_FOLD)
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
