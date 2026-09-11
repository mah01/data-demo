"""
Multi-seed robustness test: regenerate the dataset with many seeds (each into
its own temporary folder; ./data is never touched) and run every validation
check on each.

    python3 src/robustness.py                  # seeds 1..100
    python3 src/robustness.py --seeds 20 --workers 4

A changed generator reshuffles the random draws much like a new seed, so this
shows whether the business story is enforced or merely lucky.
Exit code 1 if any check fails for any seed.
"""
import json
import os
import statistics
import subprocess
import sys
import tempfile
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

SRC = Path(__file__).resolve().parent


def _arg(name, default):
    return int(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default


def run_seed(seed, tmp_root):
    out = Path(tmp_root) / f"seed{seed}"
    env = dict(os.environ, NORDFLOW_SEED=str(seed), NORDFLOW_DATA_DIR=str(out / "data"), PYTHONDONTWRITEBYTECODE="1")
    gen = subprocess.run([sys.executable, str(SRC / "generate.py")], env=env, capture_output=True, text=True)
    if gen.returncode:
        return seed, None, gen.stderr.strip().splitlines()[-1]
    result = out / "result.json"
    subprocess.run([sys.executable, str(SRC / "validate.py"), "--quiet", "--data", str(out / "data"), "--json", str(result)],
                   env=env, capture_output=True, text=True)
    if not result.exists():
        return seed, None, "validator crashed"
    return seed, json.loads(result.read_text()), None


def main():
    n, workers = _arg("--seeds", 100), _arg("--workers", os.cpu_count() or 4)
    with tempfile.TemporaryDirectory() as tmp, ThreadPoolExecutor(workers) as pool:
        results = sorted(pool.map(lambda s: run_seed(s, tmp), range(1, n + 1)), key=lambda x: x[0])

    crashed = [(s, err) for s, rec, err in results if rec is None]
    by_check, groups, failures = defaultdict(list), {}, defaultdict(list)
    for seed, records, _ in results:
        for r in records or []:
            by_check[r["id"]].append(r)
            groups[r["id"]] = r["group"]
            if not r["ok"]:
                failures[seed].append(r["id"])

    print(f"Robustness test: {n} seeds, {len(by_check)} checks per seed\n")
    print(f"{'check':<46} {'passed':>9}   {'min':>10} {'median':>10} {'max':>10}")
    last = None
    for cid, rs in by_check.items():
        g = groups[cid].split(" ")[0] + (" " + groups[cid].split(" ")[1] if groups[cid].startswith("Scenario") else "")
        if g != last:
            print(f"-- {g}")
            last = g
        vals = [r["value"] for r in rs if isinstance(r["value"], (int, float)) and not isinstance(r["value"], bool)]
        stats = f"{min(vals):>10.4g} {statistics.median(vals):>10.4g} {max(vals):>10.4g}" if vals and groups[cid].startswith(("Story", "Scenario")) else ""
        ok = sum(r["ok"] for r in rs)
        print(f"{'  ' + cid:<46} {ok:>4}/{len(rs):<4}   {stats}{'   <-- FAILS' if ok < len(rs) else ''}")

    for seed, err in crashed:
        print(f"\nseed {seed}: generation/validation crashed: {err}")
    for seed, ids in sorted(failures.items()):
        print(f"seed {seed}: {', '.join(ids)}")
    clean = n - len(failures) - len(crashed)
    print(f"\n{clean}/{n} seeds pass every check.")
    if clean < n:
        sys.exit(1)
    print("ROBUSTNESS PASSED: every story check and scenario invariant holds for every seed.")


if __name__ == "__main__":
    main()
