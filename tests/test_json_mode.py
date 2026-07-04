"""Finding 10: JSON parsing modes (auto/true/false), stats and bounds."""
from __future__ import annotations

import re

from detecto.analyzer import LogAnalyzer
from detecto.config import _normalize_json_mode
from detecto.tokenizer import extract_json_values


def _pw_analyzer(mode):
    return LogAnalyzer(
        field=[("Passwort", 1, "pw", re.compile(r"(?i)(passw|kennw)"), 1)],
        parse_json=mode,
    )


def test_normalize_json_mode():
    assert _normalize_json_mode("auto") == "auto"
    assert _normalize_json_mode("true") == "true"
    assert _normalize_json_mode("false") == "false"
    assert _normalize_json_mode(True) == "true"
    assert _normalize_json_mode(False) == "false"
    assert _normalize_json_mode("nonsense") == "auto"


def test_auto_attempts_json_line():
    a = _pw_analyzer("auto")
    assert a._want_json('{"password":"x"}') is True


def test_auto_skips_plain_line():
    a = _pw_analyzer("auto")
    assert a._want_json("just a plain log line here") is False


def test_mode_false_never():
    a = _pw_analyzer("false")
    assert a._want_json('{"password":"x"}') is False


def test_mode_true_always():
    a = _pw_analyzer("true")
    assert a._want_json("plain line") is True


def test_json_password_found_and_stats(tmp_path):
    p = tmp_path / "j.log"
    p.write_text('{"user":"max","password":"W1nter#7"}\n', encoding="utf-8")
    a = _pw_analyzer("auto")
    results, _ = a.analyze([str(p)], refresh_status=0, workers=1)
    assert "W1nter#7" in results["Passwort"][2]
    assert a.diag.json_candidates == 1
    assert a.diag.json_parsed == 1


def test_invalid_json_does_not_crash_and_counts(tmp_path):
    p = tmp_path / "bad.log"
    p.write_text('{"password": broken json here\n', encoding="utf-8")
    a = _pw_analyzer("auto")
    results, lines = a.analyze([str(p)], refresh_status=0, workers=1)
    assert lines == 1
    assert a.diag.json_failed == 1


def test_deeply_nested_json_bounded():
    # 5000 levels of nesting must not blow the stack
    deep = "[" * 5000 + "1" + "]" * 5000
    import json
    try:
        obj = json.loads(deep)
    except (ValueError, RecursionError):
        return  # json itself rejected it - fine
    vals = extract_json_values(obj)
    assert isinstance(vals, list)  # returned, did not hang/overflow
