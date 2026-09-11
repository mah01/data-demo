"""
The runtime boundary: runtime + MCP code may only read the four system
exports. It must not depend on the Phase 1 answer key, validation or generator.
"""
import ast
import builtins
import json
import sys
from pathlib import Path

from phase2.runtime import Runtime
from phase2.runtime.sources import REPO_ROOT

from .examples import EXAMPLES

PHASE2 = Path(__file__).resolve().parents[1]
RUNTIME_CODE = sorted((PHASE2 / "runtime").rglob("*.py")) + sorted((PHASE2 / "mcp").rglob("*.py"))
PHASE1_MODULES = {"src", "config", "roster", "world", "common", "generate", "gen_crm", "gen_erp", "gen_payroll",
                  "gen_ledger", "crm_render", "metrics", "analysis", "validate", "robustness", "manifest"}
FORBIDDEN_TEXT = ["ground_truth", "data_manifest", "validate.py", "analysis.py", "metrics.py", "robustness.py",
                  "generate.py", "world.py", "executive"]
SYSTEM_FOLDERS = {"erp", "crm", "payroll", "mappings"}


def test_runtime_code_imports_no_phase1_modules():
    allowed_roots = set(sys.stdlib_module_names) | {"phase2", "mcp"}
    for path in RUNTIME_CODE:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0:
                names = [node.module]
            for name in names:
                root = name.split(".")[0]
                assert root not in PHASE1_MODULES, f"{path.name} imports Phase 1 module {name}"
                assert root in allowed_roots, f"{path.name} imports non-stdlib/non-runtime module {name}"


def test_runtime_code_does_not_reference_answer_key():
    for path in RUNTIME_CODE:
        text = path.read_text(encoding="utf-8").lower()
        for token in FORBIDDEN_TEXT:
            assert token not in text, f"{path.relative_to(PHASE2)} mentions '{token}'"


def test_runtime_only_opens_system_exports(monkeypatch):
    """Run every operation on the real dataset and record every file opened."""
    data = REPO_ROOT / "data"
    opened = []
    real_open = builtins.open

    def spy(file, *a, **k):
        opened.append(Path(file).resolve())
        return real_open(file, *a, **k)
    monkeypatch.setattr(builtins, "open", spy)
    rt = Runtime(data)
    ops = rt.operations()
    for name, kwargs in EXAMPLES.items():
        json.dumps(ops[name](**kwargs))
    assert opened, "expected CSV reads"
    for p in opened:
        rel = p.relative_to(data.resolve())
        assert rel.parts[0] in SYSTEM_FOLDERS and p.suffix == ".csv", f"unexpected file access: {p}"
    assert not any(p.name == "ground_truth.json" for p in opened)


def test_every_operation_has_an_example_and_docstring():
    ops = Runtime(PHASE2 / "tests" / "fixtures" / "data").operations()
    assert set(ops) == set(EXAMPLES)
    for name, fn in ops.items():
        assert fn.__doc__ and len(fn.__doc__.strip()) > 30, f"{name} needs a description"


def test_no_phase1_evaluation_modules_loaded():
    Runtime(REPO_ROOT / "data").operations()
    for mod in ("analysis", "metrics", "validate", "robustness", "world", "gen_crm"):
        assert mod not in sys.modules
