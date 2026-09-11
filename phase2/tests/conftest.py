"""Shared fixtures.

`rt`   - runtime over the small hand-made fixture dataset (tests/fixtures/data);
         expected values in the tests are worked out by hand from those CSVs.
`real` - runtime over the frozen Phase 1 dataset (data/), used only for generic
         reconciliation/integration checks, never for scenario conclusions.
"""
from pathlib import Path

import pytest

from phase2.runtime import Runtime
from phase2.runtime.sources import REPO_ROOT

FIXTURE_DATA = Path(__file__).parent / "fixtures" / "data"


@pytest.fixture(scope="session")
def rt():
    return Runtime(FIXTURE_DATA)


@pytest.fixture(scope="session")
def real():
    data = REPO_ROOT / "data"
    if not (data / "erp" / "invoices.csv").exists():
        pytest.skip("frozen dataset not present")
    return Runtime(data)


def rows(result):
    return result["rows"]


def by(result, key):
    return {r[key]: r for r in result["rows"]}
