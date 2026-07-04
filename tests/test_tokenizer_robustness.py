"""Finding 9: robust tokenization of URLs, IPv6, JDBC, paths, inline fields."""
from __future__ import annotations

import pytest

from detecto.tokenizer import extract_url_tokens, split_inline_field, tokenize


class TestUrlExtraction:
    def test_userinfo_credentials(self):
        toks = extract_url_tokens("https://user:secret@example.org/path")
        assert "user" in toks and "secret" in toks

    def test_hyphen_param(self):
        assert "value" in extract_url_tokens("https://x.org/?client-secret=value")

    def test_dotted_param(self):
        assert "max" in extract_url_tokens("https://x.org/?user.name=max")

    def test_bracket_param_single_decode(self):
        toks = extract_url_tokens("https://x.org/?filters[email]=a%40b.example")
        assert "a@b.example" in toks

    def test_encoded_value_decoded_once(self):
        toks = extract_url_tokens("https://x.org/?password=Secret%402026")
        assert "Secret@2026" in toks
        # not double-decoded
        assert "Secret402026" not in toks

    def test_ipv6_host_does_not_crash(self):
        # userinfo before an IPv6 host is still extracted, no exception
        toks = extract_url_tokens("http://admin:pw@[2001:db8::1]:8080/x")
        assert "admin" in toks and "pw" in toks


class TestInlineField:
    def test_password_colon(self):
        assert split_inline_field("password:Secret123") == ("password", "Secret123")

    def test_json_style(self):
        assert split_inline_field('"password":"W1nter#7"') == ("password", "W1nter#7")

    def test_ipv6_not_split(self):
        assert split_inline_field("2001:db8::1") is None

    def test_timestamp_not_split(self):
        assert split_inline_field("12:34:56") is None

    def test_url_not_split(self):
        assert split_inline_field("https://user:pw@host/path") is None

    def test_equals_still_works(self):
        assert split_inline_field("api_key=abc123") == ("api_key", "abc123")


class TestTokenizeStructured:
    def test_jdbc_kept_intact(self):
        toks = tokenize("db jdbc:oracle:thin:@host:1521/service", parse_json=False)
        assert "jdbc:oracle:thin:@host:1521/service" in toks

    def test_windows_path_kept(self):
        toks = tokenize(r"file C:\temp\file.log opened", parse_json=False)
        assert any("temp" in t for t in toks)

    def test_urn_kept(self):
        toks = tokenize("id urn:example:value here", parse_json=False)
        assert "urn:example:value" in toks
