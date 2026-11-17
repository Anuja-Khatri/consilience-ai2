"""Static code facts: n constants, literals on the output path, column reads."""

from __future__ import annotations

from consilience_ai2.audit.codeanalysis import analyse


def test_unparseable_code():
    f = analyse("def f(:\n")
    assert not f.ok and "SyntaxError" in f.error


def test_n_constants():
    f = analyse("NUM_EPISODES = 50\nmodes = {'PILOT': 25, 'FULL_EXPERIMENT': 200}\n"
                "for i in range(30):\n    pass\nalpha = 0.05\nflag = True\n")
    assert set(f.n_constants) == {50, 25, 200, 30}


def test_literals_on_output_path_skip_format_specs():
    f = analyse("acc = 0.87\nprint(f'acc = {acc:.3f}')\nprint('rate 0.25')\nx = 0.33\n")
    on = {(lit.value, lit.context) for lit in f.literals if lit.on_output_path}
    assert ("0.87", "result-assign") in on and ("0.25", "sink-arg") in on
    assert not any(v in ("0.3", ".3", "3") for v, _ in on)
    assert ("0.33", "other") in {(lit.value, lit.context) for lit in f.literals}


def test_columns_read_created_and_formula():
    code = ("import pandas as pd\nimport statsmodels.formula.api as smf\n"
            "data = pd.read_csv('x.csv')\nsub = data.dropna(subset=['a'])\n"
            "sub['c'] = sub['a'] * 2\nm = smf.ols('y ~ a + C(g)', data=sub).fit()\n"
            "g = sub.groupby('g')['a'].mean()\nprint(g['label'])\n"
            "sub = sub.rename(columns={'a': 'renamed'})\n")
    f = analyse(code)
    assert set(f.columns_read) == {"a", "y", "g"}  # "c" is only written; "label" is a group label
    assert {"c", "renamed"} <= f.columns_created
