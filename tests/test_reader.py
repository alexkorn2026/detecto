"""Findings 26, 27, 28: encoding, oversized lines, special/binary/gz files."""
from __future__ import annotations

import gzip
import os
import re

import pytest

from detecto.analyzer import LogAnalyzer
from detecto.diagnostics import ScanDiagnostics
from detecto.reader import ReaderOptions, classify_file, iter_file_lines


def _pw_opts(**kw):
    return ReaderOptions(**kw)


def _analyzer():
    return LogAnalyzer(
        field=[("Passwort", 1, "pw", re.compile(r"(?i)(passw|kennw)"), 1)],
    )


# --- Finding 28: file classification --------------------------------------

def test_directory_skipped(tmp_path):
    assert classify_file(str(tmp_path), follow_symlinks=False) == "directory"


def test_symlink_skipped_by_default(tmp_path):
    target = tmp_path / "real.log"
    target.write_text("password=x\n", encoding="utf-8")
    link = tmp_path / "link.log"
    os.symlink(target, link)
    assert classify_file(str(link), follow_symlinks=False) is not None
    assert classify_file(str(link), follow_symlinks=True) is None


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="no FIFO support")
def test_fifo_skipped(tmp_path):
    fifo = tmp_path / "pipe"
    os.mkfifo(fifo)
    assert classify_file(str(fifo), follow_symlinks=False) == "not a regular file"


def test_binary_file_skipped(tmp_path):
    f = tmp_path / "bin.log"
    f.write_bytes(b"\x00\x01\x02\x03binary\x00stuff\xff")
    diag = ScanDiagnostics()
    lines = list(iter_file_lines(str(f), diag, _pw_opts()))
    assert lines == []
    assert diag.skipped_files and "binary" in diag.skipped_files[0][1]


# --- Finding 28: gz streaming ---------------------------------------------

def test_gz_file_read(tmp_path):
    gz = tmp_path / "log.gz"
    with gzip.open(gz, "wt", encoding="utf-8") as f:
        f.write("user password=Secret123\n")
    a = _analyzer()
    results, lines = a.analyze([str(gz)], refresh_status=0, workers=1)
    assert lines == 1
    assert "Secret123" in results["Passwort"][2]


def test_gz_bomb_budget(tmp_path):
    gz = tmp_path / "big.gz"
    with gzip.open(gz, "wt", encoding="utf-8") as f:
        for _ in range(1000):
            f.write("x" * 100 + "\n")
    diag = ScanDiagnostics()
    opts = _pw_opts(max_decompressed_bytes=500)  # tiny budget
    lines = list(iter_file_lines(str(gz), diag, opts))
    assert len(lines) < 1000  # stopped early


# --- Finding 27: oversized lines ------------------------------------------

def test_oversized_truncate(tmp_path):
    f = tmp_path / "big.log"
    f.write_text("password=Secret " + "A" * 5000 + "\n", encoding="utf-8")
    diag = ScanDiagnostics()
    opts = _pw_opts(max_line_bytes=100, oversized_policy="truncate")
    lines = list(iter_file_lines(str(f), diag, opts))
    assert diag.lines_oversized == 1
    assert len(lines[0]) <= 100


def test_oversized_skip(tmp_path):
    f = tmp_path / "big.log"
    f.write_text("A" * 5000 + "\n" + "short\n", encoding="utf-8")
    diag = ScanDiagnostics()
    opts = _pw_opts(max_line_bytes=100, oversized_policy="skip")
    lines = list(iter_file_lines(str(f), diag, opts))
    assert "short" in lines
    assert all("A" * 200 not in line for line in lines)
    assert diag.files_partial >= 1


def test_oversized_line_numbering(tmp_path):
    f = tmp_path / "big.log"
    f.write_text("A" * 5000 + "\n" + "second\n", encoding="utf-8")
    diag = ScanDiagnostics()
    opts = _pw_opts(max_line_bytes=100, oversized_policy="truncate")
    lines = list(iter_file_lines(str(f), diag, opts))
    assert lines[1] == "second"  # line 2 still correctly read


# --- Finding 26: encoding --------------------------------------------------

def test_utf8_bom_detected(tmp_path):
    f = tmp_path / "bom.log"
    f.write_bytes("﻿password=Secret1\n".encode("utf-8"))
    diag = ScanDiagnostics()
    list(iter_file_lines(str(f), diag, _pw_opts()))
    assert diag.encodings_used[str(f)] == "utf-8-sig"


def test_explicit_windows1252(tmp_path):
    f = tmp_path / "w.log"
    f.write_bytes("Grüße password=x\n".encode("windows-1252"))
    diag = ScanDiagnostics()
    lines = list(iter_file_lines(str(f), diag, _pw_opts(encoding="windows-1252")))
    assert "Grüße" in lines[0]


def test_strict_encoding_marks_partial(tmp_path):
    f = tmp_path / "s.log"
    f.write_bytes(b"good\ninvalid \xff byte\n")
    diag = ScanDiagnostics()
    opts = _pw_opts(encoding="utf-8", errors="strict")
    list(iter_file_lines(str(f), diag, opts))
    assert diag.files_partial >= 1 or diag.decode_errors >= 1
