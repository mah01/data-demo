# Phase 2B baseline: blind agent evaluation

Protocol `2B-baseline-1` · model `claude-opus-5` via Claude Code 2.1.268 headless · 19 runs, each in a fresh isolated process · system prompt sha256 `0bd16140ba04…`

**Baseline finding.** Claude Opus 5, given only the Phase 2A MCP tools and a neutral instruction, investigated NordFlow independently and reached the Phase 1 business story in every run. All 19 runs are classified **PASS**. The headline pattern (revenue up, operating profit down about a third), the German sales expansion with collapsing conversion, and Danish service erosion behind revenue growth were found in **every** run, including all 9 open-ended runs. The main gap is depth on open-ended questions: the German key accounts (Rheinmark, Brandauer) surfaced in only **3 of 9** open-ended runs, although they were found in every benchmark run whose question pointed at German customers or sales (Q04-Q07). No run fell for the salary-inflation red herring. No invented facts were found. There were a handful of minor numeric slips and one significant window-choice misinterpretation (Q01).

## Results at a glance

- Benchmark questions: **10 PASS / 0 PARTIAL / 0 FAIL** (1 run each)
- Open-ended questions: **9 PASS / 0 PARTIAL / 0 FAIL** (3 runs each)
- Tool calls: 674 total, 20–58 per run · tool errors 12 · wall time 101–549 s per run · reported cost $35.99

| run | question | result | tool calls | systems | time (s) | cost ($) |
|---|---|---|---|---|---|---|
| [BA-t1](runs/BA-t1.md) | How is the business doing? Is there anything I should be concerned about? | **PASS** | 33 | crm, erp, payroll | 229 | 2.43 |
| [BA-t2](runs/BA-t2.md) | How is the business doing? Is there anything I should be concerned about? | **PASS** | 35 | crm, erp, payroll | 158 | 1.72 |
| [BA-t3](runs/BA-t3.md) | How is the business doing? Is there anything I should be concerned about? | **PASS** | 54 | crm, erp, identity, payroll | 338 | 3.00 |
| [BB-t1](runs/BB-t1.md) | What deserves management attention right now? | **PASS** | 33 | crm, erp, identity, payroll | 292 | 2.00 |
| [BB-t2](runs/BB-t2.md) | What deserves management attention right now? | **PASS** | 58 | crm, erp, identity, payroll | 337 | 2.99 |
| [BB-t3](runs/BB-t3.md) | What deserves management attention right now? | **PASS** | 51 | crm, erp, identity, payroll | 344 | 2.48 |
| [BC-t1](runs/BC-t1.md) | Where would you investigate first if you were the CEO? | **PASS** | 28 | crm, erp, payroll | 157 | 1.98 |
| [BC-t2](runs/BC-t2.md) | Where would you investigate first if you were the CEO? | **PASS** | 26 | crm, erp, payroll | 134 | 1.57 |
| [BC-t3](runs/BC-t3.md) | Where would you investigate first if you were the CEO? | **PASS** | 31 | crm, erp, identity, payroll | 160 | 1.66 |
| [Q01-t1](runs/Q01-t1.md) | How are we performing this year compared with last year? | **PASS** | 22 | crm, erp, payroll | 101 | 0.98 |
| [Q02-t1](runs/Q02-t1.md) | Revenue increased, so why is profitability down? | **PASS** | 36 | crm, erp, identity, payroll | 163 | 2.07 |
| [Q03-t1](runs/Q03-t1.md) | What is driving the increase in personnel costs? | **PASS** | 20 | crm, erp, identity, payroll | 111 | 1.06 |
| [Q04-t1](runs/Q04-t1.md) | We hired more salespeople in Germany. Did that investment pay off? | **PASS** | 42 | crm, erp, identity, payroll | 282 | 2.03 |
| [Q05-t1](runs/Q05-t1.md) | Why is the German pipeline growing while German revenue is falling? | **PASS** | 40 | crm, erp, identity, payroll | 340 | 1.96 |
| [Q06-t1](runs/Q06-t1.md) | Are we losing new business or existing customers in Germany? | **PASS** | 38 | crm, erp, identity | 549 | 2.13 |
| [Q07-t1](runs/Q07-t1.md) | Which customers contributed most to the German decline? | **PASS** | 36 | crm, erp, identity | 234 | 1.38 |
| [Q08-t1](runs/Q08-t1.md) | Is Denmark actually performing well? | **PASS** | 34 | crm, erp, payroll | 193 | 1.49 |
| [Q09-t1](runs/Q09-t1.md) | What would profitability have looked like if German conversion had remained at the 2025 level? | **PASS** | 25 | crm, erp, identity, payroll | 179 | 1.11 |
| [Q10-t1](runs/Q10-t1.md) | What are the three issues management should investigate first? | **PASS** | 32 | crm, erp, payroll | 234 | 1.95 |

## Open-ended discovery matrix

Manual assessment of what each open-ended run surfaced without being led (✓ found, ~ partly, ✗ not found).

| discovery | BA-t1 | BA-t2 | BA-t3 | BB-t1 | BB-t2 | BB-t3 | BC-t1 | BC-t2 | BC-t3 | found in |
|---|---|---|---|---|---|---|---|---|---|---|
| Overall revenue growth but operating-profit deterioration | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 9/9 |
| Germany as a major contributor to the profit decline | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 9/9 |
| German sales headcount expansion (8 -> 12) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 9/9 |
| Pipeline growth combined with worse conversion (win rate) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 9/9 |
| Poor new-rep performance (new hires convert worse) | ✓ | ~ | ✓ | ✓ | ✓ | ✓ | ~ | ~ | ✓ | 6/9 |
| Rheinmark / Brandauer identified at customer level | ✗ | ✗ | ✓ | ✗ | ✓ | ✓ | ✗ | ✗ | ✗ | 3/9 |
| Danish revenue growth masking mix / margin deterioration | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 9/9 |
| Salary inflation insufficient to explain the profit decline | ✗ | ✗ | ✗ | ✗ | ✗ | ~ | ✗ | ✗ | ~ | 0/9 |

## Benchmark discovery coverage

| discovery | Q01 | Q02 | Q03 | Q04 | Q05 | Q06 | Q07 | Q08 | Q09 | Q10 |
|---|---|---|---|---|---|---|---|---|---|---|
| Overall revenue growth but operating-profit deterioration | ✓ | ✓ | – | – | – | – | – | ✓ | ✓ | ✓ |
| Germany as a major contributor to the profit decline | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| German sales headcount expansion (8 -> 12) | ✓ | ✓ | ✓ | ✓ | ✓ | ~ | ✗ | ~ | ✓ | ✓ |
| Pipeline growth combined with worse conversion (win rate) | ✓ | ~ | ✓ | ✓ | ✓ | ✓ | – | – | ✓ | ✓ |
| Poor new-rep performance (new hires convert worse) | ~ | ✗ | ✓ | ✓ | ✓ | ~ | – | – | ✓ | ✓ |
| Rheinmark / Brandauer identified at customer level | ✗ | ✗ | – | ✓ | ✓ | ✓ | ✓ | – | ✗ | ~ |
| Danish revenue growth masking mix / margin deterioration | ✓ | ✓ | – | ~ | – | – | – | ✓ | ~ | ✓ |
| Salary inflation insufficient to explain the profit decline | ~ | ~ | ✓ | – | – | – | – | – | – | ✗ |

## What the agent discovers

- **Revenue up, profit down:** 19/19 runs where relevant. The figures match the reference exactly. Every run compared Jan-Aug 2026 with Jan-Aug 2025 (the data ends 31 Aug 2026), and several also checked H1.
- **Germany as the largest contributor:** 9/9 open-ended runs. Typically sized at about 3.6M of the 5.4M Jan-Aug decline (gross profit -1.8M plus sales payroll +1.77M).
- **German sales headcount 8 -> 12:** found from payroll hires in 9/9 open-ended runs and all relevant benchmark runs.
- **Pipeline +35% with win rate about 30% -> 18%:** 9/9 open-ended runs.
- **New-rep underperformance:** quantified (about 8 of 67-69 won, about 12%) in 6/9 open-ended runs and partly in the rest. Usually with the correct nuance that veterans also declined. Found by joining payroll hire dates to CRM owners.
- **Danish revenue growth masking service/mix/margin erosion:** 9/9 open-ended runs. Traced to the December 2025 renewal round and matched customer by customer to missing ERP service invoices.
- **Key accounts:** Q04, Q05, Q06 and Q07 each identified Rheinmark and Brandauer, the September-October 2025 bulk reassignment to new hires, and the CRM notes. Three open-ended runs (BA-t3, BB-t2, BB-t3) got there unprompted.
- **Beyond the encoded story:** agents consistently promoted equipment discounting (DE 7% -> 15%, DK 7% -> 11%) to a standalone issue, and flagged the timing risk of the upcoming renewal round. Two runs (BA-t3, BC-t3) found that the CRM loss-reason field contradicts reps' notes on some lost renewals, which is a real inconsistency in the Phase 1 data.

## What the agent misses

- **German key-account attrition in 6 of 9 open-ended runs.** Two of them (BB-t1, BC-t2) noticed German components/spare parts -16% and explicitly left it uninvestigated. So the misses are about stopping early, not about blindness to the signal.
- **Explicit treatment of salary inflation** in open-ended answers: 0/9 state that raises are insufficient (2/9 partly, calling them 'normal'). The misattribution never happened, though: all 9 attribute about 75% of the personnel increase to the German hires. Q03, which asks directly, handles it precisely (3.6% like-for-like, about 0.45M).
- **Payroll link for the key-account owners in Q07:** it found the handover but did not establish from payroll that the new owners were recent hires.
- **Lost renewals in Q01:** checked with the wrong window (see below).
- **Tools never used:** `crm_find_companies` and `identity_crm_users_to_employees`. Agents used `identity_find_person` / `identity_employees_to_crm_users` and owner ids instead.

## What the agent misinterprets

- **Q01 (significant).** It checked service renewals for Jan-Aug 2026 vs Jan-Aug 2025 across all markets, concluded 'renewals look healthy' and 'this doesn't match the CRM', and suggested checking for a billing gap. The Danish losses closed in Nov-Dec 2025, outside that window. Q02 and every open-ended run chose correct windows and found them.
- **Minor numeric slips.**
  - Q10 quotes German revenue -8.6% (actual -8.0%).
  - BA-t3 values the new hires' 8 wins at 3.4M (actual 2.64M), and says 'the other 11 reassigned accounts actually grew' (net +1.71M, but 8 of 11 grew).
  - BB-t3 says 'experienced reps are also winning only 13-14%' (true of some; veteran average about 23%).
- **Framing difference, not an error.** Agents rank discounting as a separate top issue. Phase 1 folds it into the German and Danish narratives.

## What the agent invents

No fabricated facts, customers, events or causes were found. Every spot-checked figure matched the data exactly (renewal counts, new-rep wins, account-level revenue, Q2 deltas, individual rep win rates).

Explanations beyond the data were consistently labelled as interpretation or hypothesis, for example: discounting as a possible policy change, weaker pipeline qualification, a possible sales pay-plan change (BC-t3, 'I haven't checked that'), and a possible billing gap (Q01). Answers repeatedly stated what the data could *not* show (why discounts rose, why customers insourced maintenance).

## Investigation behaviour

- **Orientation first:** all 19 runs began with `meta_describe_sources` + `meta_get_semantics`, then used the coverage information to choose comparable periods.
- **Volume and time:** 674 tool calls in total (20-58 per run, median about 34), 101-549 s per run, no repeated identical calls, 31 of 33 tools used.
- **Errors:** 12 tool errors, all recovered on the next call. 10 were single dates passed where the tools expect a period format; 2 are a Phase 2A defect (see below).
- **Cross-system:** payroll queried in 17/19 runs, identity tools in 12/19. Typical chains: payroll hires -> identity -> CRM owner win rates; ERP decliners -> identity -> CRM owner history -> activity notes; CRM lost renewals -> ERP service invoices of the same customers.
- **Hypothesis testing:** examples include ruling out market mis-tagging and stale deals (Q05), separating one-off project customers from lost accounts by product mix (Q07), checking the deal-to-invoice assumption (Q09), testing a renewal owner's activity before rejecting a neglect hypothesis (BC-t3), and cross-checking loss reasons against note text (BA-t3, BC-t3).
- **Convergence:** the 9 open-ended runs converge on the same three issues (German expansion, Danish renewals, discounting). Depth varies: 26-58 calls, and only runs above about 50 calls reached customer level.

## Where the gaps come from (for the post-baseline decision; nothing tuned yet)

- **Investigation strategy / stopping criterion (main gap).** The key-account attrition was reachable with the same tools in every run (benchmark runs and 3 open-ended runs found it). Open-ended runs that stopped at about 26-35 calls missed it, two of them after spotting the signal. A prompt or strategy change (for example 'decompose the largest variances to entity level before concluding') is a candidate, but it is not applied.
- **Tool description / primitive gap (minor).** Period parameters and `first_invoice_from/to` do not accept a single date (`2025-09-01`). This caused 10 errors, which agents fixed by trial and error.
- **Phase 2A defect (found, not fixed per instructions).** `compare_rows` (`phase2/runtime/query/common.py` line 74) raises `TypeError` when a comparison measure that can be null (for example `avg_won_value_dkk` for a group with no wins) is null in the current period but not in the comparison. It surfaced in Q06 and Q09 as a generic tool error; both agents worked around it.
- **Semantic metadata (candidate).** Q01's window error suggests the semantics could state that renewal deals close before the contract term they renew, so their effect shows in the following period's billing. This describes the systems, not the scenario.
- **Too many tools:** no evidence. 31 of 33 used appropriately.
- **Weak model reasoning:** not observed. Causal language was careful throughout.

## Limitations of this baseline

- **Sample:** one model (Claude Opus 5 via Claude Code headless), one run per benchmark question, three per open-ended question. The PASS rate should be confirmed with more trials and at least one other model.
- **Evaluator independence:** the evaluator is the same assistant that designed the Phase 1 scenario and the Phase 2A tools. Assessments were made against the answer key with spot-checks, but an independent human review of `reports/runs/*.md` is recommended.
- **Tool design bias:** the Phase 2A tools are generic, but some were designed with the scenario in mind (owner history, first-invoice filters, like-for-like salary change, `sort_by='revenue_dkk_change'` guidance in a description). These may make discovery easier than a less curated interface would. This is worth an ablation later.
- **Signal strength:** the synthetic data carries a strong, engineered signal. Real data would be noisier.
- **Windows:** agents used Jan-Aug where the reference uses H1. Figures were judged against the equivalent window.
- **Cost:** the reported cost ($35.99 total) is the CLI's API-equivalent figure for this account.

## Files

- `results/runs/<run_id>.json`: machine-readable run records (question, model, config, isolation check, ordered trace with full tool arguments and results, final answer, stats, usage, errors)
- `results/raw/`: raw CLI event streams, server-side call logs and stderr per run
- `reports/runs/<run_id>.md`: per-run evaluation with dimensions, trace and answer
- `reports/evaluations.json`: machine-readable evaluation table
- `reports/worksheets/`, `reports/reference_facts.json`: evaluator material (answer-key derived)