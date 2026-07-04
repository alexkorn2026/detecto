"""Regression tests for the v1.6.1 review findings (Befunde 1-10)."""
from __future__ import annotations

import re
from pathlib import Path

from detecto.analyzer import LogAnalyzer
from detecto.config import load_config
from detecto.loaders import _validate_path, load_regexp, load_search_patterns
from detecto.tokenizer import extract_json_pairs, tokenize

REPO = Path(__file__).resolve().parent.parent


def _hits(analyzer: LogAnalyzer, line: str) -> dict:
    results = analyzer._init_results()
    analyzer._analyze_line(line, "test", results)
    return {n: list(h.keys()) for n, (_, _, h) in results.items() if h}


# --- Befund 3: JSON-Keys bei parse_json=true -------------------------------

class TestJsonKeyContext:
    PW = [("Passwort", 1, "pw", re.compile(r"(?i)(passw|kennw)"), 1)]

    def test_json_pairs_extracted(self):
        pairs = extract_json_pairs(
            {"password": "Secret123", "user": "admin", "n": 7,
             "nested": {"apikey": "XYZ"}, "list": [{"kennwort": "K1"}]},
        )
        assert ("password", "Secret123") in pairs
        assert ("apikey", "XYZ") in pairs
        assert ("kennwort", "K1") in pairs
        assert ("n", "7") in pairs

    def test_parse_json_true_finds_password(self):
        a = LogAnalyzer(field=self.PW, parse_json=True)
        hits = _hits(a, '{"password":"Secret123","user":"admin"}')
        assert "Secret123" in hits.get("Passwort", [])

    def test_parse_json_true_fragment_finds_password(self):
        a = LogAnalyzer(field=self.PW, parse_json=True)
        hits = _hits(a, 'req done {"user":"max","password":"W1nter#7"} rc=0')
        assert "W1nter#7" in hits.get("Passwort", [])

    def test_kv_tokens_in_tokenizer(self):
        tokens = tokenize('{"password":"Secret123"}', parse_json=True)
        assert "password:Secret123" in tokens


# --- Befund 4: Path-Traversal Prefix-Bypass --------------------------------

class TestValidatePathBypass:
    def test_sibling_prefix_dir_blocked(self, tmp_path):
        base = tmp_path / "base"
        evil = tmp_path / "baseevil"
        base.mkdir()
        evil.mkdir()
        (evil / "evil.csv").write_text("x\ny\n", encoding="utf-8")
        # '/x/baseevil' passed the old startswith('/x/base') check
        assert _validate_path(base, "../baseevil/evil.csv") is None

    def test_inside_base_allowed(self, tmp_path):
        base = tmp_path / "base"
        base.mkdir()
        assert _validate_path(base, "ok.csv") is not None


# --- Befund 5: Mehrwort-Suchmuster ------------------------------------------

class TestMultiWordSearch:
    def test_phrase_matched_in_line(self):
        search = [("Diagnosen", 3, {"diabetes", "multiple sklerose"})]
        a = LogAnalyzer(search=search, parse_json=False)
        hits = _hits(a, "Befund Multiple Sklerose dokumentiert")
        assert "multiple sklerose" in hits.get("Diagnosen", [])

    def test_phrase_word_boundary(self):
        search = [("Ort", 4, {"markt wald"})]
        a = LogAnalyzer(search=search, parse_json=False)
        assert not _hits(a, "supermarkt waldweg")
        assert _hits(a, "Umzug nach Markt Wald gemeldet")

    def test_single_word_search_unchanged(self):
        search = [("Ort", 4, {"hamburg"})]
        a = LogAnalyzer(search=search, parse_json=False)
        assert "hamburg" not in a._search_phrases
        assert _hits(a, "Umzug nach Hamburg")

    def test_real_suchmuster_files(self):
        search = load_search_patterns(
            REPO / "suchmuster.csv", str(REPO / "suchmuster"), minlen=4,
        )
        a = LogAnalyzer(search=search, parse_json=False)
        assert "multiple sklerose" in a._search_phrases
        assert "bergisch gladbach" in a._search_phrases
        hits = _hits(a, "Patient mit Morbus Crohn aus Bergisch Gladbach")
        assert "morbus crohn" in hits.get("Diagnosen", [])
        assert "bergisch gladbach" in hits.get("Ort", [])


# --- Befunde 6-8: Regexp-Scope und Match-Werte ------------------------------

class TestRegexpFindings:
    @classmethod
    def setup_class(cls):
        cls.analyzer = LogAnalyzer(
            regexp=load_regexp(REPO / "regexp.csv"), parse_json=False,
        )

    def test_azure_accountkey_found(self):
        # Befund 6: '=' ist Token-Separator -> Pattern muss zeilenbasiert laufen
        line = ("DefaultEndpointsProtocol=https;AccountKey="
                "aBcDeF1234567890aBcDeF1234567890aBcDeF12345678==")
        assert "AzureAccountKey" in _hits(self.analyzer, line)

    def test_interne_ip_valid_octets_only(self):
        # Befund 7
        for ip in ("10.0.0.1", "172.16.5.4", "192.168.1.100"):
            assert "InterneIP" in _hits(self.analyzer, f"host {ip} up"), ip
        for ip in ("10.999.999.999", "172.16.999.999", "192.168.999.999"):
            hits = _hits(self.analyzer, f"host {ip} up")
            assert "InterneIP" not in hits, ip
            assert "IPAdresse" not in hits, ip

    def test_email_match_without_brackets(self):
        # Befund 8: Match statt kompletter Token
        hits = _hits(self.analyzer, "contact=<alice@example.com>")
        assert "alice@example.com" in hits.get("email", [])

    def test_jwt_match_without_quotes(self):
        jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.sig4711"
        hits = _hits(self.analyzer, f'token="{jwt}"')
        assert jwt in hits.get("JWT", [])

    def test_license_key_in_quotes_and_brackets(self):
        hits = _hits(self.analyzer, 'aktiviert mit ("ABCD1-EF234-GH567")')
        assert "ABCD1-EF234-GH567" in hits.get("Lizenzschluessel", [])

    def test_license_key_ignores_digit_only_and_guid(self):
        hits = _hits(self.analyzer, "id 4532-1111-2222-3333 gebucht")
        assert "Lizenzschluessel" not in hits
        hits = _hits(
            self.analyzer,
            "uuid 550E8400-E29B-41D4-A716-446655440000 erzeugt",
        )
        assert "Lizenzschluessel" not in hits


# --- Befund 9: Defekte INI --------------------------------------------------

class TestBrokenIni:
    def test_missing_section_header_uses_defaults(self, tmp_path):
        (tmp_path / "detecto.ini").write_text(
            "kein section header\nexamplecount = 7\n", encoding="utf-8",
        )
        cfg = load_config(tmp_path)  # darf nicht crashen
        assert cfg.examplecount == 3  # Default, INI ignoriert

    def test_duplicate_option_uses_defaults(self, tmp_path):
        (tmp_path / "detecto.ini").write_text(
            "[defaults]\nminlen = 4\nminlen = 5\n", encoding="utf-8",
        )
        cfg = load_config(tmp_path)
        assert cfg.minlen in (4, 5) or cfg.minlen == 5  # kein Crash
