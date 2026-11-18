"""Evidence receipts (C1): deterministic, receipt-backed validity checks for evidence.

- ``check_workspace(root, sources=None, with_w2=False)``: an Asta workspace
  (``evidence.yml``, ``references.bib``, ``.qmd`` files with ``.ev`` spans): codes E0-E6
  and W1; W2 only with ``with_w2=True`` (opt-in: on a hand-checked sample only about a
  third of its flags were real overreach).
- ``consilience_ai2.receipts.theorizer``: the released Theorizer theories (T1, T2, W1, W2).
- ``consilience_ai2.receipts.sciarena``: SciArena-Eval responses with inline citations
  (citation resolution, W1, W2 and a verbatim check of quoted text).
- ``number_overreach`` (W1) and ``certainty_upgrade`` (W2) compare any claim with any
  source text, under rules ``v0.2`` (the default) or the frozen ``v0.1``.

No language-model calls; the same inputs give byte-identical reports.
"""

from consilience_ai2.receipts.claims import (
    certainty_profile,
    certainty_upgrade,
    certainty_words,
    number_overreach,
)
from consilience_ai2.receipts.workspace import check_workspace

__all__ = ["certainty_profile", "certainty_upgrade", "certainty_words", "check_workspace",
           "number_overreach"]
