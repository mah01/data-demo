"""Shared helpers for query operations: grouping, period comparison, result envelopes."""
from datetime import date, datetime

from ..periods import CALENDAR_DIMENSIONS, parse_period

RATIO_SUFFIXES = ("_margin", "win_rate", "_pct", "_share", "margin", "rate")


def is_ratio(name):
    return name.endswith(RATIO_SUFFIXES)


def check_dims(group_by, allowed):
    group_by = list(group_by or [])
    bad = [g for g in group_by if g not in allowed]
    if bad:
        raise ValueError(f"Unknown group_by {bad}. Allowed: {', '.join(allowed)}")
    return group_by


def calendar_dims(date_field):
    return {name: (lambda r, fn=fn: fn(r[date_field]) if r[date_field] else None)
            for name, fn in CALENDAR_DIMENSIONS.items()}


def aggregate(records, group_by, dims, sums, counts_distinct=None):
    """Group records by the chosen dimensions and sum numeric fields.

    Returns a list of dicts: dimension values + summed fields + 'record_count'
    + distinct counts (e.g. invoice_count)."""
    groups = {}
    counts_distinct = counts_distinct or {}
    for r in records:
        key = tuple(dims[g](r) for g in group_by)
        g = groups.get(key)
        if g is None:
            g = groups[key] = {**dict(zip(group_by, key)), **{s: 0.0 for s in sums}, "record_count": 0,
                               "_distinct": {n: set() for n in counts_distinct}}
        for s in sums:
            g[s] += r.get(s) or 0.0
        g["record_count"] += 1
        for n, fn in counts_distinct.items():
            v = fn(r)
            if v is not None:
                g["_distinct"][n].add(v)
    out = []
    for g in groups.values():
        for n, vals in g.pop("_distinct").items():
            g[n] = len(vals)
        out.append(g)
    return out


def ratio(num, den):
    return num / den if den else None


def compare_rows(current, previous, group_by, measures, finish=None):
    """Join current and comparison rows on the group keys and add
    <m>_compare, <m>_change and (for non-ratio measures) <m>_change_pct."""
    key = lambda r: tuple(r.get(g) for g in group_by)
    prev = {key(r): r for r in previous}
    cur = {key(r): r for r in current}
    empty = {m: None if is_ratio(m) else (0 if m.endswith("count") else 0.0) for m in measures}
    out = []
    for k in list(cur) + [k for k in prev if k not in cur]:
        row = dict(cur.get(k) or {**dict(zip(group_by, k)), **empty})
        p = prev.get(k) or empty
        for m in measures:
            a, b = row.get(m), p.get(m)
            row[f"{m}_compare"] = b
            row[f"{m}_change"] = (a - b) if a is not None and b is not None else None
            if not is_ratio(m):
                row[f"{m}_change_pct"] = ((a - b) / abs(b)) if b else None
        out.append(row)
    return out


def sort_limit(rows, sort_by, ascending, limit):
    if sort_by:
        if rows and sort_by not in rows[0]:
            raise ValueError(f"Cannot sort by '{sort_by}'. Available: {', '.join(rows[0])}")
        present = [r for r in rows if r.get(sort_by) is not None]
        missing = [r for r in rows if r.get(sort_by) is None]
        rows = sorted(present, key=lambda r: r[sort_by], reverse=not ascending) + missing
    total = len(rows)
    return (rows[:limit] if limit else rows), total


def periods(period, compare_to):
    return parse_period(period), (parse_period(compare_to) if compare_to else None)


def clean(value):
    """JSON-friendly: ISO dates, rounded floats."""
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items() if not k.startswith("_")}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, float):
        return round(value, 2) if abs(value) >= 100 else round(value, 4)
    if isinstance(value, set):
        return sorted(value)
    return value


def envelope(operation, source, params, rows, *, period=None, compare=None, totals=None, notes=None,
             total_rows=None, currency="DKK"):
    notes = [n for n in (notes or []) if n]
    out = {"operation": operation, "source": source,
           "parameters": {k: v for k, v in params.items() if v not in (None, [], "")},
           "currency": currency}
    if period is not None:
        out["period"] = period.as_dict()
    if compare is not None:
        out["compare_period"] = compare.as_dict()
    out["row_count"] = total_rows if total_rows is not None else len(rows)
    if total_rows is not None and total_rows > len(rows):
        notes.append(f"Showing {len(rows)} of {total_rows} rows; raise 'limit' to see more.")
    out["rows"] = rows
    if totals is not None:
        out["totals"] = totals
    if notes:
        out["notes"] = notes
    return clean(out)
