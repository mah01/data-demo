"""
EVALUATION SIDE ONLY.

    phase2/.venv/bin/python -m phase2.evaluation.evaluator.evaluate worksheets   # review material per run
    phase2/.venv/bin/python -m phase2.evaluation.evaluator.evaluate report       # merge assessments -> reports

Step 1 renders, for every run, the ordered tool trace, the final answer, the
automatic discovery signals and the reference facts relevant to the question.
Step 2 merges the human assessments (evaluator/assessments.json: PASS /
PARTIAL / FAIL with per-dimension notes) into per-run evaluation files, a
machine-readable evaluation table and the baseline report.
"""
import json
import sys
from pathlib import Path

from . import signals
from .reference import build as build_reference

EVAL = Path(__file__).resolve().parents[1]
RUNS = EVAL / "results" / "runs"
REPORTS = EVAL / "reports"
ASSESSMENTS = Path(__file__).parent / "assessments.json"
DIMENSIONS = ["factual_correctness", "coverage", "causal_reasoning", "cross_system_reasoning", "evidence",
              "unsupported_claims", "investigation_quality"]
RELEVANT = {"Q01": ["company", "markets_h1_revenue"], "Q02": ["company", "bridge", "markets_h1_gross_profit", "personnel"],
            "Q03": ["personnel"], "Q04": ["personnel", "germany_sales", "bridge"],
            "Q05": ["germany_sales", "markets_h1_revenue", "germany_customers"], "Q06": ["germany_customers", "germany_sales"],
            "Q07": ["germany_customers"], "Q08": ["denmark"], "Q09": ["counterfactual", "germany_sales", "company"],
            "Q10": ["bridge", "story"], "BA": ["story", "company", "bridge"], "BB": ["story", "company", "bridge"],
            "BC": ["story", "company", "bridge"]}


def load_runs():
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(RUNS.glob("*.json"))]


def _m(v):
    return f"{v / 1e6:,.2f}m" if isinstance(v, (int, float)) and abs(v) >= 1e4 else v


def _fmt_facts(obj, indent=0):
    pad = "  " * indent
    if isinstance(obj, dict):
        return "\n".join(f"{pad}- {k}: " + (("\n" + _fmt_facts(v, indent + 1)) if isinstance(v, (dict, list)) and v and
                                             not all(isinstance(x, (int, float)) for x in (v if isinstance(v, list) else []))
                                             else str(_fmt_list(v))) for k, v in obj.items())
    if isinstance(obj, list):
        return "\n".join(f"{pad}- {json.dumps(x, default=str, ensure_ascii=False)[:400]}" for x in obj)
    return f"{pad}{obj}"


def _fmt_list(v):
    if isinstance(v, list) and all(isinstance(x, (int, float)) for x in v):
        return " -> ".join(str(_m(x)) if abs(x) >= 1e4 else f"{x:.4f}" for x in v)
    return _m(v) if isinstance(v, (int, float)) else v


def trace_lines(run):
    out = []
    for c in run["tool_calls"]:
        args = json.dumps(c["arguments"], ensure_ascii=False)
        err = " **ERROR**" if c["is_error"] else ""
        out.append(f"{c['seq']:>3}. `{c['tool']}` {args}{err}")
    return out


def worksheets():
    facts = build_reference()
    (REPORTS / "worksheets").mkdir(parents=True, exist_ok=True)
    for run in load_runs():
        q = run["question"]
        sig = signals.detect(run)
        s = run["stats"]
        lines = [f"# Worksheet {run['run_id']}", "", f"**Question ({q['kind']}):** {q['text']}", "",
                 f"Status: {run['status']} | model {run['model']['reported']} | {s['tool_call_count']} tool calls | "
                 f"systems {', '.join(s['systems_queried'])} | {run['elapsed_s']} s | cost ${run['total_cost_usd']} | "
                 f"isolation ok: {run['isolation']['ok']}", "", "## Tool trace", "", *trace_lines(run), "",
                 "## Final answer", "", run["final_answer"] or "(none)", "", "## Automatic discovery signals", "",
                 "| item | stated | investigated | snippet |", "|---|---|---|---|"]
        for k, v in sig.items():
            lines.append(f"| {k} | {v['stated']} | {v['investigated']} | {(v['snippet'] or '').replace('|', '/')[:160]} |")
        lines += ["", "## Reference facts (evaluation only)", ""]
        for key in RELEVANT[q["id"]]:
            lines += [f"### {key}", _fmt_facts(facts[key]), ""]
        (REPORTS / "worksheets" / f"{run['run_id']}.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"worksheets written to {REPORTS / 'worksheets'}")


def report():
    runs = {r["run_id"]: r for r in load_runs()}
    assess = json.loads(ASSESSMENTS.read_text(encoding="utf-8"))
    (REPORTS / "runs").mkdir(parents=True, exist_ok=True)
    table = []
    for rid, run in runs.items():
        a = assess["runs"].get(rid)
        if not a:
            print(f"WARNING: no assessment for {rid}")
            continue
        sig = signals.detect(run)
        s = run["stats"]
        usage = run.get("usage") or {}
        row = {"run_id": rid, "question_id": run["question"]["id"], "kind": run["question"]["kind"],
               "question": run["question"]["text"], "classification": a["classification"],
               "tool_calls": s["tool_call_count"], "systems": s["systems_queried"], "elapsed_s": run["elapsed_s"],
               "output_tokens": usage.get("output_tokens"), "cost_usd": run.get("total_cost_usd"),
               "discoveries": a.get("discoveries", {}), "auto_signals": sig, "dimensions": a["dimensions"],
               "summary": a["summary"]}
        table.append(row)
        md = [f"# Evaluation {rid}: {a['classification']}", "", f"**Question ({run['question']['kind']}):** "
              f"{run['question']['text']}", "",
              f"Model `{run['model']['reported']}` · {s['tool_call_count']} tool calls · systems: "
              f"{', '.join(s['systems_queried'])} · {run['elapsed_s']} s · output tokens {usage.get('output_tokens')} · "
              f"cost ${run.get('total_cost_usd')} · tool errors {s['tool_errors']} · repeated identical calls "
              f"{s['repeated_identical_calls']}", "", f"**Summary.** {a['summary']}", "", "| dimension | assessment |",
              "|---|---|"]
        md += [f"| {d.replace('_', ' ')} | {a['dimensions'].get(d, '')} |" for d in DIMENSIONS]
        if a.get("discoveries"):
            md += ["", "**Discoveries** (manual; ✓ found, ~ partly, ✗ not found, – not applicable)", ""]
            md += [f"- {signals.DISCOVERIES[k]}: {v}" for k, v in a["discoveries"].items()]
        md += ["", "## Tool trace", "", *trace_lines(run), "", "## Final answer", "", run["final_answer"] or "(none)"]
        (REPORTS / "runs" / f"{rid}.md").write_text("\n".join(md), encoding="utf-8")
    (REPORTS / "evaluations.json").write_text(json.dumps(table, indent=2, ensure_ascii=False), encoding="utf-8")
    write_baseline(table, assess, runs)


def write_baseline(table, assess, runs):
    bench = [r for r in table if r["kind"] == "benchmark"]
    blind = [r for r in table if r["kind"] == "blind"]
    cnt = lambda rows, c: sum(1 for r in rows if r["classification"] == c)
    all_runs = list(runs.values())
    tot = lambda f: sum((f(r) or 0) for r in all_runs)
    md = ["# Phase 2B baseline: blind agent evaluation", "",
          f"Protocol `{all_runs[0]['protocol_version']}` · model `{all_runs[0]['model']['reported']}` via Claude Code "
          f"{all_runs[0]['config']['cli_version']} headless · {len(all_runs)} runs, each in a fresh isolated process · "
          f"system prompt sha256 `{all_runs[0]['config']['system_prompt_sha256'][:12]}…`", "",
          assess["overall"]["headline"], "",
          "## Results at a glance", "",
          f"- Benchmark questions: **{cnt(bench, 'PASS')} PASS / {cnt(bench, 'PARTIAL')} PARTIAL / {cnt(bench, 'FAIL')} FAIL** (1 run each)",
          f"- Open-ended questions: **{cnt(blind, 'PASS')} PASS / {cnt(blind, 'PARTIAL')} PARTIAL / {cnt(blind, 'FAIL')} FAIL** (3 runs each)",
          f"- Tool calls: {tot(lambda r: r['stats']['tool_call_count'])} total, "
          f"{min(r['stats']['tool_call_count'] for r in all_runs)}–{max(r['stats']['tool_call_count'] for r in all_runs)} per run · "
          f"tool errors {tot(lambda r: r['stats']['tool_errors'])} · "
          f"wall time {min(r['elapsed_s'] for r in all_runs):.0f}–{max(r['elapsed_s'] for r in all_runs):.0f} s per run · "
          f"reported cost ${tot(lambda r: r.get('total_cost_usd')):.2f}", "",
          "| run | question | result | tool calls | systems | time (s) | cost ($) |", "|---|---|---|---|---|---|---|"]
    for r in table:
        md.append(f"| [{r['run_id']}](runs/{r['run_id']}.md) | {r['question']} | **{r['classification']}** | {r['tool_calls']} | "
                  f"{', '.join(x for x in r['systems'] if x != 'meta')} | {r['elapsed_s']:.0f} | {r['cost_usd']:.2f} |")
    items = list(signals.DISCOVERIES)
    md += ["", "## Open-ended discovery matrix", "",
           "Manual assessment of what each open-ended run surfaced without being led (✓ found, ~ partly, ✗ not found).", "",
           "| discovery | " + " | ".join(r["run_id"] for r in blind) + " | found in |", "|---|" + "---|" * (len(blind) + 1)]
    for k in items:
        vals = [r["discoveries"].get(k, "✗") for r in blind]
        md.append(f"| {signals.DISCOVERIES[k]} | " + " | ".join(vals) + f" | {sum(v == '✓' for v in vals)}/{len(blind)} |")
    md += ["", "## Benchmark discovery coverage", "", "| discovery | " + " | ".join(r["question_id"] for r in bench) + " |",
           "|---|" + "---|" * len(bench)]
    for k in items:
        md.append(f"| {signals.DISCOVERIES[k]} | " + " | ".join(r["discoveries"].get(k, "–") for r in bench) + " |")
    for section in ("discovers", "misses", "misinterprets", "invents", "investigation_behaviour", "failure_sources",
                    "limitations"):
        if section in assess["overall"]:
            md += ["", f"## {assess['overall'][section]['title']}", "", assess["overall"][section]["text"]]
    md += ["", "## Files", "",
           "- `results/runs/<run_id>.json`: machine-readable run records (question, model, config, isolation check, "
           "ordered trace with full tool arguments and results, final answer, stats, usage, errors)",
           "- `results/raw/`: raw CLI event streams, server-side call logs and stderr per run",
           "- `reports/runs/<run_id>.md`: per-run evaluation with dimensions, trace and answer",
           "- `reports/evaluations.json`: machine-readable evaluation table",
           "- `reports/worksheets/`, `reports/reference_facts.json`: evaluator material (answer-key derived)"]
    (REPORTS / "baseline_report.md").write_text("\n".join(md), encoding="utf-8")
    print(f"report written: {REPORTS / 'baseline_report.md'}")


if __name__ == "__main__":
    {"worksheets": worksheets, "report": report}[sys.argv[1] if len(sys.argv) > 1 else "worksheets"]()
