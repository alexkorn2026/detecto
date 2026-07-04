#!/usr/bin/env python3
"""Detecto detection-quality benchmark (Findings 19 / 33).

Runs the shipped patterns against a small, fully synthetic gold dataset and
reports precision / recall / F1 overall and per finding type. This measures
detection *quality* - unlike a raw unit-test count, which says nothing about
precision or recall.

Run:  python benchmarks/quality_benchmark.py

All data here is synthetic. No real personal identifiers are used.
"""
from __future__ import annotations

import sys
from collections import defaultdict
from importlib.resources import files
from pathlib import Path

# Allow running from a source checkout without installation.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from detecto.analyzer import LogAnalyzer  # noqa: E402
from detecto.loaders import (  # noqa: E402
    load_field_patterns,
    load_regexp,
    load_search_patterns,
)

# (line, {expected pattern IDs that SHOULD fire})
GOLD: list[tuple[str, set[str]]] = [
    ("user login password=Sup3rSecret", {"Passwort"}),
    ("contact alice@example.com for info", {"email"}),
    ("card 4111 1111 1111 1111 charged", {"Kreditkarte"}),
    ("card 1234 5678 9012 3456 invalid", set()),          # fails Luhn
    ("iban DE89 3704 0044 0532 0130 00", {"IBAN"}),
    ("iban DE00 3704 0044 0532 0130 00", set()),          # bad checksum
    ("steuer id 86095742719 filed", {"SteuerID"}),
    ("ticket number 12345678901 opened", set()),          # not a valid tax id
    ("token eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.sig here", {"JWT"}),
    ("home address Hauptstraße 12 Berlin", {"strasse"}),
    ("free disk Speicherplatz low", set()),               # street false positive
    ("plain log line with nothing sensitive", set()),
    ("aws key AKIAIOSFODNN7EXAMPLE rotated", {"AWSAccessKey"}),
    ("server main root prod test started", set()),        # tech terms, not names
    ("ip 192.168.1.10 connected", {"InterneIP", "IPAdresse"}),
]


def _build_analyzer() -> LogAnalyzer:
    data = files("detecto") / "data"
    regexp = load_regexp(str(data / "regexp.csv"))
    field = load_field_patterns(str(data / "field.csv"))
    search = load_search_patterns(
        str(data / "suchmuster.csv"), str(data / "suchmuster"), minlen=4
    )
    return LogAnalyzer(regexp, field, search, parse_json="auto")


def _fired(analyzer: LogAnalyzer, line: str) -> set[str]:
    results = analyzer._init_results()
    analyzer._analyze_line(line, "bench", results, 1)
    return {name for name, (_t, _k, hits) in results.items() if hits}


def run_benchmark() -> dict:
    analyzer = _build_analyzer()
    type_of = {}
    for name, (t, _k, _h) in analyzer._init_results().items():
        type_of[name] = t

    tp = fp = fn = 0
    per_type: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])
    for line, expected in GOLD:
        fired = _fired(analyzer, line)
        # Only score against patterns that appear in the gold's expectations
        # across the whole set, so unrelated background patterns do not distort
        # the numbers.
        relevant = {n for _, exp in GOLD for n in exp}
        fired &= relevant
        for name in fired & expected:
            tp += 1
            per_type[type_of.get(name, "?")][0] += 1
        for name in fired - expected:
            fp += 1
            per_type[type_of.get(name, "?")][1] += 1
        for name in expected - fired:
            fn += 1
            per_type[type_of.get(name, "?")][2] += 1

    def prf(t, f, n):
        prec = t / (t + f) if (t + f) else 1.0
        rec = t / (t + n) if (t + n) else 1.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
        return prec, rec, f1

    prec, rec, f1 = prf(tp, fp, fn)
    return {
        "overall": {"tp": tp, "fp": fp, "fn": fn,
                    "precision": prec, "recall": rec, "f1": f1},
        "per_type": {
            typ: dict(zip(("tp", "fp", "fn"), vals))
            for typ, vals in per_type.items()
        },
        "gold_size": len(GOLD),
    }


def main() -> None:
    m = run_benchmark()
    o = m["overall"]
    print("Detecto quality benchmark (synthetic gold dataset)")
    print(f"  Gold lines : {m['gold_size']}")
    print(f"  TP/FP/FN   : {o['tp']}/{o['fp']}/{o['fn']}")
    print(f"  Precision  : {o['precision']:.3f}")
    print(f"  Recall     : {o['recall']:.3f}")
    print(f"  F1         : {o['f1']:.3f}")
    for typ, v in sorted(m["per_type"].items()):
        print(f"  [{typ}] TP/FP/FN = {v['tp']}/{v['fp']}/{v['fn']}")
    print("\nNote: heuristic detection - no guarantee of complete PII coverage.")


if __name__ == "__main__":
    main()
