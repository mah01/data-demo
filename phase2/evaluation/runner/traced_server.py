"""
Evaluation-only MCP entrypoint: exactly the Phase 2A tools (same runtime
operations, names, descriptions, annotations and error handling as
phase2.mcp.server), plus a server-side JSONL log of every call.

    NORDFLOW_TRACE_FILE=/path/log.jsonl python -m phase2.evaluation.runner.traced_server
"""
import functools
import json
import os
import time
from datetime import datetime, timezone

from mcp.server.mcpserver import MCPServer

from phase2.mcp.server import INSTRUCTIONS, READ_ONLY, _user_errors_visible
from phase2.runtime import Runtime

TRACE_FILE = os.environ.get("NORDFLOW_TRACE_FILE")
_seq = 0


def _log(record):
    if TRACE_FILE:
        with open(TRACE_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


def traced(name, fn):
    @functools.wraps(fn)
    def tool(*args, **kwargs):
        global _seq
        _seq += 1
        record = {"seq": _seq, "tool": name, "arguments": kwargs,
                  "started_at": datetime.now(timezone.utc).isoformat()}
        t0 = time.perf_counter()
        try:
            out = fn(*args, **kwargs)
            record.update(ok=True, result=out)
            return out
        except Exception as exc:
            record.update(ok=False, error=f"{type(exc).__name__}: {exc}")
            raise
        finally:
            record["elapsed_ms"] = round((time.perf_counter() - t0) * 1000, 1)
            _log(record)
    return tool


def build_traced_server():
    server = MCPServer("nordflow-business-data", instructions=INSTRUCTIONS, version="0.1.0")
    for name, op in Runtime().operations().items():
        server.add_tool(traced(name, _user_errors_visible(op)), name=name, annotations=READ_ONLY)
    return server


if __name__ == "__main__":
    build_traced_server().run("stdio")
