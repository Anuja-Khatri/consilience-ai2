# Changelog

## [0.1.0] - 2026-11-17

First release: the shared core, data fetch, and the three tools, each measured on data
released by Ai2 and its collaborators. Results: [docs/RESULTS.md](docs/RESULTS.md);
limits: [docs/LIMITATIONS.md](docs/LIMITATIONS.md).

### Added
- **Evidence receipts** (`consilience-ai2 receipts check`): checks of an Asta workspace
  (`evidence.yml`, `.qmd` `.ev` spans, `references.bib`) for unknown keys, missing
  quotes, citations missing from the bibliography, orphaned entries and provenance
  format (E1 to E5, plus E0 for unreadable input); quotes verbatim in local source text
  with SHA-256 and offsets (E6); number overreach (W1) and certainty upgrades (W2).
  Adapters for Theorizer's released export (T1, T2) and SciArena-Eval citations. A
  `make check` snippet and the `evidence-receipts` plugin skill.
- **Experiment audit** (`consilience-ai2 audit run`): checks A1 to A7 and R1 to R5 per
  experiment of an AutoDiscovery run (local `--out_dir` or hosted `results.json`) or a
  CodeScientist experiment directory, with Benjamini–Hochberg q across the run and a
  per-node `pass` / `flag` / `refuse`; AutoDiscovery's Validity Check text is hashed
  beside each verdict. Writes `validity_audit.json`. Synthetic AutoDiscovery fixtures
  from the released schema, an example in-run wrapper, and the `experiment-audit`
  plugin skill.
- **Reproduction verdict** (`consilience-ai2 reproduce check`): the asta-flows
  secondary-reproduction rubric as deterministic checks on a versioned record format
  (JSON Schema): faithfulness (F1), decidability with closed-form power (D1), the
  verdict from the numbers against committed thresholds (V1), commit order from git
  (P1) and a verbatim hypothesis copy (P2). Writes `reproduction_verdict.json`. A
  `verdict.py` drop-in for the workflow, synthetic example records and the
  `reproduction-verdict` plugin skill. Optional unit-aware comparability through the
  `consilience` package (the `[consilience]` extra, or `pip install consilience`).
- **Analyses** on Theorizer, SciArena-Eval, CodeScientist and DiscoveryBench, with two
  preregistered held-out tests committed before scoring: receipts on SciArena votes
  (null) and the audit on CodeScientist reruns (H1 not supported in the predicted
  direction, p = 0.0845; H2 null).
- `docs/RESULTS.md`, `docs/LIMITATIONS.md` and `docs/INTEGRATION.md` (hook points and
  the version-1 JSON schemas); the plugin marketplace lists the three plugins.
- `consilience_ai2.core`: SHA-256 helpers and canonical JSON; the versioned text
  normalisation for verbatim checks (six named steps, with an offset map back to the
  original text); deterministic number extraction (printed precision, spans, percent,
  scientific notation, `±`, fail-closed on ambiguous separators); the findings, receipt
  and report schema with deterministic JSON and GitHub annotations; CLI auto-discovery
  of components; metric records, per-component results files and the merged registry.
- `consilience-ai2 fetch`: pinned sources (SHA-256 and size for files, commit for git
  repositories) downloaded into a cache outside the repository and refused on mismatch;
  `--from-dir` and `--offline` to copy in local files; safe unzip.
- `scripts/numbers_lock.py` (every result-like number in the docs must render from
  `results/registry.json`; renders the grouped results table),
  `scripts/build_marketplace.py`, `scripts/check_secrets.py` (secrets, data files and
  model identifiers in the tracked tree), a Makefile and GitHub Actions CI.

### Fixed
- `core.numbers.agrees_at_printed_precision` no longer raises `decimal.InvalidOperation`
  on values far outside the default decimal precision; such a value is not agreeing,
  and long printed integers compare exactly.
