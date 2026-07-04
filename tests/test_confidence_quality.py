"""Findings 18 + 19: confidence for name/place hints, minlen safeguards, benchmark."""
from __future__ import annotations

from detecto.analyzer import LogAnalyzer, _name_confidence


def _name_analyzer():
    return LogAnalyzer(search=[("Vornamen", 4, {"anna", "mueller"})])


def _scan(tmp_path, line):
    p = tmp_path / "n.log"
    p.write_text(line + "\n", encoding="utf-8")
    a = _name_analyzer()
    results, _ = a.analyze([str(p)], refresh_status=0, workers=1)
    return results


def test_plain_name_match_low_confidence(tmp_path):
    results = _scan(tmp_path, "the value anna appears here")
    entry = results["Vornamen"][2]["anna"][0]
    assert entry[7] == "low"


def test_name_with_context_medium(tmp_path):
    results = _scan(tmp_path, "vorname=anna in record")
    entry = results["Vornamen"][2]["anna"][0]
    assert entry[7] == "medium"


def test_name_confidence_helper():
    assert _name_confidence("plain text") == "low"
    assert _name_confidence("firstname: bob") == "medium"
    assert _name_confidence("adresse hauptstrasse") == "medium"


# --- Finding 19: technical terms not reported as names --------------------

def test_tech_terms_not_matched_as_names(tmp_path):
    a = LogAnalyzer(search=[("Vornamen", 4, {"main", "root", "test", "anna"})])
    p = tmp_path / "t.log"
    p.write_text("server main root test started; user anna here\n", encoding="utf-8")
    results, _ = a.analyze([str(p)], refresh_status=0, workers=1)
    found = set(results["Vornamen"][2])
    assert "main" not in found and "root" not in found and "test" not in found
    assert "anna" in found  # a real name still matches


# --- Finding 19: quality benchmark ----------------------------------------

def test_quality_benchmark_runs():
    import os
    import sys
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, os.path.join(root, "benchmarks"))
    import quality_benchmark

    m = quality_benchmark.run_benchmark()
    o = m["overall"]
    assert 0.0 <= o["precision"] <= 1.0
    assert 0.0 <= o["recall"] <= 1.0
    assert 0.0 <= o["f1"] <= 1.0
    # validators should keep precision high on the curated gold
    assert o["precision"] >= 0.8
    assert o["recall"] >= 0.8
