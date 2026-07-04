"""Finding 8: explicit regex scope field (token | line)."""
from __future__ import annotations

import re

from detecto.analyzer import LogAnalyzer, _infer_scope
from detecto.loaders import DEFAULT_SCOPE, load_regexp


def test_scope_parsed_from_file(tmp_path):
    f = tmp_path / "regexp.csv"
    f.write_text(
        "TokenPat::4::desc::[A-Z]{2}[0-9]{2}::token\n"
        "LinePat::4::desc::foo bar::line\n",
        encoding="utf-8",
    )
    patterns = load_regexp(f)
    scopes = {p[0]: p[4] for p in patterns}
    assert scopes == {"TokenPat": "token", "LinePat": "line"}


def test_missing_scope_defaults_and_warns(tmp_path, caplog):
    import logging
    f = tmp_path / "regexp.csv"
    f.write_text("Legacy::4::desc::abc\n", encoding="utf-8")
    with caplog.at_level(logging.WARNING):
        patterns = load_regexp(f)
    assert patterns[0][4] == DEFAULT_SCOPE
    assert any("scope" in m.lower() for m in caplog.messages)


def test_analyzer_routes_by_explicit_scope(tmp_path):
    # A pattern with a space would be token-inferred wrong; explicit scope wins.
    line_pat = ("Greeting", 4, "d", re.compile(r"hello world"), "line")
    a = LogAnalyzer(regexp=[line_pat])
    assert a._regexp_line and not a._regexp_token
    p = tmp_path / "l.log"
    p.write_text("say hello world now\n", encoding="utf-8")
    results, _ = a.analyze([str(p)], refresh_status=0, workers=1)
    assert results["Greeting"][2]


def test_explicit_token_scope_overrides_whitespace_heuristic():
    entry = ("X", 4, "d", re.compile(r"[a-z]+"), "token")
    a = LogAnalyzer(regexp=[entry])
    assert a._regexp_token and not a._regexp_line


def test_infer_scope_fallback_for_4tuples():
    assert _infer_scope(r"foo bar") == "line"
    assert _infer_scope(r"foo\sbar") == "line"
    assert _infer_scope(r"[A-Z]{2}[0-9]{2}") == "token"


def test_no_source_replace_manipulation():
    # Lookaround with '=' must not be treated as a literal separator anymore.
    entry = ("Look", 4, "d", re.compile(r"(?=abc)\w+"), "token")
    a = LogAnalyzer(regexp=[entry])
    assert a._regexp_token
