"""Identity/mapping primitives against the fixture dataset."""
from .conftest import rows


def test_crm_company_to_erp(rt):
    res = {r["crm_company_id"]: r for r in rows(rt.links.identity_crm_companies_to_erp(
        ["cmp_00002", "cmp_00003", "cmp_00004", "cmp_99999"]))}
    assert res["cmp_00002"]["status"] == "mapped" and res["cmp_00002"]["links"][0]["erp_customer_number"] == "20002"
    assert res["cmp_00003"]["links"][0]["note"] == "Duplicate CRM record"
    assert res["cmp_00002"]["crm_name"] == "Beta Chemie" and res["cmp_00002"]["links"][0]["erp_name"] == "Beta Chemie GmbH"
    assert res["cmp_00004"]["status"] == "not_mapped" and res["cmp_00004"]["links"] == []
    assert res["cmp_99999"]["status"] == "unknown_id"


def test_erp_customer_to_crm(rt):
    beta = rows(rt.links.identity_erp_customers_to_crm(["20002"]))[0]
    assert {l["crm_company_id"] for l in beta["links"]} == {"cmp_00002", "cmp_00003"}   # many-to-one
    gamma = rows(rt.links.identity_erp_customers_to_crm([30003]))[0]                   # int accepted
    assert gamma["status"] == "not_mapped" and gamma["erp_market"] == "SE"


def test_crm_user_to_employee(rt):
    res = {r["crm_user_id"]: r for r in rows(rt.links.identity_crm_users_to_employees(["usr_000002", "usr_000003"]))}
    link = res["usr_000002"]["links"][0]
    assert link["payroll_employee_id"] == "DE0002" and link["employee_name"] == "Bernhard Schulz"
    assert res["usr_000002"]["crm_user_name"] == "Bernd Schulz" and link["employment_start"] == "2026-01-15"
    assert res["usr_000003"]["status"] == "not_mapped" and "Left before" in res["usr_000003"]["note"]


def test_employee_to_crm_user(rt):
    res = {r["payroll_employee_id"]: r for r in rows(rt.links.identity_employees_to_crm_users(["DK0001", "SE0003"]))}
    assert res["DK0001"]["links"][0]["crm_user_id"] == "usr_000001"
    assert res["SE0003"]["status"] == "not_mapped"


def test_find_company_across_systems(rt):
    beta = rows(rt.links.identity_find_company("beta"))
    assert len(beta) == 1 and beta[0]["erp_customer_number"] == "20002" and len(beta[0]["crm"]) == 2
    delta = rows(rt.links.identity_find_company("delta"))
    assert delta[0]["erp_customer_number"] is None and delta[0]["crm"][0]["crm_company_id"] == "cmp_00004"
    assert rows(rt.links.identity_find_company("ALPHA vand a/s"))[0]["crm"][0]["crm_company_id"] == "cmp_00001"


def test_find_person_across_systems(rt):
    bernd = rows(rt.links.identity_find_person("bernd"))       # CRM name; payroll says Bernhard
    assert bernd[0]["payroll_employee_id"] == "DE0002"
    carl = rows(rt.links.identity_find_person("carl"))
    assert carl[0]["payroll_employee_id"] is None and "Left before" in carl[0]["crm_users"][0]["note"]
