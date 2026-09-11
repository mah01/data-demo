"""
Generate the complete NordFlow synthetic dataset into ./data

    python3 src/generate.py
"""
import shutil
from datetime import timedelta

import config
import roster
from common import DATA_DIR, DATA_MONTHS, rng, write_csv, fx, month_key
from world import build_products, build_customers, build_initial_contracts, PRODUCT_GROUPS
from gen_crm import CRMGenerator
import crm_render
from gen_erp import ERPGenerator, COUNTRY_DA, CUSTOMER_GROUP, VAT_RATE
from gen_payroll import PayrollGenerator
from gen_ledger import LedgerGenerator


def render_erp(erp, products, ledger):
    r = rng("erp-render")
    customers = [c for c in erp.customers.values() if c.erp_since]
    new = sorted([c for c in customers if c.erp_number is None], key=lambda c: (c.erp_since, c.key))
    number = 70011
    for c in new:
        c.erp_number = number
        number += r.randint(1, 3)
    invoiced = {inv["cust"].key for inv in erp.invoices}
    cust_rows = []
    for c in sorted(customers, key=lambda c: c.erp_number):
        grp = CUSTOMER_GROUP[c.market]
        cust_rows.append({"customer_number": c.erp_number, "name": c.legal_name, "customer_group_number": grp[0],
                          "customer_group_name": grp[1], "country": COUNTRY_DA[c.market], "city": c.city,
                          "currency": config.CURRENCY[c.market], "vat_number": c.vat,
                          "payment_terms": r.choice(["Netto 30 dage", "Netto 30 dage", "Lb. md. + 30 dage", "Netto 14 dage"]),
                          "created_date": c.erp_since, "barred": c.key not in invoiced and c.erp_since.year < 2023})

    prod_rows = [{"product_number": p.number, "name": p.name, "product_group_number": PRODUCT_GROUPS[p.category][0],
                  "product_group_name": PRODUCT_GROUPS[p.category][1], "sales_price_dkk": float(p.list_dkk),
                  "cost_price_dkk": float(p.cost_dkk), "unit": p.unit} for p in products]

    erp.invoices.sort(key=lambda i: (i["date"], i["kind"] == "credit_note", i["cust"].key))
    inv_rows, line_rows = [], []
    for n, inv in enumerate(erp.invoices, start=24871):
        inv["number"] = n
    for inv in erp.invoices:
        c, key = inv["cust"], month_key(inv["date"])
        rate = fx(inv["currency"], key)
        net = round(sum(ln["net"] for ln in inv["lines"]), 2)
        vat = round(net * VAT_RATE[c.market], 2)
        credited = inv.get("credits")
        inv_rows.append({"invoice_number": inv["number"], "invoice_date": inv["date"],
                         "due_date": inv["date"] + timedelta(days=30), "customer_number": c.erp_number,
                         "customer_name": c.legal_name, "currency": inv["currency"], "exchange_rate": rate,
                         "net_amount": net, "vat_amount": vat, "gross_amount": round(net + vat, 2),
                         "net_amount_dkk": round(net * rate, 2), "document_type": inv["kind"],
                         "your_reference": inv["ref"], "credited_invoice_number": credited["number"] if credited else None})
        for i, ln in enumerate(inv["lines"], start=1):
            p = ln["product"]
            line_rows.append({"invoice_number": inv["number"], "line_number": i, "product_number": p.number,
                              "description": ln["desc"], "quantity": ln["qty"], "unit": p.unit,
                              "unit_price": float(ln["unit_price"]), "discount_pct": round(ln["disc"] * 100, 1),
                              "net_amount": ln["net"], "unit_cost_dkk": ln["unit_cost"],
                              "total_cost_dkk": round(ln["qty"] * ln["unit_cost"], 2)})
    fx_rows = [{"month": k, "currency": cur, "rate_to_dkk": fx(cur, k)} for k in DATA_MONTHS for cur in ("EUR", "SEK")]
    acc_rows = [{"account_number": 1010, "name": "Salg af varer og ydelser", "type": "revenue (from invoices)"},
                {"account_number": 1310, "name": "Vareforbrug", "type": "cost of sales (from invoice lines)"}]
    acc_rows += [{"account_number": n, "name": name, "type": t} for n, name, t in roster.ACCOUNTS]

    write_csv("erp/customers.csv", cust_rows, list(cust_rows[0]))
    write_csv("erp/products.csv", prod_rows, list(prod_rows[0]))
    write_csv("erp/invoices.csv", inv_rows, list(inv_rows[0]))
    write_csv("erp/invoice_lines.csv", line_rows, list(line_rows[0]))
    write_csv("erp/exchange_rates.csv", fx_rows, list(fx_rows[0]))
    write_csv("erp/accounts.csv", acc_rows, list(acc_rows[0]))
    write_csv("erp/ledger_entries.csv", ledger.entries,
              ["entry_number", "date", "voucher", "account_number", "department", "amount_dkk", "text"])
    return len(inv_rows), len(line_rows)


def render_mappings(crm, uid):
    r = rng("mappings")
    emp_rows = []
    notes = {"dk_se1": "CRM display name 'JP Hansen'", "de_julia": "CRM uses married name Fischer-Lang",
             "de_deniz": "Spelling differs (Yılmaz / Yilmaz)", "dk_se2": "CRM name without ø",
             "se_anna": "CRM name without ö", "de_cm": "Payroll lists middle initial"}
    for row in roster.ROSTER:
        if row[12]:
            emp_rows.append({"payroll_employee_id": row[1], "crm_user_id": uid[row[0]],
                             "match_basis": "manual (HR)" if row[0] in notes else "name + start date",
                             "note": notes.get(row[0])})
    emp_rows.append({"payroll_employee_id": None, "crm_user_id": uid["crm_heinz"], "match_basis": "none",
                     "note": "Left Oct 2024 - not in payroll extract"})
    emp_rows.append({"payroll_employee_id": None, "crm_user_id": uid["crm_system"], "match_basis": "none",
                     "note": "System/integration user"})

    cust_rows = []
    smalls = sorted([c for c in crm.customers.values() if c.crm_id and c.erp_number and not c.is_key and not c.prospect],
                    key=lambda c: c.weight)[:40]
    unmapped = {c.key for c in r.sample(smalls, 3)}
    for c in crm.customers.values():
        if not (c.crm_id and c.erp_number) or c.key in unmapped:
            continue
        if c.crm_name == c.legal_name:
            method = "exact_name"
        elif c.vat and r.random() < 0.35:
            method = "vat_number"
        elif c.crm_name.lower().replace(" ", "") in c.legal_name.lower().replace(" ", ""):
            method = "name_contains"
        else:
            method = "manual"
        cust_rows.append({"crm_company_id": c.crm_id, "erp_customer_number": c.erp_number, "match_method": method,
                          "note": None})
        if c.crm_dup_id:
            cust_rows.append({"crm_company_id": c.crm_dup_id, "erp_customer_number": c.erp_number,
                              "match_method": "manual", "note": "Duplicate CRM record"})

    vm = []
    for code, crm_label, erp_label in (("DK", "Denmark", "Danmark"), ("SE", "Sweden", "Sverige"), ("DE", "Germany", "Tyskland")):
        vm += [{"domain": "market", "system": "payroll", "field": "employees.country", "source_value": code, "canonical_value": code},
               {"domain": "market", "system": "crm", "field": "companies.country / deals.market", "source_value": crm_label, "canonical_value": code},
               {"domain": "market", "system": "crm", "field": "deals.deal_currency (fallback)", "source_value": config.CURRENCY[code], "canonical_value": code},
               {"domain": "market", "system": "erp", "field": "customers.country", "source_value": erp_label, "canonical_value": code}]
    for cat, crm_label in (("Equipment", "Pumps & Systems"), ("Components", "Spare Parts Agreement"), ("Service", "Service Contract")):
        vm += [{"domain": "product_category", "system": "erp", "field": "products.product_group_number",
                "source_value": PRODUCT_GROUPS[cat][0], "canonical_value": cat},
               {"domain": "product_category", "system": "crm", "field": "deals.product_category",
                "source_value": crm_label, "canonical_value": cat}]
    write_csv("mappings/employee_crm_user.csv", emp_rows, list(emp_rows[0]))
    write_csv("mappings/crm_company_erp_customer.csv", cust_rows, list(cust_rows[0]))
    write_csv("mappings/value_mappings.csv", vm, list(vm[0]))


def main():
    if DATA_DIR.exists():
        for sub in ("crm", "erp", "payroll", "mappings"):
            shutil.rmtree(DATA_DIR / sub, ignore_errors=True)
    products = build_products()
    customers = build_customers()
    contracts = build_initial_contracts(customers)

    crm = CRMGenerator(customers, contracts).run()
    uid, users = crm_render.build_users(crm)
    companies = crm_render.build_companies(crm, uid)
    deals = crm_render.build_deal_rows(crm, uid)
    acts = crm_render.build_activities(crm, uid)
    hist = crm_render.build_property_history(crm, uid)

    erp = ERPGenerator(customers, products, crm).run()
    payroll = PayrollGenerator(crm).run()
    ledger = LedgerGenerator(erp, payroll, users).run()

    write_csv("crm/owners.csv", users, list(users[0]))
    write_csv("crm/companies.csv", companies, list(companies[0]))
    write_csv("crm/deals.csv", deals, list(deals[0]))
    write_csv("crm/activities.csv", acts, ["activity_id", "timestamp", "type", "owner_id", "company_id", "deal_id", "subject", "body"])
    write_csv("crm/property_history.csv", hist, list(hist[0]))
    write_csv("payroll/employees.csv", payroll.employee_rows(), list(payroll.employee_rows()[0]))
    write_csv("payroll/payroll_entries.csv", payroll.rows,
              [k for k in payroll.rows[0] if k not in ("emp_key", "country")])
    n_inv, n_lines = render_erp(erp, products, ledger)
    render_mappings(crm, uid)

    print("NordFlow synthetic data generated in ./data")
    print(f"  CRM:      {len(users)} owners, {len(companies)} companies, {len(deals)} deals, {len(acts)} activities, {len(hist)} history rows")
    print(f"  ERP:      {n_inv} invoices, {n_lines} lines, {len(ledger.entries)} ledger entries")
    print(f"  Payroll:  {len(payroll.rows)} payroll entries")
    print(f"  Calibration: salary scale {payroll.scale:.3f}, recurring opex scale {ledger.scale:.3f}")
    for s in erp.shortfalls:
        print(f"  WARNING: fixed revenue exceeded plan for {s[:3]} by {-s[3] / 1e6:.2f}m")


if __name__ == "__main__":
    main()
