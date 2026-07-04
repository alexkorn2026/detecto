"""Tests for the tokenizer module."""
from __future__ import annotations

from detecto.tokenizer import extract_json_fragments, find_field_value, tokenize


class TestTokenize:
    def test_simple(self):
        tokens = tokenize("hello world test")
        assert "hello" in tokens and "world" in tokens

    def test_url_params(self):
        tokens = tokenize("GET /app?email=test@mail.de&name=Hans")
        assert "test@mail.de" in tokens and "Hans" in tokens

    def test_json_fragment_preserved(self):
        tokens = tokenize('payload {"street":"Gartenweg 7","zip":"50667"}')
        json_t = [t for t in tokens if t.startswith('{"street"')]
        assert len(json_t) > 0 and json_t[0].endswith("}")

    def test_json_values_extracted(self):
        assert "wert123" in tokenize('data {"key":"wert123"}')

    def test_json_log_line(self):
        assert "admin" in tokenize('{"message": "login", "user": "admin"}')

    def test_multipart_url_param(self):
        assert "65 170839 J 08 8" in tokenize("GET /login?nr=65 170839 J 08 8")

    def test_credentials_in_jdbc_url(self):
        tokens = tokenize("jdbc:oracle://admin:P@ssw0rd!@host:1521/db")
        assert "admin" in tokens
        assert "P@ssw0rd!" in tokens

    def test_credentials_in_http_url(self):
        tokens = tokenize("http://user:secret123@proxy.internal:8080/path")
        assert "user" in tokens
        assert "secret123" in tokens

    def test_url_without_credentials(self):
        tokens = tokenize("https://example.com/path?key=value")
        # Should not crash or extract spurious credentials
        assert "example.com" in tokens or any("example" in t for t in tokens)


class TestJsonFragments:
    def test_balanced_nested(self):
        frags = extract_json_fragments('vor {"a":"b","c":{"d":"e"}} nach')
        assert len(frags) == 1 and frags[0][0] == '{"a":"b","c":{"d":"e"}}'

    def test_no_json(self):
        assert extract_json_fragments("kein json") == []

    def test_raw_decode(self):
        frags = extract_json_fragments('text {"key": "value"} rest')
        assert len(frags) == 1 and '"key"' in frags[0][0]


class TestFieldValue:
    def test_direct(self):
        assert find_field_value(["password", "secret123"], 1)[0] == "secret123"

    def test_arrow(self):
        assert find_field_value(["password", "->", "secret123"], 1)[0] == "secret123"

    def test_double_arrow(self):
        assert find_field_value(["password", "=>", "secret123"], 1)[0] == "secret123"

    def test_separator_skipped(self):
        val, _ = find_field_value(["password", "->", "Produktiv!1"], 1)
        assert val == "Produktiv!1"

    def test_no_value(self):
        assert find_field_value(["password"], 1)[0] is None

    def test_quoted(self):
        assert find_field_value(["password:", '"geheim"'], 1)[0] == "geheim"
