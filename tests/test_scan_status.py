"""Finding 2: explicit scan status + exit codes.

A scan that could not read every file must never be reported as a clean,
complete success. Status is derived from per-file counters and mapped to
distinct process exit codes.
"""
from __future__ import annotations

import argparse
import os
from collections import OrderedDict

import pytest

from detecto.analyzer import LogAnalyzer
from detecto.diagnostics import (
    EXIT_FAILED,
    EXIT_OK,
    EXIT_PARTIAL,
    ScanDiagnostics,
    ScanStatus,
)


def _make_analyzer():
    import re
    return LogAnalyzer(
        regexp=[("Secret", 1, "secret", re.compile(r"secret=\w+"))],
    )


def test_status_failed_when_nothing_evaluated():
    d = ScanDiagnostics()
    assert d.status() is ScanStatus.FAILED


def test_status_complete():
    d = ScanDiagnostics(files_complete=3)
    assert d.status() is ScanStatus.COMPLETE


def test_status_partial_on_unreadable():
    d = ScanDiagnostics(files_complete=1, files_unreadable=1)
    assert d.status() is ScanStatus.PARTIAL


def test_status_partial_when_pattern_disabled():
    d = ScanDiagnostics(files_complete=1)
    d.disabled_patterns.add("Evil")
    assert d.status() is ScanStatus.PARTIAL


def test_unreadable_file_marks_failed(tmp_path):
    bad = tmp_path / "bad.log"
    bad.write_text("secret=abc\n", encoding="utf-8")
    os.chmod(bad, 0o000)
    try:
        if os.access(str(bad), os.R_OK):
            pytest.skip("cannot revoke read permission (running as root?)")
        analyzer = _make_analyzer()
        _, lines = analyzer.analyze([str(bad)], refresh_status=0, workers=1)
        assert analyzer.diag.files_unreadable == 1
        assert analyzer.diag.status() is ScanStatus.FAILED
        assert analyzer.diag.file_errors  # error text recorded
    finally:
        os.chmod(bad, 0o644)


def test_mixed_files_marks_partial(tmp_path):
    good = tmp_path / "good.log"
    good.write_text("secret=abc\n", encoding="utf-8")
    bad = tmp_path / "bad.log"
    bad.write_text("secret=xyz\n", encoding="utf-8")
    os.chmod(bad, 0o000)
    try:
        if os.access(str(bad), os.R_OK):
            pytest.skip("cannot revoke read permission (running as root?)")
        analyzer = _make_analyzer()
        analyzer.analyze([str(good), str(bad)], refresh_status=0, workers=1)
        assert analyzer.diag.files_complete == 1
        assert analyzer.diag.files_unreadable == 1
        assert analyzer.diag.status() is ScanStatus.PARTIAL
    finally:
        os.chmod(bad, 0o644)


def test_compute_exit_code():
    from detecto.cli import _compute_exit_code

    args = argparse.Namespace(exit_on_findings=False)
    empty: OrderedDict = OrderedDict()
    assert _compute_exit_code(ScanStatus.COMPLETE, empty, args) == EXIT_OK
    assert _compute_exit_code(ScanStatus.PARTIAL, empty, args) == EXIT_PARTIAL
    assert _compute_exit_code(ScanStatus.FAILED, empty, args) == EXIT_FAILED

    args_findings = argparse.Namespace(exit_on_findings=True)
    with_findings: OrderedDict = OrderedDict()
    with_findings["x"] = ("regexp", 1, {"v": [("f", "l", None)]})
    assert _compute_exit_code(ScanStatus.COMPLETE, with_findings, args_findings) == 1


def test_summary_lines_contains_status():
    d = ScanDiagnostics(files_complete=2)
    text = "\n".join(d.summary_lines())
    assert "Scan-Status: complete" in text
