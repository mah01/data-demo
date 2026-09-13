PY ?= python3

.PHONY: data validate robustness verify verify-regen all demo demo-test

all: data validate

data:
	$(PY) src/generate.py

validate:
	$(PY) src/validate.py

robustness:
	$(PY) src/robustness.py

# Phase 1 release integrity (data_manifest.json)
verify:
	$(PY) src/manifest.py

verify-regen:
	$(PY) src/manifest.py --regenerate

# Phase 3 demo (see phase3/README.md)
demo:
	phase2/.venv/bin/python -m phase3.server

demo-test:
	phase2/.venv/bin/python -m pytest phase2/tests phase3/tests -q -p no:warnings
