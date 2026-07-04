"""Finding 4: global memory / result limits with transparent counting."""
from __future__ import annotations

import re

from detecto.analyzer import LogAnalyzer
from detecto.constants import EXAMPLE_TRUNCATE_MARKER


def _write(tmp_path, name, lines):
    p = tmp_path / name
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(p)


def _email_analyzer(**kw):
    return LogAnalyzer(
        regexp=[("email", 4, "Email", re.compile(r"[^\s=]+@[^\s=]+\.[a-z]+"))],
        **kw,
    )


def test_max_example_chars_truncates_with_marker(tmp_path):
    long_line = "prefix " * 500 + "email=a@b.example " + "suffix " * 500
    logfile = _write(tmp_path, "long.log", [long_line])
    a = _email_analyzer(max_example_chars=100)
    results, _ = a.analyze([logfile], refresh_status=0, workers=1)
    stored = next(iter(results["email"][2].values()))[0][1]
    assert EXAMPLE_TRUNCATE_MARKER in stored
    assert len(stored) <= 100 + len(EXAMPLE_TRUNCATE_MARKER) + 2
    assert a.diag.examples_truncated >= 1


def test_max_total_findings_caps_and_counts(tmp_path):
    lines = [f"email=user{i}@test.de" for i in range(50)]
    logfile = _write(tmp_path, "many.log", lines)
    a = _email_analyzer(max_total_findings=10)
    results, _ = a.analyze([logfile], refresh_status=0, workers=1)
    assert len(results["email"][2]) == 10
    assert a.diag.findings_dropped_global > 0
    assert a.diag.global_limit_hit == "max_total_findings"


def test_max_examples_per_value_caps(tmp_path):
    # same value on many lines -> examples per value capped
    lines = ["email=same@test.de"] * 20
    logfile = _write(tmp_path, "same.log", lines)
    a = _email_analyzer(max_examples=3)
    results, _ = a.analyze([logfile], refresh_status=0, workers=1)
    examples = results["email"][2]["same@test.de"]
    assert len(examples) == 3


def test_max_total_examples_caps(tmp_path):
    lines = [f"email=user{i}@test.de" for i in range(50)]
    logfile = _write(tmp_path, "many.log", lines)
    a = _email_analyzer(max_total_examples=5)
    results, _ = a.analyze([logfile], refresh_status=0, workers=1)
    total = sum(len(v) for v in results["email"][2].values())
    assert total <= 5
    assert a.diag.global_limit_hit == "max_total_examples"


def test_findings_stored_counted(tmp_path):
    lines = [f"email=user{i}@test.de" for i in range(7)]
    logfile = _write(tmp_path, "seven.log", lines)
    a = _email_analyzer()
    a.analyze([logfile], refresh_status=0, workers=1)
    assert a.diag.findings_stored == 7
