# Changelog

## [0.2.0] - 2026-11-18

A fix round on all three tools. Every v0.1 number keeps its value, n and metric id; v0.2
numbers sit beside them under their own ids. Results: [docs/RESULTS.md](docs/RESULTS.md);
limits: [docs/LIMITATIONS.md](docs/LIMITATIONS.md).

### Fixed
- **Receipts, Theorizer T1: the cause was misattributed.** The dangling evidence links
  were attributed to lines of asta-theorizer's `src/Theorizer.py` that assign training
  extraction IDs; those lines do not write the links. The verified cause is the HTML
  exporter's silent fallback: `src/ExportTheoryStoreAsHTML.py` line 286 (commit c4802aa)
  is `extraction_id = uuid_to_extraction_id.get(uuid, uuid)`, so an unmapped ID becomes
  its own file name and renders as a link to a record that does not exist. Why the IDs
  are unmapped upstream is not established. The docs, the adapter docstring and the T1
  caveats say so; a regression test pins the exporter line and an example.

### Changed
- **Receipts: W1/W2 rules v0.2 are the default** (`--rules v0.1` for the frozen rules of
  the preregistered SciArena test), and **W2 is opt-in** (`--with-w2`,
  `check_workspace(..., with_w2=True)`): W2 is opt-in because on a hand-checked sample
  only about a third of its flags were real overreach. W1 stays on by default, as a
  warning (about half of its flags were real). Each report records the codes that ran
  (`checks`). The analyses compute W2 explicitly, so no reported W2 rate changes.
- **Audit: rules v0.2 (`audit-rules-2`).** Severities recalibrated on the development
  set (an error is what a reviewer would reject a result for); only U1 refuses; A7 (no
  effect size) is an info note, not a flag; A1 has tiers (error only when a number is
  absent; a derived relative change passes; one digit more than printed, or a number
  possibly only in a saved figure, is a warning); R1 excludes limiting statements ("only
  slightly better than random"); R2 is split (an error when refuting reruns are at least
  as many as supporting ones, else a warning); each node has a `verdict_level` (`pass`,
  `flag(warning)`, `flag(error)`, `refuse`). The v0.1 results
  are recomputed from the frozen v0.1 rules taken from git. A v0.2 held-out test was
  preregistered on the 13 full-50 runs no version had audited; it was not testable (1
  flagged, below the preregistered minimum of 3 per group).
- **Reproduce: extraction v0.2 and verdict rule v0.2.** The CodeScientist extraction
  reads the files a run saved for its report and its log as well as `results.json`, with
  tolerant parsing (preregistered, deviations recorded). Under verdict rule v0.2 (the
  default) the expected direction is the sign of the source effect, and a source that
  claims no effect is `undecided(source_null)`; `--rule v0.1` keeps the declared
  direction. The rule change was decided after the v0.2 extraction results were seen.

### Added
- A hand-labelled precision sample of W1 and W2 flags (50 per check and rule version,
  SciArena and Theorizer; one annotator, labelled dev).
- Receipts sources: the Asta PaperStore JSON format pinned (`theory/paperstore.json`),
  and `--sources` is repeatable (stores tried in order).
- Audit A5: a derived set on DiscoveryBench (a target and gold columns named from the
  query text by a fixed rule) for the queries without a machine-readable relation.
- Reproduce: a DiscoveryBench sensitivity analysis (Spearman's rho and binned mutual
  information beside Pearson), derived pairs from prose hypotheses, and a count of the
  CodeScientist batch whose run outputs are not released.
- `examples/reproduce/demo_commit_order.py`: commits the thresholds before the result in
  a scratch repository, so P1 passes and the check exits 0.
- The audit documents the search for public outputs of real AutoDiscovery runs (none
  found).

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
