# NordFlow demo — project handoff

State of the repository, for picking the work up in a fresh session.
Last updated: 2026-09-28. Current branch: `main`, working tree clean.

---

## 1. Purpose and product concept

We are exploring a product for executive decision support: senior management asks
questions in plain language instead of requesting reports from departments, and an
AI agent answers by querying the company's separate business systems (finance/ERP,
CRM, payroll) and reasoning across them.

To demonstrate that idea safely, the project builds its own fictional company —
**NordFlow A/S**, a Danish B2B pump supplier operating in Denmark, Sweden and Germany —
with synthetic but internally coherent data, exposes it through generic read-only
tools, measures whether an LLM can investigate it unaided, and finally wraps it in a
browser demo.

Four phases, all complete:

| Phase | What it is | Status |
|---|---|---|
| 1 | Deterministic synthetic dataset + validation | done, tagged `phase1-v1.1` |
| 2A | Read-only runtime + MCP server over that data | done |
| 2B | Blind agent evaluation (can an LLM find the story?) | done, tagged `phase2b-baseline-v1.0` |
| 3 | Interactive browser demo | done, committed |
| 3b | Deployment hardening (auth, secrets, run guide) | done, committed; **not deployed** |

---

## 2. Git state

Branches:
- **`main` — everything.** On 2026-09-28 `phase3-demo` was merged into `main` as a fast-forward
  (the branches were identical), so `main` now holds Phase 1 v1.1, Phase 2A + 2B, Phase 3 and the
  deployment work. Continue here.
- `phase3-demo` — same commit as `main`; kept as a label, safe to delete.
- `phase1-maintenance` — Phase 1 patch line; holds the v1.1 commit.
- `phase2-agent-prototype` — Phase 2A + 2B baseline (frozen at the baseline tag).

Commits on `main` (newest first):

| Commit | Contents |
|---|---|
| `722b9c8` | OpenAI agent option (`NORDFLOW_AGENT=openai`, default `gpt-5.6-sol`) for the deployment |
| `a19ee0b` | Handoff: record the hardening commit |
| `5a9d34b` | Phase 3b deployment hardening (auth, secret validation, DEPLOY.md) |
| `d543902` | This handoff document |
| `46884aa` | Phase 3 interactive demo |
| `df08a6f` | Phase 2A defect fixes + regression tests, on v1.1 data |
| `be399ac` | Merge of the Phase 1 v1.1 patch into the Phase 2/3 line |
| `8391920` | Phase 1 v1.1 patch release (tagged `phase1-v1.1`) |
| `9849ecb` | Phase 2 baseline: runtime, MCP server, 2B evaluation (tagged `phase2b-baseline-v1.0`) |
| `867de08` | Phase 1 v1.0 (tagged `phase1-v1.0`) |

Tags: `phase1-v1.0`, `phase1-v1.1`, `phase2b-baseline-v1.0`.

**Everything is committed.** Nothing is pushed; there is no remote. Not in git by design:
`phase2/.venv/` (local virtualenv), `phase3/logs/` (runtime logs; one example run is
committed at `phase3/docs/example-conversation.jsonl`), `__pycache__`, `.pytest_cache`.

---

## 3. Repository layout

```
data/                  Phase 1 generated dataset (erp/, crm/, payroll/, mappings/) — the only runtime data
src/                   Phase 1 generator + validator + robustness + manifest  (ANSWER KEY SIDE)
ground_truth.json      Phase 1 intended story, metric definitions, tolerances   (ANSWER KEY SIDE)
data_manifest.json     SHA-256 of every generated file (release integrity)
README.md              Phase 1 documentation (company, story, schemas, releases)

phase2/runtime/        Adapters (erp/crm/payroll/identity), semantics, periods, query layer
phase2/mcp/server.py   Read-only MCP server (33 tools)
phase2/tests/          97 tests incl. boundary + regression tests
phase2/evaluation/     Phase 2B runner, results, evaluator, baseline report      (ANSWER KEY SIDE)
phase2/TOOLS.md        Generated tool reference; phase2/README.md = architecture

phase3/server.py       Demo backend (Starlette + SSE)
phase3/config.py       Settings, secret validation, redaction (environment-only)
phase3/auth.py         Shared HTTP Basic middleware
phase3/agent/          prompt.py, base.py, api_agent.py (Anthropic SDK), openai_agent.py (OpenAI Responses), cli_agent.py (Claude Code)
phase3/mcp_server.py   Phase 2A tools + present_answer
phase3/web/            index.html, app.js, style.css (no build step)
phase3/tests/          22 tests (no LLM calls); phase3/README.md = demo docs
phase3/DEPLOY.md       Private 1 vCPU / 2 GB VM deployment guide (nothing deployed yet)
phase3/requirements.txt  Phase 2 requirements + the web stack (starlette, uvicorn, sse-starlette) + openai
HANDOFF.md             this file
```

---

## 4. The encoded business story (answer key — never shown to an agent)

H1 2026 vs H1 2025: revenue +3.6% (85.8m → 88.8m DKK) but operating profit −33%
(12.0m → 8.0m), margin 14.0% → 9.0%. Causes:

1. **German sales expansion that has not paid off** — headcount 8 → 12, pipeline +35%,
   win rate 31% → 19% (new reps ~12%, veterans ~23%), German revenue −8%.
2. **German key-account attrition** — Rheinmark Chemie and Brandauer Papierwerke were
   reassigned to new hires in Sep/Oct 2025 and together lost ~3.6m DKK, more than
   Germany's whole net decline.
3. **Danish mix/margin erosion** — revenue +9.5% but service −23% and gross profit down.
4. **Red herring** — a ~3.9% pay rise explains only ~0.56m of the decline.

Sweden is a stable control market. Full detail: `ground_truth.json` and README §2.

---

## 5. Architecture

```
Browser (phase3/web) ──SSE── HTTP Basic auth (phase3/auth.py, every route but /healthz)
                                   │
                                   ▼
                      Demo backend (phase3/server.py) · config+secrets (phase3/config.py)
                                   │
                                   ▼
          Agent: Anthropic SDK loop  |  OpenAI Responses loop  |  Claude Code headless
                                   │ MCP (stdio)
                                   ▼
                 phase3/mcp_server.py = Phase 2A tools (33) + present_answer
                                   │
                                   ▼
        Phase 2A runtime: ERP · CRM · Payroll · Identity adapters → data/ (v1.1)
```

Key properties:
- The three systems stay separate; there is no unified database. Cross-system questions
  are composed from per-system operations plus the `identity_*` mapping tools.
- Query operations compute facts and aggregations only — never conclusions
  (`get_win_rate(market, period)`, not `explain_why_germany_is_failing()`).
- Everything is read-only; MCP tools are annotated `read_only_hint`.
- Money is DKK; each system converts with its own rates. Periods are inclusive.
- CRM deal market falls back: `deals.market` → company country → deal currency; results
  report which source was used.

---

## 6. Boundaries (the important rule)

**Runtime side** (`phase2/runtime`, `phase2/mcp`, `phase3`) may read only:
`data/erp`, `data/crm`, `data/payroll`, `data/mappings`, plus the semantic metadata in
`phase2/runtime/semantics.py`.

**Answer-key side** (evaluation only): `ground_truth.json`, `src/*` (generator, validator,
robustness, manifest), `phase2/evaluation/**` including `reports/reference_facts.json`
and the baseline report.

Enforced by tests, not convention:
- `phase2/tests/test_boundary.py` — parses every runtime/MCP module for forbidden imports,
  fails on any mention of answer-key files, and monkeypatches `open` while running **every**
  operation to assert only `*.csv` under the four system folders is read.
- `phase3/tests/test_demo.py::test_demo_code_has_no_access_to_evaluation_material` — same idea
  for the demo, and also fails if demo code mentions scenario entities.

The agent prompt (`phase3/agent/prompt.py`) is the neutral Phase 2B instruction plus
presentation rules. It contains no scenario hints. Keep it that way.

---

## 7. How to run things

```bash
python3 -m venv phase2/.venv && phase2/.venv/bin/pip install -r phase3/requirements.txt   # once (superset)

# Phase 1
python3 src/generate.py        # or make data      — regenerate dataset (deterministic, seed 4217)
python3 src/validate.py        # or make validate  — 106 checks + executive walkthrough; exit 1 on failure
python3 src/robustness.py      # or make robustness— all checks across 100 seeds (~15 s)
make verify                    # ./data matches data_manifest.json
make verify-regen              # a fresh regeneration matches it (catches generator/Python drift)

# Phase 2
phase2/.venv/bin/python -m pytest phase2/tests          # 97 tests
phase2/.venv/bin/python -m phase2.mcp.server            # MCP server on stdio
phase2/.venv/bin/python -m phase2.evaluation.runner.run_all      # re-run 2B (new experiment; don't overwrite baseline)

# Phase 3 demo
make demo          # http://127.0.0.1:8765
make demo-check    # validate configuration + secrets + data, then exit (no port, no model call)
make demo-test     # Phase 2 + Phase 3 tests (119), no LLM calls
```

Demo environment: `NORDFLOW_MODE` (`local` | `deploy`), `NORDFLOW_AGENT` (`api` | `openai` | `cli` | `auto`;
`openai` is never picked by `auto`), `ANTHROPIC_API_KEY` (api mode), `OPENAI_API_KEY` (openai mode), `NORDFLOW_AUTH_USER`/`NORDFLOW_AUTH_PASSWORD` (Basic auth),
`NORDFLOW_MODEL`, `NORDFLOW_EFFORT`, `NORDFLOW_HOST`/`NORDFLOW_PORT`,
`NORDFLOW_MAX_CONVERSATIONS`/`NORDFLOW_MAX_QUESTION_CHARS`. Full table and deployment steps:
`phase3/DEPLOY.md`. Configuration is environment-only and validated at startup; a missing
secret prints every problem at once and exits 2.

Expected state today: validation 106/106, robustness 100/100 seeds, tests 119 passed,
manifest `ae8eeb8d…8bba`.

---

## 8. Design decisions worth knowing

- **Headcount ~50→54, not ~110→120.** At 110 employees the specified personnel costs would
  imply implausible salaries. All financial targets were kept instead.
- **Only two calibration anchors**, both on H1 2025: one scale factor on base salaries,
  one on recurring operating costs. Nothing about 2026 is calibrated; those results emerge.
- **Scenario invariants** (`src/config.py`) enforce five story-critical outcomes by
  construction so they hold for any seed, while *which* customers/deals are affected stays
  random. Verified by `robustness.py` across 100 seeds.
- **Hidden world model**: the generator keeps one set of facts and renders each system's own
  view (different IDs, names, currencies, gaps). It is never exported.
- **Phase 2B protocol is frozen** (`2B-baseline-1`). Re-running with changes = a new experiment;
  bump `PROTOCOL_VERSION` and keep the baseline results.
- **Deployment mode is a switch, not a fork.** `NORDFLOW_MODE=deploy` keeps the same code
  path but makes the loose local defaults strict: API agent only, API key required, Basic
  auth required with a 12-character minimum, loopback bind unless TLS is declared in front.
  Local `make demo` is unchanged, so the demo stays easy to run on a laptop.
- **Provider is swappable at the agent layer only.** `api_agent.py` (Anthropic) and
  `openai_agent.py` (OpenAI Responses, `store=False`, encrypted reasoning passed back) run the
  same loop over the same MCP tools, prompt, `present_answer` contract, evidence check and logs.
  OpenAI was added because the deployment uses existing OpenAI credits; default `gpt-5.6-sol`.
- **Demo answer contract**: the agent must finish by calling `present_answer` (headline,
  key points, evidence with source system, follow-ups). The tool just echoes; the UI renders
  conclusion and evidence separately.

---

## 9. Phase 2B baseline result (one-line summary)

Claude Opus 5, given only the MCP tools and a neutral instruction, reached the story in
**all 19 runs** (10 benchmark + 3 open-ended × 3). Revenue-vs-profit, Germany, the sales
expansion, conversion collapse and the Danish erosion were found in every open-ended run;
the German key accounts in only 3 of 9 (the misses were stopping early, not missing tools).
No invented facts. No run fell for the salary red herring. Full detail:
`phase2/evaluation/reports/baseline_report.md`.

---

## 10. Known limitations and open issues

Data//validation:
- Synthetic signal is strong and clean; real data would be noisier.
- `make verify-regen` can differ on a different Python version (the `random` module's
  sequences change); the committed data is unaffected.

Runtime:
- Some Phase 2A tools were designed with the scenario in mind (owner history, first-invoice
  filters, like-for-like salary change). Generic, but worth an ablation before claiming
  the tool surface is neutral.
- `crm_find_companies` and `identity_crm_users_to_employees` were never used by any agent.

Demo:
- Answers take ~30–50 s at medium effort; deep questions longer.
- **OpenAI mode is unmeasured.** All quality evidence (Phase 2B, example conversation) is for
  Claude Opus 5. `openai` mode is covered only by tests with a scripted model; its answer
  quality and real cost per question are unknown until it runs. Estimated from Claude token
  counts at list prices: ~$0.15–0.30 per typical demo question with `gpt-5.6-sol`.
- **API mode has never run live** (no API key on this machine). It is covered only by tests
  with a scripted model against the real MCP server. CLI mode is what was demonstrated.
- Conversations live in server memory; a server restart loses them (`?c=<id>` re-renders
  while the process lives), and only the newest `NORDFLOW_MAX_CONVERSATIONS` (50) are kept.
- Access control is one shared Basic-auth credential: no accounts, no rate limiting, no
  brute-force lockout, no audit trail, and no protection of API spend beyond keeping the
  password private. Basic credentials are clear text, so a deployment must sit behind TLS.
- The deployment path itself is untested end to end: `phase3/DEPLOY.md` has been written and
  the server verified locally in `deploy` mode (401/200 behaviour, health check), but no VM,
  systemd unit or Caddy configuration has been run anywhere.
- CLI mode depends on a local Claude Code login and writes sessions under `~/.claude/projects/`.
- Evidence verification is coarse (see the next section).

Evaluation:
- One model, one run per benchmark question, three per open-ended question.
- The evaluator was the same assistant that designed the scenario and tools; an independent
  human review of `phase2/evaluation/reports/runs/*.md` is still worth doing.

---

## 11. Next tasks (agreed, not yet implemented)

Two small demo-hardening items. Nothing else was agreed; do these before adding features.

**A. Evidence must trace to an actual MCP result.**
Today `finish_turn` in `phase3/agent/base.py` only checks that the *source system* named in
an evidence row was queried somewhere in the conversation (`verified_source`), and the UI
marks an unconfirmed row with "?". That does not check the number itself.
Wanted: tie each evidence row to the specific tool call it came from — e.g. have
`present_answer` carry the originating tool (and ideally the call sequence number), verify
that call exists in this conversation's trace, and where practical confirm the quoted value
appears in that call's result. Unverifiable rows should be visibly marked in the UI, not
silently accepted. Keep the check honest: if it cannot confirm a value, say so.

**B. Comparison periods must be explicit.**
Agents choose their own window (Jan–Aug year-to-date, H1, quarters) and occasionally compare
mismatched ranges; one Phase 2B run drew a wrong conclusion from a badly scoped window.
Wanted: every answer states the periods compared, and the demo makes the comparison explicit —
e.g. require a period/comparison field in `present_answer`, echo it in the answer header, and
have the prompt insist on a like-for-like window. Consider surfacing the runtime's existing
partial-coverage note (it already warns when a period is only partly covered by a system).

---

## 12. Do NOT build yet

Out of scope until explicitly requested:
- Real e-conomic / HubSpot / Danløn integrations, or any external/public data.
- User management, permissions, roles, billing, multi-tenancy, rate limiting or SSO. The
  shared Basic-auth credential in `phase3/auth.py` is all the access control this demo gets.
- Deploying anywhere: `phase3/DEPLOY.md` is a guide to follow by hand when asked, not a
  pipeline to automate.
- A vector database or RAG layer (the MCP query tools are the access path).
- Dashboards, charts, or recreations of the real SaaS UIs.
- Mobile optimisation beyond basic responsiveness.
- Changes to Phase 1 data or the business story, except a genuine data defect — and then as a
  new patch release (bump `RELEASE` in `src/manifest.py`, validate, robustness, rewrite the
  manifest, commit, tag).
- Re-running or editing the Phase 2B baseline results; they are a preserved artefact.
