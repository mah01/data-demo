"""Render CRM generator state into HubSpot-style export tables."""
from datetime import date, datetime, time, timedelta

import config
import roster
from common import rng, months_between, business_day, month_start
from gen_crm import CRM_CATEGORY, MARKET_LABEL, PIPELINE, OPEN_STAGES

INDUSTRY_OPTIONAL = 0.82

KEY_ACCOUNT_NOTES = [
    # date, account, owner, type, subject, body
    (date(2025, 6, 12), "rheinmark", "de_stefan", "MEETING", "Quartalsgespräch Rheinmark",
     "Very satisfied with service response times. Tank farm pump replacement planned for 2026. Dr. Vogt wants to extend the service agreement scope."),
    (date(2025, 9, 17), "rheinmark", "de_stefan", "NOTE", "Übergabe an Lukas Hoffmann",
     "Handover as part of DACH territory re-cut. Key contacts: Dr. Vogt (maintenance), Fr. Albers (purchasing). Service renewal due in Q4."),
    (date(2025, 10, 8), "rheinmark", "de_lukas", "MEETING", "Intro meeting Rheinmark",
     "First site visit. Dr. Vogt asked why Stefan no longer covers the site; wants continuity on the service agreement."),
    (date(2025, 11, 5), "rheinmark", "de_lukas", "CALL", "Servicevertrag 2026",
     "Rheinmark has an alternative offer from a regional service provider incl. 24h response. Asking for 12% price reduction."),
    (date(2025, 12, 9), "rheinmark", "de_lukas", "NOTE", "Renewal lost",
     "Rheinmark will not renew the service agreement for 2026. Competitor bundled service and spare parts. Slow response in Q3 cited."),
    (date(2026, 2, 20), "rheinmark", "de_lukas", "NOTE", "Tanklager project lost",
     "Tank farm pump replacement awarded to the provider that took over the service contract."),
    (date(2025, 6, 26), "brandauer", "de_stefan", "MEETING", "Jahresgespräch Brandauer",
     "Stable demand for PM2/PM3 spare parts. Hr. Kessler (purchasing) happy with delivery times."),
    (date(2025, 10, 14), "brandauer", "de_jana", "MEETING", "Intro Brandauer",
     "Purchasing (Hr. Kessler) had not been informed about the change of contact person. Relationship needs rebuilding."),
    (date(2025, 12, 2), "brandauer", "de_jana", "EMAIL", "Ersatzteile Rahmenvertrag 2026 - Angebot", "Quote sent for 2026 spare parts framework."),
    (date(2026, 1, 22), "brandauer", "de_jana", "NOTE", "Spare parts moved to local distributor",
     "Brandauer moved PM2/PM3 spare parts to a local distributor with consignment stock. Keeping us for specialist pumps only."),
    (date(2026, 3, 18), "brandauer", "de_jana", "NOTE", "Won PM3 vacuum pump", "Small order. Hr. Kessler open to a quarterly review again."),
]

SUBJECTS = {
    "CALL": ["Opfølgning på tilbud", "Follow-up call", "Status on quote", "Telefonat Angebot", "Uppföljning offert", "Discovery call"],
    "EMAIL": ["Tilbud fremsendt", "Quote sent", "Angebot versendet", "Technical datasheet", "Offert skickad", "Revised quote"],
    "MEETING": ["Besøg på anlæg", "Site visit", "Vor-Ort-Termin", "Kundmöte", "Technical workshop", "Quarterly review"],
    "NOTE": ["Intern note", "Note", "Notiz", "Anteckning"],
}
NOTE_BODIES = {
    "normal": ["Customer comparing offers, decision expected next month.", "Budget confirmed for this year.",
               "Needs updated pump curve before approval.", "Purchasing wants better payment terms.",
               "Technical approval received; waiting for purchasing.", "", ""],
    "de_new": ["Cold call - no current need, follow up in Q3.", "Lead from WasserTech Messe; budget unclear.",
               "Contact is not decision maker.", "Asked for price indication only.",
               "Competitor already installed; low chance.", "Sent brochure, no reply yet.", ""],
    "renewal_lost_dk": ["Customer is taking maintenance in-house with own technicians.",
                        "Customer found cheaper service partner.", "Budget cut - service reduced to ad hoc calls."],
}


RENEWAL_LOSS_NOTES = {  # salesperson note written when a Danish renewal is lost (v1.1: consistent with loss_reason)
    "Customer insourced maintenance": "Customer is taking maintenance in-house with own technicians.",
    "Price too high": "Customer found a cheaper service partner.",
    "Lost to competitor": "Customer moved the service agreement to a competitor.",
    "Budget cuts": "Budget cut - service reduced to ad hoc calls.",
}


def _ts(r, d):
    return datetime.combine(d, time(r.randint(7, 16), r.choice([0, 5, 10, 15, 20, 30, 40, 45, 50])))


def build_users(gen):
    r = rng("crm-users")
    uid, rows, used = {}, [], set()

    def new_id():
        while True:
            n = f"usr_{r.randint(100000, 999999)}"
            if n not in used:
                used.add(n)
                return n
    for row in roster.ROSTER:
        key, start, end, crm = row[0], row[7], row[8], row[12]
        if not crm:
            continue
        first, last, email, team = crm
        created = date(2021, 1, 12) + timedelta(days=r.randint(0, 40)) if start < date(2021, 1, 12) else start + timedelta(days=r.randint(0, 3))
        archived = end + timedelta(days=r.randint(1, 10)) if end else None
        uid[key] = new_id()
        rows.append({"user_id": uid[key], "first_name": first, "last_name": last, "email": email, "team": team,
                     "active": archived is None or archived > config.DATA_END, "created_at": created, "archived_at": archived})
    for first, last, email, team, active, created, archived in roster.CRM_ONLY_USERS:
        k = "crm_heinz" if first == "Heinz" else "crm_system"
        uid[k] = new_id()
        rows.append({"user_id": uid[k], "first_name": first, "last_name": last, "email": email, "team": team,
                     "active": active, "created_at": created, "archived_at": archived})
    return uid, rows


def converted_prospects(gen):
    conv = {}
    for d in gen.deals:
        c = gen.customers[d.customer_key]
        if c.prospect and d.outcome == "won" and d.close_date <= config.DATA_END:
            conv[c.key] = min(conv.get(c.key, d.close_date), d.close_date)
    return conv


def build_companies(gen, uid):
    r = rng("crm-companies")
    conv = converted_prospects(gen)
    has_open = {d.customer_key for d in gen.deals if d.outcome == "open"}
    rows = []
    for c in gen.customers.values():
        if not c.crm_id:
            continue
        if c.crm_created is None:  # unworked lead
            c.crm_created = date(2024, 3, 1) + timedelta(days=r.randint(0, 900))
            if c.crm_created > config.DATA_END:
                c.crm_created = config.DATA_END - timedelta(days=r.randint(5, 200))
            if r.random() < 0.6:
                pool = gen.sellers(c.market, max(c.crm_created, config.CRM_HISTORY_START))
                gen.owner_tl[c.key] = [(c.crm_created, r.choice(pool), None, "IMPORT")]
        if not c.prospect or c.key in conv:
            stage = "customer"
        elif c.key in has_open or c.key in gen.prospect_claims:
            stage = "opportunity" if c.key in has_open else "lead"
        else:
            stage = r.choice(["lead", "lead", "subscriber"])
        owner = gen.owner_tl.get(c.key, [(None, None)])[-1][1]
        size = int(min(5000, 15 * (1 + c.weight) ** 1.6 * r.uniform(0.6, 1.5)))
        rows.append({"company_id": c.crm_id, "name": c.crm_name,
                     "domain": c.domain if c.domain and r.random() < 0.8 else None,
                     "country": MARKET_LABEL[c.market] if r.random() > 0.03 else None,
                     "city": c.city if r.random() > 0.12 else None,
                     "industry": c.industry if r.random() < INDUSTRY_OPTIONAL else None,
                     "lifecycle_stage": stage, "owner_id": uid.get(owner),
                     "created_at": c.crm_created, "num_employees": size if r.random() < 0.6 else None})
        if c.crm_dup_id:
            created = date(2025, r.randint(2, 11), r.randint(1, 28))
            rows.append({"company_id": c.crm_dup_id, "name": c.crm_duplicate_name, "domain": None,
                         "country": MARKET_LABEL[c.market], "city": None, "industry": None,
                         "lifecycle_stage": "lead", "owner_id": uid[r.choice(roster.SELLERS["DK"][:4])],
                         "created_at": created, "num_employees": None})
    rows.sort(key=lambda x: x["created_at"])
    return rows


def build_deal_rows(gen, uid):
    r = rng("crm-deal-rows")
    rows = []
    for d in gen.deals:
        c = gen.customers[d.customer_key]
        expected = d.close_date
        if d.outcome == "open":
            span = max(1, (d.close_date - d.created).days)
            frac = (config.DATA_END - d.created).days / span
            stage = OPEN_STAGES[min(3, int(frac * 4))]
            if r.random() < 0.12:  # slipped: expected close date already passed
                expected = config.DATA_END - timedelta(days=r.randint(3, 45))
        else:
            stage = "Closed Won" if d.outcome == "won" else "Closed Lost"
        renewal = d.deal_type == "Renewal"
        rows.append({
            "deal_id": d.deal_id, "deal_name": d.name,
            "pipeline": "Service Renewals" if renewal else PIPELINE[d.market], "stage": stage,
            "deal_type": d.deal_type,
            "company_id": c.crm_dup_id if d.on_duplicate else c.crm_id,
            "owner_id": uid.get(d.owner),
            "market": MARKET_LABEL[d.market] if renewal or r.random() > 0.04 else None,
            "product_category": CRM_CATEGORY[d.category] if renewal or r.random() > 0.05 else None,
            "amount": float(d.amount_local), "deal_currency": d.currency,
            "amount_company_currency": d.amount_dkk,
            "discount_pct": round(d.discount * 100, 1) if d.discount is not None else None,
            "created_at": _ts(r, d.created), "expected_close_date": expected,
            "closed_at": _ts(r, d.close_date) if d.outcome != "open" else None,
            "outcome": d.outcome, "loss_reason": d.loss_reason,
        })
    return rows


def build_activities(gen, uid):
    r = rng("crm-activities")
    acts = []

    def add(d, owner, company_id, typ, deal_id=None, subject=None, body=None):
        acts.append({"timestamp": _ts(r, d), "type": typ, "owner_id": uid.get(owner), "company_id": company_id,
                     "deal_id": deal_id, "subject": subject or r.choice(SUBJECTS[typ]), "body": body})

    for d in gen.deals:
        c = gen.customers[d.customer_key]
        cid = c.crm_dup_id if d.on_duplicate else c.crm_id
        end = min(d.close_date, config.DATA_END)
        n = {"won": r.randint(4, 9), "lost": r.randint(2, 6), "open": r.randint(1, 5)}[d.outcome]
        if c.is_key and d.created >= config.KEY_ACCOUNTS[c.key]["reassigned_on"]:
            n = r.randint(1, 3)  # key accounts after the handover: thin coverage by the new owner
        span = max(1, (end - d.created).days)
        de_new = d.market == "DE" and d.owner in roster.NEW_DE_REPS
        for _ in range(n):
            typ = r.choices(["CALL", "EMAIL", "MEETING", "NOTE"], weights=[35, 35, 18, 12])[0]
            body = None
            if typ in ("NOTE", "MEETING"):
                body = r.choice(NOTE_BODIES["de_new" if de_new else "normal"])
            # v1.1: clamp to the deal's window (v1.0 let a deal created on the cutoff day log an activity a day later)
            add(min(d.created + timedelta(days=r.randint(0, span)), end), d.owner, cid, typ, d.deal_id, body=body or None)
        if d.deal_type == "Renewal" and d.outcome == "lost" and d.market == "DK":
            r.choice(NOTE_BODIES["renewal_lost_dk"])  # v1.0 draw kept so the random stream, and every other record, is unchanged
            # v1.1: the note now follows the recorded loss reason (v1.0 picked it independently, so they could contradict)
            add(d.close_date, d.owner, cid, "NOTE", d.deal_id, "Fornyelse tabt",
                RENEWAL_LOSS_NOTES.get(d.loss_reason, "Renewal declined; the customer gave no specific reason."))

    for c in gen.customers.values():
        if not c.crm_id or c.prospect:
            continue
        for key in months_between(config.CRM_HISTORY_START, config.DATA_END):
            day = business_day(r, key)
            owner = gen.owner_at(c.key, day)
            if not owner or not gen.active(owner, day):
                continue
            if c.is_key:
                ka = config.KEY_ACCOUNTS[c.key]
                n = r.randint(4, 6) if day < ka["reassigned_on"] else r.randint(0, 1)
            else:
                n = 1 if r.random() < min(0.5, 0.05 + 0.03 * c.weight) else 0
            for _ in range(n):
                add(business_day(r, key), owner, c.crm_id, r.choices(["CALL", "EMAIL", "MEETING"], weights=[40, 40, 20])[0],
                    subject=r.choice(["Account follow-up", "Opfølgning", "Kundenbesuch", "Kvartalsmøde", "Quarterly review", "Uppföljning"]))
    for d, acc, owner, typ, subject, body in KEY_ACCOUNT_NOTES:
        add(d, owner, gen.customers[acc].crm_id, typ, subject=subject, body=body)

    acts.sort(key=lambda a: a["timestamp"])
    nid = 51_000_000_000
    for a in acts:
        nid += r.randint(50, 90_000)
        a["activity_id"] = str(nid)
    return acts


def build_property_history(gen, uid):
    r = rng("crm-history")
    rows = []
    for ckey, tl in gen.owner_tl.items():
        c = gen.customers[ckey]
        for (_, before, *_), (when, after, by, source) in zip(tl, tl[1:]):
            rows.append({"object_type": "company", "object_id": c.crm_id, "property": "hubspot_owner_id",
                         "value_before": uid.get(before), "value_after": uid.get(after),
                         "changed_at": _ts(r, when), "source": source, "changed_by_user_id": uid.get(by)})
    for ckey, when in converted_prospects(gen).items():
        rows.append({"object_type": "company", "object_id": gen.customers[ckey].crm_id, "property": "lifecyclestage",
                     "value_before": "opportunity", "value_after": "customer", "changed_at": _ts(r, when),
                     "source": "WORKFLOW", "changed_by_user_id": uid["crm_system"]})
    rows.sort(key=lambda x: x["changed_at"])
    return rows
