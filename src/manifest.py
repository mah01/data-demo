"""
Checksum manifest for the default generated dataset (Phase 1 release).

    python3 src/manifest.py               # verify ./data against data_manifest.json
    python3 src/manifest.py --regenerate  # regenerate the default seed into a temp folder and compare
    python3 src/manifest.py --write       # (releases only) rewrite data_manifest.json from ./data

Exit code 1 on any mismatch, missing or unexpected file.
"""
import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "data_manifest.json"
RELEASE = "phase1-v1.0"
DEFAULT_SEED = 4217


def snapshot(data_dir):
    files = {}
    for p in sorted(Path(data_dir).rglob("*.csv")):
        raw = p.read_bytes()
        files[p.relative_to(data_dir).as_posix()] = {
            "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw), "rows": raw.count(b"\n") - 1}
    combined = hashlib.sha256("".join(f"{k}:{v['sha256']}\n" for k, v in files.items()).encode()).hexdigest()
    return files, combined


def compare(data_dir, label):
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    files, combined = snapshot(data_dir)
    problems = [f"missing: {k}" for k in m["files"] if k not in files]
    problems += [f"unexpected: {k}" for k in files if k not in m["files"]]
    problems += [f"changed: {k} (rows {m['files'][k]['rows']} -> {v['rows']}, bytes {m['files'][k]['bytes']} -> {v['bytes']})"
                 for k, v in files.items() if k in m["files"] and v["sha256"] != m["files"][k]["sha256"]]
    print(f"{label}: {len(files)} files vs manifest {m['release']} ({len(m['files'])} files)")
    for p in problems:
        print("  " + p)
    if problems:
        print(f"MANIFEST CHECK FAILED ({len(problems)} problem(s)).")
        if "--regenerate" in sys.argv and m.get("python") != platform.python_version():
            print(f"  note: manifest was produced with Python {m.get('python')}, this is {platform.python_version()}.")
        sys.exit(1)
    print(f"MANIFEST OK: dataset sha256 {combined}")


def main():
    if "--write" in sys.argv:
        files, combined = snapshot(ROOT / "data")
        MANIFEST.write_text(json.dumps({
            "release": RELEASE, "created": date.today().isoformat(), "seed": DEFAULT_SEED,
            "python": platform.python_version(), "generator_command": "python3 src/generate.py",
            "dataset_sha256": combined, "files": files}, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {MANIFEST.name}: {len(files)} files, dataset sha256 {combined}")
    elif "--regenerate" in sys.argv:
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, NORDFLOW_SEED=str(DEFAULT_SEED), NORDFLOW_DATA_DIR=tmp, PYTHONDONTWRITEBYTECODE="1")
            subprocess.run([sys.executable, str(ROOT / "src" / "generate.py")], env=env, check=True, capture_output=True)
            compare(tmp, "Regenerated (seed %d)" % DEFAULT_SEED)
    else:
        compare(ROOT / "data", "./data")


if __name__ == "__main__":
    main()
