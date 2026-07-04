"""Tests for the Anonymizer class."""
from __future__ import annotations

from detecto.anonymizer import Anonymizer


def test_default_pattern():
    r = Anonymizer().redact("amelie.hofmann")
    assert len(r) == len("amelie.hofmann")
    assert r[:3] == "ame"
    assert r[3:5] == "**"


def test_redacted():
    assert Anonymizer("<redacted>").redact("geheim") == "<redacted>"


def test_redacted_case_insensitive():
    assert Anonymizer("<REDACTED>").redact("test") == "<redacted>"


def test_invalid_pattern_no_crash():
    r = Anonymizer("abc").redact("geheim123")
    assert isinstance(r, str) and len(r) > 0


def test_empty_pattern_no_crash():
    assert isinstance(Anonymizer("").redact("test"), str)


def test_ssss_xxxx():
    r = Anonymizer("ssss****ss**").redact("amelie.hofmann")
    assert r[:4] == "amel" and r[4:8] == "****"


def test_short_text():
    assert len(Anonymizer("sss**sss**").redact("ab")) == 2
