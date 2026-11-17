# Changelog

## [0.1.0] - unreleased

The skeleton. No validity tool is built yet; the shared core, data fetch and release
tooling are.

### Added
- `consilience_ai2.core`: SHA-256 helpers and canonical JSON; the versioned text
  normalisation for verbatim checks (six named steps, with an offset map back to the
  original text); deterministic number extraction (printed precision, spans, percent,
  scientific notation, `±`, fail-closed on ambiguous separators); the findings, receipt
  and report schema with deterministic JSON and GitHub annotations; CLI auto-discovery
  of components; metric records, per-component results files and the merged registry.
- `consilience-ai2 fetch`: pinned sources (SHA-256 and size for files, commit for git
  repositories) downloaded into a cache outside the repository and refused on mismatch;
  `--from-dir` and `--offline` to copy in local files; safe unzip.
- Claude Code marketplace file in the asta-plugins layout, with no plugins listed yet,
  and `scripts/build_marketplace.py` to generate it from per-plugin entries.
- `scripts/numbers_lock.py` (every result-like number in the docs must render from
  `results/registry.json`), `scripts/check_secrets.py` (secrets, data files and model
  identifiers in the tracked tree), a Makefile and GitHub Actions CI.
- README, NOTICE, CONTRIBUTING (the component contract) and `docs/SPEC.md`.
