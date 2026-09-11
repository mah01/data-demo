"""
Re-attach the server-side call logs to existing run records (bookkeeping only:
timing / server status per tool call). Does not re-run or alter any agent output.

    phase2/.venv/bin/python -m phase2.evaluation.runner.reattach
"""
import json

from phase2.runtime.sources import REPO_ROOT

from .run_agent import RUNS_DIR, attach_server_log


def main():
    for path in sorted(RUNS_DIR.glob("*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        calls = record["tool_calls"]
        for c in calls:
            for k in ("server_seq", "server_elapsed_ms", "server_ok", "server_error"):
                c.pop(k, None)
        server_records = attach_server_log(calls, REPO_ROOT / record["raw_files"]["server_log"])
        record["server_calls_logged"] = len(server_records)
        path.write_text(json.dumps(record, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
        matched = sum(1 for c in calls if "server_seq" in c)
        print(f"{record['run_id']}: {matched}/{len(calls)} client calls matched to {len(server_records)} server records")


if __name__ == "__main__":
    main()
