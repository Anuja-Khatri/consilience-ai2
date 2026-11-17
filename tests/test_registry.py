import argparse
import sys
import textwrap

import pytest

from consilience_ai2 import cli
from consilience_ai2.core.registry import COMPONENTS, discover


def test_component_list_is_fixed():
    assert COMPONENTS == ("receipts", "audit", "reproduce", "fetch")


@pytest.fixture
def fake_package(tmp_path, monkeypatch):
    pkg = tmp_path / "fakepkg"
    (pkg / "dummy").mkdir(parents=True)
    (pkg / "nocli").mkdir()
    (pkg / "broken").mkdir()
    for d in (pkg, pkg / "dummy", pkg / "nocli", pkg / "broken"):
        (d / "__init__.py").write_text("")
    (pkg / "dummy" / "cli.py").write_text(textwrap.dedent("""
        def register(subparsers):
            p = subparsers.add_parser("dummy", help="a dummy component")
            p.add_argument("--n", type=int, default=0)
            p.set_defaults(func=lambda args: args.n)
    """))
    (pkg / "broken" / "cli.py").write_text("import a_module_that_does_not_exist_xyz\n")
    monkeypatch.syspath_prepend(str(tmp_path))
    yield "fakepkg"
    for name in list(sys.modules):
        if name.startswith("fakepkg"):
            del sys.modules[name]


def test_discovers_present_and_skips_missing(fake_package):
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    names = discover(sub, components=["absent", "nocli", "dummy"], package=fake_package)
    assert names == ["dummy"]
    args = parser.parse_args(["dummy", "--n", "7"])
    assert args.func(args) == 7


def test_real_import_errors_are_not_hidden(fake_package):
    sub = argparse.ArgumentParser().add_subparsers()
    with pytest.raises(ModuleNotFoundError):
        discover(sub, components=["broken"], package=fake_package)


def test_register_must_exist(fake_package, tmp_path):
    (tmp_path / "fakepkg" / "noreg").mkdir()
    (tmp_path / "fakepkg" / "noreg" / "__init__.py").write_text("")
    (tmp_path / "fakepkg" / "noreg" / "cli.py").write_text("x = 1\n")
    sub = argparse.ArgumentParser().add_subparsers()
    with pytest.raises(TypeError):
        discover(sub, components=["noreg"], package=fake_package)


def test_real_cli_has_fetch_and_skips_absent_components():
    _, names = cli.build_parser()
    assert "fetch" in names
    assert set(names) <= set(COMPONENTS)


def test_main_without_command_is_usage_error(capsys):
    assert cli.main([]) == 2


def test_version(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["--version"])
    assert exc.value.code == 0
    assert "consilience-ai2 0.1.0" in capsys.readouterr().out
