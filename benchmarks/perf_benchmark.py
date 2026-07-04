#!/usr/bin/env python3
"""Detecto performance benchmark (Finding 34).

Generates a synthetic dataset, runs the scanner and reports throughput together
with the full test conditions, so numbers are reproducible and comparable.

Run:  python benchmarks/perf_benchmark.py [--lines N] [--workers W]
"""
from __future__ import annotations

import argparse
import platform
import statistics
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from detecto.analyzer import LogAnalyzer, detect_cpu_count  # noqa: E402
from detecto.loaders import (  # noqa: E402
    load_field_patterns,
    load_regexp,
    load_search_patterns,
)

try:
    from importlib.resources import files
    DATA = Path(str(files("detecto") / "data"))
except Exception:  # pragma: no cover
    DATA = Path(__file__).resolve().parent.parent / "src" / "detecto" / "data"

SAMPLE_LINES = [
    "2026-07-04 INFO user login password=Sup3rSecret ok",
    "GET /api?token=eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.sig 200",
    "contact alice@example.com iban DE89 3704 0044 0532 0130 00",
    "plain informational line without any sensitive content here",
    "client 192.168.1.10 card 4111 1111 1111 1111 charged",
]


def _make_file(lines: int) -> str:
    fd = tempfile.NamedTemporaryFile("w", suffix=".log", delete=False, encoding="utf-8")
    for i in range(lines):
        fd.write(SAMPLE_LINES[i % len(SAMPLE_LINES)] + "\n")
    fd.close()
    return fd.name


def _analyzer(parse_json: str, prefilter: str) -> LogAnalyzer:
    regexp = load_regexp(str(DATA / "regexp.csv"))
    field = load_field_patterns(str(DATA / "field.csv"))
    search = load_search_patterns(str(DATA / "suchmuster.csv"), str(DATA / "suchmuster"), 4)
    return LogAnalyzer(regexp, field, search, parse_json=parse_json, prefilter=prefilter)


def run(lines: int, workers: int, parse_json: str, prefilter: str, repeats: int = 3) -> dict:
    path = _make_file(lines)
    size = Path(path).stat().st_size
    durations = []
    line_count = 0
    for _ in range(repeats):
        a = _analyzer(parse_json, prefilter)
        t0 = time.perf_counter()
        _, line_count = a.analyze([path], refresh_status=0, workers=workers)
        durations.append(time.perf_counter() - t0)
    best = min(durations)
    return {
        "cpu": platform.processor() or platform.machine(),
        "os": f"{platform.system()} {platform.release()}",
        "python": platform.python_version(),
        "detected_cpus": detect_cpu_count(),
        "workers": workers,
        "file_bytes": size,
        "lines": line_count,
        "avg_line_len": round(size / max(1, line_count), 1),
        "parse_json": parse_json,
        "prefilter": prefilter,
        "runtime_s": round(best, 4),
        "lines_per_s": int(line_count / best) if best else 0,
        "bytes_per_s": int(size / best) if best else 0,
        "runtime_stdev_s": round(statistics.pstdev(durations), 4),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lines", type=int, default=200_000)
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--parse-json", default="auto")
    ap.add_argument("--prefilter", default="off")
    args = ap.parse_args()
    m = run(args.lines, args.workers, args.parse_json, args.prefilter)
    print("Detecto performance benchmark (synthetic data)")
    for k, v in m.items():
        print(f"  {k:<16}: {v}")
    print("\nCite these numbers only together with the conditions above. "
          "The optional prefilter can reduce recall depending on configuration.")


if __name__ == "__main__":
    main()
