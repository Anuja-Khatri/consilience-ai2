---
name: evidence-receipts
description: Deterministic structural and verbatim checks for an Asta workspace's `.ev` evidence (evidence.yml, references.bib, .qmd spans), with a receipt for every quote found in local source text. Use before `make check`, or when asked to "check the evidence structure", "verify quotes are verbatim", "find number overreach" or "add evidence receipts to make check". Complements asta-tools:check-claims, which judges whether a quote supports a claim.
allowed-tools: Read Grep Glob Bash(consilience-ai2 receipts check *) Bash(make check) Bash(git diff *) Skill(asta-tools:check-claims)
---

# Evidence receipts

Runs `consilience-ai2 receipts check`, a rule-based checker with no model calls, over an
Asta workspace. It reads the workspace files as the workspace's evidence filter does and
reports each finding with a code, a file and line, and a receipt (the SHA-256 of what
was checked, plus character offsets when a quote was found). Same files in, same report
out.

| Code | Meaning | Fails the run |
|---|---|---|
| E0 | An input cannot be read or parsed (warning when a file named in `_quarto.yml` is missing) | yes (error) |
| E1 | A `.ev` span names a key that is not in the evidence store | yes |
| E2 | A `.ev` span has no quote (inline or stored) | yes |
| E3 | A `cite` key is not in the bibliography | yes |
| E4 | An evidence entry is referenced by no span | yes |
| E5 | `provenance` is malformed: `method` not an exact `asta` subcommand, `corpus_id` not an integer, `url` not http/https/asta, `retrieved` not an ISO date | yes |
| E6 | Quote verbatim in local source text: `FOUND` (receipt), `NOT_FOUND` (fails), `UNCHECKABLE` (no local text) | only `NOT_FOUND` |
| W1 | A number in the claim is not in the quote (on by default) | no (warning) |
| W2 | The claim is assertive where the quote is hedged (fixed word list); opt-in with `--with-w2` | no (warning) |

## Procedure

1. **Run it on the workspace root** (the directory with `_quarto.yml`):
   `consilience-ai2 receipts check . --json _receipts/receipts.json`.
   Add `--sources <dir>` when local source text exists: a directory of `<cite>.txt` or
   `<corpus_id>.txt` files, an Asta `paperstore.json` (a theory run keeps one at
   `<run>/theory/paperstore.json`), or an AutoDiscovery `index.json`. Repeat
   `--sources` to try several in order. Without it every E6 is `UNCHECKABLE`, which does
   not fail the run.
2. **Read the annotation lines.** Each is `::error file=…,line=…::CODE message` (or
   `::warning`). Fix E codes in `evidence.yml`, `references.bib` or the `.qmd` span they
   name. For `E6 NOT_FOUND`, copy the quote again from the source; never edit a quote
   to make it match something it does not say.
3. **Treat W1 and W2 as prompts to read, not verdicts.** They are lexical. On a
   hand-checked sample, about half of the W1 flags and about a third of the W2 flags were
   a real overreach, so W1 runs by default and W2 is opt-in: add `--with-w2` to run it.
   A W1 number may be a name (`Industry 4.0`), a figure reference, or a difference the
   reader can compute; a W2 hedge in the source may be about something else. When the
   claim does overstate the quote, reword the claim. For whether the quote supports the claim
   at all, load `asta-tools:check-claims`.
4. **Wire it into `make check`** when the project wants it on every PR: copy
   `assets/evidence-receipts.mk` into the project (for example next to the Makefile) and
   add `include evidence-receipts.mk` to the project's Makefile, beside its other
   project-owned checks. It adds `evidence-receipts` as a prerequisite of `check`.
   Settings: `CONSILIENCE_AI2` (the command), `RECEIPTS_SOURCES` (passed as
   `--sources`), `RECEIPTS_REPORT` (the JSON report path), `RECEIPTS_FLAGS` (for example
   `--with-w2`). Then run `make check`.

Exit code: 0 with no error finding, 1 on any error, 2 on a usage error. Add
`--fail-on-warnings` to fail on W1 (and on W2 when `--with-w2` is given) too. The JSON
report (version 1) lists the inputs with their SHA-256, every finding with its receipt,
and summary counts.
