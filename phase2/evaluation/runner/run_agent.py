"""
Run ONE evaluation question in a fresh, isolated agent context and persist the run record.

    phase2/.venv/bin/python -m phase2.evaluation.runner.run_agent Q01 1

Isolation: a new `claude -p` process per run, empty temporary working directory,
built-in tools disabled (--tools ""), only the NordFlow MCP server
(--strict-mcp-config), no user/project settings, no slash commands/skills,
no session persistence, neutral system prompt replacing the default one.
The runner never reads ground truth or evaluation material.
"""
import json
import shutil
import subprocess
import sys
import tempfile
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from phase2.runtime.sources import REPO_ROOT

from . import protocol

EVAL_DIR = Path(__file__).resolve().parents[1]
RUNS_DIR = EVAL_DIR / "results" / "runs"
RAW_DIR = EVAL_DIR / "results" / "raw"
VENV_PYTHON = REPO_ROOT / "phase2" / ".venv" / "bin" / "python"
SERVER_KEY = "nordflow"
TOOL_PREFIX = f"mcp__{SERVER_KEY}__"


def _now():
    return datetime.now(timezone.utc).isoformat()


def _text(content):
    if isinstance(content, str):
        return content
    return "\n".join(c.get("text", "") for c in content or [] if isinstance(c, dict) and c.get("type") == "text")


def build_command(question, mcp_config):
    return ["claude", "-p", question["text"],
            "--model", protocol.MODEL,
            "--system-prompt", protocol.SYSTEM_PROMPT,
            "--tools", "",
            "--mcp-config", str(mcp_config), "--strict-mcp-config",
            "--allowedTools", f"mcp__{SERVER_KEY}",
            "--permission-mode", "dontAsk",
            "--setting-sources", "",
            "--disable-slash-commands",
            "--no-session-persistence",
            "--max-turns", str(protocol.MAX_TURNS),
            "--output-format", "stream-json", "--verbose"]


def parse_stream(lines):
    init, result, trace, calls, pending = None, None, [], [], {}
    for line in lines:
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        kind = ev.get("type")
        if kind == "system" and ev.get("subtype") == "init":
            init = ev
        elif kind == "assistant":
            for block in ev.get("message", {}).get("content", []):
                if block.get("type") == "text" and block.get("text", "").strip():
                    trace.append({"type": "assistant_text", "text": block["text"]})
                elif block.get("type") == "tool_use":
                    call = {"seq": len(calls) + 1, "tool_use_id": block.get("id"),
                            "tool": block.get("name", "").removeprefix(TOOL_PREFIX), "raw_tool_name": block.get("name"),
                            "arguments": block.get("input", {}), "is_error": None, "result_text": None}
                    calls.append(call)
                    pending[block.get("id")] = call
                    trace.append({"type": "tool_call", "seq": call["seq"], "tool": call["tool"],
                                  "arguments": call["arguments"]})
        elif kind == "user":
            content = ev.get("message", {}).get("content", [])
            for block in content if isinstance(content, list) else []:
                if block.get("type") == "tool_result" and block.get("tool_use_id") in pending:
                    call = pending.pop(block["tool_use_id"])
                    call["is_error"] = bool(block.get("is_error"))
                    call["result_text"] = _text(block.get("content"))
                    trace.append({"type": "tool_result", "seq": call["seq"], "is_error": call["is_error"],
                                  "result_chars": len(call["result_text"] or "")})
        elif kind == "result":
            result = ev
    return init, result, trace, calls


def attach_server_log(calls, server_log):
    """Match client tool calls to server-side records (same tool, client arguments contained in the server's
    arguments, which also carry defaults), in order, for timing and server-side status."""
    records = []
    if server_log.exists():
        records = [json.loads(l) for l in server_log.read_text(encoding="utf-8").splitlines() if l.strip()]
    used = set()
    for call in calls:
        for i, rec in enumerate(records):
            if i not in used and rec["tool"] == call["tool"] and \
                    all(rec["arguments"].get(k) == v for k, v in call["arguments"].items()):
                used.add(i)
                call.update(server_seq=rec["seq"], server_elapsed_ms=rec["elapsed_ms"], server_ok=rec["ok"],
                            server_error=rec.get("error"))
                break
    return records


def stats(calls, result):
    systems = Counter(c["tool"].split("_")[0] for c in calls if c["tool"])
    keys = Counter((c["tool"], json.dumps(c["arguments"], sort_keys=True)) for c in calls)
    return {"tool_call_count": len(calls), "tool_errors": sum(1 for c in calls if c["is_error"]),
            "distinct_tools": sorted({c["tool"] for c in calls}),
            "systems_queried": sorted(s for s in systems if s in ("erp", "crm", "payroll", "identity", "meta")),
            "calls_per_system": dict(systems),
            "repeated_identical_calls": sum(n - 1 for n in keys.values() if n > 1),
            "num_turns": (result or {}).get("num_turns")}


def run(qid, trial, overwrite=False):
    q = next(x for x in protocol.QUESTIONS if x["id"] == qid)
    rid = protocol.run_id(q, trial)
    out_path = RUNS_DIR / f"{rid}.json"
    if out_path.exists() and not overwrite:
        print(f"{rid}: exists, skipping (baseline results are never overwritten)")
        return json.loads(out_path.read_text())
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    stream_path, server_log, stderr_path = (RAW_DIR / f"{rid}.stream.jsonl", RAW_DIR / f"{rid}.server.jsonl",
                                            RAW_DIR / f"{rid}.stderr.txt")
    for p in (stream_path, server_log, stderr_path):
        p.unlink(missing_ok=True)

    workdir = Path(tempfile.mkdtemp(prefix=f"nordflow-eval-{rid}-"))
    mcp_config = workdir / "mcp.json"
    mcp_config.write_text(json.dumps({"mcpServers": {SERVER_KEY: {
        "command": str(VENV_PYTHON), "args": ["-m", "phase2.evaluation.runner.traced_server"],
        "env": {"PYTHONPATH": str(REPO_ROOT), "NORDFLOW_DATA_DIR": str(REPO_ROOT / "data"),
                "NORDFLOW_TRACE_FILE": str(server_log), "PYTHONDONTWRITEBYTECODE": "1"}}}}))
    cmd = build_command(q, mcp_config)
    started, t0, status, errors = _now(), time.time(), "completed", []
    try:
        proc = subprocess.run(cmd, cwd=workdir, capture_output=True, text=True, timeout=protocol.TIMEOUT_SECONDS,
                              stdin=subprocess.DEVNULL)
        stdout, stderr, code = proc.stdout, proc.stderr, proc.returncode
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr, code, status = "timeout", None, "timeout"
    elapsed = round(time.time() - t0, 1)
    shutil.rmtree(workdir, ignore_errors=True)
    stream_path.write_text(stdout, encoding="utf-8")
    stderr_path.write_text(stderr or "", encoding="utf-8")

    init, result, trace, calls = parse_stream(stdout.splitlines())
    attach_server_log(calls, server_log)
    tools_exposed = sorted((init or {}).get("tools", []))
    builtin = [t for t in tools_exposed if not t.startswith(TOOL_PREFIX)]
    if code not in (0, None):
        errors.append(f"claude exited with code {code}")
    if result is None:
        status = "error" if status == "completed" else status
        errors.append("no result message in stream")
    elif result.get("is_error") or result.get("subtype") != "success":
        status = "max_turns" if result.get("subtype") == "error_max_turns" else "error"
        errors.append(f"result subtype {result.get('subtype')}")
    errors += [f"tool error in call {c['seq']} ({c['tool']}): {(c['result_text'] or '')[:200]}" for c in calls if c["is_error"]]

    record = {
        "run_id": rid, "protocol_version": protocol.PROTOCOL_VERSION,
        "question": {"id": q["id"], "kind": q["kind"], "text": q["text"]}, "trial": trial,
        "model": {"requested": protocol.MODEL, "reported": (init or {}).get("model"),
                  "model_usage": (result or {}).get("modelUsage")},
        "config": {"cli": "claude (Claude Code) headless -p", "cli_version": (init or {}).get("claude_code_version"),
                   "command": [c if c != protocol.SYSTEM_PROMPT else "<SYSTEM_PROMPT>" for c in cmd],
                   "system_prompt": protocol.SYSTEM_PROMPT, "system_prompt_sha256": protocol.sha256(protocol.SYSTEM_PROMPT),
                   "max_turns": protocol.MAX_TURNS, "timeout_seconds": protocol.TIMEOUT_SECONDS,
                   "permission_mode": (init or {}).get("permissionMode")},
        "isolation": {"tools_exposed": tools_exposed, "builtin_tools_exposed": builtin,
                      "mcp_servers": (init or {}).get("mcp_servers"), "fresh_process": True,
                      "ok": bool(init) and not builtin and len(tools_exposed) > 0},
        "status": status, "started_at": started, "finished_at": _now(), "elapsed_s": elapsed,
        "final_answer": (result or {}).get("result"),
        "stats": stats(calls, result),
        "usage": (result or {}).get("usage"), "total_cost_usd": (result or {}).get("total_cost_usd"),
        "duration_ms": (result or {}).get("duration_ms"), "duration_api_ms": (result or {}).get("duration_api_ms"),
        "errors": errors,
        "trace": trace, "tool_calls": calls,
        "raw_files": {"stream": str(stream_path.relative_to(REPO_ROOT)), "server_log": str(server_log.relative_to(REPO_ROOT)),
                      "stderr": str(stderr_path.relative_to(REPO_ROOT))},
    }
    out_path.write_text(json.dumps(record, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    s = record["stats"]
    print(f"{rid}: {status} in {elapsed}s, {s['tool_call_count']} tool calls, systems {s['systems_queried']}, "
          f"isolation_ok={record['isolation']['ok']}")
    return record


if __name__ == "__main__":
    run(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 1, overwrite="--overwrite" in sys.argv)
