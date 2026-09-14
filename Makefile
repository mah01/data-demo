PY ?= python3

.PHONY: data validate robustness verify verify-regen all demo demo-check demo-test

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

# configuration/secret and data check; opens no port and calls no model (phase3/DEPLOY.md)
demo-check:
	phase2/.venv/bin/python -m phase3.server --check

demo-test:
	phase2/.venv/bin/python -m pytest phase2/tests phase3/tests -q -p no:warnings
