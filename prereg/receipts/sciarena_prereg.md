# Preregistration: W1/W2 flag rate and the human vote on SciArena-Eval

Component: receipts (C1). Split: `heldout`. Committed on its own, before any code that
reads the votes in relation to the flags is written or run.

## Hypothesis

In a SciArena-Eval vote, the response with the higher per-citation W1+W2 flag rate loses
the human vote more often than its paired response.

## Data

SciArena-Eval `train.json` as pinned in `consilience_ai2/fetch/sources.yaml`
(`sciarena-eval`, SHA-256 `fb0e5b44c616cd4a1a9e5ea19c5e51c7f28b372874255074065394c8954ad1f1`,
dataset revision `e20851545db108e94e35f8c0595b8ad72169b480`): 2,000 votes, each with two
responses, their listed citations with passage text, and the vote.

## Measure (frozen)

The checks are those of `consilience_ai2/receipts/sciarena.py`, `claims.py` and the word
list `consilience_ai2/receipts/data/certainty_words.json` (version
`consilience-ai2.certainty/1`), with normalisation `consilience-ai2.normalise/1`, exactly
as committed in commit `32807cb467ed31bdd13d5a856b3b006991ca038d`. They are not changed for this test.

- Inline citations, resolution, the citing sentence, the claim and the cited passages are
  as defined in the `sciarena.py` module docstring at that commit.
- For one response: `flags` = the number of its inline citations with W1 set plus the
  number with W2 set (a citation with both counts twice); `n` = the number of its inline
  citations (unresolved citations count in `n`, with no flags).
- Flag rate = `flags / n`, defined only when `n >= 1`.

## Pairs

A vote is included when all of these hold:

1. its `vote` is `A` or `B` (anything else is a tie or missing and is excluded);
2. both responses have at least one inline citation;
3. the two flag rates differ (equal rates are excluded, like ties).

For an included vote, the outcome is 1 when the response with the higher flag rate lost
the vote, else 0. `k` = the sum of outcomes; `N` = the number of included votes.

## Test

- Primary: a two-sided exact sign test of `k` against `N` with probability 0.5
  (`scipy.stats.binomtest(k, N, 0.5, alternative="two-sided")`).
- Permutation null, reported beside it: 10,000 draws from `numpy.random.default_rng(0)`;
  in each draw every included vote's outcome is flipped independently with probability
  0.5; `p_perm = (1 + #{draws with |k_draw - N/2| >= |k - N/2|}) / (10,000 + 1)`.
- Effect size: `k / N` with its exact (Clopper-Pearson) 95% confidence interval.

## Decision rule

- **Supported**: `k / N > 0.5` and the sign-test p < 0.05.
- **Opposite direction**: `k / N < 0.5` and the sign-test p < 0.05; reported as such,
  and the hypothesis is not supported.
- **Null**: otherwise (sign-test p >= 0.05); reported as a null, meaning no evidence of
  a difference at this sample size, not evidence of no difference.

The decision uses the sign test. The permutation p is reported; if it falls on the other
side of 0.05, both are reported and the disagreement is noted.

## Secondary analyses (exploratory, not decision-bearing)

The same procedure with W1 alone and with W2 alone as the flag. Reported with the label
`exploratory`.

## What was seen before this commit

- The file's format, including the counts of A and B votes, was inspected when the
  adapter was written.
- Descriptive per-citation rates (resolution, W1, W2) were computed and committed. That
  code does not read the vote field.
- No association between flags and votes has been computed or looked at.

## Reporting

The metric `receipts.sciarena.heldout.higher_flag_rate_loses` (value `k / N`, `n = N`,
the 95% CI) and its p-values go in `results/receipts.json` with `dev_or_heldout:
heldout` and this file's path and commit in `prereg`. A null is reported as a null.
