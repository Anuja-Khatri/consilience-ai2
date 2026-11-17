"""The Theorizer adapter on synthetic files in the released export format."""

from __future__ import annotations

from consilience_ai2.receipts import theorizer as th


def law_html(i, name, statement, scope, items, pe=None):
    scope_html = scope if scope is not None else '<span class="empty-note">Not specified.</span>'
    if items is None:
        ev = '<p class="empty-note">No evidence provided.</p>'
    else:
        lis = []
        for text, ids in items:
            links = "".join(
                f'<a href="../results/{href}.html#{e}" class="evidence-link">[{e}]</a> '
                for e, href in ids)
            lis.append(f"    <li>{text} {links}</li>\n")
        ev = "<ol>\n" + "".join(lis) + "</ol>"
    pe_html = (f'<p><strong>Predictive Accuracy Evaluation:</strong> <a href="../{pe}" '
               'class="evidence-link">[x]</a></p>') if pe else ""
    return (f'            <h3>Statement {i}: {name}</h3>\n'
            f'            <p><strong>Statement:</strong> {statement}</p>\n'
            f'            <p><strong>Domain/Scope:</strong> {scope_html}</p>\n'
            '            <h4>Special Cases</h4>\n'
            '            <h4>Supporting Evidence for this Law</h4>\n'
            f'{ev}'
            '            <h4>Self-Evaluation of Law Novelty (produced by the generation model)</h4>\n'
            '            <h4>External Evaluations of this Law</h4>\n'
            f'{pe_html}\n            <hr/>\n')


def theory_html(laws):
    return ('<div class="content"><h1>Theory Details for theory-9</h1>'
            '<p><strong>Name:</strong> A synthetic theory</p>'
            '<h2>Theory (Statement/Laws)</h2>' + "".join(laws)
            + '</div><div class="section"><h2>Theory (Additional Details)</h2>'
            '<h3>Unaccounted for Evidence</h3><ol><li>x '
            '<a href="../results/extraction-result-1.html#e1.9" class="evidence-link">[e1.9]</a>'
            '</li></ol></div>')


RESULTS = (
    '<h1>Extracted Data Details for extraction-result-1</h1>'
    '<div class="extraction-instance-container" id="e1.0"><table><tbody>'
    '<tr>\n<td><strong>name_short</strong></td>\n<td>Method A</td>\n</tr>'
    '<tr>\n<td><strong>performance_metrics</strong></td>\n<td>Accuracy 87.5% vs 80.1%; the gain may be associated with &lt;b&gt;size</td>\n</tr>'
    '</tbody></table></div>'
    '<div class="extraction-instance-container" id="e1.1"><table><tbody>'
    '<tr><td><strong>result</strong></td><td>We show a 3.0 point gain.</td></tr>'
    '</tbody></table></div>')


def fixture(tmp_path):
    cond = tmp_path / "html_output-literature-supported-accuracy-focused"
    (cond / "theories").mkdir(parents=True)
    (cond / "results").mkdir()
    (cond / "results" / "extraction-result-1.html").write_text(RESULTS)
    (cond / "results" / "extraction-result-2.html").write_text("<h1>no records</h1>")
    laws = [
        law_html(0, "Clean law", "Method A reaches 87.5% accuracy.", "Applies to A.",
                 [("Method A (e1.0) reaches 87.5%.", [("e1.0", "extraction-result-1")])],
                 pe="predictiveaccuracy/pe-00001-theory-9.html"),
        law_html(1, "Dangling law", "Size causes the gain.", "Applies to B.",
                 [("A gain of 4.2 points (e1.0, e7.3).",
                   [("e1.0", "extraction-result-1"), ("e7.3", "e7.3")])]),
        law_html(2, "Empty law", "Something.", None, None),
        law_html(3, "Uncited law", "Something else.", "Scope.", [("No IDs here.", [])]),
    ]
    (cond / "theories" / "theory-9.html").write_text(theory_html(laws))
    return cond


def test_records_parse(tmp_path):
    cond = fixture(tmp_path)
    recs, info = th.load_records(cond)
    assert sorted(recs) == ["e1.0", "e1.1"]
    assert info == {"results_files": 2, "records": 2, "duplicate_ids": 0,
                    "files_without_records": 1}
    assert recs["e1.0"].fields[1] == ("performance_metrics",
                                      "Accuracy 87.5% vs 80.1%; the gain may be associated with <b>size")
    assert "Method A" in recs["e1.0"].text and "name_short" not in recs["e1.0"].text


def test_theory_parse(tmp_path):
    cond = fixture(tmp_path)
    (t,) = list(th.iter_theories(cond))
    assert t.id == "theory-9" and t.name == "A synthetic theory"
    assert [law.index for law in t.laws] == [0, 1, 2, 3]
    a, b, c, d = t.laws
    assert a.scope == "Applies to A." and a.ids == ["e1.0"]
    assert a.pe_file == "predictiveaccuracy/pe-00001-theory-9.html"
    assert b.ids == ["e1.0", "e7.3"] and b.items[0].hrefs[1] == "../results/e7.3.html#e7.3"
    assert c.scope is None and c.evidence_empty and c.items == []
    assert d.items[0].ids == () and not d.evidence_empty
    # Unaccounted-for evidence after the laws is not a law's evidence
    assert "e1.9" not in sum((law.ids for law in t.laws), [])


def test_checks_both_directions(tmp_path):
    cond = fixture(tmp_path)
    recs, _ = th.load_records(cond)
    (t,) = list(th.iter_theories(cond))
    findings, results = th.check_theory(t, recs, cond.name)
    got = sorted((f.code, f.key, (f.details or {}).get("level")) for f in findings)
    assert got == [
        ("T1", "theory-9#statement-1", None),
        ("T2", "theory-9#statement-2", None),
        ("W1", "theory-9#statement-1/item-1", "item"),
        ("W2", "theory-9#statement-1", "law"),
    ]
    t1 = next(f for f in findings if f.code == "T1")
    text = (cond / "theories" / "theory-9.html").read_text()
    assert text[t1.receipt.offset:t1.receipt.end].startswith('<a href="../results/e7.3.html')
    assert t1.details == {"id": "e7.3", "href": "../results/e7.3.html#e7.3", "well_formed": True}
    r0, r1, r2, r3 = results
    assert (r0.w1, r0.w2, r0.unresolved) == (False, False, [])
    assert (r1.w1, r1.w2, r1.unresolved, r1.w1_items) == (False, True, ["e7.3"], 1)
    assert (r2.empty_scope, r2.empty_evidence, r2.w1) == (True, True, None)
    assert (r3.items_without_ids, r3.items_checked) == (1, 0)


def test_info_receipts_for_clean_laws(tmp_path):
    cond = fixture(tmp_path)
    recs, _ = th.load_records(cond)
    (t,) = list(th.iter_theories(cond))
    findings, _ = th.check_theory(t, recs, cond.name, emit_info=True)
    info = [f for f in findings if f.severity == "info"]
    assert [f.key for f in info] == ["theory-9#statement-0"]


def test_predictive_accuracy_parse():
    row = ('<tr><td><strong>Counts (# of papers)</strong></td>\n<td>{}</td>\n<td>{}</td>\n'
           '<td>{}</td></tr>')
    html = ('<p><strong>Theory ID:</strong> theory-9</p>' + row.format(3, 0, 10)
            + row.format(1, 2, 11))
    pa = th.parse_predictive_accuracy(html, "predictiveaccuracy/pe-1.html")
    assert (pa.theory_id, pa.support, pa.contradict, pa.no_evidence, pa.predictions) == (
        "theory-9", 4, 2, 21, 2)


def test_strip_html():
    assert th.strip_html("a <b>b</b>  &amp; c") == "a b & c"
