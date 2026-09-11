"""
Run the whole baseline: 10 benchmark questions x 1 and 3 blind questions x 3,
each in its own fresh agent process. Existing run records are never overwritten.

    phase2/.venv/bin/python -m phase2.evaluation.runner.run_all [--workers 4]
"""
import sys
from concurrent.futures import ThreadPoolExecutor

from . import protocol
from .run_agent import run


def main():
    workers = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 4
    jobs = [(q["id"], t) for q, t in protocol.plan()]
    print(f"Protocol {protocol.PROTOCOL_VERSION}, model {protocol.MODEL}: {len(jobs)} runs, {workers} in parallel")
    with ThreadPoolExecutor(workers) as pool:
        records = list(pool.map(lambda j: run(*j), jobs))
    done = sum(1 for r in records if r and r.get("status") == "completed")
    print(f"\n{done}/{len(jobs)} runs completed.")


if __name__ == "__main__":
    main()
