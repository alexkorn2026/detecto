"""Finding 41: pattern files are opened safely (no symlink following)."""
from __future__ import annotations

import os

import pytest

from detecto.loaders import _read_lines, _safe_open_text, load_regexp


@pytest.mark.skipif(not hasattr(os, "O_NOFOLLOW"), reason="needs O_NOFOLLOW")
def test_symlinked_pattern_file_rejected(tmp_path):
    real = tmp_path / "real.csv"
    real.write_text("A::1::d::abc::token\n", encoding="utf-8")
    link = tmp_path / "link.csv"
    os.symlink(real, link)
    with pytest.raises(OSError):
        _safe_open_text(link)


def test_read_lines_skips_symlink(tmp_path):
    if not hasattr(os, "O_NOFOLLOW"):
        pytest.skip("needs O_NOFOLLOW")
    real = tmp_path / "real.csv"
    real.write_text("A::1::d::abc::token\n", encoding="utf-8")
    link = tmp_path / "link.csv"
    os.symlink(real, link)
    # _read_lines refuses the symlink and returns nothing (with a warning).
    assert _read_lines(link) == []
    assert load_regexp(link) == []


def test_regular_file_still_loads(tmp_path):
    real = tmp_path / "real.csv"
    real.write_text("A::1::d::abc::token\n", encoding="utf-8")
    patterns = load_regexp(real)
    assert patterns and patterns[0][0] == "A"


def test_non_regular_rejected(tmp_path):
    if not hasattr(os, "mkfifo"):
        pytest.skip("no FIFO")
    fifo = tmp_path / "pipe"
    os.mkfifo(fifo)
    with pytest.raises(OSError):
        _safe_open_text(fifo)
