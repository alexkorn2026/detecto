"""Finding 6: duplicate pattern IDs are a fatal configuration error.

IDs must be globally unique across regexp, field and string patterns.
"""
from __future__ import annotations

import pytest

from detecto.loaders import (
    DuplicatePatternError,
    load_field_patterns,
    load_regexp,
    load_search_patterns,
    register_pattern_id,
)


def test_registry_detects_duplicate():
    reg: dict = {}
    register_pattern_id(reg, "Foo", "regexp", "regexp.csv", 1)
    with pytest.raises(DuplicatePatternError) as exc:
        register_pattern_id(reg, "Foo", "field", "field.csv", 7)
    msg = str(exc.value)
    assert "Foo" in msg and "regexp.csv:1" in msg and "field.csv:7" in msg


def test_duplicate_within_regexp(tmp_path):
    f = tmp_path / "regexp.csv"
    f.write_text("Dup::1::d::a\nDup::2::d::b\n", encoding="utf-8")
    with pytest.raises(DuplicatePatternError):
        load_regexp(f, {})


def test_duplicate_regexp_vs_field(tmp_path):
    r = tmp_path / "regexp.csv"
    r.write_text("Same::1::d::abc\n", encoding="utf-8")
    fi = tmp_path / "field.csv"
    fi.write_text("Same::1::d::(?i)passw\n", encoding="utf-8")
    reg: dict = {}
    load_regexp(r, reg)
    with pytest.raises(DuplicatePatternError):
        load_field_patterns(fi, reg)


def test_duplicate_field_vs_string(tmp_path):
    fi = tmp_path / "field.csv"
    fi.write_text("Cat::1::d::(?i)passw\n", encoding="utf-8")
    sm = tmp_path / "suchmuster.csv"
    sm.write_text("Cat::3::names.csv\n", encoding="utf-8")
    (tmp_path / "names.csv").write_text("header\nmueller\n", encoding="utf-8")
    reg: dict = {}
    load_field_patterns(fi, reg)
    with pytest.raises(DuplicatePatternError):
        load_search_patterns(sm, str(tmp_path), 4, reg)


def test_unique_ids_ok(tmp_path):
    r = tmp_path / "regexp.csv"
    r.write_text("A::1::d::abc\nB::2::d::xyz\n", encoding="utf-8")
    reg: dict = {}
    load_regexp(r, reg)
    assert set(reg) == {"A", "B"}


def test_shipped_patterns_are_unique():
    """The bundled pattern files must not collide (Detecto would not start)."""
    from importlib.resources import files

    import detecto.config as cfg

    data = files("detecto") / "data"
    reg: dict = {}
    load_regexp(str(data / cfg.REGEXP_FILE), reg)
    load_field_patterns(str(data / cfg.FIELD_FILE), reg)
    load_search_patterns(
        str(data / cfg.SUCHMUSTER_FILE), str(data / cfg.SUCHMUSTER_DIR), 4, reg
    )
    assert len(reg) > 100
