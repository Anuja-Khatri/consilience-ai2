"""The asta-plugins example workspace, when it is in the local cache (skipped otherwise).

This reads the pinned checkout of allenai/asta-plugins through ``fetch.require`` (no
network) and records what the checker finds on its real example workspace.
"""

from __future__ import annotations

import pytest

from consilience_ai2.fetch import FetchError, require
from consilience_ai2.receipts import check_workspace


@pytest.fixture
def asta_example():
    try:
        root = require("asta-plugins")
    except FetchError:
        pytest.skip("asta-plugins is not in the local cache")
    return root / "examples" / "workspace"


def test_asta_plugins_example_workspace(asta_example):
    r = check_workspace(asta_example)
    assert r.extra["checked_spans"] == 1 and r.extra["entries"] == 1
    assert [(f.code, f.severity, f.file, f.line, f.key, f.details["outcome"])
            for f in r.findings] == [
        ("E6", "info", "lit-review/index.qmd", 10, "transformer-attention", "UNCHECKABLE")]
    assert r.exit_code() == 0
