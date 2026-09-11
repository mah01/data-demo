"""
Employee roster and payroll / operating-cost parameters.

Base salaries are monthly, in local currency, BEFORE calibration. The payroll
generator applies one scale factor to all base salaries so that H1 2025
employer cost lands on the planned level; 2026 then follows from the story
(raises, German hires, commissions, bonuses).
"""
from datetime import date

D = date

# key, employee_id, first, last, country, department, title, start, end, base, weekly_hours, bonus_pct
# crm: None (no CRM seat) or (crm_first, crm_last, crm_email, team)
ROSTER = [
    # --- Denmark: management & admin -------------------------------------------------
    ("dk_ceo", "DK0047", "Henrik", "Vestergaard", "DK", "Management", "CEO", D(2016, 3, 1), None, 112000, 37, 0.15,
     ("Henrik", "Vestergaard", "hv@nordflow.dk", "Management")),
    ("dk_cfo", "DK0112", "Camilla", "Frost", "DK", "Management", "CFO", D(2019, 8, 1), None, 88000, 37, 0.10,
     ("Camilla", "Frost", "cfr@nordflow.dk", "Management")),
    ("dk_coo", "DK0083", "Jesper", "Holm", "DK", "Management", "COO", D(2018, 1, 15), None, 82000, 37, 0.10, None),
    ("dk_controller", "DK0131", "Louise", "Dam", "DK", "Finance & Admin", "Financial Controller", D(2021, 2, 1), None, 52000, 37, 0.05, None),
    ("dk_accountant", "DK0154", "Anders", "Kjær", "DK", "Finance & Admin", "Accountant", D(2022, 9, 1), None, 40000, 37, 0.0, None),
    ("dk_hr", "DK0142", "Mette", "Bruun", "DK", "Finance & Admin", "HR & Payroll Specialist", D(2021, 11, 1), None, 41000, 37, 0.0, None),
    ("dk_office", "DK0061", "Pia", "Lund", "DK", "Finance & Admin", "Office Manager", D(2014, 5, 1), None, 35000, 32, 0.0, None),
    # --- Denmark: sales & customer service -------------------------------------------
    ("dk_salesdir", "DK0095", "Søren", "Mikkelsen", "DK", "Sales", "Sales Director Nordics", D(2018, 10, 1), None, 70000, 37, 0.08,
     ("Søren", "Mikkelsen", "smi@nordflow.dk", "Sales DK")),
    ("dk_kam1", "DK0102", "Rasmus", "Winther", "DK", "Sales", "Key Account Manager", D(2019, 3, 1), None, 50000, 37, 0.0,
     ("Rasmus", "Winther", "rwi@nordflow.dk", "Sales DK")),
    ("dk_se1", "DK0120", "Jens Peter", "Hansen", "DK", "Sales", "Sales Engineer", D(2020, 1, 6), None, 47000, 37, 0.0,
     ("JP", "Hansen", "jph@nordflow.dk", "Sales DK")),
    ("dk_se2", "DK0137", "Katrine", "Møller", "DK", "Sales", "Sales Engineer", D(2021, 4, 1), None, 46000, 37, 0.0,
     ("Katrine", "Moller", "kmo@nordflow.dk", "Sales DK")),
    ("dk_se3", "DK0158", "Thomas", "Bech", "DK", "Sales", "Sales Engineer", D(2023, 2, 1), None, 44500, 37, 0.0,
     ("Thomas", "Bech", "tbe@nordflow.dk", "Sales DK")),
    ("dk_servsales", "DK0109", "Line", "Østergaard", "DK", "Sales", "Service Sales Manager", D(2019, 6, 1), None, 48000, 37, 0.0,
     ("Line", "Østergaard", "los@nordflow.dk", "Service Sales")),
    ("dk_is1", "DK0126", "Maria", "Nielsen", "DK", "Customer Service", "Inside Sales Coordinator", D(2020, 8, 1), None, 35500, 37, 0.0,
     ("Maria", "Nielsen", "mni@nordflow.dk", "Customer Service")),
    ("dk_is2", "DK0149", "Kasper", "Toft", "DK", "Customer Service", "Inside Sales", D(2022, 3, 1), None, 34000, 37, 0.0,
     ("Kasper", "Toft", "kto@nordflow.dk", "Customer Service")),
    ("dk_order", "DK0071", "Signe", "Poulsen", "DK", "Customer Service", "Order Handler", D(2015, 9, 1), None, 29000, 30, 0.0, None),
    # --- Denmark: service technicians ------------------------------------------------
    ("dk_tech1", "DK0034", "Brian", "Jensen", "DK", "Service", "Lead Service Technician", D(2012, 4, 1), None, 45000, 37, 0.0, None),
    ("dk_tech2", "DK0058", "Michael", "Larsen", "DK", "Service", "Service Technician", D(2014, 1, 1), None, 41500, 37, 0.0, None),
    ("dk_tech3", "DK0066", "Kim", "Andersen", "DK", "Service", "Service Technician", D(2015, 3, 1), None, 41000, 37, 0.0, None),
    ("dk_tech4", "DK0118", "Nikolaj", "Friis", "DK", "Service", "Service Technician", D(2020, 5, 1), D(2025, 9, 30), 39500, 37, 0.0, None),
    ("dk_tech5", "DK0089", "Martin", "Skov", "DK", "Service", "Service Technician", D(2018, 8, 1), None, 40500, 37, 0.0, None),
    ("dk_tech6", "DK0077", "Peter", "Dalgaard", "DK", "Service", "Service Technician", D(2016, 9, 1), None, 41000, 37, 0.0, None),
    ("dk_tech7", "DK0145", "Lars", "Iversen", "DK", "Service", "Service Technician", D(2022, 1, 3), None, 39000, 37, 0.0, None),
    ("dk_tech8", "DK0161", "Jonas", "Krogh", "DK", "Service", "Service Technician", D(2023, 6, 1), None, 38500, 37, 0.0, None),
    ("dk_tech9", "DK0172", "Emil", "Thorsen", "DK", "Service", "Service Technician", D(2025, 11, 3), None, 39500, 37, 0.0, None),
    # --- Denmark: operations, marketing, IT ------------------------------------------
    ("dk_opsmgr", "DK0052", "Carsten", "Munk", "DK", "Operations", "Operations Manager", D(2013, 2, 1), None, 54000, 37, 0.05, None),
    ("dk_wh1", "DK0063", "Ole", "Svendsen", "DK", "Operations", "Warehouse Lead", D(2014, 6, 1), None, 37000, 37, 0.0, None),
    ("dk_wh2", "DK0098", "Dennis", "Kristensen", "DK", "Operations", "Warehouse Operator", D(2018, 11, 1), None, 33000, 37, 0.0, None),
    ("dk_wh3", "DK0151", "Ahmad", "Rahimi", "DK", "Operations", "Warehouse Operator", D(2022, 5, 1), None, 32500, 37, 0.0, None),
    ("dk_purch", "DK0115", "Tina", "Mortensen", "DK", "Operations", "Purchaser", D(2020, 3, 1), None, 40000, 37, 0.0, None),
    ("dk_logi", "DK0133", "Frederik", "Laursen", "DK", "Operations", "Logistics Coordinator", D(2021, 3, 1), None, 38000, 37, 0.0, None),
    ("dk_mktmgr", "DK0124", "Julie", "Sand", "DK", "Marketing", "Marketing Manager", D(2020, 6, 1), None, 49000, 37, 0.05,
     ("Julie", "Sand", "jsa@nordflow.dk", "Marketing")),
    ("dk_mkt", "DK0166", "Oliver", "Berg", "DK", "Marketing", "Marketing Coordinator", D(2024, 2, 1), None, 37000, 37, 0.0,
     ("Oliver", "Berg", "obe@nordflow.dk", "Marketing")),
    ("dk_it", "DK0107", "Mads", "Eskildsen", "DK", "IT", "IT Manager", D(2019, 5, 1), None, 53000, 37, 0.05, None),
    # --- Sweden (SEK) ----------------------------------------------------------------
    ("se_cm", "SE0012", "Erik", "Lindqvist", "SE", "Sales", "Country Manager Sweden", D(2017, 9, 1), None, 66000, 40, 0.08,
     ("Erik", "Lindqvist", "erik.lindqvist@nordflow.se", "Sales SE")),
    ("se_anna", "SE0019", "Anna", "Bergström", "SE", "Sales", "Sales Engineer", D(2019, 2, 1), None, 49000, 40, 0.0,
     ("Anna", "Bergstrom", "anna.bergstrom@nordflow.se", "Sales SE")),
    ("se_johan", "SE0023", "Johan", "Nyberg", "SE", "Sales", "Sales Engineer", D(2020, 4, 1), D(2025, 3, 31), 48000, 40, 0.0,
     ("Johan", "Nyberg", "johan.nyberg@nordflow.se", "Sales SE")),
    ("se_oskar", "SE0031", "Oskar", "Wallin", "SE", "Sales", "Sales Engineer", D(2022, 8, 15), None, 47000, 40, 0.0,
     ("Oskar", "Wallin", "oskar.wallin@nordflow.se", "Sales SE")),
    ("se_sara", "SE0036", "Sara", "Holmgren", "SE", "Sales", "Sales Engineer", D(2025, 5, 12), None, 50000, 40, 0.0,
     ("Sara", "Holmgren", "sara.holmgren@nordflow.se", "Sales SE")),
    ("se_tech1", "SE0015", "Mikael", "Sandberg", "SE", "Service", "Service Technician", D(2018, 3, 1), None, 38000, 40, 0.0, None),
    ("se_tech2", "SE0027", "Fredrik", "Åkesson", "SE", "Service", "Service Technician", D(2021, 10, 1), None, 37000, 40, 0.0, None),
    # --- Germany (EUR) ---------------------------------------------------------------
    ("de_cm", "DE0204", "Andreas M.", "Keller", "DE", "Sales", "Country Manager Germany", D(2017, 1, 1), None, 9000, 40, 0.08,
     ("Andreas", "Keller", "a.keller@nordflow.de", "Sales DACH")),
    ("de_stefan", "DE0211", "Stefan", "Brenner", "DE", "Sales", "Business Development Manager Süd", D(2016, 5, 1), None, 7200, 40, 0.0,
     ("Stefan", "Brenner", "s.brenner@nordflow.de", "Sales DACH")),
    ("de_monika", "DE0217", "Monika", "Schulz", "DE", "Sales", "Sales Engineer", D(2018, 4, 1), None, 6100, 40, 0.0,
     ("Monika", "Schulz", "m.schulz@nordflow.de", "Sales DACH")),
    ("de_tobias", "DE0223", "Tobias", "Wagner", "DE", "Sales", "Sales Engineer", D(2019, 7, 1), None, 5900, 40, 0.0,
     ("Tobias", "Wagner", "t.wagner@nordflow.de", "Sales DACH")),
    ("de_julia", "DE0229", "Julia", "Fischer", "DE", "Sales", "Sales Engineer", D(2020, 9, 1), None, 5800, 40, 0.0,
     ("Julia", "Fischer-Lang", "j.fischer-lang@nordflow.de", "Sales DACH")),
    ("de_markus", "DE0236", "Markus", "Becker", "DE", "Sales", "Sales Engineer", D(2021, 2, 1), None, 5700, 40, 0.0,
     ("Markus", "Becker", "m.becker@nordflow.de", "Sales DACH")),
    ("de_sabine", "DE0241", "Sabine", "Koch", "DE", "Sales", "Inside Sales", D(2021, 11, 1), None, 4500, 40, 0.0,
     ("Sabine", "Koch", "s.koch@nordflow.de", "Sales DACH")),
    ("de_florian", "DE0247", "Florian", "Braun", "DE", "Sales", "Sales Engineer", D(2023, 3, 1), None, 5600, 40, 0.0,
     ("Florian", "Braun", "f.braun@nordflow.de", "Sales DACH")),
    ("de_lukas", "DE0258", "Lukas", "Hoffmann", "DE", "Sales", "Key Account Manager", D(2025, 9, 1), None, 6200, 40, 0.0,
     ("Lukas", "Hoffmann", "l.hoffmann@nordflow.de", "Sales DACH")),
    ("de_jana", "DE0261", "Jana", "Richter", "DE", "Sales", "Key Account Manager", D(2025, 10, 1), None, 6100, 40, 0.0,
     ("Jana", "Richter", "j.richter@nordflow.de", "Sales DACH")),
    ("de_timo", "DE0264", "Timo", "Neumann", "DE", "Sales", "Sales Engineer", D(2025, 11, 3), None, 5700, 40, 0.0,
     ("Timo", "Neumann", "t.neumann@nordflow.de", "Sales DACH")),
    ("de_deniz", "DE0270", "Deniz", "Yılmaz", "DE", "Sales", "Sales Engineer", D(2026, 1, 5), None, 5800, 40, 0.0,
     ("Deniz", "Yilmaz", "d.yilmaz@nordflow.de", "Sales DACH")),
    ("de_tech1", "DE0213", "Uwe", "Schmitt", "DE", "Service", "Servicetechniker", D(2015, 6, 1), None, 4300, 40, 0.0, None),
    ("de_tech2", "DE0226", "Dirk", "Lehmann", "DE", "Service", "Servicetechniker", D(2019, 1, 1), None, 4200, 40, 0.0, None),
    ("de_tech3", "DE0233", "Patrick", "Zimmermann", "DE", "Service", "Servicetechniker", D(2020, 11, 1), None, 4100, 40, 0.0, None),
]

# CRM-only users (no payroll record in the extract).
CRM_ONLY_USERS = [
    # first, last, email, team, active, created, archived
    ("Heinz", "Albrecht", "h.albrecht@nordflow.de", "Sales DACH", False, D(2019, 3, 4), D(2024, 10, 31)),
    ("ERP", "Integration", "erp-sync@nordflow.dk", "System", True, D(2021, 1, 12), None),
]

# Roles that sell (own deals / accounts) per market.
SELLERS = {
    "DK": ["dk_kam1", "dk_se1", "dk_se2", "dk_se3", "dk_salesdir"],
    "SE": ["se_cm", "se_anna", "se_johan", "se_oskar", "se_sara"],
    "DE": ["de_cm", "de_stefan", "de_monika", "de_tobias", "de_julia", "de_markus", "de_sabine", "de_florian",
           "de_lukas", "de_jana", "de_timo", "de_deniz"],
}
SERVICE_RENEWAL_OWNER = {"DK": "dk_servsales", "SE": "se_cm", "DE": None}  # DE: account owner
NEW_DE_REPS = ["de_lukas", "de_jana", "de_timo", "de_deniz"]

# ---------------------------------------------------------------------------
# Payroll mechanics
# ---------------------------------------------------------------------------
PERSONNEL_TARGET_H1_2025 = 14.80e6  # employer cost, DKK; calibration anchor
GENERAL_RAISE = {"DK": 0.034, "SE": 0.031, "DE": 0.038}  # effective 1 Jan 2026
INDIVIDUAL_RAISES = [("de_stefan", "2025-10", 0.05), ("dk_controller", "2025-07", 0.04), ("se_anna", "2025-09", 0.03)]
BONUS_MONTH = 3
BONUS_FACTOR = {2025: 1.00, 2026: 0.80}  # paid in March for the prior year's performance
DE_RAMP_GUARANTEE_EUR = 750  # minimum monthly commission for new German reps, first 6 months
SOCIAL = {
    "DK": {"pension_pct": 0.08, "social_fixed": 99.0, "social_pct": 0.006},
    "SE": {"pension_pct": 0.045, "social_fixed": 0.0, "social_pct": 0.3142},
    "DE": {"pension_pct": 0.0, "social_fixed": 0.0, "social_pct": 0.205, "social_cap": 8050.0, "social_uncapped_pct": 0.012},
}

# ---------------------------------------------------------------------------
# Operating costs (ERP ledger). Monthly DKK amounts before calibration.
# ---------------------------------------------------------------------------
ACCOUNTS = [
    (2210, "Lønninger", "personnel"), (2220, "Pension, arbejdsgiver", "personnel"),
    (2230, "Sociale omkostninger", "personnel"),
    (2710, "Husleje", "opex"), (2720, "El, vand og varme", "opex"), (2810, "Autodrift", "opex"),
    (2820, "Rejseomkostninger", "opex"), (2830, "Fragt og emballage", "opex"),
    (2910, "Markedsføring og messer", "opex"), (2920, "IT og software", "opex"),
    (2930, "Rekruttering og konsulenter", "opex"), (2940, "Forsikringer", "opex"),
    (2950, "Kontorhold og administration", "opex"), (2960, "Garantiomkostninger", "opex"),
    (2990, "Øvrige driftsomkostninger", "opex"), (3510, "Afskrivninger", "opex"),
]
# account, department, monthly DKK, start, end, seasonal
RECURRING_COSTS = [
    (2710, "DK", 165000, None, None, False), (2710, "SE", 22000, None, None, False),
    (2710, "DE", 38000, None, D(2025, 9, 30), False), (2710, "DE", 53000, D(2025, 10, 1), None, False),
    (2720, "DK", 28000, None, None, True), (2720, "SE", 4000, None, None, True), (2720, "DE", 6000, None, None, True),
    (2810, "DK", 77000, None, None, False), (2810, "SE", 13000, None, None, False), (2810, "DE", 43000, None, None, False),
    (2820, "DK", 45000, None, None, True), (2820, "SE", 18000, None, None, True),
    (2820, "DE", 40000, None, D(2025, 9, 30), True), (2820, "DE", 64000, D(2025, 10, 1), None, True),
    (2910, "DK", 42000, None, None, False), (2910, "DE", 14000, None, None, False), (2910, "SE", 6000, None, None, False),
    (2920, None, 104000, None, None, False),
    (2940, None, 32000, None, None, False),
    (2950, None, 48000, None, None, False),
    (2960, None, 38000, None, None, False),
    (2990, None, 26000, None, None, False),
    (3510, None, 95000, None, None, False),
]
# Company car per German sales rep (starts with employment), DKK per month.
DE_CAR_PER_REP = 5500
CRM_SEAT_COST = 650  # per active CRM user per month, booked on 2920
FREIGHT_PCT = {"DK": 0.009, "SE": 0.014, "DE": 0.016}  # of invoiced revenue, booked on 2830
# One-off costs: date, account, department, DKK, text
ONE_OFF_COSTS = [
    (D(2025, 3, 14), 2910, "DK", 180000, "Nordic Water Expo 2025 - stand og rejser"),
    (D(2025, 4, 9), 2910, "DE", 200000, "WasserTech Messe Köln 2025"),
    (D(2025, 3, 28), 2950, None, 110000, "Revision årsregnskab 2024"),
    (D(2025, 2, 20), 2930, None, 120000, "ERP-opgradering, konsulent"),
    (D(2025, 4, 25), 2930, "SE", 60000, "Rekrutteringsbureau - Sales Engineer SE"),
    (D(2025, 7, 18), 2930, "DE", 95000, "Personalberatung - Key Account Manager"),
    (D(2025, 8, 22), 2930, "DE", 95000, "Personalberatung - Key Account Manager"),
    (D(2025, 9, 19), 2930, "DE", 90000, "Personalberatung - Vertriebsingenieur"),
    (D(2025, 10, 10), 2930, "DK", 30000, "Jobannonce servicetekniker"),
    (D(2025, 10, 22), 2910, "SE", 90000, "Pumpdagarna Göteborg 2025"),
    (D(2025, 11, 20), 2930, "DE", 95000, "Personalberatung - Vertriebsingenieur"),
    (D(2026, 1, 16), 2930, "DE", 60000, "Vertriebs-Onboarding Programm"),
    (D(2026, 3, 13), 2910, "DK", 185000, "Nordic Water Expo 2026 - stand og rejser"),
    (D(2026, 3, 27), 2950, None, 115000, "Revision årsregnskab 2025"),
    (D(2026, 4, 15), 2910, "DE", 380000, "WasserTech Messe Köln 2026 - erweiterter Stand"),
]
PROFIT_TARGET_H1_2025 = 12.0e6  # calibration anchor for recurring operating costs
COST_INFLATION_2026 = 0.025      # general price increase on recurring costs from Jan 2026
