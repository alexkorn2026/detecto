"""Finding 40: verify all pattern/data files are packaged into the wheel."""
from __future__ import annotations

import glob
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "src" / "detecto" / "data"

REQUIRED_DATA = [
    "detecto.ini", "regexp.csv", "field.csv", "suchmuster.csv",
    "stopword_regexp.txt", "stopword_field.txt", "stopword_suchmuster.txt",
]


def test_source_data_files_exist():
    for name in REQUIRED_DATA:
        assert (DATA / name).is_file(), f"missing source data file: {name}"
    assert list((DATA / "suchmuster").glob("*.csv")), "no suchmuster CSVs"


def test_pyproject_declares_data():
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    for glob_pat in ["data/*.ini", "data/*.csv", "data/*.txt", "data/suchmuster/*.csv"]:
        assert glob_pat in text, f"package-data missing {glob_pat}"


def test_built_wheel_contains_data():
    """If a wheel has been built into dist/, verify its contents (Finding 40)."""
    wheels = glob.glob(str(ROOT / "dist" / "*.whl"))
    if not wheels:
        pytest.skip("no built wheel in dist/ (run `python -m build` first)")
    wheel = max(wheels, key=lambda p: Path(p).stat().st_mtime)
    names = zipfile.ZipFile(wheel).namelist()
    for name in REQUIRED_DATA:
        assert any(n.endswith(f"data/{name}") for n in names), f"{name} not in wheel"
    assert any("data/suchmuster/" in n and n.endswith(".csv") for n in names)
    # No presentation / node artefacts in the wheel.
    bad = [n for n in names if n.endswith(".js") or "node_modules" in n]
    assert not bad, f"unexpected files in wheel: {bad}"
