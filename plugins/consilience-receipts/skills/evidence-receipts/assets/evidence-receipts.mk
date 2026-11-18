# evidence-receipts.mk: add deterministic evidence receipts to a workspace's `make check`.
#
# Usage: copy this file into the workspace and add one line to the project's Makefile
# (or to a project-owned workspace.mk), next to the other project-owned checks:
#
#     include evidence-receipts.mk
#
# `make check` then runs `consilience-ai2 receipts check` on the workspace and fails on
# any E code (E0-E6). W1 (number overreach) is printed as a warning; on a hand-checked
# sample about half of its flags were real. W2 (certainty upgrade) is opt-in, because
# only about a third of its flags were real: add RECEIPTS_FLAGS=--with-w2 to run it. Set
# RECEIPTS_FLAGS=--fail-on-warnings to fail on warnings too (the two flags combine:
# RECEIPTS_FLAGS="--with-w2 --fail-on-warnings"). Requires the consilience-ai2 command:
#   pip install "git+https://github.com/Anuja-Khatri/consilience-ai2"
#
# Settings (override on the command line or before the include):
#   CONSILIENCE_AI2   the command to run                 (default: consilience-ai2)
#   RECEIPTS_DIR      the workspace directory to check   (default: .)
#   RECEIPTS_SOURCES  local source text for E6, passed as --sources (default: none)
#   RECEIPTS_REPORT   where to write the JSON report     (default: _receipts/receipts.json)
#   RECEIPTS_FLAGS    extra flags, e.g. --with-w2        (default: none)

CONSILIENCE_AI2 ?= consilience-ai2
RECEIPTS_DIR ?= .
RECEIPTS_SOURCES ?=
RECEIPTS_REPORT ?= _receipts/receipts.json
RECEIPTS_FLAGS ?=

.PHONY: check evidence-receipts
check: evidence-receipts
evidence-receipts:
	$(CONSILIENCE_AI2) receipts check '$(RECEIPTS_DIR)' $(if $(RECEIPTS_SOURCES),--sources '$(RECEIPTS_SOURCES)') --json '$(RECEIPTS_REPORT)' $(RECEIPTS_FLAGS)
