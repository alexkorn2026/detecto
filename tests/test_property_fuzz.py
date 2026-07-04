"""Finding 35: property / fuzz / differential tests via hypothesis.

Invariants that must hold for arbitrary input:
  1. the scanner never hangs / raises an unhandled exception,
  2. stored match positions lie within the stored example line,
  3. parallel and sequential runs produce identical findings,
  4. anonymized output never contains the original value,
  5. the excel sanitizer never emits a formula cell.
"""
from __future__ import annotations

import re

from hypothesis import given, settings
from hypothesis import strategies as st

from detecto.analyzer import LogAnalyzer
from detecto.anonymizer import Anonymizer
from detecto.exporter import _sanitize_cell
from detecto.formatter import highlight

PATTERNS = [
    ("email", 4, "e", re.compile(r"[^\s=]+@[^\s=]+\.[a-z]+"), "token"),
    ("word", 4, "w", re.compile(r"[A-Za-z]{4,}"), "token"),
]
FIELDS = [("Passwort", 1, "pw", re.compile(r"(?i)(passw|kennw)"), 1)]

# A mix of hostile characters: unicode, nulls, escapes, urls, @, IPv6, spaces.
line_strategy = st.text(
    alphabet=st.characters(min_codepoint=0, max_codepoint=0x2FFF),
    max_size=300,
) | st.sampled_from([
    "password=\x00\x00\x00",
    "user@@@@host",
    "2001:db8::1 ff02::1",
    "https://u:p@[::1]:80/a?b[c]=d%40e",
    "{'broken': json,,,}",
    "a" * 200 + "!",
    "\t\r\n   =SUM(1)  ",
])


def _analyzer():
    return LogAnalyzer(regexp=PATTERNS, field=FIELDS, parse_json="auto")


@settings(max_examples=200, deadline=None)
@given(line=line_strategy)
def test_scanner_never_crashes_and_positions_valid(line, tmp_path_factory):
    d = tmp_path_factory.mktemp("fuzz")
    p = d / "f.log"
    p.write_text(line + "\n", encoding="utf-8", errors="ignore")
    a = _analyzer()
    results, _ = a.analyze([str(p)], refresh_status=0, workers=1)
    for _name, (_t, _k, hits) in results.items():
        for _val, examples in hits.items():
            for e in examples:
                stored, start, end = e[1], e[4], e[5]
                if start >= 0 and end >= 0:
                    assert 0 <= start <= end <= len(stored)


@settings(max_examples=100, deadline=None)
@given(lines=st.lists(line_strategy, min_size=1, max_size=8))
def test_parallel_equals_sequential(lines, tmp_path_factory):
    d = tmp_path_factory.mktemp("fuzz2")
    paths = []
    for i, ln in enumerate(lines):
        p = d / f"f{i}.log"
        p.write_text(ln + "\n", encoding="utf-8", errors="ignore")
        paths.append(str(p))

    def snap(results):
        return {n: {v: len(ex) for v, ex in h.items()}
                for n, (_t, _k, h) in results.items()}

    seq, _ = _analyzer().analyze(paths, refresh_status=0, workers=1)
    par, _ = _analyzer().analyze(paths, refresh_status=0, workers=4)
    assert snap(seq) == snap(par)


@settings(max_examples=200, deadline=None)
@given(value=st.text(
    alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
    min_size=5, max_size=40,
))
def test_anonymized_output_hides_value(value):
    # A distinctive alnum value that is not a substring of the wrapper text.
    line = f"KEYXYZ={value} ENDXYZ"
    anon = Anonymizer("sss**sss**")
    out = highlight(line, value, anon=True, color=False, anonymizer=anon)
    redacted = anon.redact(value)
    if redacted != value:  # anonymizer actually changed something
        assert value not in out


@settings(max_examples=300, deadline=None)
@given(text=st.text(max_size=50))
def test_excel_sanitizer_no_formula(text):
    out = _sanitize_cell(text)
    if isinstance(out, str) and out:
        effective = out.lstrip(" \t\r\n\v\f")
        assert not effective or effective[0] not in ("=", "+", "-", "@")
