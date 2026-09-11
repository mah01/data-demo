"""
Period parsing and calendar dimensions.

Accepted period strings (inclusive boundaries):
    "2026"                      calendar year
    "2026-H1", "H1 2026"        half year
    "2026-Q2", "Q2 2026"        quarter
    "2026-03"                   month
    "2026-01..2026-08"          month range
    "2025-01-01..2025-06-30"    date range
"""
import calendar
import re
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Period:
    label: str
    start: date
    end: date

    def contains(self, day):
        return day is not None and self.start <= day <= self.end

    def as_dict(self):
        return {"label": self.label, "start": self.start.isoformat(), "end": self.end.isoformat()}


def _month_end(y, m):
    return date(y, m, calendar.monthrange(y, m)[1])


def parse_period(text):
    if isinstance(text, Period):
        return text
    if not text or not isinstance(text, str):
        raise ValueError("period is required, e.g. '2026-H1', '2026-Q2', '2026-03', '2026' or '2025-01-01..2025-06-30'")
    t = text.strip().upper().replace(" ", "")
    if ".." in t:
        a, z = t.split("..", 1)
        start = date.fromisoformat(a) if len(a) == 10 else date(int(a[:4]), int(a[5:7]), 1)
        end = date.fromisoformat(z) if len(z) == 10 else _month_end(int(z[:4]), int(z[5:7]))
        if end < start:
            raise ValueError(f"period end before start: {text}")
        return Period(f"{start.isoformat()}..{end.isoformat()}", start, end)
    m = re.fullmatch(r"(\d{4})-?H([12])|H([12])-?(\d{4})", t)
    if m:
        y, h = (int(m.group(1)), int(m.group(2))) if m.group(1) else (int(m.group(4)), int(m.group(3)))
        return Period(f"{y}-H{h}", date(y, 1 if h == 1 else 7, 1), date(y, 6, 30) if h == 1 else date(y, 12, 31))
    m = re.fullmatch(r"(\d{4})-?Q([1-4])|Q([1-4])-?(\d{4})", t)
    if m:
        y, q = (int(m.group(1)), int(m.group(2))) if m.group(1) else (int(m.group(4)), int(m.group(3)))
        return Period(f"{y}-Q{q}", date(y, 3 * q - 2, 1), _month_end(y, 3 * q))
    m = re.fullmatch(r"(\d{4})-(\d{2})", t)
    if m:
        y, mo = int(m.group(1)), int(m.group(2))
        return Period(f"{y}-{mo:02d}", date(y, mo, 1), _month_end(y, mo))
    m = re.fullmatch(r"(\d{4})", t)
    if m:
        y = int(m.group(1))
        return Period(str(y), date(y, 1, 1), date(y, 12, 31))
    raise ValueError(f"Unrecognised period '{text}'. Use e.g. '2026-H1', 'Q2 2026', '2026-03', '2026', "
                     "'2026-01..2026-08' or '2025-01-01..2025-06-30'.")


def month_of(day):
    return f"{day.year}-{day.month:02d}"


def quarter_of(day):
    return f"{day.year}-Q{(day.month - 1) // 3 + 1}"


def half_of(day):
    return f"{day.year}-H{1 if day.month <= 6 else 2}"


def year_of(day):
    return str(day.year)


CALENDAR_DIMENSIONS = {"month": month_of, "quarter": quarter_of, "half": half_of, "year": year_of}


def coverage_note(period, first, last, system):
    """Warn when a requested period is only partly covered by a system's data."""
    if first is None:
        return None
    if period.start < first or period.end > last:
        return (f"Period {period.label} is only partly covered by {system} data "
                f"({first.isoformat()}..{last.isoformat()}); figures cover the overlap only.")
    return None
