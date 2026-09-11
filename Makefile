PY ?= python3

.PHONY: data validate robustness verify verify-regen all

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
