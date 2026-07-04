"""Finding 1: runtime regex-DoS timeout.

Proves that a catastrophic-backtracking pattern applied to hostile input does
not stall the scan: the per-match timeout aborts it, the offending pattern is
recorded and disabled after a threshold, and the whole scan finishes well
within a bounded time.
"""
from __future__ import annotations

import time

import pytest

from detecto.analyzer import LogAnalyzer
from detecto.regexsafe import HAS_REGEX, compile_pattern

CATASTROPHIC = ["^(a+)+$", "(a|aa)+$", r"(\w+\s?)*$"]


def _write(tmp_path, name, lines):
    p = tmp_path / name
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(p)


@pytest.mark.parametrize("pattern_src", CATASTROPHIC)
def test_scan_finishes_within_time_bound(tmp_path, pattern_src):
    """Core guarantee: hostile input never hangs the scan (Finding 1).

    Some of the example patterns are optimised by the regex engine and never
    backtrack; the timeout catches the ones that do. Either way the scan must
    finish quickly.
    """
    compiled = compile_pattern(pattern_src)
    hostile = "a" * 45 + "!"
    logfile = _write(tmp_path, "evil.log", [hostile] * 12)
    analyzer = LogAnalyzer(
        regexp=[("Evil", 1, "catastrophic", compiled)],
        regex_timeout_ms=50,
        regex_disable_threshold=3,
    )
    start = time.time()
    _, line_count = analyzer.analyze([logfile], refresh_status=0, workers=1)
    elapsed = time.time() - start
    assert elapsed < 10.0, f"scan did not finish promptly ({elapsed:.1f}s)"
    assert line_count == 12


@pytest.mark.skipif(not HAS_REGEX, reason="runtime timeout needs the regex package")
def test_catastrophic_pattern_times_out_and_disables(tmp_path):
    # (a|aa)+$ reliably triggers exponential backtracking on the regex engine.
    compiled = compile_pattern("(a|aa)+$")
    hostile = "a" * 45 + "!"
    logfile = _write(tmp_path, "evil.log", [hostile] * 12)

    analyzer = LogAnalyzer(
        regexp=[("Evil", 1, "catastrophic", compiled)],
        regex_timeout_ms=50,
        regex_disable_threshold=3,
    )
    start = time.time()
    _, line_count = analyzer.analyze([logfile], refresh_status=0, workers=1)
    elapsed = time.time() - start

    assert elapsed < 10.0, f"scan did not finish promptly ({elapsed:.1f}s)"
    assert line_count == 12
    assert analyzer.diag.regex_timeouts.get("Evil", 0) >= 1
    # After the threshold the pattern is disabled for the rest of the scan.
    assert "Evil" in analyzer.diag.disabled_patterns
    # A disabled pattern makes the scan status 'partial', not silently complete.
    assert analyzer.diag.status().value == "partial"


@pytest.mark.skipif(not HAS_REGEX, reason="runtime timeout needs the regex package")
def test_normal_pattern_not_disabled(tmp_path):
    compiled = compile_pattern(r"[a-z]+@[a-z]+\.[a-z]{2,}")
    analyzer = LogAnalyzer(
        regexp=[("Email", 4, "email", compiled)],
        regex_timeout_ms=100,
    )
    logfile = _write(tmp_path, "ok.log", ["contact alice@example.com now"] * 5)
    results, _ = analyzer.analyze([logfile], refresh_status=0, workers=1)
    assert not analyzer.diag.disabled_patterns
    assert analyzer.diag.regex_timeouts == {}
    assert results["Email"][2]  # the email was found
    assert analyzer.diag.status().value == "complete"


def test_safe_finditer_returns_matches():
    """The timeout wrapper must not change normal match results."""
    compiled = compile_pattern(r"\d+")
    from detecto.regexsafe import safe_finditer, safe_search

    matches = safe_finditer(compiled, "a1 b22 c333", 100)
    assert [m.group(0) for m in matches] == ["1", "22", "333"]
    assert safe_search(compiled, "no digits here", 100) is None
