# Evidence receipts (`consilience-ai2 receipts`)

Rule-based checks of the evidence behind written claims, for Asta workspaces and for two
released datasets (Theorizer theories and SciArena-Eval). There are no model calls. The
same input gives byte-identical output. Every finding carries a receipt: the SHA-256 of
what was checked and, where there is one, the character span.

Independent work, not affiliated with or endorsed by the Allen Institute for AI (Ai2).

## Running it

```bash
consilience-ai2 receipts check <workspace_dir> [--sources DIR|paperstore.json|index.json ...]
                               [--rules v0.1|v0.2] [--with-w2] [--json OUT]
```

W2 is opt-in because on a hand-checked sample only about a third of its flags were real
overreach. W1 stays on by default, as a warning: about half of its flags were real (see
"Precision of W1 and W2" below for the measured precision).

- One GitHub annotation line is printed per error or warning, for example
  `::error file=defects.qmd,line=7::E1 .ev span references unknown key "d-missing-key"`.
  `--all-annotations` also prints the info receipts. `--no-annotations` prints none.
- `--json OUT` writes the version-1 report (format below).
- Exit codes: 0 when there is no error; 1 on any error; 2 on a usage error (for example
  a `--sources` path that does not exist). `--fail-on-warnings` makes warnings (W1, and
  W2 when it is on) fail the run too.
- `--with-w2` turns on W2, the certainty-upgrade check. It is off by default.
- `--rules` picks the W1/W2 rule version: `v0.2` (the default) or `v0.1`, the frozen
  rules of the preregistered SciArena test (see "W1 and W2 rule versions" below).
- `--sources` may be repeated; the stores are tried in the order given.

Python API: `consilience_ai2.receipts.check_workspace(root, sources=None, rules="v0.2",
with_w2=False)` returns a `Report`; `sources` may be a path or a list of paths, and
`with_w2=True` turns on W2. `number_overreach(claim,
source, rules=...)` (W1) and `certainty_upgrade(claim, source, rules=...)` (W2) compare
any claim with any source text.

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
| W1 | warning | Number overreach: a number in the claim (the span's text) that no number in the quote supports. On by default |
| W2 | warning | Certainty upgrade: an assertive claim over a hedged quote. Opt-in (`--with-w2`) |

W1 and W2 are lexical. On a hand-checked sample (see "Precision of W1 and W2" below),
about half of the W1 flags and about a third of the W2 flags were a real overreach. That
is why W1 runs by default, as a warning, and W2 runs only when asked for. The analyses of
released data below compute W2 explicitly; their W2 rates do not depend on the default.

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
| an Asta PaperStore JSON (below) | `provenance.corpus_id` via the key `paper-<id>`; text is `paper_markdown` when `status` is `full-text` | `paperstore:<id>` | that text (UTF-8) |
| an AutoDiscovery exploration `index.json` | the entry's `source`, `run <label>, experiment <n>`; text is hypothesis, analysis and review joined by spaces, as the asta-flows `check.py` builds it | `autodiscovery:experiment-<n>` | that text |

Without `--sources`, or when nothing matches, the outcome is `UNCHECKABLE`, with the
reason. Offsets are character offsets into the decoded text. With several `--sources`,
the first store that has the text is used; when none has it, the reason lists each
store's reason.

The PaperStore format is the one asta-theorizer's `src/PaperStore.py` writes with
`PaperStore.save` (commit c4802aa). The asta-plugins `data-driven-theory-generation`
workflow keeps one per run at `<run>/theory/paperstore.json`.

- `paperstore` maps a primary key to a paper record with `status` (`full-text`,
  `metadata-only`, `failed` or `timeout`), `corpus_id`, `title` and `paper_markdown`.
- `paperstore_lut` maps every alternate key (`paper-<corpus_id>`, `paper-<S2 sha>`,
  `paper-<sanitised title>`) to the primary key.
- The checker looks up `paper-<corpus_id>` in the LUT, as `PaperStore._paper_lookup_by_key`
  does, and then as a primary key. A record whose status is not `full-text` is
  `UNCHECKABLE`, with its status as the reason.

`tests/receipts/test_sources.py` checks a synthetic PaperStore in this layout, a
directory keyed by `corpus_id`, and several stores in order. When the pinned
asta-theorizer checkout is in the local cache, it also checks the format against
`PaperStore.py`.

### W1 and W2 rule versions

There are two versions of the W1 and W2 rules. Each finding records its version
(`number_rules` for W1, `word_list` for W2), and the report records both under `rules`.

- **v0.1** is frozen. It scored the preregistered SciArena test, which is not re-scored
  with any later rules. Its descriptive rates keep their metric IDs.
- **v0.2** is the default. Its changes are listed under each check below. Its
  descriptive rates are reported beside the v0.1 rates under metric IDs containing
  `v02`.

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

Rules v0.2 (`consilience-ai2.w1/2`, in `consilience_ai2/receipts/numbers_w1.py`) read
numbers the same way on both sides, with five additions:

1. **Powers.** `10^2`, `10**2`, `10^{-3}`, `2^10` and `10⁻³` are one number each. v0.1
   reads `10^2` as 10 and 2. `10^k` has the precision of its order of magnitude; another
   base gives the exact power. The exponent of a symbol (`x^2`) is not a number.
2. **Percent words.** `50 percent`, `50 per cent`, `50 pct` and `5 percentage points`
   are percentages, so `50 percent` agrees with a source fraction of 0.5.
3. **Scale words.** `1.5 million` is 1,500,000 at the precision of its last printed
   digit, and likewise `thousand`, `billion` and `trillion`.
4. **Scale suffixes** written directly after the digits. `1.5k` and `3bn` are read as
   thousands and billions. `K`, `M` and `B` are also units (kelvin, molar, bytes), so
   `2M` is read both ways, as 2 and as 2,000,000. A claim number is supported when any
   of its readings is. `1.5kg` is not scaled.
5. **Number words.** `zero` to `nineteen`, the tens and the multipliers (`hundred` to
   `trillion`), combined as written: `twenty-five`, `two hundred and five`, `a
   thousand`. A phrase ending in a multiplier has that multiplier's precision.

Not read in v0.2, by decision:

- `one` alone, which is more often a pronoun or determiner ("one of the", "no one")
  than a quantity; it is read inside a compound (`one hundred`);
- a number word joined by a hyphen to a word that is not a number (`two-stage`,
  `zero-shot`): a modifier, not a stated quantity;
- plurals (`hundreds`) and ordinals (`third`);
- the relations `half`, `twice`, `double` and `triple`. They state a ratio between two
  quantities, which a source supports by giving the two quantities rather than by
  printing the ratio, so reading them would flag correct claims.

Signs in v0.2: when the claim and a source number both carry an explicit sign and the
signs differ, that source number does not support the claim. An unsigned number on
either side still agrees with either sign. v0.1 ignores signs.

### W2: certainty upgrade, and the word lists

The word lists are matched whole-word and case-insensitively on normalised text.

- A text is *assertive* when it has a non-negated assertive word and no hedged word.
- A text is *hedged* when it has a hedged word and no non-negated assertive word.

W2 flags an assertive claim over a hedged quote. Any change to the lists changes the
version, and the version is recorded in each W2 finding and in the report.

Rules v0.1 use `consilience_ai2/receipts/data/certainty_words.json` (version
`consilience-ai2.certainty/1`):

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
  "n't". An assertive word is negated when a negator occurs among the two words before
  it.

Rules v0.2 use `consilience_ai2/receipts/data/certainty_words_v2.json` (version
`consilience-ai2.certainty/2`). It keeps every v0.1 word, and lists each added word, by
group, under `added`.

- **Negation scope is the clause.** A negator negates every later assertive word up to
  the next clause punctuation (`, ; : . ! ? ( ) [ ]` and dashes) or clause conjunction
  (although, and, because, but, however, nevertheless, nonetheless, since, though,
  unless, whereas, while, whilst). "There is no evidence that this clearly causes harm"
  is negated throughout. `or` is not a boundary, because under negation it coordinates
  inside the scope ("did not show or confirm"). `yet` is not one either, because in
  scientific prose it is mostly the adverb ("has not yet been shown").
- **Added hedges**: epistemic adverbs and adjectives (arguably, conceivable(ly),
  potential, possibility, probable, putatively, seemingly, speculatively, uncertain,
  unclear, unlikely); verbs that present a claim as proposed (postulate(s/d), presumed,
  tend(s/ed), speculation, suggestion); and forms missing from v0.1 (appearing,
  correlating, hypothesises, hypothesizes, indicating, indicative, speculated,
  speculates).
- **Added boosters**: evidently, incontrovertibly, indisputably, irrefutably, obviously,
  unambiguously, undeniably, unquestionably, and the forms causation, confirming,
  demonstrating, establishing, proving and showing.
- **Added negators**: fail(s/ed/ing), lack(s/ed/ing), nobody, none, nothing, unable
  ("failed to show").

No published hedging lexicon was both permissively licensed and fit for use:

- The MIT-licensed `words/hedges` list (Titus Wormer) mixes boosters ("always",
  "certainly", "clearly", "definitely", "must") into its hedges. It also includes very
  common words ("about", "can", "find", "found", "most", "will").
- Hyland's hedge and booster lists (*Metadiscourse*, 2005) are not under a permissive
  licence.

Neither is copied. The added words follow the published categories instead: epistemic
verbs, adverbs and adjectives that lower (hedges) or raise (boosters) commitment.

## Report format

The report is version 1 of the shared format (see `docs/SPEC.md`, section 3). It has:

- `inputs`, each with a path, role and SHA-256;
- `findings`, each with a code, severity, message, file, line, key, receipt and details;
- `summary` counts.

Fields specific to this component:

- `checked_spans` and `entries`;
- `checks`: the codes that ran (`E0` to `E6` and `W1`, plus `W2` with `--with-w2`);
- `sources`: the kind of local text and its size;
- `rules`: the W1/W2 rule version (`w1_w2_rules`), the normalisation, number-rule,
  word-list and method-list versions.

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
- `RECEIPTS_FLAGS`: for example `--with-w2` or `--fail-on-warnings`.

`tests/receipts/test_plugin.py` runs `make check` with the snippet:

- on the clean synthetic workspace, it passes;
- on the seeded workspace, it fails;
- with `--fail-on-warnings`, it fails on a W1 warning, and on a W2 warning only with
  `--with-w2` as well.

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

The W2 defect is planted, so the expected file is written for a run with `--with-w2`;
without it, every other finding is the same and the W2 is not reported.
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

W1 and W2 below use rules v0.1; the v0.2 rates follow them.

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
- **Rules v0.2 (descriptive).** W1: 37.73% of laws (0.29% accuracy-focused, 84.51%
  novelty-focused) and 5.18% of evidence items (0.67% accuracy-focused, 21.39%
  novelty-focused). W2: 0.16% of laws and 2.45% of evidence items. The
  `receipts.theorizer.v02.*` metrics hold the intervals.

Exploratory (not preregistered, rules v0.1). Within each literature-supported
condition, theories were split at the median released predictive-accuracy support fraction (supporting
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
- **W1** (rules v0.1). 1.42% of resolved citations (n = 31819) sit in a sentence that
  gives a number absent from the passages it cites.
- **W2** (rules v0.1). 1.40% sit in an assertive sentence over hedged passages.
- **Either** (rules v0.1). 2.80% carry W1 or W2.
- **Rules v0.2 (descriptive).** W1 1.5%, W2 1.65%, either 3.11% of the same citations
  (`receipts.sciarena.v02.*`). These rates are not used by the preregistered test.
- **Quotes.** Responses rarely quote. There are 10 quoted spans of three or more words
  in cited sentences, and 20% of them are found verbatim in a cited passage.

### Preregistered: flag rate and the human vote (held-out)

This test was scored with W1/W2 rules v0.1, frozen in the preregistration. It stays as
published and is not re-scored with rules v0.2.

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

### Precision of W1 and W2 (dev, one annotator)

How often is a flag a real overreach? A fixed-seed sample of flagged units was read by
hand. The sampling and labelling are in `analyses/receipts/precision_sample.py`. The
labels, with a one-line reason each and short spans only, are in
`analyses/receipts/precision_sample.jsonl`.

- **Units.** A SciArena unit is a citing sentence against its cited passages. A
  Theorizer unit is an evidence item against the records it cites (both
  literature-supported conditions).
- **Sample.** Per check and per rule version, 25 flagged SciArena units and 25 flagged
  Theorizer units are drawn, by the smallest SHA-256 of a fixed key. Both versions use
  the same keys, so a unit flagged by both is drawn for both: 48 of the W1 units and 36 of
  the W2 units are scored under both versions.
- **Labels.** `true` when the claim states a quantity, or a certainty, that the cited
  text does not support; `false_alarm` otherwise (the number is there in another form,
  is not a stated quantity, or the hedge is about something else).
- **Caveat.** There was one annotator, the author of the rules, so the labels are
  neither blind nor independent. The split is `dev`. The two datasets are weighted
  equally, not by their number of flags.

| Check | Rules | Precision | 95% interval (Wilson) | n |
|---|---|---|---|---|
| W1 | v0.1 | 54% | 40.4% to 67.0% | 50 |
| W1 | v0.2 | 56% | 42.3% to 68.8% | 50 |
| W2 | v0.1 | 26% | 15.9% to 39.6% | 50 |
| W2 | v0.2 | 32% | 20.8% to 45.8% | 50 |

The differences between versions are well inside the intervals. On the same units:

- **W1.** Of the 50 sampled v0.1 flags, v0.2 drops 2, and both were false alarms
  (`RMB 88.79 million` against `88,788,500`; a table reference). Per dataset, v0.1 and
  v0.2 are 48% on SciArena; on Theorizer, 60% (v0.1) and 64% (v0.2).
- **W2.** Of the 50 sampled v0.1 flags, v0.2 drops 6, all false alarms; most are dropped
  because the source also uses a booster added in v0.2 ("showing"). Of the 14 sampled
  units that only v0.2 flags, 5 are true.

The false alarms fall into a few classes. They are candidates for a later rule
version, which would need a fresh sample to measure.

- **W1.**
  - Names with digits: `Landsat 8`, `Industry 4.0`, `SDG 13`, `Big Five`, `3D`,
    `OATP1B1/3`.
  - Compound names written with a non-breaking hyphen (`COVID‑19`, `CFC‑11`), which
    `core.numbers` does not treat as a hyphen.
  - Table, figure and section references.
  - Differences of two source numbers (`+16.7%` from 62.4% to 79.1%).
  - Paraphrased bounds ("over 50" for a range ending at 51).
  - Notation (`O(1)`), and text-extraction damage in the source (`1.5e7.0` for `1.5–7.0`).
- **W2.**
  - Most W2 false alarms have a hedge in the source that is about a different statement
    from the claim.
  - The rest use "show" as "exhibit" or "show promise", or "established" as an
    adjective.

## Limits

- **Lexical, not semantic.** W1 and W2 compare numbers and words; they do not judge
  meaning or support.
  - A W1 number may come from elsewhere in the paper, a calculation or a unit
    conversion.
  - A W2 word may be appropriate in context. The word lists are short and fixed, and
    they miss hedges and assertions phrased in other words.
  - W2 does not check that a source's hedge concerns the claimed statement. That is the
    most common W2 false alarm in the precision sample.
  - Negation reaches two words in v0.1 and the rest of the clause in v0.2. A clause
    boundary inside a negated clause ("not, as far as we know, shown") ends the scope
    early.
  - Whether a quote supports a claim is out of scope: asta-plugins leaves that to the
    `check-claims` skill.
- **Numbers.**
  - Year-like integers and ambiguous separators are not checked. v0.1 also does not
    read numbers written as words.
  - v0.1 reads powers written `10^2` as two numbers; v0.2 reads them as one.
  - v0.1 compares absolute values, so a sign error is not flagged. v0.2 flags only two
    explicit signs that differ.
  - Fractions (`1/2`) and space-grouped thousands (`11 000`) are not read as one number.
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
