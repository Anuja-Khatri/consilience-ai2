"""Reproduction verdict (C3): the asta-flows "Secondary reproduction" rubric as code.

A reproduction is judged on three separate axes (Faithfulness, Decidability, Outcome),
"read from the numbers, not from the prose", plus two process checks from the same
workflow: thresholds committed before the result, and the hypothesis copied verbatim.

    from consilience_ai2.reproduce import check_file
    report = check_file("record.yaml", repo=".")
    report.extra["verdict"]      # {"faithfulness", "decidability", "outcome", "verdict", ...}
    report.write("reproduction_verdict.json")

Codes: S1 (record), F1 (faithfulness), D1 (decidability), V1 (verdict), P1 (commit
order), P2 (verbatim hypothesis). See ``docs/reproduce.md`` for the decision tables.
"""

from consilience_ai2.reproduce.comparability import (
    Faithfulness,
    check_faithfulness,
    consilience_version,
    resolve_backend,
)
from consilience_ai2.reproduce.decide import (
    D1_CLASSES,
    OUTCOMES,
    VERDICT_OF,
    aggregate,
    check_decidability,
    check_hypothesis,
    check_verdict,
)
from consilience_ai2.reproduce.gitorder import check_commit_order
from consilience_ai2.reproduce.record import (
    SCHEMA_VERSION,
    Parsed,
    RecordError,
    load_file,
    parse,
    parse_file,
    schema,
    validate,
)
from consilience_ai2.reproduce.stats import p_from_effect, power
from consilience_ai2.reproduce.verdict import CHECKS, RUBRIC, TOOL, check_file, evaluate

__all__ = [
    "CHECKS", "D1_CLASSES", "OUTCOMES", "RUBRIC", "SCHEMA_VERSION", "TOOL", "VERDICT_OF",
    "Faithfulness", "Parsed", "RecordError", "aggregate", "check_commit_order",
    "check_decidability", "check_faithfulness", "check_file", "check_hypothesis",
    "check_verdict", "consilience_version", "evaluate", "load_file", "p_from_effect",
    "parse", "parse_file", "power", "resolve_backend", "schema", "validate",
]
