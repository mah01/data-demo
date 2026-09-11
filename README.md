# NordFlow Executive Decision Support Demo — Phase 1: Synthetic Data Foundation

A small, internally consistent synthetic company. The records come from three
independent business systems (payroll, CRM, ERP). They encode a deliberate
business story that is only discoverable by **combining** those systems.

Phase 1 is only the data foundation. There is no MCP server, LLM, UI or real
integration here.

```bash
python3 src/generate.py    # or: make data        -> writes ./data (deterministic, ~1 s)
python3 src/validate.py    # or: make validate    -> 104 checks + executive walkthrough; exit 1 on failure
python3 src/robustness.py  # or: make robustness  -> all checks across 100 seeds (~15 s); exit 1 on any failure
```

Requires Python 3.9+ and the standard library only. No packages to install.

---

## 1. The company

**NordFlow A/S** is a Danish B2B industrial company (HQ in Kolding, offices in
Göteborg and Frankfurt). It sells:

| Category | What | Typical gross margin |
|---|---|---|
| Equipment | Pumps, booster sets, pump stations, control panels | ~27–29% (lower with discounts) |
| Components | Spare parts: seals, impellers, motors, sensors | ~41% |
| Service | Service agreements (billed quarterly), technician hours, commissioning | ~59% |

The service-line cost in the ERP covers materials, consumables and subcontractors.
Technicians' salaries are personnel costs in payroll.

| | 2025 | 2026 |
|---|---|---|
| Markets | Denmark, Sweden, Germany | same |
| Headcount (30 Jun) | 50 | 54 |
| German sales headcount | 8 | 12 |
| Annual revenue | ~DKK 178m | |

Data period: **January 2025 – August 2026**. The CRM also holds pipeline history
from September 2024.

The headcount is deliberately about half of the originally sketched ~110/120.
At ~110 employees, DKK 14.8m personnel cost per half-year would imply roughly
DKK 22k per month fully loaded per person, which is unrealistic for DK/SE/DE. All
financial targets are kept, and the German sales team becomes a visibly large
investment.

## 2. The business story (ground truth)

| | H1 2025 | H1 2026 |
|---|---|---|
| Revenue | DKK 85.8m | DKK 88.8m (+3.6%) |
| Operating profit | DKK 12.0m | DKK 8.0m (−33%) |
| Operating margin | 14.0% | 9.0% |
| Personnel costs | DKK 14.8m | DKK 16.6m |

Revenue is up but profit is down. There are three real causes and one red herring.

1. **German sales expansion that has not paid off** (payroll + CRM + ERP)
   - German sales headcount went from 8 to 12. Four reps were hired Sep 2025–Jan 2026 (payroll).
   - New pipeline grew +35%, but the win rate fell from 31% to 19% and won value fell 25%. The new reps win about 12%, veterans about 23% (CRM, joined to payroll through the user mapping).
   - German revenue fell 8% and equipment discounts rose, cutting margin (ERP).
   - Germany's net profit contribution changed by about DKK −3.4m: gross profit −1.4m, sales payroll −1.4m, and German operating costs −0.6m (cars, office, travel, trade fair).
2. **German key-account attrition after a reassignment** (ERP → mappings → CRM → payroll)
   - *Rheinmark Chemie* and *Brandauer Papierwerke* are the two largest German decliners (−1.9m and −1.7m). Together they lost more than Germany's entire net decline.
   - In Sep/Oct 2025 the CRM reassigned both accounts from a veteran account manager to two newly hired reps (`property_history`). Payroll shows the new owners started in Sep and Oct 2025.
   - Activity per month dropped sharply after the handover. Rheinmark's service-contract renewal and two follow-on deals were lost. Brandauer moved spare parts to a local distributor. The CRM notes say so.
3. **Hidden margin erosion in Denmark** (ERP + CRM)
   - Danish revenue grew +9.5%, but service fell −23% while equipment grew +33% at bigger discounts.
   - The service share fell from 30% to 21%, gross margin from 40.7% to 36.3%, and Danish gross profit is *down* DKK 0.5m.
   - Service-contract billing fell 25%. The CRM shows 16 of 39 Danish service renewals lost in H2 2025 (39% of their value).
4. **Red herring: the salary increase.** Every payslip shows a ~3.9% raise in
   January 2026. It accounts for only about DKK 0.56m, a third of the personnel
   increase and ~14% of the profit decline.

Sweden acts as a stable control market: flat revenue, a win rate of about 30%, and a slightly better margin.

## 3. The executive questions and where their answers live

| # | Question | Systems needed |
|---|---|---|
| 1 | How are we performing this year vs last year? | ERP (invoices + ledger incl. payroll journal) |
| 2 | Revenue increased, so why is profitability down? | ERP + payroll + CRM |
| 3 | What is driving the increase in personnel costs? | Payroll (ERP only shows a single monthly total) |
| 4 | We hired more salespeople in Germany. Did it pay off? | Payroll + CRM (via user mapping) + ERP |
| 5 | Why is German pipeline growing while revenue is falling? | CRM + ERP |
| 6 | Is Germany losing new business, existing customers, or both? | ERP + CRM |
| 7 | Which customers contributed most to the German decline? | ERP → company mapping → CRM owner history & activities → payroll |
| 8 | Is Denmark actually performing well? | ERP (mix, margin) + CRM (lost renewals) |
| 9 | What if German conversion had stayed at the 2025 level? | CRM (win rates, deal sizes) + ERP (margin) |
| 10 | Top three issues to investigate first? | All |

`python3 src/validate.py` prints a derived answer to each question, computed only from the raw CSVs.

## 4. Systems and schemas

The three systems are generated as **independent exports**. Each has its own
identifiers, naming, language, currency conventions and gaps. They share no
keys; the only bridge is `data/mappings/`.

### 4.1 Payroll — `data/payroll/` (Danløn-like group payroll export)

| File | Columns |
|---|---|
| `employees.csv` (56) | `employee_id` (e.g. `DK0047`, `DE0258`), `first_name`, `last_name`, `work_email` (optional, ~60% filled), `country` (DK/SE/DE), `department` (Management, Finance & Admin, IT, Sales, Customer Service, Marketing, Service, Operations), `job_title` (current), `employment_type`, `weekly_hours`, `employment_start`, `employment_end`, `status` (active/terminated), `cost_center`, `manager_employee_id`, `current_base_salary`, `currency` |
| `payroll_entries.csv` (1,039) | `pay_period` (YYYY-MM), `payment_date`, `employee_id`, `currency` (local), `base_salary` (prorated), `overtime_pay`, `commission`, `bonus`, `gross_pay`, `pension_employer`, `social_contributions_employer`, `employer_cost`, `fx_rate_to_dkk`, `employer_cost_dkk` |

- Commission is paid the month after a CRM deal is won: 1.5% in DK/SE, 2% in DE, 1% on renewals.
- New German reps get a EUR 750 per month guaranteed minimum commission for their first 6 months.
- Annual bonuses are paid in March. The 2026 bonus pool is cut to 80%.
- Employer contributions follow simplified national rules: DK pension 8% + ATP, SE arbetsgivaravgifter 31.42% + 4.5% pension, DE social security 20.5% up to a cap.

### 4.2 CRM — `data/crm/` (HubSpot-like)

| File | Columns |
|---|---|
| `owners.csv` (31) | `user_id` (`usr_######`), `first_name`, `last_name`, `email` (initials style), `team`, `active`, `created_at`, `archived_at` |
| `companies.csv` (523) | `company_id` (`cmp_#####`), `name`, `domain`, `country` (Denmark/Sweden/Germany), `city`, `industry`, `lifecycle_stage`, `owner_id` (current), `created_at`, `num_employees` |
| `deals.csv` (1,137) | `deal_id` (10 digits), `deal_name`, `pipeline` (Nordics Sales / DACH Sales / Service Renewals), `stage`, `deal_type` (New Business / Existing Business / Renewal), `company_id`, `owner_id`, `market`, `product_category` (Pumps & Systems / Spare Parts Agreement / Service Contract), `amount`, `deal_currency`, `amount_company_currency` (DKK), `discount_pct`, `created_at`, `expected_close_date`, `closed_at`, `outcome` (won/lost/open), `loss_reason` |
| `activities.csv` (6,203) | `activity_id`, `timestamp`, `type` (CALL/EMAIL/MEETING/NOTE), `owner_id`, `company_id`, `deal_id` (optional), `subject`, `body` (notes) |
| `property_history.csv` (112) | `object_type`, `object_id`, `property` (`hubspot_owner_id`, `lifecyclestage`), `value_before`, `value_after`, `changed_at`, `source`, `changed_by_user_id` |

### 4.3 ERP — `data/erp/` (e-conomic-like)

| File | Columns |
|---|---|
| `customers.csv` (324) | `customer_number` (5 digits), `name` (legal name), `customer_group_number`/`_name`, `country` (**Danish**: Danmark/Sverige/Tyskland), `city`, `currency`, `vat_number`, `payment_terms`, `created_date`, `barred` |
| `products.csv` (49) | `product_number`, `name` (Danish), `product_group_number` (10 Pumper og anlæg / 20 Reservedele og komponenter / 30 Service og vedligehold), `product_group_name`, `sales_price_dkk`, `cost_price_dkk`, `unit` |
| `invoices.csv` (7,939) | `invoice_number`, `invoice_date`, `due_date`, `customer_number`, `customer_name`, `currency`, `exchange_rate` (DKK per 1 unit), `net_amount`, `vat_amount`, `gross_amount`, `net_amount_dkk`, `document_type` (invoice/credit_note), `your_reference`, `credited_invoice_number` |
| `invoice_lines.csv` (19,510) | `invoice_number`, `line_number`, `product_number`, `description`, `quantity`, `unit`, `unit_price` (invoice currency), `discount_pct`, `net_amount` (invoice currency), `unit_cost_dkk`, `total_cost_dkk` |
| `ledger_entries.csv` (589) | `entry_number`, `date`, `voucher`, `account_number`, `department` (DK/SE/DE, sometimes blank), `amount_dkk` (positive = cost), `text` |
| `accounts.csv` | chart of accounts, with `type` = personnel / opex (1010/1310 are listed for reference and derived from invoices) |
| `exchange_rates.csv` | monthly EUR and SEK rates to DKK |

The ledger contains cost postings that do not come from sales invoices: the
monthly **payroll journal**, which is one total per account with no country or
department breakdown, and **operating expenses** such as rent, cars, travel,
freight, marketing and trade fairs, IT and CRM seats, recruiting, insurance and
depreciation.

### 4.4 Mappings — `data/mappings/` (the "integration knowledge")

| File | Purpose |
|---|---|
| `employee_crm_user.csv` | `payroll_employee_id` ↔ `crm_user_id`, with `match_basis` and a `note`. Some names differ ("JP Hansen", "Fischer-Lang", "Yilmaz"). Two CRM users have no payroll record: a rep who left in 2024 and an integration user. |
| `crm_company_erp_customer.csv` | `crm_company_id` ↔ `erp_customer_number`, with `match_method` (exact_name / vat_number / name_contains / manual). Some ERP customers are not in the CRM. Three small customers exist in both systems but are unmapped. Duplicate CRM records map to the same ERP customer. |
| `value_mappings.csv` | Canonical market (DK/SE/DE) and product category (Equipment/Components/Service) for each system's own labels. Also maps CRM deal currency to market, for deals where both `market` and the company country are blank. |

## 5. Deliberate imperfections

- **Name and field conventions.** About 80% of mapped CRM company names differ from the ERP legal name (suffix dropped, ASCII-folded, "(HQ)", upper-case, typos). Countries are Danish in the ERP, English in the CRM and ISO codes in payroll. Product descriptions are Danish.
- **Currencies.** Invoices are in DKK, SEK or EUR and ERP costs in DKK. Payroll is in local currency with a DKK conversion.
- **Missing optional fields.** Loss reasons, industry, city, domain, VAT numbers, work emails, the deal `market` and `product_category`, and ledger departments are sometimes blank.
- **Staff changes.** There are terminated employees (a Danish technician who was replaced, a Swedish rep who left). A former German rep is still owner of old CRM records as an archived user.
- **Pipeline timing.** Deals cross reporting periods, 143 deals are still open at the data end, and some are "slipped" with an expected close date in the past.
- **Customer records.** Customers have many invoices. There are duplicate CRM company records and some unmapped customers.
- **Credit notes.** About 1% of invoices are credit notes, either returns of spare parts or price corrections.
- **Variable pay.** Commission varies month to month, bonuses are paid in March, and technicians get overtime.
- **Seasonality.** Summer is weak and Q4 strong. Service contracts are billed quarterly in advance.
- **Cost and mix noise.** Supplier-cost noise, two supplier credits, and one-off projects from new customers.

## 6. How generation works

```
src/
  config.py       story parameters: revenue plan, win rates, pipeline, discounts, key accounts, contracts
  roster.py       employees, payroll rules, operating-cost plan
  world.py        hidden "real world": products, customers/prospects, service contracts
  gen_crm.py      deals (incl. key-account deals, renewals), owners, territory re-cut
  crm_render.py   HubSpot-style tables: owners, companies, deals, activities, property history
  gen_erp.py      invoices: won deals -> service contracts -> key accounts -> run-rate orders -> credit notes
  gen_payroll.py  monthly payroll incl. commissions from CRM wins, raises, bonuses, contributions
  gen_ledger.py   payroll journal + operating costs
  generate.py     orchestrates everything and writes CSVs + mapping files
  metrics.py      (validation side) reads raw CSVs only; P&L, market/category, payroll, CRM primitives
  analysis.py     (validation side) question-level analyses, profit bridge, counterfactual
  validate.py     structural, identity and realism checks + story checks from ground_truth.json
  robustness.py   regenerates with many seeds (temporary folders) and runs every check on each
ground_truth.json intended business facts, scenario invariants, metric definitions and expected ranges
```

**Why there is a "world" model.** To stay coherent, won CRM deals must become ERP
invoices and payroll commission. That requires one hidden set of real-world
facts behind the systems. The world model is never exported as a table. Each
system renders its own view with its own IDs, labels, currencies and gaps, as if
it had been exported from a separate tool.

**Determinism.** A fixed seed (`config.SEED`) is used, with one derived RNG
stream per purpose, so changing one part of the generator doesn't reshuffle
everything else. Repeated runs produce byte-identical CSVs.

**Calibration is kept to two anchors.**

1. One scale factor on all base salaries makes H1 2025 personnel cost DKK 14.8m (currently 0.906).
2. One scale factor on the recurring operating-cost base makes H1 2025 profit DKK 12.0m (currently 1.04).

Revenue follows a per market × category × half-year plan, filled by run-rate
orders after deals, contracts and key accounts are booked. **Nothing about 2026
profit, personnel cost or margin is calibrated.** Those results emerge from the
German hires, raises, CRM win rates, key-account decline, discounts and mix.

**Scenario invariants.** Some story-critical outcomes are enforced by
construction instead of being left to random draws (`config.py`, section
"Scenario invariants"). Each fixes *how much* happens; *which* customers,
contracts and deals are affected stays random. Across seeds, only 1–3 of the
~12–20 churned Danish contracts and 2–3 of the ~23 German wins are the same.

| # | Invariant | How it is enforced |
|---|---|---|
| 1 | Danish service-contract billing H1 2026 = −25% vs H1 2025 | End-2025 renewal losses are sized after accounting for new contracts and other renewals (random first pass, then swaps toward the target) |
| 2 | German expansion hires win 12% of deals closed in H1 2026; veterans take the rest of the 19% | Separate win-rate stratum for the new reps |
| 3 | Rheinmark and Brandauer are the two largest German decliners, ≥ DKK 0.3m ahead of the next customer | No other German customer may win more than DKK 0.8m of equipment in any 12-month window |
| 4 | German won value H1 2026 = −25% vs H1 2025 | Winners and losers are swapped within each rep stratum; win counts are unchanged |

Key-account activity after the handover is also thinner by construction: 0–1 account touches a month, and 1–3 activities per deal.

Changing the story means editing `config.py` / `roster.py`, regenerating, then
running `validate.py` and `robustness.py`.

## 7. Validation

`python3 src/validate.py` reads only `data/` and `ground_truth.json`. It does not
import the generator. It runs:

- **Structure & referential integrity:** files exist, foreign keys resolve, invoice totals equal their lines, dates fall inside the period.
- **Cross-system identity:** each system's ID formats, no identifier shared across systems, mapping coverage, name divergence.
- **Realism:** the presence of the imperfections listed above.
- **Story checks (54):** each tagged with the questions it supports and the systems it needs, with the tolerances defined in `ground_truth.json`. Five are marked `"invariant": true` and verify the scenario invariants above.
- **Executive walkthrough:** answers to all ten questions derived from the records (skip with `--quiet`).

It exits with code 1 and lists each `FAIL` if a change breaks the story. As a
test, setting the German 2026 win rate back to 31% and removing the key-account
decline makes 6 story checks fail.

### Robustness test

`python3 src/robustness.py [--seeds N] [--workers W]` regenerates the dataset for
seeds 1..N (default 100), each into a temporary folder, so `./data` is never
touched. It runs all 104 checks on every seed and prints, per check, the pass
count and the min/median/max value. Any change to the generator reshuffles the
random draws much like a new seed does, so run this after generator changes.

Current result: **100/100 seeds pass all 104 checks.** Invariant spread across 100 seeds:

| Invariant check | Band | min / median / max |
|---|---|---|
| Danish contract billing change | −30% to −20% | −25.0% / −25.0% / −25.0% |
| New-rep win rate H1 2026 | 8–16% | 10.8% / 11.9% / 13.2% |
| Veteran win rate H1 2026 | 20–30% | 21.4% / 23.1% / 26.8% |
| German won value change | −35% to −15% | −25.0% / −25.0% / −25.0% |
| Key accounts' lead over next decliner | ≥ DKK 0.3m | 0.39m / 0.96m / 1.30m |

### Expected metrics (current seed)

| Metric | Value | Tolerance in ground_truth.json |
|---|---|---|
| Revenue H1 2025 / H1 2026 | 85.8m / 88.8m | 85–87m / 88–90m |
| Operating profit H1 2025 / H1 2026 | 12.0m / 8.0m | 11.5–12.5m / 7.5–8.5m |
| Operating margin | 14.0% / 9.0% | 13.3–14.6% / 8.4–9.6% |
| Jan–Aug revenue / profit | 113.2m → 115.7m / 16.0m → 10.6m | growth 1–5% / profit ≤ −20% |
| Personnel costs (payroll = ledger) | 14.81m / 16.61m | 14.6–15.0m / 16.3–16.9m |
| Salary inflation (red herring) | 3.9%, ≈0.56m, 14% of profit decline | ≤ 20% of decline |
| German sales headcount | 8 → 12 | exact |
| German new pipeline | 26.0m → 35.1m (+35%) | +30–40% |
| German win rate | 30.8% → 18.6% (new reps 12.5%, veterans 23.1%) | 28–34% / 16–22% |
| German won value | −25.0% | −15 to −35% |
| German revenue | 22.0m → 20.2m (−8.0%) | −6 to −10% |
| Two key accounts (Rheinmark, Brandauer) | −3.59m (203% of German net decline) | −2.8 to −4.5m |
| Danish revenue / gross profit | +9.5% / −0.48m | +5–13% / ≤ 0 |
| Danish service share / gross margin | 29.9% → 21.0% / 40.7% → 36.3% | ≤ −5pp / ≤ −2pp |
| Danish contract billing | −25.0% | −20 to −30% |
| Counterfactual (2025 German win rate) | +0.67m gross profit → profit ≈ 8.7m, margin ≈ 9.4% | uplift 0.4–1.5m; margin gap to 2025 ≥ 2.5pp |
| Profit bridge (Germany / DK GP / other personnel / SE GP) | −3.36m / −0.48m / −0.44m / +0.39m | reconciles to 0 |

### Known simplifications

- One group payroll export covers all three countries. In reality Swedish and German payroll would come from local providers.
- The ERP export contains invoices and cost ledger entries but not revenue/COGS ledger postings, to avoid double counting.
- Product costs are standard costs. There is no inventory, purchasing, accounts receivable or cash data.
- The counterfactual in Q9 is an upper bound. It assumes the extra wins would have been invoiced within H1 2026 and ignores commission.
- All company and person names are fictional. Any resemblance to real entities is coincidental.

## 8. Release: Phase 1 v1.0 (frozen)

This version is tagged **`phase1-v1.0`** in Git. `data_manifest.json` records the
SHA-256, byte size and row count of every default generated file (seed 4217,
Python 3.11.12), plus a combined dataset hash.

```bash
python3 src/manifest.py               # or: make verify        -> ./data matches the manifest
python3 src/manifest.py --regenerate  # or: make verify-regen  -> a fresh default regeneration matches it
```

- `make verify` detects accidental edits to the committed data.
- `make verify-regen` detects any change to the generator's output, including dependency on the Python version. The `random` module's sequences can differ between Python versions.
- `.gitattributes` keeps Git from rewriting the CSVs' CRLF line endings.

Phase 1 is frozen while Phase 2 is built. Change the generator, data, mappings
or validation only to fix a genuine data defect. If that happens:

1. Bump the version.
2. Run `validate.py` and `robustness.py`.
3. Rewrite the manifest (`python3 src/manifest.py --write`) and update `RELEASE` in `src/manifest.py`.
4. Commit and tag the new version.

## 9. Out of scope (Phase 1)

MCP server, LLM integration, RAG and vector DB, UI, authentication, real
Danløn, HubSpot or e-conomic integrations, external/public data, and production
architecture.
