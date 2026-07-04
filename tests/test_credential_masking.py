"""Finding 5: credential path/mask handling.

Credential values must not be dropped just because they start with '/' or
'C:'. Masked values become a distinct, lower-severity finding and are never
reported as plaintext secrets.
"""
from __future__ import annotations

import re

from detecto.analyzer import LogAnalyzer
from detecto.constants import MASKED_STATUS, MASKED_SUFFIX


def _analyzer():
    return LogAnalyzer(
        field=[
            ("Passwort", 1, "pw", re.compile(r"(?i)(passw|kennw)"), 1),
            ("APIKey", 1, "api", re.compile(r"(?i)(api.?key)"), 1),
            ("Credential", 1, "cred", re.compile(r"(?i)\b(secret|credential)\b"), 1),
            ("Token", 1, "tok", re.compile(r"(?i)(token)"), 1),
        ],
    )


def _scan(tmp_path, line):
    p = tmp_path / "c.log"
    p.write_text(line + "\n", encoding="utf-8")
    a = _analyzer()
    results, _ = a.analyze([str(p)], refresh_status=0, workers=1)
    return a, results


def test_password_with_leading_slash_is_found(tmp_path):
    a, results = _scan(tmp_path, "password=/MySecret2026")
    found = results["Passwort"][2]
    assert any("/MySecret2026" in v for v in found), found


def test_password_windows_like_is_found(tmp_path):
    a, results = _scan(tmp_path, "password=C:verySecret")
    found = results["Passwort"][2]
    assert any("verySecret" in v for v in found), found


def test_masked_apikey_is_distinct_finding(tmp_path):
    a, results = _scan(tmp_path, "api_key=********")
    masked_key = "APIKey" + MASKED_SUFFIX
    assert masked_key in results
    values = results[masked_key][2]
    assert MASKED_STATUS in values
    # the real APIKey slot has no plaintext-secret hit
    assert not results["APIKey"][2]
    # masked slot has the configured lower criticality (default 4, not 1)
    assert results[masked_key][1] == 4


def test_masked_token_redacted(tmp_path):
    a, results = _scan(tmp_path, "token=<redacted>")
    assert "Token" + MASKED_SUFFIX in results


def test_masked_secret_brackets(tmp_path):
    a, results = _scan(tmp_path, "secret=[MASKED]")
    assert "Credential" + MASKED_SUFFIX in results


def test_real_path_value_suppressed(tmp_path):
    # an actual file path as a credential value is still suppressed
    a, results = _scan(tmp_path, "password=/var/log/app.log")
    assert not results["Passwort"][2]
