"""Tests for loader security and functionality."""
from __future__ import annotations

from detecto.loaders import _read_lines, _safe_compile, _validate_path, load_stopwords


class TestPathValidation:
    def test_normal_path_accepted(self, tmp_path):
        assert _validate_path(str(tmp_path), "data.csv") is not None

    def test_traversal_blocked(self, tmp_path):
        assert _validate_path(str(tmp_path), "../../etc/passwd") is None

    def test_dot_dot_blocked(self, tmp_path):
        assert _validate_path(str(tmp_path), "../secret.csv") is None

    def test_absolute_outside_blocked(self, tmp_path):
        assert _validate_path(str(tmp_path), "/etc/passwd") is None


class TestSafeCompile:
    def test_valid_pattern(self):
        assert _safe_compile(r"\d+", "test.csv") is not None

    def test_invalid_returns_none(self):
        assert _safe_compile(r"[invalid", "test.csv") is None

    def test_simple_accepted(self):
        assert _safe_compile(r"(?i)password", "test.csv") is not None


class TestReadLines:
    def test_skips_empty(self, tmp_path):
        (tmp_path / "t.csv").write_text("line1\n\nline2\n\n")
        assert len(_read_lines(str(tmp_path / "t.csv"))) == 2

    def test_splits_by_delimiter(self, tmp_path):
        (tmp_path / "t.csv").write_text("a::b::c::d\n")
        # _read_lines now returns (lineno, raw, parts) for Finding 6.
        lineno, raw, parts = _read_lines(str(tmp_path / "t.csv"))[0]
        assert lineno == 1 and len(parts) == 4


class TestStopwords:
    def test_loads_and_normalizes(self, tmp_path):
        (tmp_path / "stop.txt").write_text("Hello\nWORLD\nM\u00fcller\n")
        result = load_stopwords(str(tmp_path / "stop.txt"))
        assert {"hello", "world", "muller"} <= result

    def test_nonexistent_returns_empty(self):
        assert load_stopwords("/nonexistent/path.txt") == set()
