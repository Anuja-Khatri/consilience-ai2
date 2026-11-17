"""The repo scripts: numbers lock, marketplace builder and the secret/data scan."""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from consilience_ai2.core.results import metric, write_results

REPO = Path(__file__).resolve().parent.parent


def load_script(name):
    spec = importlib.util.spec_from_file_location(f"_script_{name}", REPO / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


nl = load_script("numbers_lock")
mk = load_script("build_marketplace")
cs = load_script("check_secrets")


# ------------------------------------------------------------------ numbers lock

@pytest.mark.parametrize("line,tokens", [
    ("accuracy was 0.42 and 31%", ["0.42", "31%"]),
    ("see https://x.org/a/0.42 and doi:10.1234/5.6", []),
    ("CodeScientist, arXiv:2503.22708, and 2601.16282", []),
    ("pinned at a2dcade6ed2a and sha256: 21d2b98599dc", []),
    ("version 0.1.0, v1.2, requires consilience>=0.1.1 on Python 3.11+", []),
    ("as in §4.2 of the spec", []),
    ("p < 0.05 and q = 0.12", ["0.05", "0.12"]),     # thresholds and results ARE scanned
    ("n = 2856 theories", []),                       # integers are not result-like
    ("cited as [e595.3] under Apache-2.0 and CC-BY-4.0", []),  # ids and licences
    ("F1.5 is an identifier; 1.5 is not", ["1.5"]),
])
def test_result_tokens(line, tokens):
    assert nl.result_tokens(line) == tokens


def test_allowed_strings_cover_roundings_and_percents():
    allowed = nl.allowed_strings([{"value": 0.4433, "ci_lo": 0.41, "ci_hi": 0.47}])
    for s in ("0.4433", "0.44", "0.443", "44.3%", "44%", "44.33", "0.41", "47%"):
        assert s in allowed


@pytest.fixture
def fake_repo(tmp_path, monkeypatch):
    for d in ("results", "docs/tables", "scripts/numbers_allowlist"):
        (tmp_path / d).mkdir(parents=True)
    monkeypatch.setattr(nl, "REPO", tmp_path)
    monkeypatch.setattr(nl, "RESULTS", tmp_path / "results")
    monkeypatch.setattr(nl, "REGISTRY", tmp_path / "results" / "registry.json")
    monkeypatch.setattr(nl, "LOCK", tmp_path / "results" / "NUMBERS_LOCK.json")
    monkeypatch.setattr(nl, "TABLE", tmp_path / "docs" / "tables" / "results.md")
    monkeypatch.setattr(nl, "ALLOW_DIR", tmp_path / "scripts" / "numbers_allowlist")
    return tmp_path


def rec(mid, v):
    return metric(mid, v, n=100, source="fetch:x", dev_or_heldout="descriptive")


def test_lock_then_check_cycle(fake_repo, capsys):
    write_results("receipts", [rec("receipts.t1_rate", 0.0731)], fake_repo / "results")
    assert nl.lock() == 0
    (fake_repo / "README.md").write_text("The dangling-ID rate is 7.3% (0.0731).\n")
    assert nl.check(strict=True) == 0

    # an unregistered result-like number fails
    (fake_repo / "README.md").write_text("The rate is 7.9%.\n")
    assert nl.check(strict=False) == 1
    assert "README.md:1  7.9%" in capsys.readouterr().out

    # ...unless a component allow-lists it as a structural constant
    (fake_repo / "scripts" / "numbers_allowlist" / "receipts.txt").write_text("7.9%  # margin\n")
    assert nl.check(strict=False) == 0


def test_component_branch_flow(fake_repo, capsys):
    """A worker adds results/<component>.json and a doc citing it, without touching the
    registry or the lock: non-strict check passes (warning), strict check fails."""
    assert nl.lock() == 0  # skeleton state: empty registry
    write_results("audit", [rec("audit.fdr_reduction", 0.62)], fake_repo / "results")
    (fake_repo / "docs" / "audit.md").write_text("BH removes 62% of false discoveries.\n")
    assert nl.check(strict=False) == 0
    assert "warning" in capsys.readouterr().out
    assert nl.check(strict=True) == 1
    assert nl.lock() == 0  # the integrator
    assert nl.check(strict=True) == 0


def test_stale_lock_and_table_fail(fake_repo):
    write_results("audit", [rec("audit.a", 0.5)], fake_repo / "results")
    assert nl.lock() == 0
    (fake_repo / "docs" / "tables" / "results.md").write_text("edited\n")
    assert nl.check(strict=False) == 1
    assert nl.lock() == 0
    reg = json.loads((fake_repo / "results" / "registry.json").read_text())
    reg["metrics"][0]["value"] = 0.6
    (fake_repo / "results" / "registry.json").write_text(json.dumps(reg))
    assert nl.check(strict=False) == 1


def test_repo_numbers_lock_passes():
    # Non-strict: holds on a component branch too (a stale registry is a warning there).
    # GitHub CI runs the strict form on the integrated tree (make lock-check STRICT=1).
    assert nl.check(strict=False) == 0


# ------------------------------------------------------------------ marketplace

def test_marketplace_matches_asta_layout():
    data = json.loads((REPO / ".claude-plugin" / "marketplace.json").read_text())
    assert set(data) == {"name", "owner", "metadata", "plugins"}
    assert data["name"] == "consilience-ai2" and data["owner"]["name"]
    for entry in data["plugins"]:
        source = (REPO / entry["source"]).resolve()
        assert source.is_dir() and (source / "skills").is_dir(), entry["name"]
        assert entry["license"] == "MIT"


def test_no_per_plugin_manifests_and_skill_frontmatter():
    names = []
    for plugin in sorted(p for p in (REPO / "plugins").iterdir() if p.is_dir()):
        for vendor in (".plugin", ".claude-plugin", ".codex-plugin", ".cursor-plugin"):
            assert not (plugin / vendor / "plugin.json").exists(), plugin.name
        for md in sorted((plugin / "skills").glob("*/SKILL.md")):
            text = md.read_text()
            assert text.startswith("---\n"), md
            front = text.split("---\n", 2)[1]
            fields = dict(ln.split(":", 1) for ln in front.splitlines() if ":" in ln)
            assert fields.get("name", "").strip() == md.parent.name, md
            assert fields.get("description", "").strip(), md
            names.append(md.parent.name)
    assert len(names) == len(set(names)), "skill names must be unique across plugins"


def test_marketplace_check_passes():
    # Non-strict for the same reason; CI runs make marketplace-check STRICT=1.
    assert mk.check(strict=False) == 0


def test_marketplace_builder_with_an_entry(tmp_path, monkeypatch):
    (tmp_path / "plugins" / "consilience-demo" / "skills" / "demo").mkdir(parents=True)
    (tmp_path / "plugins" / "consilience-demo" / "marketplace-entry.json").write_text(
        json.dumps({"name": "consilience-demo", "description": "d", "keywords": ["k"]}))
    (tmp_path / ".claude-plugin").mkdir()
    (tmp_path / "pyproject.toml").write_text('[project]\nversion = "9.9.9"\n')
    monkeypatch.setattr(mk, "REPO", tmp_path)
    monkeypatch.setattr(mk, "PLUGINS", tmp_path / "plugins")
    monkeypatch.setattr(mk, "MARKETPLACE", tmp_path / ".claude-plugin" / "marketplace.json")
    (tmp_path / ".claude-plugin" / "marketplace.json").write_text(
        mk.render({"name": "consilience-ai2", "owner": {}, "metadata": {}, "plugins": []}))
    assert mk.check(strict=False) == 0   # unlisted entry: warning only
    assert mk.check(strict=True) == 1
    assert mk.main([]) == 0
    built = json.loads((tmp_path / ".claude-plugin" / "marketplace.json").read_text())
    assert built["plugins"][0] == {
        "name": "consilience-demo", "source": "./plugins/consilience-demo", "description": "d",
        "version": "9.9.9", "author": mk.OWNER, "repository": mk.REPOSITORY, "license": "MIT",
        "keywords": ["k"], "strict": False}
    assert mk.check(strict=True) == 0


# ------------------------------------------------------------------ secret scan

def test_secret_patterns_match_key_shapes_only():
    fake_key = "sk-" + "ant-" + "A" * 30
    assert any(rx.search(fake_key) for _, rx in cs.SECRETS)
    assert not any(rx.search("keys look like sk-... in prose") for _, rx in cs.SECRETS)
    aws = "AKIA" + "ABCDEFGHIJKLMNOP"
    assert any(rx.search(aws) for _, rx in cs.SECRETS)


def test_model_id_patterns():
    hit = "claude" + "-" + "sonnet" + "-4"
    assert any(rx.search(hit) for _, rx in cs.MODEL_IDS)
    assert any(rx.search("gpt" + "-4o") for _, rx in cs.MODEL_IDS)
    assert not any(rx.search("a Claude Code plugin skill") for _, rx in cs.MODEL_IDS)


def test_bad_names():
    def bad(rel):
        return any(rx.search(rel) for _, rx in cs.BAD_NAMES)
    assert bad("x/api_keys.donotcommit.json")
    assert bad("data/full50.zip") and bad(".env")
    assert not bad("examples/workspace/evidence.yml")


def test_repo_tree_is_clean():
    assert cs.main() == 0
