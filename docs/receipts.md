# Evidence receipts (`consilience-ai2 receipts`)

Rule-based checks of the evidence behind written claims, for Asta workspaces and for two
released datasets (Theorizer theories and SciArena-Eval). There are no model calls. The
same input gives byte-identical output. Every finding carries a receipt: the SHA-256 of
what was checked and, where there is one, the character span.

Independent work, not affiliated with or endorsed by the Allen Institute for AI (Ai2).

## Running it

```bash
consilience-ai2 receipts check <workspace_dir> [--sources DIR|paperstore.json|index.json] [--json OUT]
```

- One GitHub annotation line is printed per error or warning, for example
  `::error file=defects.qmd,line=7::E1 .ev span references unknown key "d-missing-key"`.
  `--all-annotations` also prints the info receipts. `--no-annotations` prints none.
- `--json OUT` writes the version-1 report (format below).
- Exit codes: 0 when there is no error; 1 on any error; 2 on a usage error (for example
  a `--sources` path that does not exist). `--fail-on-warnings` makes W1 and W2 fail the
  run too.

Python API: `consilience_ai2.receipts.check_workspace(root, sources=None)` returns a
`Report`. `number_overreach(claim, source)` (W1) and `certainty_upgrade(claim, source)`
(W2) compare any claim with any source text.

## What is read

The checker reads the workspace the way Quarto and the asta-plugins evidence filter
(`plugins/asta-tools/skills/workspace/assets/_extensions/evidence/snippet.lua`, read at
commit a2dcade) read it.

- **Evidence store.** The files listed under `metadata-files` in `_quarto.yml`, read in
  order; a later file's entry replaces an earlier entry with the same key. With no
  `_quarto.yml`, the checker reads `evidence.yml` at the root. A `.qmd` file's front matter
  may add or replace entries under `evidence:` for that file only. As in the filter, only
  entries that are maps are stored. YAML is read the way Pandoc reads metadata: every
  scalar is text, so `corpus_id: 289622360` and `retrieved: 2026-08-29` arrive as written.
- **Bibliography.** `bibliography` in `_quarto.yml` and in each file's front matter (a
  path or a list). With no `_quarto.yml`, the checker reads `references.bib` at the root.
  Keys are the `@type{key,` entries; `@string`, `@preamble` and `@comment` are not entries.
- **Documents.** Every `*.qmd` under the workspace. Directories whose names start with
  `.` or `_` (`_extensions`, `_site`, `.quarto`) and `node_modules` are skipped.
- **Spans.** A `.ev` span is a Pandoc bracketed span `[content]{attributes}` whose classes
  include `ev`.
  - Fenced code, inline code, HTML comments and front matter are masked first, so an
    example inside code is not a span.
  - Attribute values may be bare, double-quoted or single-quoted, with backslash
    escapes, across lines.
  - A link (`[text](url)`) or an image (`![...]`) is not a span.
  - Each field (`quote`, `cite`, `source`, `url`, `locator`) comes from the inline
    attribute first, then from the stored entry named by `key`. An empty value counts as
    absent.

## Checks

| Code | Severity | Rule |
|---|---|---|
| E0 | error | An input cannot be read or parsed (invalid YAML, undecodable text, no such workspace) |
| E0 | warning | A file named in `_quarto.yml` or front matter (`metadata-files`, `bibliography`) does not exist |
| E1 | error | A span's `key` is not in the evidence store. Reported at the span |
| E2 | error | A span has no quote: no inline `quote=`, and no stored quote that is non-empty text. Reported at the span. An unknown key with no inline quote gets both E1 and E2, as the filter warns twice |
| E3 | error | A `cite` key is not in the bibliography. An inline `cite=` is reported at the span. A stored `cite` is reported once, at its line in the evidence file. A stored cite also passes if it is in the bibliography of a document whose span uses the entry |
| E4 | error | An evidence entry is referenced by no span in any document. Reported at its key's line |
| E5 | error | Provenance format, one finding per bad field at its line (see below) |
| E6 | error / info | Verbatim check against local source text: `FOUND` (info, with receipt), `NOT_FOUND` (error), `UNCHECKABLE` (info: no local text) |
| W1 | warning | Number overreach: a number in the claim (the span's text) that no number in the quote supports |
| W2 | warning | Certainty upgrade: an assertive claim over a hedged quote |

The run fails on any error. Warnings and info findings do not fail it.

### E5: provenance

`provenance` must be a map. Each field that is present is checked:

- `method` must be exactly one of the `asta` subcommands in
  `consilience_ai2/receipts/data/asta_methods.json` (version `consilience-ai2.asta-methods/1`).
  The list was read from the click command tree of `allenai/asta-plugins` `src/asta` at
  commit a2dcade.
  - Leaf commands must match exactly, for example `asta papers snippet-search`.
  - `asta artifacts`, `asta documents`, `asta experiment` and `asta generate-theories`
    pass their arguments to another tool whose subcommands are not defined in that
    repository. They are accepted alone, or followed by lowercase subcommand words. They
    are never accepted with options or arguments.
- `corpus_id` must be a non-negative integer, written in digits.
- `url` must use the scheme `http`, `https` or `asta` (case-insensitive), the set the
  filter's `safe_url` accepts.
- `retrieved` must be a valid calendar date written `YYYY-MM-DD`.

### E6: verbatim, and the normalisation

The quote and the source text are both normalised with `consilience_ai2.core.normalise`
(version `consilience-ai2.normalise/1`). The six steps, in order:

1. expand ligatures;
2. apply NFKC only to meaning-preserving compatibility forms (superscripts, subscripts
   and fractions are kept);
3. straighten curly quotes;
4. remove a line-break hyphen before a lowercase letter;
5. remove soft hyphens and zero-width characters;
6. collapse whitespace.

The quote is `FOUND` when its normalised text occurs in the normalised source. The receipt
gives the source id, the source's SHA-256, the original character span `[offset, end)`
of the first occurrence, and the normalisation version.

Case, digits, words and other punctuation are not changed. A quote that differs from the
source in any of these is `NOT_FOUND`. Step 4 joins a word split across a line
(`over-\nfitting` becomes `overfitting`), and it does so on both sides of the comparison.

Local source text (`--sources`):

| Given | Looked up by | Receipt source | SHA-256 of |
|---|---|---|---|
| a directory of `<name>.txt` / `<name>.md` | `cite`, then `provenance.corpus_id` | `file:<name>.txt` | the file bytes |
| a Theorizer PaperStore JSON (`PaperStore.save` format) | `provenance.corpus_id` via the key `paper-<id>`; text is `paper_markdown` when `status` is `full-text` | `paperstore:<id>` | that text (UTF-8) |
| an AutoDiscovery exploration `index.json` | the entry's `source`, `run <label>, experiment <n>`; text is hypothesis, analysis and review joined by spaces, as the asta-flows `check.py` builds it | `autodiscovery:experiment-<n>` | that text |

Without `--sources`, or when nothing matches, the outcome is `UNCHECKABLE`, with the
reason. Offsets are character offsets into the decoded text.

### W1: number overreach

Numbers are read with `consilience_ai2.core.numbers`. A claim number is supported when a
number in the source agrees with it at the claim's printed precision.

- Absolute values are compared, because the sign is often carried by a word such as
  "fell".
- One percent scaling is allowed: a claim of 45% agrees with a source fraction of 0.45,
  and the other way round.
- A claim printed more precisely than the source is not supported. A claim of 0.421 is
  not supported by a source of 0.42; a claim of 0.42 is supported by a source of 0.4213.
- Uncertainties after `±` are checked like any other number.

These are not checked, and are listed in the finding's details:

- ambiguous separators (`1,2`, `1.234,5`), which are uncheckable rather than mismatches;
- year-like integers: an integer from 1900 to 2100 with no decimals, exponent or percent
  sign.

Numbers written as words ("three") are not read.

### W2: certainty upgrade, and the word lists

The word lists are in `consilience_ai2/receipts/data/certainty_words.json` (version
`consilience-ai2.certainty/1`). They are matched whole-word and case-insensitively on
normalised text.

- **Hedged**: apparently, appear(s/ed), associated, association(s), correlate(s/d),
  correlation(s), could, hypothesise(d), hypothesize(d), indicate(s/d), likely, linked,
  may, might, perhaps, plausible, plausibly, possible, possibly, potentially,
  preliminary, presumably, probably, putative, seem(s/ed), speculate, speculative,
  suggest(s/ed/ing), suggestive, tentative, tentatively.
- **Assertive**: always, causal, causally, cause(s/d), causing, certainly, clearly,
  conclusively, confirm(s/ed), definitely, definitively, demonstrate(s/d),
  establish(es/ed), guarantee(s/d), prove(s/d), proven, show(s/ed/n), undoubtedly,
  unequivocally.
- **Negators**: cannot, neither, never, no, nor, not, without, and any word ending in
  "n't".

An assertive word is negated when a negator occurs among the two words before it.

- A text is *assertive* when it has a non-negated assertive word and no hedged word.
- A text is *hedged* when it has a hedged word and no non-negated assertive word.

W2 flags an assertive claim over a hedged quote. Any change to the lists changes the
version, and the version is recorded in each W2 finding and in the report.

## Report format

The report is version 1 of the shared format (see `docs/SPEC.md`, section 3). It has:

- `inputs`, each with a path, role and SHA-256;
- `findings`, each with a code, severity, message, file, line, key, receipt and details;
- `summary` counts.

Fields specific to this component:

- `checked_spans` and `entries`;
- `sources`: the kind of local text and its size;
- `rules`: the normalisation, word-list and method-list versions.

The report has no timestamp. Findings are sorted by file, line, code, key and message.

## Using it in `make check`

The plugin `plugins/consilience-receipts` holds the skill `evidence-receipts` and a
snippet, `skills/evidence-receipts/assets/evidence-receipts.mk`. To use the snippet:

1. Copy it into the workspace.
2. Add `include evidence-receipts.mk` to the project's Makefile, next to its own checks.

The snippet makes `evidence-receipts` a prerequisite of `check`. Its settings are:

- `CONSILIENCE_AI2`: the command;
- `RECEIPTS_DIR`: the directory to check;
- `RECEIPTS_SOURCES`: passed as `--sources`;
- `RECEIPTS_REPORT`: the JSON path;
- `RECEIPTS_FLAGS`: for example `--fail-on-warnings`.

`tests/receipts/test_plugin.py` runs `make check` with the snippet:

- on the clean synthetic workspace, it passes;
- on the seeded workspace, it fails;
- with `--fail-on-warnings`, it fails on a warning.

## Adapters for released data

### Theorizer (`consilience_ai2.receipts.theorizer`)

The adapter reads the released HTML export of the theory stores (four conditions), as
written by asta-theorizer's `src/ExportTheoryStoreAsHTML.py`.

- **Laws.** In each theory file, each law is a `Statement <i>` section with its statement,
  its `Domain/Scope` and its "Supporting Evidence for this Law" items. Each item has text
  and evidence links such as `[e595.3]`.
- **Evidence records.** Each records file holds `extraction-instance-container` divisions
  with their field tables.
- **Predictive accuracy.** The evaluation pages give per-prediction counts of papers that
  support or contradict a law, or give no evidence.

Checks:

- **T1**: a cited evidence ID with no record of that ID in the same condition's records.
  - What is verified: the released export contains links to evidence records that do
    not exist. For example, `theories/theory-172.html` in
    `html_output-literature-supported-accuracy-focused` cites `e2232.5` to `e2232.9`,
    linked to `../results/e2232.5.html` to `../results/e2232.9.html`. No such files
    exist, and `results/extraction-result-2232.html` holds only `e2232.0` to `e2232.4`.
  - The exporter falls back silently. asta-theorizer `src/ExportTheoryStoreAsHTML.py`
    line 286 (commit c4802aa) is `extraction_id = uuid_to_extraction_id.get(uuid, uuid)`.
    The map is built from the `uuid` fields of the store's extraction results
    (`build_extraction_maps`, lines 875 to 884). An ID with no entry becomes its own
    file name, with no warning, so it renders as a link to `../results/<id>.html`. T1
    counts these links.
  - Why these IDs have no entry upstream is not established. The export cannot show
    whether the store never held those records or held them and lost them, and the
    checker does not guess.
- **T2**: a law whose scope is the empty note "Not specified.", or whose evidence list is
  the empty note "No evidence provided.".
- **W1 and W2**, at two levels:
  - each law statement against the field values of all the records it cites;
  - each evidence item (its text, IDs removed) against the records that item cites.

  A source made of several records is read record by record: numbers are pooled, and a
  negation never reaches across records.

Each finding's receipt gives the SHA-256 of the theory file and the character span of the
law section, or of the evidence link for T1.

### SciArena-Eval (`consilience_ai2.receipts.sciarena`)

- **Inline citations.** An inline citation is the `concise_authors` string of a listed
  citation, which in this release always has the form `<Name> et al. <year><letter>`.
  - It resolves when the string equals a listed citation's `concise_authors` and that
    citation has passage text.
- **Claims.** The citing sentence is split at `.`, `!` or `?` followed by whitespace and
  a capital letter or an opening bracket or quote, and at blank lines. Abbreviations such
  as `et al.` and `e.g.` do not end a sentence.
  - The claim is the sentence with its citations, and any parentheses that held only
    citations, removed.
- **Cited passages.** A sentence's claim is attributed jointly to all its citations. So
  each citation is checked against the concatenated passages of every resolved citation
  in that sentence.
- **Quotes.** A span of three or more words inside double quotes, in a sentence with at
  least one resolved citation, is checked verbatim against those passages (`FOUND` or
  `NOT_FOUND`).

## Validation

All numbers here render from `results/receipts.json`, written by
`analyses/receipts/run.py`. Rates carry Wilson 95% intervals there. Short examples with
receipts are in `analyses/receipts/examples.json`.

### Seeded-defect workspace (synthetic)

`examples/receipts/seeded/` is a synthetic workspace in the Asta format.

- **Planted defects.** Every code from E1 to E6, W1 and W2 is planted at a known line, 17
  planted findings in all. They are listed by hand in `expected_findings.json`.
- **Clean controls.** There are 14 control spans and 11 control entries. They exercise
  ligatures, line-break hyphenation, curly quotes, `87.5 %` against `87.5%`, hedged
  claims over hedged quotes, a negated assertive word, inline attributes over several
  lines, nested citations, a `corpus_id` lookup and an `asta://` URL. They also include
  spans inside code and comments, which must not be read.

`tests/receipts/test_seeded.py` asserts that the findings equal the expected file exactly.
Recall is 100% (`receipts.seeded.recall`, n = 17). There are 0 unexpected findings and 0
false findings on the controls. This is true by construction; it shows that the rules do
what they say, not how often real workspaces have these defects.

### The asta-plugins example workspace

`examples/workspace` in asta-plugins (pinned commit) has one `.ev` span and one evidence
entry. The checker reports 0 errors and 0 warnings. Its one quote is `UNCHECKABLE`
because no local source text ships with the example. It is the only real workspace
available to check, so there is no live defect to show.

### Theorizer (released HTML export)

The release has 2856 theories in four conditions and 4187 laws. The two
literature-supported conditions hold 1338 theories, 1897 laws, 18205 evidence links and
14343 distinct (law, evidence ID) pairs. Their results files hold 62093 evidence records
in 16316 extraction files.

Parse coverage:

- every theory file yields at least one law, and every law's statement parses;
- 80.9% of the extraction files contain at least one record. The rest show the
  export's "No extracted data." note.

Results:

- **T1.** 1.36% of cited (law, ID) pairs resolve to no record (n = 14343). They fall in
  0.52% of literature-supported theories, seven theories in all, all in the
  accuracy-focused condition.
  - Every unresolved link uses the export's fallback file name (100%,
    `receipts.theorizer.t1_href_fallback_share`).
  - The unresolved IDs share their extraction number with 18 extraction files that do
    exist but hold fewer records than were cited. For example, theory-172 cites
    `e2232.5` to `e2232.9` while `extraction-result-2232.html` holds `e2232.0` to
    `e2232.4` (the example above).
  - The novelty-focused condition has none.
- **T2.** 0.88% of all laws have an empty scope and an empty evidence list together.
  All of them are in the parametric accuracy-focused condition (2.48% of its laws).
  None of the literature-supported laws has either.
- **W1.**
  - At the law level, 37.78% of laws with resolved evidence (n = 1887) state a number
    that their cited records do not contain. This is driven by the novelty-focused
    condition (84.62%), whose laws are written as quantitative predictions with
    thresholds. Absence from the evidence is expected there by design. The rate is
    0.29% in the accuracy-focused condition.
  - At the evidence-item level, 5.28% of items (n = 7677) give a number not in the
    records they cite: 0.72% accuracy-focused, 21.62% novelty-focused.
- **W2.** 0.11% of laws and 2.51% of evidence items are assertive where their cited
  records are hedged.

Exploratory (not preregistered). Within each literature-supported condition, theories
were split at the median released predictive-accuracy support fraction (supporting
papers over supporting plus contradicting papers).

- **Accuracy-focused** (n = 317). T1 is not detectably different between the halves:
  1.55% against 0.81%, permutation p 0.67. Neither is W1: 2.59% against 6.45%, p 0.15.
- **Novelty-focused** (n = 115). There is no T1 in either half. W1 is 84.75% against
  87.5%, p 0.79.

These are differences with wide intervals on small groups, not findings.

### SciArena-Eval

The release has 2000 votes, 3993 of 4000 responses with at least one inline citation,
31820 inline citations and 27577 listed citations.

- **Resolution.** All but one of the 31820 inline citations resolve to a listed citation
  with passage text (`receipts.sciarena.resolution_rate`); the one that does not has an
  author-year string that is not listed. All but one of the 27577 listed citations are
  cited inline at least once.
- **W1.** 1.42% of resolved citations (n = 31819) sit in a sentence that gives a number
  absent from the passages it cites.
- **W2.** 1.40% sit in an assertive sentence over hedged passages.
- **Either.** 2.80% carry W1 or W2.
- **Quotes.** Responses rarely quote. There are 10 quoted spans of three or more words
  in cited sentences, and 20% of them are found verbatim in a cited passage.

### Preregistered: flag rate and the human vote (held-out)

The test is preregistered in `prereg/receipts/sciarena_prereg.md`, which was committed
before any code related flags to votes.

- **Hypothesis.** The response with the higher W1+W2 flag rate per citation loses the
  human vote more often.
- **Included votes.** 569 votes have both responses citing and unequal rates. Of the
  rest, 7 have a response citing nothing and 1424 have equal rates. There are no ties.
- **Result.** In 50.09% of included votes the higher-rate response lost. The exact 95%
  interval is 45.9% to 54.27%. The two-sided sign test gives p = 1.0, and the
  10,000-draw permutation p is also 1.0.
- **Decision under the preregistered rule: null.** There is no evidence of a difference
  at this sample size. This is not evidence that there is no difference.

The exploratory secondaries are not decision-bearing; both are null:

- W1 alone: 44.28% (n = 271, sign-test p 0.07);
- W2 alone: 52.3% (n = 348, sign-test p 0.42).

## Limits

- **Lexical, not semantic.** W1 and W2 compare numbers and words; they do not judge
  meaning or support.
  - A W1 number may come from elsewhere in the paper, a calculation or a unit
    conversion.
  - A W2 word may be appropriate in context. The word lists are short and fixed, and
    they miss hedges and assertions phrased in other words.
  - Negation is handled only within two words.
  - Whether a quote supports a claim is out of scope: asta-plugins leaves that to the
    `check-claims` skill.
- **Numbers.**
  - Numbers written as words, year-like integers and ambiguous separators are not
    checked.
  - Powers written `10^2` are read as two numbers.
  - Absolute values are compared, so a sign error is not flagged.
- **E6 needs local text.** Without `--sources` every quote is `UNCHECKABLE`.
  - Quotes are compared as written in `evidence.yml`. Pandoc would render Markdown in a
    metadata string (for example `*emphasis*`); the checker does not, so a quote with
    Markdown markup may be `NOT_FOUND`.
  - Text extracted from a PDF may differ from the published wording in ways the
    normalisation does not cover, such as reflowed tables and dropped symbols.
- **Workspace reading is a reimplementation.** The checker does not run Quarto or
  Pandoc. These are not read:
  - directory-level `_metadata.yml` files and Quarto profiles (`_quarto-*.yml`);
  - includes;
  - YAML merge keys;
  - an attribute value that contains backticks.

  A non-text quote (a YAML list or map) is treated as no quote (E2), where Pandoc would
  stringify it.
- **The E5 method list is a snapshot.** It is read from asta-plugins at commit a2dcade.
  New subcommands need a new list version. Subcommands of passthrough tools are accepted
  by form, not by name.
- **Theorizer.**
  - The checks read the HTML export, not the theory store, so T1 counts IDs that the
    export could not map. It does not say why they were unmapped upstream.
  - An evidence record holds an extraction, not the paper, so W1 against records
    overstates how often a number is absent from the source paper.
  - The novelty-focused W1 law rate reflects how those laws are written.
  - The predictive-accuracy split is exploratory and has small groups.
- **SciArena.**
  - Inline citations are found by their author-year string. A citation written another
    way is not counted.
  - A claim is attributed to all the citations in its sentence. A claim that spans two
    sentences, or a citation that supports only part of a sentence, is not separated.
  - HTML entities in responses (`&gt;`) are left as written.
