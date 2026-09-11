# NordFlow Phase 2 — Read-only business data runtime

This is the data access layer that a future AI agent will use. It exposes the
three NordFlow business systems (ERP, CRM, payroll) and the identity mappings
between them as **generic, read-only query operations**, wrapped in a thin MCP
server.

**No LLM is connected.** The runtime calculates facts and aggregations; it does
not explain or conclude anything.

The Phase 1 dataset is consumed as-is from the frozen tag `phase1-v1.0`, and
this branch changes no Phase 1 files.

```bash
python3 -m venv phase2/.venv && phase2/.venv/bin/pip install -r phase2/requirements.txt

phase2/.venv/bin/python -m pytest phase2/tests    # 90 tests (runtime + MCP)
python3 -m pytest phase2/tests                    # runtime tests with the stdlib only; MCP tests skip
phase2/.venv/bin/python -m phase2.mcp.server      # MCP server on stdio (run from the repo root)
python3 -m phase2.gen_tool_docs                   # regenerate TOOLS.md from the code
```

The runtime itself uses only the standard library. Only the MCP layer needs the `mcp` SDK (v2).

## 1. Architecture

```
data/erp/*.csv      data/crm/*.csv      data/payroll/*.csv     data/mappings/*.csv
      │                   │                    │                        │
 ERPAdapter          CRMAdapter          PayrollAdapter           IdentityAdapter      adapters: one folder each,
      │                   │                    │                        │              typed records, no aggregation
      └──────────── Semantics (value_mappings.csv + system documentation) ┘
      │                   │                    │                        │
 FinanceQueries      SalesQueries        PeopleQueries            IdentityQueries      query layer: generic operations
      └───────────────────┴──────── Runtime (registry) ─┴────────────────────┘
                                          │
                              phase2/mcp/server.py (thin)                           33 read-only MCP tools
```

| Layer | Location | Responsibility |
|---|---|---|
| Sources | `runtime/sources.py` | Cached CSV reading of one folder, typed parsing (blank → null), name folding for search |
| Adapters | `runtime/adapters/{erp,crm,payroll,identity}.py` | Each reads **only its own folder**. Joins stay inside the system (e.g. ERP line → ERP invoice → ERP customer). |
| Semantics | `runtime/semantics.py` | Market and category classification from `value_mappings.csv`, input normalisation ("Tyskland" → DE), documentation of fields, dates, currencies, stages and metrics |
| Periods | `runtime/periods.py` | Period parsing, calendar dimensions, partial-coverage notes |
| Query layer | `runtime/query/*.py` | Filtering, grouping, period comparison, sorting and paging. Returns JSON-ready result envelopes. |
| Registry | `runtime/service.py` | `Runtime(data_dir)` builds everything. `operations()` lists the tools. |
| MCP | `mcp/server.py` | Registers each operation unchanged as a read-only tool. Turns parameter errors into readable tool errors. No business logic. |

### Design rules

- **The systems stay separate.** There is no unified analytical database. A question that spans systems has to be composed from per-system operations plus the `identity_*` tools. That composition is the agent's job, not the runtime's.
- **Facts, not conclusions.** Operations are parameterised aggregations: `crm_win_rate(period, group_by, market, owner_ids, …)`, `erp_customer_revenue(period, compare_to, sort_by="revenue_dkk_change")`. None of them names a scenario, a culprit or an explanation.
- **Read-only.** There are no writes anywhere. Every MCP tool is annotated `read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False`.

### Runtime vs evaluation boundary

| The runtime may use | The runtime must not use (evaluation only) |
|---|---|
| `data/erp`, `data/crm`, `data/payroll`, `data/mappings` CSVs | `ground_truth.json`, `src/validate.py`, `src/analysis.py`, `src/metrics.py`, `src/robustness.py` |
| Schema and semantic documentation in `runtime/semantics.py` | The generator and its hidden world model (`src/*.py`), the executive walkthrough, expected metrics |

`tests/test_boundary.py` enforces this:

- It parses every runtime and MCP module and fails on any import outside the standard library, `phase2` and `mcp`, or of any Phase 1 module.
- It fails if runtime code mentions answer-key files.
- It runs **every** operation with the built-in `open` monkeypatched, and asserts that only `*.csv` files inside the four system folders were read.

## 2. Tools

The full reference (parameters, types, defaults, descriptions) is in [`TOOLS.md`](TOOLS.md), generated from the code.

| Group | Tools |
|---|---|
| Metadata | `meta_describe_sources`, `meta_get_semantics` |
| ERP / Finance | `erp_financial_summary`, `erp_sales_summary` (revenue + gross profit by dimensions), `erp_customer_revenue`, `erp_operating_costs`, `erp_ledger_entries`, `erp_find_customers`, `erp_invoices`, `erp_invoice_lines`, `erp_products` |
| CRM / Sales | `crm_pipeline`, `crm_win_rate`, `crm_loss_reasons`, `crm_deals`, `crm_renewals`, `crm_find_companies`, `crm_activities`, `crm_activity_summary`, `crm_owner_history`, `crm_users` |
| Payroll / People | `payroll_headcount`, `payroll_personnel_costs`, `payroll_base_salary_change`, `payroll_find_employees`, `payroll_entries`, `payroll_hires_and_departures` |
| Identity | `identity_crm_companies_to_erp`, `identity_erp_customers_to_crm`, `identity_crm_users_to_employees`, `identity_employees_to_crm_users`, `identity_find_company`, `identity_find_person` |

### Common parameters

| Parameter | Meaning |
|---|---|
| `period`, `compare_to` | `"2026"`, `"2026-H1"` / `"H1 2026"`, `"2026-Q2"`, `"2026-03"`, `"2026-01..2026-08"`, `"2025-01-01..2025-06-30"`. Boundaries are inclusive. |
| `group_by` | A list of dimensions valid for that tool, e.g. `["market", "category"]`, `["owner"]`, `["month"]`. Unknown dimensions raise an error listing the allowed ones. |
| `market` | `DK`/`SE`/`DE`, or any known label (`Germany`, `Tyskland`, …), case- and accent-insensitive. |
| `category` / `product_category` | `Equipment`, `Components`, `Service`, or a system label (`Pumps & Systems`, `10`, …). |
| `owner_ids`, `company_ids`, `customer_numbers`, `user_ids`, `employee_ids` | Lists of the system's own ids. The identity tools translate between systems. |
| `sort_by`, `ascending`, `limit` | Any returned field. `limit` pages list results (the envelope reports `row_count` and a truncation note). |

### Return structure

Every tool returns one JSON object:

```json
{
  "operation": "crm_win_rate", "source": "crm",
  "parameters": {"period": "2026-H1", "group_by": ["market"], "compare_to": "2025-H1"},
  "currency": "DKK",
  "period": {"label": "2026-H1", "start": "2026-01-01", "end": "2026-06-30"},
  "compare_period": {"label": "2025-H1", "start": "2025-01-01", "end": "2025-06-30"},
  "row_count": 2,
  "rows": [{"market": "DE", "closed_count": 3, "won_count": 1, "win_rate": 0.3333,
            "win_rate_compare": null, "win_rate_change": null, "...": "..."}],
  "totals": {"closed_count": 3, "win_rate": 0.3333, "win_rate_compare": 1.0, "win_rate_change": -0.6667},
  "notes": ["Period 2025-H1 is only partly covered by CRM data (...); figures cover the overlap only."]
}
```

(This example is from the test fixture data.)

- **Comparisons.** With `compare_to`, each measure `m` gets `m_compare`, `m_change` and, for amounts and counts, `m_change_pct`. Ratios (margins, rates, shares) get `m_change` in points and no `_pct`. Groups present in only one period are included, with zeros for amounts and `null` for undefined ratios.
- **Money.** Rounded to 0.01 DKK. Ratios are fractions (0.3333 = 33.33%), rounded to 4 decimals.
- **Nulls.** A blank source field stays `null`; nothing is filled in. Loss reasons are the one exception: blank reasons are grouped as `"(not recorded)"`.
- **Notes.** Carry definitions that matter for the result: partial period coverage, truncation, company-level costs.
- **Errors.** Invalid parameters return an MCP tool error with a readable message, e.g. `Unrecognised period 'last spring'. Use e.g. '2026-H1', …`.

## 3. Semantic assumptions

These are the definitions used by the runtime (`meta_get_semantics` returns them at runtime):

- **Currency.** All aggregated money values are DKK. Each system uses its own conversion:
  - ERP: `invoice_lines.net_amount × invoices.exchange_rate`; costs are already in DKK.
  - CRM: `deals.amount_company_currency`.
  - Payroll: local amount × `payroll_entries.fx_rate_to_dkk`.

  Record-level results keep the source currency and amount (`net_amount`, `amount`/`deal_currency`, local payroll amounts). `erp_sales_summary` grouped by `currency` also returns `revenue_source_currency`.
- **Dates.**
  - ERP revenue by `invoice_date`, with credit notes included on their own date. Costs by ledger `date`.
  - CRM pipeline by `created_at`. Win rate, won/lost value and renewals by `closed_at`.
  - Open pipeline at a date: created on or before it and not closed by then. The historical stage is not recorded.
  - Payroll by `pay_period`. Employment start and end dates are inclusive.
- **Markets.**
  - ERP: `customers.country` (Danish names). Payroll: `employees.country`.
  - CRM deals: `deals.market`, falling back to the company's `country`, then to `deals.deal_currency` (DKK = DK, SEK = SE, EUR = DE; each market trades in its own currency). Results report `market_source`.
  - Ledger costs use `department`. The payroll journal has none, so operating profit cannot be split by market.
- **Product categories.** ERP `product_group_number` 10/20/30 → Equipment/Components/Service. CRM `product_category` labels → the same canonical values.
- **CRM.**
  - Win rate = won ÷ (won + lost) by count. `value_win_rate` uses DKK value.
  - Renewal deals (service-contract renewals) are excluded from pipeline and win rate unless `include_renewals=true` or `deal_type="Renewal"`.
- **Finance.**
  - Operating profit = revenue − cost of sales − personnel costs (ledger payroll journal) − other operating costs (ledger opex).
  - `avg_discount_pct` = 1 − revenue ÷ list value.
- **People.**
  - Point-in-time headcount = employed on the date. Average monthly headcount = employees with a pay slip each month, averaged.
  - `payroll_base_salary_change` is like-for-like: only employees employed for the whole of both months, with the change measured in local currency, so FX has no effect.
- **Identity.** Links come only from the mapping files. Names are shown from each system's own master data. Statuses are `mapped`, `not_mapped` or `unknown_id`, and duplicates return several links.

## 4. Tests

| File | Covers |
|---|---|
| `test_periods_semantics.py` | Period formats, inclusive boundaries, errors, market/category normalisation, metadata |
| `test_erp.py` | P&L, grouping, filters, currency conversion, credit notes, discounts, comparisons, customer first-invoice filter, cost ledger, search |
| `test_crm.py` | Market fallback chain, pipeline (created / open at end), win rate, owner filter, renewals switch, loss reasons incl. blanks, deal listing, activities, owner history |
| `test_payroll.py` | Headcount boundaries (hire and leave dates), average headcount, cost components in DKK, comparisons, hires/departures, FX-neutral salary change |
| `test_identity.py` | All four directions, duplicates, unmapped, unknown ids, cross-system name search |
| `test_boundary.py` | No Phase 1 imports or answer-key references; only system CSVs are opened; every operation documented |
| `test_real_data.py` | On the frozen dataset: reconciliation across groupings, payroll = ERP journal, full fallback coverage, mappings resolve both ways, every operation returns JSON |
| `test_mcp.py` | 33 tools = runtime operations, all read-only, calls, list parameters, readable errors, real stdio subprocess |

Expected values in the unit tests are worked out by hand from the small fixture dataset in `tests/fixtures/data/`. It has the same schemas as the real exports, with deliberate edge cases.

**No test checks a business conclusion about the NordFlow scenario.** Those belong to a later evaluation step.

## 5. Connecting an MCP client (later)

The server speaks MCP over stdio. A typical client entry, not configured by this step:

```json
{"command": "<repo>/phase2/.venv/bin/python", "args": ["-m", "phase2.mcp.server"],
 "env": {"PYTHONPATH": "<repo>", "NORDFLOW_DATA_DIR": "<repo>/data"}}
```

## 6. Known data notes

- The frozen CRM export contains one activity timestamped 2026-09-01, one day after the other systems' cut-off. It is left unchanged (Phase 1 is frozen), shows up in `meta_describe_sources` coverage, and does not affect any aggregate over the business periods.
- Open deals can have an `expected_close_date` in the past, as exported.
