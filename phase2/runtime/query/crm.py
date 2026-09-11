"""Generic sales operations over the CRM adapter. Deal values in DKK (CRM company currency)."""
from ..periods import coverage_note, parse_period
from ..sources import fold
from .common import aggregate, calendar_dims, check_dims, compare_rows, envelope, periods, ratio, sort_limit

DEAL_FIELDS = ["deal_id", "deal_name", "deal_type", "pipeline", "stage", "outcome", "company_id", "company_name",
               "owner_id", "owner_name", "market", "market_source", "category", "amount", "deal_currency", "value_dkk",
               "discount_pct", "created_at", "expected_close_date", "closed_at", "loss_reason"]
NOT_RECORDED = "(not recorded)"


class SalesQueries:
    def __init__(self, crm, semantics):
        self.crm, self.sem = crm, semantics
        self.base_dims = {"market": lambda r: r["market"], "market_source": lambda r: r["market_source"],
                          "owner": lambda r: r["owner_id"], "deal_type": lambda r: r["deal_type"],
                          "category": lambda r: r["category"], "pipeline": lambda r: r["pipeline"],
                          "stage": lambda r: r["stage"], "company": lambda r: r["company_id"]}

    # ------------------------------------------------------------------ helpers
    def _note(self, p):
        return coverage_note(p, *self.crm.coverage(), "CRM")

    def _dims(self, date_field):
        return {**self.base_dims, **calendar_dims(date_field)}

    def _filter(self, market=None, owner_ids=None, deal_type=None, product_category=None, include_renewals=False,
                company_id=None):
        mkt, cat = self.sem.normalize_market(market), self.sem.normalize_category(product_category)
        owners = set(owner_ids) if owner_ids else None
        return [x for x in self.crm.deals
                if (include_renewals or not x["is_renewal"] or deal_type == "Renewal")
                and (mkt is None or x["market"] == mkt) and (owners is None or x["owner_id"] in owners)
                and (deal_type is None or x["deal_type"] == deal_type) and (cat is None or x["category"] == cat)
                and (company_id is None or x["company_id"] == company_id)]

    def _decorate(self, rows, group_by):
        for r in rows:
            if "owner" in group_by:
                r["owner_name"] = self.crm.user_name(r["owner"])
            if "company" in group_by:
                r["company_name"] = self.crm.companies.get(r["company"], {}).get("name")
        return rows

    # ------------------------------------------------------------------ pipeline
    def _pipeline_rows(self, deals, p, basis, group_by):
        if basis == "created":
            sel = [x for x in deals if p.contains(x["created_date"])]
        else:
            sel = [x for x in deals if x["created_date"] <= p.end and (x["closed_date"] is None or x["closed_date"] > p.end)]
        rows = aggregate(sel, group_by, self._dims("created_date"), ["value_dkk"])
        for r in rows:
            r["deal_count"] = r.pop("record_count")
            r["avg_deal_value_dkk"] = ratio(r["value_dkk"], r["deal_count"])
        return self._decorate(rows, group_by)

    def crm_pipeline(self, period: str, basis: str = "created", group_by: list[str] | None = None,
                     market: str | None = None, owner_ids: list[str] | None = None, deal_type: str | None = None,
                     product_category: str | None = None, include_renewals: bool = False,
                     compare_to: str | None = None, sort_by: str | None = "value_dkk", ascending: bool = False,
                     limit: int = 100) -> dict:
        """Deal count and DKK value. basis='created': deals created in the period (new pipeline);
        basis='open_at_end': deals open at the period end. group_by any of: market, market_source, owner,
        deal_type, category, pipeline, stage, company, month, quarter, half, year (calendar = created date).
        Renewals excluded unless include_renewals=true or deal_type='Renewal'."""
        if basis not in ("created", "open_at_end"):
            raise ValueError("basis must be 'created' or 'open_at_end'")
        dims = self._dims("created_date")
        group_by = check_dims(group_by, dims)
        p, c = periods(period, compare_to)
        deals = self._filter(market, owner_ids, deal_type, product_category, include_renewals)
        rows, totals = self._pipeline_rows(deals, p, basis, group_by), self._pipeline_rows(deals, p, basis, [])
        measures = ["deal_count", "value_dkk", "avg_deal_value_dkk"]
        if c:
            rows = compare_rows(rows, self._pipeline_rows(deals, c, basis, group_by), group_by, measures)
            totals = compare_rows(totals, self._pipeline_rows(deals, c, basis, []), [], measures)
        rows, n = sort_limit(rows, sort_by, ascending, limit)
        notes = [self._note(p), c and self._note(c)]
        if basis == "open_at_end":
            notes.append("Open-at-date is reconstructed from created/closed dates; the stage at that date is not recorded.")
        return envelope("crm_pipeline", "crm", {"period": period, "basis": basis, "group_by": group_by,
                        "market": market, "owner_ids": owner_ids, "deal_type": deal_type,
                        "product_category": product_category, "include_renewals": include_renewals,
                        "compare_to": compare_to}, rows, period=p, compare=c,
                        totals=totals[0] if totals else None, total_rows=n, notes=notes)

    # ------------------------------------------------------------------ win rate
    def _closed(self, deals, p):
        out = []
        for x in deals:
            if x["outcome"] in ("won", "lost") and p.contains(x["closed_date"]):
                won = x["outcome"] == "won"
                out.append({**x, "won_count": 1.0 if won else 0.0, "lost_count": 0.0 if won else 1.0,
                            "won_value_dkk": x["value_dkk"] if won else 0.0,
                            "lost_value_dkk": 0.0 if won else x["value_dkk"]})
        return out

    def _win_rows(self, deals, p, group_by):
        rows = aggregate(self._closed(deals, p), group_by, self._dims("closed_date"),
                         ["won_count", "lost_count", "won_value_dkk", "lost_value_dkk"])
        for r in rows:
            r.pop("record_count")
            r["won_count"], r["lost_count"] = int(r["won_count"]), int(r["lost_count"])
            r["closed_count"] = r["won_count"] + r["lost_count"]
            r["win_rate"] = ratio(r["won_count"], r["closed_count"])
            r["value_win_rate"] = ratio(r["won_value_dkk"], r["won_value_dkk"] + r["lost_value_dkk"])
            r["avg_won_value_dkk"] = ratio(r["won_value_dkk"], r["won_count"])
            r["avg_lost_value_dkk"] = ratio(r["lost_value_dkk"], r["lost_count"])
        return self._decorate(rows, group_by)

    def crm_win_rate(self, period: str, group_by: list[str] | None = None, market: str | None = None,
                     owner_ids: list[str] | None = None, deal_type: str | None = None,
                     product_category: str | None = None, include_renewals: bool = False,
                     compare_to: str | None = None, sort_by: str | None = "closed_count", ascending: bool = False,
                     limit: int = 100) -> dict:
        """Won/lost counts and values for deals CLOSED in the period: win_rate (by count), value_win_rate,
        won/lost value and average won/lost deal value. group_by as crm_pipeline (calendar = close date).
        owner_ids restricts to deals owned by those CRM users."""
        dims = self._dims("closed_date")
        group_by = check_dims(group_by, dims)
        p, c = periods(period, compare_to)
        deals = self._filter(market, owner_ids, deal_type, product_category, include_renewals)
        rows, totals = self._win_rows(deals, p, group_by), self._win_rows(deals, p, [])
        measures = ["closed_count", "won_count", "win_rate", "won_value_dkk", "lost_value_dkk", "value_win_rate",
                    "avg_won_value_dkk"]
        if c:
            rows = compare_rows(rows, self._win_rows(deals, c, group_by), group_by, measures)
            totals = compare_rows(totals, self._win_rows(deals, c, []), [], measures)
        rows, n = sort_limit(rows, sort_by, ascending, limit)
        return envelope("crm_win_rate", "crm", {"period": period, "group_by": group_by, "market": market,
                        "owner_ids": owner_ids, "deal_type": deal_type, "product_category": product_category,
                        "include_renewals": include_renewals, "compare_to": compare_to}, rows, period=p, compare=c,
                        totals=totals[0] if totals else None, total_rows=n, notes=[self._note(p), c and self._note(c)])

    def crm_loss_reasons(self, period: str, market: str | None = None, owner_ids: list[str] | None = None,
                         deal_type: str | None = None, product_category: str | None = None,
                         include_renewals: bool = False) -> dict:
        """Lost deals closed in the period by loss reason: count, DKK value and share of lost deals.
        Blank reasons are reported as '(not recorded)'."""
        p = parse_period(period)
        lost = [x for x in self._closed(self._filter(market, owner_ids, deal_type, product_category, include_renewals), p)
                if x["outcome"] == "lost"]
        rows = aggregate(lost, ["reason"], {"reason": lambda r: r["loss_reason"] or NOT_RECORDED}, ["value_dkk"])
        for r in rows:
            r["loss_reason"], r["lost_count"] = r.pop("reason"), r.pop("record_count")
            r["share_of_lost"] = ratio(r["lost_count"], len(lost))
            r["lost_value_dkk"] = r.pop("value_dkk")
        rows, n = sort_limit(rows, "lost_count", False, None)
        return envelope("crm_loss_reasons", "crm", {"period": period, "market": market, "owner_ids": owner_ids,
                        "deal_type": deal_type, "product_category": product_category,
                        "include_renewals": include_renewals}, rows, period=p,
                        totals={"lost_count": len(lost), "lost_value_dkk": sum(x["value_dkk"] for x in lost)},
                        notes=[self._note(p)])

    # ------------------------------------------------------------------ records
    def crm_deals(self, period: str | None = None, date_field: str = "created", market: str | None = None,
                  owner_ids: list[str] | None = None, company_id: str | None = None, outcome: str | None = None,
                  stage: str | None = None, deal_type: str | None = None, product_category: str | None = None,
                  name_contains: str | None = None, min_value_dkk: float | None = None,
                  sort_by: str | None = "created_at", ascending: bool = False, limit: int = 50) -> dict:
        """Deal records. period applies to date_field: 'created', 'closed' or 'expected_close'.
        outcome: won | lost | open. Includes resolved market and its source (deal.market / company.country /
        deal.currency)."""
        field = {"created": "created_date", "closed": "closed_date", "expected_close": "expected_close_date"}.get(date_field)
        if field is None:
            raise ValueError("date_field must be 'created', 'closed' or 'expected_close'")
        p = parse_period(period) if period else None
        deals = self._filter(market, owner_ids, deal_type, product_category, include_renewals=True, company_id=company_id)
        rows = [{k: x[k] for k in DEAL_FIELDS} for x in deals
                if (p is None or p.contains(x[field])) and (outcome is None or x["outcome"] == outcome)
                and (stage is None or x["stage"] == stage)
                and (name_contains is None or fold(name_contains) in fold(x["deal_name"]))
                and (min_value_dkk is None or (x["value_dkk"] or 0) >= min_value_dkk)]
        rows, n = sort_limit(rows, sort_by, ascending, limit)
        return envelope("crm_deals", "crm", {"period": period, "date_field": date_field, "market": market,
                        "owner_ids": owner_ids, "company_id": company_id, "outcome": outcome, "stage": stage,
                        "deal_type": deal_type, "product_category": product_category, "name_contains": name_contains,
                        "min_value_dkk": min_value_dkk}, rows, period=p, total_rows=n)

    def crm_renewals(self, period: str, market: str | None = None, outcome: str | None = None,
                     limit: int = 100) -> dict:
        """Service-contract renewal deals CLOSED in the period: counts and DKK values won/lost, lost value share,
        plus the renewal deals themselves."""
        p = parse_period(period)
        closed = self._closed(self._filter(market, deal_type="Renewal"), p)
        won = [x for x in closed if x["outcome"] == "won"]
        lost = [x for x in closed if x["outcome"] == "lost"]
        totals = {"closed_count": len(closed), "won_count": len(won), "lost_count": len(lost),
                  "renewal_rate": ratio(len(won), len(closed)),
                  "won_value_dkk": sum(x["value_dkk"] for x in won), "lost_value_dkk": sum(x["value_dkk"] for x in lost),
                  "lost_value_share": ratio(sum(x["value_dkk"] for x in lost), sum(x["value_dkk"] for x in closed))}
        rows = [{k: x[k] for k in DEAL_FIELDS} for x in closed if outcome is None or x["outcome"] == outcome]
        rows, n = sort_limit(rows, "value_dkk", False, limit)
        return envelope("crm_renewals", "crm", {"period": period, "market": market, "outcome": outcome}, rows,
                        period=p, totals=totals, total_rows=n, notes=[self._note(p)])

    def crm_find_companies(self, query: str | None = None, company_id: str | None = None,
                           market: str | None = None, lifecycle_stage: str | None = None,
                           owner_id: str | None = None, limit: int = 20) -> dict:
        """CRM company records by id or (accent/case-insensitive) name search, with current owner."""
        mkt = self.sem.normalize_market(market)
        words = fold(query).split() if query else []
        rows = [c for c in self.crm.companies.values() if (company_id is None or c["company_id"] == company_id)
                and (mkt is None or c["market"] == mkt) and (lifecycle_stage is None or c["lifecycle_stage"] == lifecycle_stage)
                and (owner_id is None or c["owner_id"] == owner_id) and all(w in fold(c["name"]) for w in words)]
        rows, n = sort_limit(rows, "name", True, limit)
        return envelope("crm_find_companies", "crm", {"query": query, "company_id": company_id, "market": market,
                        "lifecycle_stage": lifecycle_stage, "owner_id": owner_id}, rows, total_rows=n)

    def _activities(self, period, company_id, deal_id, owner_ids, activity_type, market=None):
        p = parse_period(period) if period else None
        owners = set(owner_ids) if owner_ids else None
        mkt = self.sem.normalize_market(market)
        return p, [a for a in self.crm.activities if (p is None or p.contains(a["date"]))
                   and (company_id is None or a["company_id"] == company_id) and (deal_id is None or a["deal_id"] == deal_id)
                   and (owners is None or a["owner_id"] in owners) and (activity_type is None or a["type"] == activity_type)
                   and (mkt is None or self.crm.companies.get(a["company_id"], {}).get("market") == mkt)]

    def crm_activities(self, company_id: str | None = None, deal_id: str | None = None,
                       owner_ids: list[str] | None = None, period: str | None = None,
                       activity_type: str | None = None, text_contains: str | None = None, limit: int = 50) -> dict:
        """Logged activities (calls, emails, meetings, notes) with subject and note body, newest first."""
        p, acts = self._activities(period, company_id, deal_id, owner_ids, activity_type)
        if text_contains:
            acts = [a for a in acts if fold(text_contains) in fold(f"{a['subject']} {a['body']}")]
        rows, n = sort_limit(acts, "timestamp", False, limit)
        return envelope("crm_activities", "crm", {"company_id": company_id, "deal_id": deal_id, "owner_ids": owner_ids,
                        "period": period, "activity_type": activity_type, "text_contains": text_contains}, rows,
                        period=p, total_rows=n)

    def crm_activity_summary(self, period: str, group_by: list[str] | None = None, company_id: str | None = None,
                             owner_ids: list[str] | None = None, market: str | None = None,
                             activity_type: str | None = None) -> dict:
        """Activity counts grouped by any of: month, quarter, half, year, type, owner, company, market
        (market = the company's CRM country). Default group_by: month."""
        dims = {"type": lambda a: a["type"], "owner": lambda a: a["owner_id"], "company": lambda a: a["company_id"],
                "market": lambda a: self.crm.companies.get(a["company_id"], {}).get("market"), **calendar_dims("date")}
        group_by = check_dims(group_by or ["month"], dims)
        p, acts = self._activities(period, company_id, None, owner_ids, activity_type, market)
        rows = aggregate(acts, group_by, dims, [])
        for r in rows:
            r["activity_count"] = r.pop("record_count")
        rows = self._decorate(rows, group_by)
        rows, n = sort_limit(rows, group_by[0] if group_by else None, True, None)
        return envelope("crm_activity_summary", "crm", {"period": period, "group_by": group_by, "company_id": company_id,
                        "owner_ids": owner_ids, "market": market, "activity_type": activity_type}, rows, period=p,
                        totals={"activity_count": len(acts)}, total_rows=n, notes=[self._note(p)])

    def crm_owner_history(self, company_id: str | None = None, object_id: str | None = None,
                          period: str | None = None, property: str | None = "hubspot_owner_id",
                          owner_id: str | None = None, limit: int = 100) -> dict:
        """CRM property change history (default: owner changes), with user names. owner_id matches either the
        previous or the new owner."""
        p = parse_period(period) if period else None
        target = company_id or object_id
        rows = [dict(h, object_name=self.crm.companies.get(h["object_id"], {}).get("name"))
                for h in self.crm.property_history if (target is None or h["object_id"] == target)
                and (p is None or p.contains(h["date"])) and (property is None or h["property"] == property)
                and (owner_id is None or owner_id in (h["value_before"], h["value_after"]))]
        rows, n = sort_limit(rows, "changed_at", True, limit)
        return envelope("crm_owner_history", "crm", {"company_id": company_id, "object_id": object_id,
                        "period": period, "property": property, "owner_id": owner_id}, rows, period=p, total_rows=n)

    def crm_users(self, team: str | None = None, active: bool | None = None, query: str | None = None) -> dict:
        """CRM users (deal/company owners) with team, active flag and archive date."""
        words = fold(query).split() if query else []
        rows = [u for u in self.crm.users.values() if (team is None or u["team"] == team)
                and (active is None or u["active"] == active) and all(w in fold(u["full_name"]) for w in words)]
        rows, n = sort_limit(rows, "full_name", True, None)
        return envelope("crm_users", "crm", {"team": team, "active": active, "query": query}, rows, total_rows=n)
