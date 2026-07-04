"""Findings 21, 22, 23, 25: workers, mp thresholds, context window, excel injection."""
from __future__ import annotations

import re

from detecto.analyzer import LogAnalyzer, detect_cpu_count, resolve_workers
from detecto.exporter import _sanitize_cell

# --- Finding 21: container-aware worker cap -------------------------------

def test_detect_cpu_count_positive():
    assert detect_cpu_count() >= 1


def test_resolve_workers_caps_auto():
    detected, cap, used = resolve_workers(0, max_auto=8)
    assert used <= 8
    assert used <= detected
    assert cap == 8


def test_resolve_workers_explicit_respected():
    _, _, used = resolve_workers(3, max_auto=8)
    assert used == 3


def test_resolve_workers_low_cap():
    _, _, used = resolve_workers(0, max_auto=2)
    assert used <= 2


# --- Finding 23: context window instead of full lines ---------------------

def _ctx_analyzer(**kw):
    return LogAnalyzer(
        field=[("Passwort", 1, "pw", re.compile(r"(?i)(passw|kennw)"), 1)],
        context_chars_before=10, context_chars_after=10, **kw,
    )


def test_context_window_trims_line(tmp_path):
    long_line = "x" * 200 + " password=Secret123 " + "y" * 200
    p = tmp_path / "c.log"
    p.write_text(long_line + "\n", encoding="utf-8")
    a = _ctx_analyzer()
    results, _ = a.analyze([str(p)], refresh_status=0, workers=1)
    entry = results["Passwort"][2]["Secret123"][0]
    stored = entry[1]
    assert len(stored) < len(long_line)
    assert "Secret123" in stored
    assert "…[gekuerzt]" in stored  # truncation marker present


def test_store_full_lines_opt_in(tmp_path):
    long_line = "x" * 200 + " password=Secret123 " + "y" * 200
    p = tmp_path / "c.log"
    p.write_text(long_line + "\n", encoding="utf-8")
    a = _ctx_analyzer(store_full_lines=True, max_example_chars=100000)
    results, _ = a.analyze([str(p)], refresh_status=0, workers=1)
    entry = results["Passwort"][2]["Secret123"][0]
    assert entry[1] == long_line


# --- Finding 25: excel formula injection ----------------------------------

def test_sanitize_formula_start():
    assert _sanitize_cell("=1+1").startswith("'=")
    assert _sanitize_cell("-2+3").startswith("'-")
    assert _sanitize_cell("@SUM(A1)").startswith("'@")


def test_sanitize_leading_whitespace():
    assert _sanitize_cell(" +SUM(A1:A2)").startswith("'")
    assert _sanitize_cell("\t=HYPERLINK(1)").startswith("'")
    assert _sanitize_cell("\r@SUM(1)").startswith("'")


def test_sanitize_plain_value_untouched():
    assert _sanitize_cell("alice@example.com") == "alice@example.com"
    assert _sanitize_cell("normal text") == "normal text"


def test_sanitize_strips_control_chars():
    out = _sanitize_cell("bad\x00value\x07here")
    assert "\x00" not in out and "\x07" not in out


def test_sanitize_length_capped():
    out = _sanitize_cell("a" * 40000)
    assert len(out) <= 32767


def test_sanitize_non_string_passthrough():
    assert _sanitize_cell(5) == 5
    assert _sanitize_cell(None) is None
