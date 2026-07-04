"""Performance smoke tests for Detecto.

Not strict timing tests — validates correctness on larger synthetic input
and reports throughput for manual benchmarking.
"""
from __future__ import annotations

import os
import re
import tempfile
import time

import pytest

from detecto.analyzer import LogAnalyzer


# --- Synthetic log line generators ---

def _generate_log_lines(count: int) -> str:
    """Generate synthetic log lines with a mix of patterns."""
    lines = []
    for i in range(count):
        mod = i % 10
        if mod == 0:
            lines.append(f"2024-01-15 10:00:{i % 60:02d} INFO user{i}@example.com logged in")
        elif mod == 1:
            lines.append(f"2024-01-15 10:00:{i % 60:02d} DEBUG password=Secret{i}!")
        elif mod == 2:
            lines.append(f"2024-01-15 10:00:{i % 60:02d} INFO Request from Hamburg client")
        elif mod == 3:
            lines.append(f"2024-01-15 10:00:{i % 60:02d} INFO User Mueller logged out")
        elif mod == 4:
            lines.append(f"2024-01-15 10:00:{i % 60:02d} DEBUG jdbc:oracle:thin:admin:pass{i}@db:1521/orcl")
        elif mod == 5:
            lines.append(f"2024-01-15 10:00:{i % 60:02d} WARN Connection timeout after {i}ms")
        elif mod == 6:
            lines.append(f"2024-01-15 10:00:{i % 60:02d} INFO Processing batch {i} of 1000")
        elif mod == 7:
            lines.append(f"2024-01-15 10:00:{i % 60:02d} DEBUG api_key -> AKI{i:08d}")
        elif mod == 8:
            lines.append(f"2024-01-15 10:00:{i % 60:02d} INFO Completed request in {i % 500}ms status=200")
        else:
            lines.append(f"2024-01-15 10:00:{i % 60:02d} ERROR NullPointerException at line {i}")
    return "\n".join(lines) + "\n"


@pytest.fixture
def large_log_file():
    """Create a large temporary log file with 50k lines."""
    content = _generate_log_lines(50_000)
    f = tempfile.NamedTemporaryFile(
        mode="w", suffix=".log", delete=False, encoding="utf-8")
    f.write(content)
    f.close()
    yield f.name
    os.unlink(f.name)


@pytest.fixture
def analyzer():
    """Create a LogAnalyzer with representative patterns."""
    regexp_patterns = [
        ("Email", 4, "E-Mail", re.compile(r"^\S+@\S+\.\S+$")),
        ("IBAN", 3, "IBAN", re.compile(r"^[A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}([A-Z0-9]?){0,16}$")),
    ]
    field_patterns = [
        ("Passwort", 1, "Password", re.compile(r"(?i)(password|passwort|pwd)"), 1),
        ("APIKey", 1, "API Key", re.compile(r"(?i)(api_key|apikey|api-key)"), 1),
    ]
    search_patterns = [
        ("Ort", 4, {"hamburg", "berlin", "muenchen", "koeln", "frankfurt",
                     "stuttgart", "dortmund", "essen", "duesseldorf", "bremen"}),
        ("Nachnamen", 4, {"mueller", "schmidt", "schneider", "fischer", "weber",
                          "meyer", "wagner", "becker", "schulz", "hoffmann"}),
    ]
    return LogAnalyzer(
        regexp=regexp_patterns,
        field=field_patterns,
        search=search_patterns,
    )


class TestPerformanceSmoke:
    """Smoke tests with larger synthetic input — correctness + throughput."""

    def test_correctness_50k_lines(self, large_log_file, analyzer):
        """Verify findings are correct on 50k lines."""
        results, lines = analyzer.analyze([large_log_file], workers=1)
        assert lines == 50_000

        # ~5000 email lines (mod 0)
        email_hits = results["Email"][2]
        assert len(email_hits) > 0, "Should find email addresses"

        # ~5000 password lines (mod 1)
        pw_hits = results["Passwort"][2]
        assert len(pw_hits) > 0, "Should find passwords"

        # ~5000 Hamburg lines (mod 2)
        ort_hits = results["Ort"][2]
        assert len(ort_hits) > 0, "Should find city names"

        # ~5000 Mueller lines (mod 3)
        name_hits = results["Nachnamen"][2]
        assert len(name_hits) > 0, "Should find last names"

        # ~5000 API key lines (mod 7)
        api_hits = results["APIKey"][2]
        assert len(api_hits) > 0, "Should find API keys"

    def test_throughput_report(self, large_log_file, analyzer, capsys):
        """Measure and report throughput (not a strict timing assertion)."""
        start = time.time()
        results, lines = analyzer.analyze([large_log_file], workers=1)
        duration = time.time() - start

        rate = lines / duration if duration > 0 else 0
        total_findings = sum(len(r[2]) for r in results.values())

        # Print for manual inspection (visible with -s flag)
        print(f"\n--- Performance Smoke ---")
        print(f"Lines:    {lines:,}")
        print(f"Duration: {duration:.2f}s")
        print(f"Rate:     {rate:,.0f} lines/sec")
        print(f"Findings: {total_findings}")
        print(f"-------------------------")

        # Sanity: should process at least 10k lines/sec on any modern machine
        assert rate > 10_000, f"Throughput too low: {rate:.0f} lines/sec"

    def test_max_examples_per_value_in_bulk(self, large_log_file):
        """Verify max_examples limit works with many hits."""
        a = LogAnalyzer(
            search=[("Ort", 4, {"hamburg"})],
            max_examples=5,
        )
        results, _ = a.analyze([large_log_file], workers=1)
        for val, entries in results["Ort"][2].items():
            assert len(entries) <= 5

    def test_prefilter_correctness(self, large_log_file):
        """Prefilter should not lose regexp/field findings."""
        patterns_re = [("Email", 4, "E-Mail", re.compile(r"^\S+@\S+\.\S+$"))]
        patterns_fd = [("PW", 1, "Passw", re.compile(r"(?i)password"), 1)]

        # Without prefilter
        a_off = LogAnalyzer(
            regexp=patterns_re, field=patterns_fd, prefilter="off")
        res_off, _ = a_off.analyze([large_log_file], workers=1)

        # With regexp_field prefilter
        a_rf = LogAnalyzer(
            regexp=patterns_re, field=patterns_fd, prefilter="regexp_field")
        res_rf, _ = a_rf.analyze([large_log_file], workers=1)

        # regexp_field should find same regexp+field hits
        for name in ("Email", "PW"):
            off_vals = set(res_off[name][2].keys())
            rf_vals = set(res_rf[name][2].keys())
            assert off_vals == rf_vals, f"Prefilter lost findings for {name}"
