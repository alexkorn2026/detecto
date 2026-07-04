"""Tests for the LogAnalyzer class."""
from __future__ import annotations

import configparser
import os
import re
import tempfile

import pytest

from detecto.analyzer import LogAnalyzer, _compute_chunks
from detecto.config import DetectoConfig, load_config


@pytest.fixture
def log_file():
    """Factory fixture: create temporary log files, cleaned up after test."""
    files: list[str] = []

    def _create(content: str) -> str:
        f = tempfile.NamedTemporaryFile(
            mode="w", suffix=".log", delete=False, encoding="utf-8")
        f.write(content)
        f.close()
        files.append(f.name)
        return f.name

    yield _create
    for path in files:
        os.unlink(path)


def test_regexp_match(log_file):
    path = log_file("email=anna@test.de\n")
    a = LogAnalyzer(regexp=[("email", 4, "Email", re.compile(r"^\S+@\S+\.\S+$"))])
    results, lines = a.analyze([path])
    assert lines == 1 and len(results["email"][2]) > 0


def test_field_match(log_file):
    path = log_file("password=geheim123\n")
    a = LogAnalyzer(field=[("PW", 1, "Passw", re.compile(r"(?i)password"), 1)])
    results, _ = a.analyze([path])
    assert "geheim123" in results["PW"][2]


def test_field_skips_separator(log_file):
    path = log_file("password -> Produktiv!1\n")
    a = LogAnalyzer(field=[("PW", 1, "Passw", re.compile(r"(?i)password"), 1)])
    results, _ = a.analyze([path])
    assert "->" not in results["PW"][2]
    assert any("Produktiv" in v for v in results["PW"][2])


def test_string_match(log_file):
    path = log_file("Name: Hamburg\n")
    a = LogAnalyzer(search=[("Ort", 4, {"hamburg"})])
    results, _ = a.analyze([path])
    assert len(results["Ort"][2]) > 0


def test_stopwords(log_file):
    path = log_file("password and something\n")
    a = LogAnalyzer(
        field=[("PW", 1, "Passw", re.compile(r"(?i)password"), 1)],
        sw_field={"and"},
    )
    results, _ = a.analyze([path])
    assert "and" not in results["PW"][2]


def test_empty_logfile(log_file):
    path = log_file("")
    a = LogAnalyzer(regexp=[("email", 4, "Email", re.compile(r"^\S+@\S+$"))])
    results, lines = a.analyze([path])
    assert lines == 0 and len(results["email"][2]) == 0


class TestPathAndMaskDetection:
    """Finding 5: only unambiguous paths suppress values; masks are distinct."""

    @pytest.mark.parametrize("value", [
        "/etc/passwd", "/opt/app/config", "\\\\server\\share",
        "~/config/app", "C:\\Users", "D:/data",
    ])
    def test_real_paths_detected(self, value):
        from detecto.analyzer import _looks_like_path
        assert _looks_like_path(value) is True

    @pytest.mark.parametrize("value", [
        # Finding 5: these are passwords, NOT paths - must not be filtered.
        "/MySecret2026!", "C:verySecret", "geheim123", "MyPassword!",
        "admin", "secret_key",
    ])
    def test_credential_values_not_treated_as_paths(self, value):
        from detecto.analyzer import _looks_like_path
        assert _looks_like_path(value) is False

    @pytest.mark.parametrize("value", [
        "********", "xxxxx", "<redacted>", "[MASKED]", "<hidden>",
    ])
    def test_masked_values_detected(self, value):
        from detecto.analyzer import _is_masked_value
        assert _is_masked_value(value) is True

    @pytest.mark.parametrize("value", [
        "geheim123", "MyPassword!", "a@b.example",
    ])
    def test_real_values_not_masked(self, value):
        from detecto.analyzer import _is_masked_value
        assert _is_masked_value(value) is False


def test_normalization_cached(log_file):
    path = log_file("password secret123\n")
    a = LogAnalyzer(
        regexp=[("test", 4, "t", re.compile(r"secret"))],
        search=[("words", 4, {"secret123"})],
    )
    results, _ = a.analyze([path])
    assert len(results["test"][2]) > 0 and len(results["words"][2]) > 0


def test_non_utf8_auto_encoding(caplog):
    # Finding 26: non-UTF-8 bytes are handled by encoding auto-detection
    # (windows-1252 fallback) instead of a per-line warning; the whole file is
    # read and the effective encoding is recorded.
    f = tempfile.NamedTemporaryFile(suffix=".log", delete=False)
    f.write(b"valid line\ninvalid \xbb byte\nanother valid\n")
    f.close()
    try:
        a = LogAnalyzer()
        results, lines = a.analyze([f.name])
        assert lines == 3
        assert a.diag.encodings_used[f.name] == "windows-1252"
        assert a.diag.status().value == "complete"
    finally:
        os.unlink(f.name)


def test_max_hits_per_pattern(log_file):
    content = "\n".join(f"email=user{i}@test.de" for i in range(100))
    path = log_file(content)
    # Finding 4: the per-pattern value cap is now a constructor/config parameter.
    a = LogAnalyzer(
        regexp=[("email", 4, "Email", re.compile(r"^\S+@\S+\.\S+$"))],
        max_values_per_pattern=10,
    )
    results, _ = a.analyze([path])
    assert len(results["email"][2]) <= 10
    assert a.diag.findings_dropped_pattern > 0  # drops are counted, not silent


class TestConfigValidation:
    def test_negative_examplecount_clamped(self):
        assert DetectoConfig(examplecount=-5).examplecount == 1

    def test_critical_too_high_clamped(self):
        assert DetectoConfig(critical=99).critical == 5

    def test_critical_too_low_clamped(self):
        assert DetectoConfig(critical=0).critical == 1

    def test_minlen_below_2_clamped(self):
        assert DetectoConfig(minlen=0).minlen == 2

    def test_valid_values_unchanged(self):
        cfg = DetectoConfig(examplecount=5, critical=3, minlen=4)
        assert cfg.examplecount == 5 and cfg.critical == 3 and cfg.minlen == 4

    def test_max_examples_clamped(self):
        assert DetectoConfig(max_examples=0).max_examples == 1
        assert DetectoConfig(max_examples=-5).max_examples == 1
        assert DetectoConfig(max_examples=50).max_examples == 50


# --- New tests for v1.3 optimizations ---

class TestReverseIndex:
    """Test that the reverse-index dict produces correct string search results."""

    def test_single_category(self, log_file):
        path = log_file("Found Hamburg in log\n")
        a = LogAnalyzer(search=[("Ort", 4, {"hamburg", "berlin", "muenchen"})])
        results, _ = a.analyze([path])
        assert len(results["Ort"][2]) > 0

    def test_multiple_categories(self, log_file):
        path = log_file("Mueller aus Hamburg\n")
        a = LogAnalyzer(search=[
            ("Ort", 4, {"hamburg"}),
            ("Nachnamen", 4, {"mueller"}),
        ])
        results, _ = a.analyze([path])
        assert len(results["Ort"][2]) > 0
        assert len(results["Nachnamen"][2]) > 0

    def test_value_in_multiple_categories(self, log_file):
        """A value that appears in two categories should match both."""
        path = log_file("Token overlap_value here\n")
        a = LogAnalyzer(search=[
            ("Cat1", 4, {"overlap_value"}),
            ("Cat2", 4, {"overlap_value"}),
        ])
        results, _ = a.analyze([path])
        assert len(results["Cat1"][2]) > 0
        assert len(results["Cat2"][2]) > 0

    def test_no_match(self, log_file):
        path = log_file("Nothing interesting here\n")
        a = LogAnalyzer(search=[("Ort", 4, {"hamburg"})])
        results, _ = a.analyze([path])
        assert len(results["Ort"][2]) == 0

    def test_search_index_built(self):
        a = LogAnalyzer(search=[
            ("Ort", 4, {"hamburg", "berlin"}),
            ("Name", 4, {"mueller"}),
        ])
        assert "hamburg" in a._search_index
        assert "berlin" in a._search_index
        assert "mueller" in a._search_index
        assert a._search_index["hamburg"] == ["Ort"]


class TestMaxExamplesPerValue:
    """Test that per-value example limit is enforced."""

    def test_limit_enforced(self, log_file):
        """More hits than max_examples should be capped."""
        lines = "\n".join(f"Found Hamburg line{i}" for i in range(50))
        path = log_file(lines)
        a = LogAnalyzer(
            search=[("Ort", 4, {"hamburg"})],
            max_examples=5,
        )
        results, _ = a.analyze([path])
        for val, entries in results["Ort"][2].items():
            assert len(entries) <= 5

    def test_different_values_independent(self, log_file):
        """Different matched values should each have their own limit."""
        lines = "\n".join(
            [f"Hamburg line{i}" for i in range(10)]
            + [f"Berlin line{i}" for i in range(10)]
        )
        path = log_file(lines)
        a = LogAnalyzer(
            search=[("Ort", 4, {"hamburg", "berlin"})],
            max_examples=3,
        )
        results, _ = a.analyze([path])
        hits = results["Ort"][2]
        for val, entries in hits.items():
            assert len(entries) <= 3


class TestMinLengthGuards:
    """Test that min-length guards don't filter valid matches."""

    def test_short_token_skipped_for_regexp(self, log_file):
        """Tokens shorter than 5 chars should skip regexp check."""
        path = log_file("a=b\n")
        a = LogAnalyzer(regexp=[("test", 4, "t", re.compile(r"a"))])
        results, _ = a.analyze([path])
        # 'a' is only 1 char, should be skipped by min-length guard
        assert len(results["test"][2]) == 0

    def test_long_token_still_matches_regexp(self, log_file):
        path = log_file("email=anna@test.de\n")
        a = LogAnalyzer(regexp=[("email", 4, "Email", re.compile(r"^\S+@\S+\.\S+$"))])
        results, _ = a.analyze([path])
        assert len(results["email"][2]) > 0

    def test_short_field_name_pwd(self, log_file):
        """'pwd' is 3 chars — should still match field pattern."""
        path = log_file("pwd=secret123\n")
        a = LogAnalyzer(field=[("PW", 1, "Passw", re.compile(r"(?i)^pwd$"), 1)])
        results, _ = a.analyze([path])
        assert "secret123" in results["PW"][2]


class TestChunkComputation:
    """Test chunk boundary computation."""

    def test_empty_file(self):
        f = tempfile.NamedTemporaryFile(suffix=".log", delete=False)
        f.close()
        try:
            chunks = _compute_chunks(f.name, 4)
            assert chunks == [(0, 0)]
        finally:
            os.unlink(f.name)

    def test_single_chunk(self):
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False)
        f.write("line1\nline2\nline3\n")
        f.close()
        try:
            chunks = _compute_chunks(f.name, 1)
            assert len(chunks) == 1
        finally:
            os.unlink(f.name)

    def test_chunks_cover_file(self):
        """All chunks together should cover the entire file without gaps."""
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False)
        content = "\n".join(f"line {i} with some content" for i in range(100)) + "\n"
        f.write(content)
        f.close()
        try:
            chunks = _compute_chunks(f.name, 4)
            # First chunk starts at 0
            assert chunks[0][0] == 0
            # Last chunk ends at file size
            file_size = os.path.getsize(f.name)
            assert chunks[-1][1] == file_size
            # No gaps between chunks
            for i in range(len(chunks) - 1):
                assert chunks[i][1] == chunks[i + 1][0]
        finally:
            os.unlink(f.name)

    def test_chunks_aligned_to_lines(self):
        """Each chunk boundary should fall on a newline."""
        f = tempfile.NamedTemporaryFile(mode="wb", suffix=".log", delete=False)
        lines = [f"line {i} with content\n".encode() for i in range(100)]
        f.writelines(lines)
        f.close()
        try:
            chunks = _compute_chunks(f.name, 4)
            with open(f.name, "rb") as fh:
                data = fh.read()
            for _, end in chunks[:-1]:
                # Byte before boundary should be newline
                assert data[end - 1:end] == b"\n"
        finally:
            os.unlink(f.name)


class TestSingleFileParallel:
    """Test chunk-based parallel analysis of a single file."""

    def test_results_match_sequential(self, log_file, monkeypatch):
        """Chunk-parallel should produce the same results as sequential."""
        lines = []
        for i in range(200):
            lines.append(f"email=user{i}@test.de password=secret{i}")
            lines.append(f"Name: Hamburg line {i}")
        content = "\n".join(lines) + "\n"
        path = log_file(content)

        patterns_re = [("email", 4, "Email", re.compile(r"^\S+@\S+\.\S+$"))]
        patterns_fd = [("PW", 1, "Passw", re.compile(r"(?i)password"), 1)]
        patterns_sr = [("Ort", 4, {"hamburg"})]

        # Sequential
        a_seq = LogAnalyzer(regexp=patterns_re, field=patterns_fd, search=patterns_sr)
        res_seq, lines_seq = a_seq.analyze([path], workers=1)

        # Force chunk-parallel by lowering the module constant
        # (an instance attribute would be ignored by analyze()).
        monkeypatch.setattr("detecto.analyzer.CHUNK_THRESHOLD_BYTES", 1)
        a_par = LogAnalyzer(regexp=patterns_re, field=patterns_fd, search=patterns_sr)
        res_par, lines_par = a_par.analyze([path], workers=2)

        assert lines_seq == lines_par

        # Same pattern names and same unique values
        for name in res_seq:
            seq_vals = set(res_seq[name][2].keys())
            par_vals = set(res_par[name][2].keys())
            assert seq_vals == par_vals, f"Mismatch for {name}"


# --- Tests for code quality fixes ---

class TestConfigLoading:
    """Test config loading edge cases."""

    def test_missing_ini_returns_defaults(self, tmp_path):
        """Missing detecto.ini should return default config without error."""
        cfg = load_config(tmp_path)
        assert cfg.examplecount == 10
        assert cfg.minlen == 4
        assert cfg.critical == 5
        assert cfg.prefilter == "off"

    def test_malformed_ini_uses_defaults(self, tmp_path):
        """Malformed INI should fall back to defaults for missing values."""
        ini = tmp_path / "detecto.ini"
        ini.write_text("[defaults]\nexamplecount = abc\n", encoding="utf-8")
        # must not crash: invalid values fall back to defaults with a warning
        cfg = load_config(tmp_path)
        assert isinstance(cfg, DetectoConfig)
        assert cfg.examplecount == 10

    def test_empty_ini_returns_defaults(self, tmp_path):
        """Empty INI file should return default config."""
        ini = tmp_path / "detecto.ini"
        ini.write_text("", encoding="utf-8")
        cfg = load_config(tmp_path)
        assert cfg.examplecount == 10

    def test_partial_ini_merges(self, tmp_path):
        """INI with only some values should merge with defaults."""
        ini = tmp_path / "detecto.ini"
        ini.write_text(
            "[defaults]\nexamplecount = 7\ncritical = 2\n",
            encoding="utf-8",
        )
        cfg = load_config(tmp_path)
        assert cfg.examplecount == 7
        assert cfg.critical == 2
        assert cfg.minlen == 4  # default preserved


class TestMergeResults:
    """Test _merge_results edge cases."""

    def test_merge_continues_after_max_hits(self, log_file):
        """_merge_results should skip full patterns but continue to others."""
        a = LogAnalyzer(
            search=[
                ("Cat1", 4, {"alpha", "beta", "gamma"}),
                ("Cat2", 4, {"delta"}),
            ],
            max_values_per_pattern=2,
        )
        # Build source results with many hits
        source = a._init_results()
        for i in range(5):
            source["Cat1"][2][f"val{i}"] = [("file", "line", None)]
        source["Cat2"][2]["delta_val"] = [("file", "line", None)]

        target = a._init_results()
        a._merge_results(target, source)
        # Cat1 should be capped at 2, Cat2 should still have its hit
        assert len(target["Cat1"][2]) <= 2
        assert len(target["Cat2"][2]) == 1  # not lost due to break


class TestFileReadErrors:
    """Test error handling for file access issues."""

    def test_nonexistent_file(self):
        """Analyzing a non-existent file should not crash."""
        a = LogAnalyzer(regexp=[("test", 4, "t", re.compile(r"test"))])
        results, lines = a.analyze(["/nonexistent/path/file.log"], workers=1)
        assert lines == 0

    def test_permission_denied(self, tmp_path):
        """Analyzing an unreadable file should not crash."""
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            pytest.skip("chmod 000 is ignored when running as root")
        f = tmp_path / "noperm.log"
        f.write_text("test data\n")
        f.chmod(0o000)
        try:
            a = LogAnalyzer()
            results, lines = a.analyze([str(f)], workers=1)
            assert lines == 0
        finally:
            f.chmod(0o644)


class TestFieldOffsetEdgeCases:
    """Test field pattern offset edge cases."""

    def test_offset_beyond_tokens(self, log_file):
        """Field offset pointing beyond token list should not crash."""
        path = log_file("password\n")  # only 1 token, offset=1 points beyond
        a = LogAnalyzer(field=[("PW", 1, "Passw", re.compile(r"(?i)password"), 1)])
        results, _ = a.analyze([path])
        # Should find no value (offset beyond tokens) but not crash
        assert len(results["PW"][2]) == 0

    def test_large_offset(self, log_file):
        """Large offset should not crash, just find nothing."""
        path = log_file("password val1 val2\n")
        a = LogAnalyzer(field=[("PW", 1, "Passw", re.compile(r"(?i)password"), 10)])
        results, _ = a.analyze([path])
        assert len(results["PW"][2]) == 0


class TestNormalizeAsciFastPath:
    """Test that the ASCII fast-path in normalize produces correct results."""

    def test_ascii_lowercase(self):
        from detecto.utils import normalize
        assert normalize("HELLO") == "hello"
        assert normalize("Test123") == "test123"

    def test_non_ascii_umlaut(self):
        from detecto.utils import normalize
        assert normalize("Müller") == "muller"
        assert normalize("Straße") == "strasse"

    def test_mixed_ascii_non_ascii(self):
        from detecto.utils import normalize
        assert normalize("Café") == "cafe"
        assert normalize("naïve") == "naive"


class TestInlineKeyValue:
    """key=value and key:value in a single line must yield the value.

    Regression tests: '=' is a token separator (value found via lookahead),
    ':' is NOT a separator (value found via inline split).
    """

    @pytest.fixture
    def pw_analyzer(self):
        pat = [("Passwort", 1, "pw", re.compile(r"(?i)(passw|kennw)"), 1)]
        # parse_json=False wie detecto.ini-Default: JSON-Zeilen werden an
        # Separatoren zerlegt, key:value bleibt in einem Token (Inline-Split).
        return LogAnalyzer(field=pat, parse_json=False)

    def test_equals_separated_value_found(self, pw_analyzer):
        results = pw_analyzer._init_results()
        pw_analyzer._analyze_line("password=SuperSecret123", "t", results)
        assert "SuperSecret123" in results["Passwort"][2]

    def test_colon_inline_value_found(self, pw_analyzer):
        results = pw_analyzer._init_results()
        pw_analyzer._analyze_line("login password:Geh31m!X", "t", results)
        assert "Geh31m!X" in results["Passwort"][2]

    def test_json_style_inline_value_found(self, pw_analyzer):
        results = pw_analyzer._init_results()
        pw_analyzer._analyze_line(
            'req {"user":"max","password":"W1nter#7"} ok', "t", results,
        )
        assert "W1nter#7" in results["Passwort"][2]

    def test_trailing_colon_uses_lookahead(self, pw_analyzer):
        results = pw_analyzer._init_results()
        pw_analyzer._analyze_line("password: Fr3itag$X", "t", results)
        assert "Fr3itag$X" in results["Passwort"][2]
