# consilience-ai2 Makefile. Deterministic by construction; no target calls a model.
#
# PY defaults to the repo venv made by `make setup`; CI sets PY=python.
# STRICT=1 (used by GitHub CI) makes generated-file staleness an error: the committed
# results/registry.json and .claude-plugin/marketplace.json must be fresh builds.

REPO := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
VENV := $(REPO)/.venv
PY ?= $(if $(wildcard $(VENV)/bin/python),$(VENV)/bin/python,python3)
STRICT ?=
STRICT_FLAG := $(if $(STRICT),--strict,)

.PHONY: setup test lint lock lock-check registry marketplace marketplace-check secrets ci fetch clean

setup:
	python3 -m venv $(VENV)
	$(VENV)/bin/python -m pip install -q --upgrade pip
	$(VENV)/bin/python -m pip install -q -e ".[dev]"
	@echo "setup done: $(VENV)"

lint:
	$(PY) -m ruff check consilience_ai2 tests scripts analyses

test:
	$(PY) -m pytest tests

# registry: merge results/<component>.json into results/registry.json (integrator)
registry:
	$(PY) -c "from consilience_ai2.core.results import write_registry; print(write_registry('results'))"

# lock: rebuild the registry, render docs/tables/results.md, write results/NUMBERS_LOCK.json
lock:
	$(PY) scripts/numbers_lock.py

lock-check:
	$(PY) scripts/numbers_lock.py --check $(STRICT_FLAG)

marketplace:
	$(PY) scripts/build_marketplace.py

marketplace-check:
	$(PY) scripts/build_marketplace.py --check $(STRICT_FLAG)

secrets:
	$(PY) scripts/check_secrets.py

# ci = lint + tests + numbers lock + marketplace consistency + secret/data scan
ci: lint test lock-check marketplace-check secrets
	@echo "ci: green"

# fetch: every pinned source into $$CONSILIENCE_AI2_DATA (default ~/.cache/consilience-ai2)
fetch:
	$(PY) -m consilience_ai2 fetch all

clean:
	find . -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .ruff_cache build dist *.egg-info
