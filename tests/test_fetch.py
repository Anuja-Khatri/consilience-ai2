"""Fetch, offline: local copy-in, hash refusal, git pin checks, safe unzip, cache guard."""

import re
import subprocess
import zipfile
from pathlib import Path

import pytest

from consilience_ai2.core.hashing import sha256_file
from consilience_ai2.fetch import (
    FetchError,
    Source,
    SourceError,
    cache_root,
    fetch_source,
    load_sources,
    require,
    status,
)
from consilience_ai2.fetch import cli as fetch_cli
from consilience_ai2.fetch.get import extract

EXPECTED = {
    "codescientist", "codescientist-example-experiments", "codescientist-full50",
    "theorizer-paper-data", "asta-theorizer", "sciarena-eval", "discoverybench",
    "asta-autodiscovery", "asta-plugins",
}


def test_packaged_sources_are_pinned():
    sources = load_sources()
    assert set(sources) == EXPECTED
    for s in sources.values():
        assert s.licence and s.citation and s.url.startswith("https://")
        if s.kind == "git":
            assert re.fullmatch(r"[0-9a-f]{40}", s.commit)
        else:
            assert s.is_todo or re.fullmatch(r"[0-9a-f]{64}", s.sha256)
            assert not s.is_todo, f"{s.name}: hash should be pinned"
            assert s.size and s.size > 0


def test_cache_root_env_and_repo_guard(tmp_path, monkeypatch, repo_root):
    monkeypatch.setenv("CONSILIENCE_AI2_DATA", str(tmp_path / "c"))
    assert cache_root() == (tmp_path / "c").resolve()
    assert cache_root(tmp_path / "o") == (tmp_path / "o").resolve()
    with pytest.raises(SourceError):
        cache_root(repo_root / "data")


def file_source(tmp_path, content=b"hello data\n", **kw):
    f = tmp_path / "dl" / "thing.bin"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_bytes(content)
    fields = dict(name="thing", kind="file", url="https://example.invalid/thing.bin",
                  path="x/thing.bin", licence="MIT", citation="c",
                  sha256=sha256_file(f), size=len(content))
    fields.update(kw)
    return Source(**fields), f.parent


def test_file_from_dir_verifies_and_stamps(tmp_path):
    src, dl = file_source(tmp_path)
    root = tmp_path / "cache"
    p = fetch_source(src, root, [dl], quiet=True, offline=True)
    assert p == root.resolve() / "x" / "thing.bin"
    assert p.read_bytes() == b"hello data\n"
    assert status(src, root) == "ok"
    # second call is a no-op that does not re-copy
    assert fetch_source(src, root, [], quiet=True, offline=True) == p


def test_file_hash_mismatch_is_refused_and_cleaned(tmp_path):
    src, dl = file_source(tmp_path)
    bad = Source(**{**src.__dict__, "sha256": "0" * 64})
    root = tmp_path / "cache"
    with pytest.raises(FetchError, match="sha256"):
        fetch_source(bad, root, [dl], quiet=True, offline=True)
    assert not any((root / "x").glob("*")), "partial file must be removed"


def test_file_size_mismatch_is_refused(tmp_path):
    src, dl = file_source(tmp_path)
    bad = Source(**{**src.__dict__, "size": 3})
    with pytest.raises(FetchError, match="size"):
        fetch_source(bad, tmp_path / "cache", [dl], quiet=True, offline=True)


def test_tampered_cache_is_refused_on_verify(tmp_path):
    src, dl = file_source(tmp_path)
    root = tmp_path / "cache"
    p = fetch_source(src, root, [dl], quiet=True, offline=True)
    p.write_bytes(b"tampered\n")
    assert status(src, root) == "unverified"
    with pytest.raises(FetchError):
        fetch_source(src, root, [], verify=True, quiet=True, offline=True)


def test_offline_without_local_copy_fails(tmp_path):
    src, _ = file_source(tmp_path)
    with pytest.raises(FetchError, match="offline"):
        fetch_source(src, tmp_path / "cache", [tmp_path / "empty"], quiet=True, offline=True)


def test_todo_hash_is_never_fetched(tmp_path):
    src, dl = file_source(tmp_path, sha256="TODO: pin after manual download")
    assert src.is_todo
    with pytest.raises(FetchError, match="not pinned"):
        fetch_source(src, tmp_path / "cache", [dl], quiet=True, offline=True)


def make_zip(path: Path, members: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, "w") as zf:
        for name, data in members.items():
            zf.writestr(name, data)


def test_zip_extract_and_idempotent(tmp_path):
    z = tmp_path / "dl" / "pack.zip"
    z.parent.mkdir()
    make_zip(z, {"top/a.txt": b"a", "top/sub/b.txt": b"b"})
    src = Source(name="pack", kind="file", url="https://example.invalid/pack.zip",
                 path="p/pack.zip", licence="MIT", citation="c", sha256=sha256_file(z),
                 size=z.stat().st_size, extract=True)
    root = tmp_path / "cache"
    fetch_source(src, root, [z.parent], quiet=True, offline=True)
    out = root / "p" / "pack"
    assert (out / "top" / "sub" / "b.txt").read_bytes() == b"b"
    assert extract(src, root.resolve(), quiet=True) == root.resolve() / "p" / "pack"


@pytest.mark.parametrize("bad", ["../evil.txt", "/abs.txt", "a/../../evil.txt"])
def test_zip_traversal_refused(tmp_path, bad):
    z = tmp_path / "dl" / "evil.zip"
    z.parent.mkdir()
    make_zip(z, {bad: b"x"})
    src = Source(name="evil", kind="file", url="https://example.invalid/evil.zip",
                 path="e/evil.zip", licence="MIT", citation="c", sha256=sha256_file(z),
                 size=z.stat().st_size, extract=True)
    with pytest.raises(FetchError, match="unsafe"):
        fetch_source(src, tmp_path / "cache", [z.parent], quiet=True, offline=True)
    assert not (tmp_path / "evil.txt").exists()


def git(*args, cwd):
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *args], cwd=cwd,
                   check=True, capture_output=True)


@pytest.fixture
def local_repo(tmp_path):
    repo = tmp_path / "dl" / "myrepo"
    repo.mkdir(parents=True)
    git("init", "-q", cwd=repo)
    (repo / "f.txt").write_text("one\n")
    git("add", ".", cwd=repo)
    git("commit", "-q", "-m", "one", cwd=repo)
    first = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True,
                           text=True).stdout.strip()
    (repo / "f.txt").write_text("two\n")
    git("commit", "-q", "-am", "two", cwd=repo)
    return repo, first


def git_source(commit):
    return Source(name="myrepo", kind="git", url="https://example.invalid/org/myrepo.git",
                  path="git/myrepo", licence="MIT", citation="c", commit=commit)


def test_git_from_dir_checks_out_the_pin(tmp_path, local_repo):
    repo, first = local_repo
    root = tmp_path / "cache"
    p = fetch_source(git_source(first), root, [repo.parent], quiet=True, offline=True)
    assert (p / "f.txt").read_text() == "one\n"
    assert status(git_source(first), root) == "ok"


def test_git_wrong_pin_refused(tmp_path, local_repo):
    repo, _ = local_repo
    with pytest.raises(FetchError):
        fetch_source(git_source("f" * 40), tmp_path / "cache", [repo.parent], quiet=True,
                     offline=True)
    assert not (tmp_path / "cache" / "git" / "myrepo").exists()


def test_require_never_downloads(tmp_path):
    with pytest.raises(FetchError, match="consilience-ai2 fetch sciarena-eval"):
        require("sciarena-eval", tmp_path / "empty-cache")


def test_cli_list_and_unknown(tmp_path, capsys):
    import argparse
    parser = argparse.ArgumentParser()
    fetch_cli.register(parser.add_subparsers())
    args = parser.parse_args(["fetch", "--list", "--cache", str(tmp_path)])
    assert args.func(args) == 0
    out = capsys.readouterr().out
    assert "sciarena-eval" in out and "missing" in out
    args = parser.parse_args(["fetch", "nope", "--cache", str(tmp_path)])
    assert args.func(args) == 2
