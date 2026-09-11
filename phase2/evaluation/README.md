# Phase 2B: Blind agent evaluation

This experiment asks whether a general-purpose LLM, given **only** the read-only Phase 2A MCP tools, can investigate NordFlow and reach the business conclusions encoded in Phase 1.

**Baseline results:** [`reports/baseline_report.md`](reports/baseline_report.md).

```
evaluation/
  runner/       agent side: frozen protocol, isolated runs, traced MCP entrypoint
  evaluator/    evaluation side: answer-key reference, discovery signals, assessments, report builder
  results/      runs/<run_id>.json   machine-readable run records
                raw/<run_id>.*       raw CLI event stream, server-side call log, stderr
  reports/      baseline_report.md, runs/<run_id>.md, evaluations.json,
                worksheets/, reference_facts.json (evaluator material)
```

## Protocol (`runner/protocol.py`, version `2B-baseline-1`)

**Model.** `claude-opus-5`, run through the Claude Code CLI in headless mode (`claude -p`). The CLI version is recorded in every run.

**What the agent receives:**

1. A neutral system instruction. It replaces the CLI's default system prompt entirely. Its SHA-256 is stored in every run record.
   > You are assisting senior management in analysing company performance.
   > Company context: NordFlow A/S is a Danish B2B industrial supplier operating in Denmark, Sweden and Germany.
   > Use the available company-data tools to investigate questions. Do not assume causes without evidence. Inspect additional data where necessary. Clearly distinguish facts from interpretation. Support significant conclusions with the source system and relevant metric.
2. One question. There are 10 benchmark questions (1 run each) and 3 open-ended questions (3 runs each).
3. The 33 Phase 2A MCP tools, with their descriptions and the server's instructions. Nothing else.

**Isolation.** Every run is a new process, started in a fresh, empty temporary working directory. The CLI is launched with these flags:

| Flag | Effect |
|---|---|
| `--tools ""` | All built-in tools disabled: no files, shell, web or subagents |
| `--strict-mcp-config` + `--mcp-config` | Only the NordFlow server is loaded |
| `--allowedTools mcp__nordflow` + `--permission-mode dontAsk` | Only NordFlow tools can run; anything else is denied |
| `--setting-sources ""` | No user or project settings |
| `--disable-slash-commands` | No skills |
| `--no-session-persistence` | No session carried between runs |

The runner checks the CLI's init event and records `isolation.ok`: only `mcp__nordflow__*` tools may be exposed. No run shares context with another.

**Tools served.** `runner/traced_server.py` serves exactly the Phase 2A operations: the same runtime, names, descriptions, annotations and error handling as `phase2/mcp/server.py`. It also appends every call to a JSONL log with its arguments, full result, status and duration. Phase 2A code is unchanged.

**Not tuned.** The prompt, the tools and the protocol were frozen before the first run and were not changed in response to any result. A changed protocol is a new experiment: bump `PROTOCOL_VERSION` and keep the baseline. Existing run records are never overwritten.

```bash
phase2/.venv/bin/python -m phase2.evaluation.runner.run_all --workers 4   # all 19 runs (skips existing records)
phase2/.venv/bin/python -m phase2.evaluation.runner.run_agent BA 4        # one extra trial of a question
phase2/.venv/bin/python -m phase2.evaluation.runner.reattach               # re-link server logs to run records
```

## Run record (`results/runs/<run_id>.json`)

Each record contains:

- the question, trial, model (requested and reported, with usage per model) and full config (command, system prompt and its hash, limits, permission mode)
- the isolation check
- status, timestamps and elapsed time
- the final answer
- stats: tool calls, errors, distinct tools, systems queried, calls per system, repeated identical calls, turns
- token usage and reported cost
- errors
- an ordered trace mixing assistant narration, tool calls and tool-result markers
- `tool_calls`: every call with its full arguments, the full result text, an error flag, and the matched server-side sequence number, duration and status
- paths to the raw files

## Evaluation (`evaluator/`, evaluation side only)

The evaluator is the only code that reads the Phase 1 answer key. The runner never imports it, and nothing it produces is ever passed to an agent.

- **`reference.py`** builds `reports/reference_facts.json` from `ground_truth.json` and the Phase 1 analysis over the frozen dataset.
- **`signals.py`** flags heuristically, per discovery item, whether it was *stated* in the answer and whether it was *investigated* in the trace. These flags are aids to review, not verdicts.
- **`evaluate.py worksheets`** renders review material for each run: trace, answer, signals and the relevant reference facts.
- **`assessments.json`** is the human assessment for each run. It gives PASS / PARTIAL / FAIL with notes on factual correctness, coverage, causal reasoning, cross-system reasoning, evidence, unsupported claims and investigation quality, plus a discovery checklist (✓ found, ~ partly, ✗ not found, – not applicable).
- **`evaluate.py report`** merges these into `reports/runs/<run_id>.md`, `reports/evaluations.json` and `reports/baseline_report.md`.

Figures quoted by agents were spot-checked against the runtime during assessment.
