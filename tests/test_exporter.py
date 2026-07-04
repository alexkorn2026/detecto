"""Tests for the Excel/log export."""
from __future__ import annotations

import os
import re
import tempfile
import zipfile
from collections import OrderedDict

import pytest

from detecto.anonymizer import Anonymizer
from detecto.exporter import export_xlsx, ExportContext, _sanitize_cell


@pytest.fixture
def xlsx_path():
    f = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
    f.close()
    yield f.name
    if os.path.exists(f.name):
        os.unlink(f.name)


@pytest.fixture
def sample_ctx():
    results: OrderedDict = OrderedDict()
    results["email"] = ("regexp", 4, {
        "test@example.de": [("test.log", "email=test@example.de", None)],
    })
    results["Passwort"] = ("field", 1, {
        "geheim123": [("test.log", "password=geheim123", "password")],
    })
    return ExportContext(
        results=results, example_count=3, critical=5,
        call_str="test", logfiles=["test.log"],
        line_count=100, duration_text="0 sec.",
        regexp=[("email", 4, "Email", re.compile(r"\S+@\S+"))],
        field=[("Passwort", 1, "PW", re.compile(r"(?i)passw"), 1)],
        search=[("Ort", 4, {"berlin"})],
        full=True, anonymizer=Anonymizer(),
    )


def _export(xlsx_path, ctx):
    export_xlsx(xlsx_path, ctx)


def test_file_created(xlsx_path, sample_ctx):
    _export(xlsx_path, sample_ctx)
    assert os.path.exists(xlsx_path)


def test_all_sheets(xlsx_path, sample_ctx):
    openpyxl = pytest.importorskip("openpyxl")
    _export(xlsx_path, sample_ctx)
    wb = openpyxl.load_workbook(xlsx_path)
    assert set(wb.sheetnames) >= {"Findings", "Full", "Tool", "Regexp", "Field", "String"}
    wb.close()


def test_no_rich_text(xlsx_path, sample_ctx):
    _export(xlsx_path, sample_ctx)
    with zipfile.ZipFile(xlsx_path) as z:
        for name in z.namelist():
            if name.endswith(".xml") and "sheet" in name:
                assert "<rPr>" not in z.read(name).decode("utf-8")


def test_treffer_marker(xlsx_path, sample_ctx):
    openpyxl = pytest.importorskip("openpyxl")
    _export(xlsx_path, sample_ctx)
    wb = openpyxl.load_workbook(xlsx_path)
    found = any(
        ">>>" in str(r[6]) and "<<<" in str(r[6])
        for r in wb["Full"].iter_rows(min_row=2, values_only=True) if r[6]
    )
    assert found, "No >>>TREFFER<<< marker"
    wb.close()


def test_feld_marker(xlsx_path, sample_ctx):
    openpyxl = pytest.importorskip("openpyxl")
    _export(xlsx_path, sample_ctx)
    wb = openpyxl.load_workbook(xlsx_path)
    found = any(
        "[FELD:" in str(r[6])
        for r in wb["Full"].iter_rows(min_row=2, values_only=True) if r[6]
    )
    assert found, "No [FELD:...] marker"
    wb.close()


class TestSanitizeCell:
    def test_formula_prefixed(self):
        assert _sanitize_cell("=cmd|test") == "'=cmd|test"

    def test_plus_prefixed(self):
        assert _sanitize_cell("+cmd") == "'+cmd"

    def test_normal_unchanged(self):
        assert _sanitize_cell("hello") == "hello"

    def test_non_string_unchanged(self):
        assert _sanitize_cell(42) == 42

    def test_empty_unchanged(self):
        assert _sanitize_cell("") == ""
