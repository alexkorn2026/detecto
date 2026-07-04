"""CLI: Argument parsing and main() entry point."""
from __future__ import annotations

import argparse
import logging
import multiprocessing
import sys
import time
from collections import OrderedDict
from datetime import datetime
from pathlib import Path

from detecto import VERSION
from detecto.analyzer import LogAnalyzer
from detecto.anonymizer import Anonymizer
from detecto.config import DetectoConfig, load_config
from detecto.constants import LABEL_WIDTH
from detecto.diagnostics import (
    EXIT_CONFIG, EXIT_FAILED, EXIT_FINDINGS, EXIT_INTERNAL,
    EXIT_OK, EXIT_PARTIAL, ScanDiagnostics, ScanStatus,
)
from detecto.exporter import export_xlsx, export_log, ExportContext
from detecto.formatter import print_header, print_status, print_results
from detecto.loaders import (
    RegexpPattern, FieldPattern, SearchPattern, DuplicatePatternError,
    load_regexp, load_field_patterns, load_search_patterns, load_stopwords,
)
from detecto.utils import find_logfiles

__all__ = ["main", "parse_args"]

log = logging.getLogger(__name__)


def parse_args(config: DetectoConfig) -> argparse.Namespace:
    """Parse CLI arguments using INI defaults as fallback values."""
    parser = argparse.ArgumentParser(
        prog="detecto",
        description="Detecto - Scannt Log-Dateien (Websphere/Liberty) nach "
                    "kritischen und personenbezogenen Daten.",
        epilog=(
            "Beispiele:\n"
            "  detecto test.log\n"
            '  detecto "*.log"\n'
            "  detecto test.log --examplecount=5\n"
            "\n"
            "Dokumentation:\n"
            "  Readme:          readme.md\n"
            "  Changelog:       changelog.md\n"
            "  Erste Schritte:  firststeps.md\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("logdateien", nargs="*", help="Log file(s) to scan")
    parser.add_argument("--examplecount", type=int, default=config.examplecount, metavar="N",
                        help=f"Examples per finding type (default: {config.examplecount})")
    parser.add_argument("--anon", action="store_true", default=config.anon,
                        help="Redact examples in output")
    parser.add_argument("--full", action="store_true", default=config.full,
                        help="Show log lines with highlighting")
    parser.add_argument("--minlen", type=int, default=config.minlen, metavar="N",
                        help=f"Min length for pattern strings (default: {config.minlen})")
    parser.add_argument("--status", action="store_true", default=False,
                        help="Show loaded search data summary")
    parser.add_argument("--nocolor", action="store_true", default=config.nocolor,
                        help="Disable colored output")
    parser.add_argument("--critical", type=int, default=config.critical, metavar="N",
                        help=f"Show findings up to criticality N (default: {config.critical})")
    parser.add_argument("--showskipped", action="store_true", default=config.showskipped,
                        help="Show patterns with no matches")
    parser.add_argument("--verbose", action="store_true", default=config.verbose,
                        help="Enable debug logging")
    parser.add_argument("--logresult", nargs="?", const="", default=None, metavar="FILE",
                        help="Save result to file")
    parser.add_argument("--logresultanon", nargs="?", const="", default=None, metavar="FILE",
                        help="Save anonymized result to file")
    parser.add_argument("--xlsx", nargs="?", const="", default=None, metavar="FILE",
                        help="Export findings as Excel file")
    parser.add_argument("--excelanon", action="store_true", default=config.excelanon,
                        help="Anonymize values in Excel file")
    parser.add_argument("--continue-on-error", action="store_true", default=False,
                        help="Weiterscannen bei Datei-Lesefehlern (Standardverhalten). "
                             "Der Scan wird nie faelschlich als 'complete' gemeldet.")
    parser.add_argument("--exit-on-findings", action="store_true", default=False,
                        help="Exit-Code 1, wenn Findings gefunden wurden")
    parser.add_argument("--show-sensitive-values", action="store_true", default=False,
                        help="Unmaskierte sensible Werte in Ausgaben zulassen "
                             "(WARNUNG: Klartext von Secrets)")

    args = parser.parse_args()
    if not args.logdateien and not args.status:
        parser.print_help()
        sys.exit(0)
    # CLI values bypass DetectoConfig.__post_init__() - clamp them here.
    # (--critical 0 would otherwise silently suppress ALL findings.)
    args.examplecount = max(1, args.examplecount)
    args.minlen = max(2, args.minlen)
    args.critical = max(1, min(5, args.critical))
    return args


def _build_call_string(
    args: argparse.Namespace, logfiles: list[str], config: DetectoConfig,
) -> str:
    """Build a compact call string showing only non-default parameters."""
    parts = list(logfiles)
    if args.examplecount != config.examplecount:
        parts.append(f"--examplecount={args.examplecount}")
    if args.minlen != config.minlen:
        parts.append(f"--minlen={args.minlen}")
    if args.critical != config.critical:
        parts.append(f"--critical={args.critical}")
    for flag in (
        "anon", "full", "nocolor", "showskipped", "verbose", "excelanon",
        "continue_on_error", "exit_on_findings", "show_sensitive_values",
    ):
        if getattr(args, flag, False):
            parts.append(f"--{flag.replace('_', '-')}")
    for param in ("logresult", "logresultanon", "xlsx"):
        val = getattr(args, param)
        if val is not None:
            parts.append(f"--{param}={val}" if val else f"--{param}")
    return " ".join(parts)


def main() -> None:
    """Detecto entry point. Wraps :func:`_run` and maps errors to exit codes."""
    try:
        code = _run()
    except SystemExit:
        raise
    except KeyboardInterrupt:  # pragma: no cover
        print("Abgebrochen.", file=sys.stderr)
        sys.exit(EXIT_INTERNAL)
    except Exception as exc:  # noqa: BLE001 - top-level guard
        log.exception("Interner Fehler")
        print(f"INTERNER FEHLER: {exc}", file=sys.stderr)
        sys.exit(EXIT_INTERNAL)
    sys.exit(code)


def _run() -> int:
    """Run a scan and return the process exit code (Finding 2)."""
    base_dir = _resolve_base_dir()
    config = load_config(base_dir)

    # Parse args early so --verbose can affect logging level
    args = parse_args(config)
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")

    print_header()

    minlen = args.minlen  # clamped in parse_args()
    anonymizer = Anonymizer(config.anon_muster)

    # Finding 3: sensitive values are anonymized by default; plaintext requires
    # an explicit, loud opt-in. This never blocks non-interactive use.
    if args.show_sensitive_values:
        print(
            "WARNUNG: --show-sensitive-values ist aktiv - Konsolenausgabe und "
            "Reports koennen sensible Werte (Passwoerter, Tokens, ...) im "
            "Klartext enthalten.",
            file=sys.stderr,
        )
        # Explicit opt-in: reveal plaintext.
        args.anon = False
        args.excelanon = False
    else:
        # Default: anonymize everything, regardless of INI/CLI toggles.
        args.anon = True
        args.excelanon = True

    regexp, field, search = _load_patterns(base_dir, config, minlen)
    sw_re = load_stopwords(str(base_dir / config.stopword_regexp_file))
    sw_fd = load_stopwords(str(base_dir / config.stopword_field_file))
    sw_sm = load_stopwords(str(base_dir / config.stopword_suchmuster_file))

    if args.status:
        print_status(config, regexp, field, search)
        return EXIT_OK

    log.info("Patterns: %d regexp, %d field, %d search", len(regexp), len(field), len(search))

    logfiles = _collect_logfiles(args.logdateien)
    print(f"Analysiere {len(logfiles)} Logdatei(en): {', '.join(logfiles)}")

    analyzer = LogAnalyzer(
        regexp, field, search, sw_re, sw_fd, sw_sm,
        parse_json=config.parse_json,
        prefilter=config.prefilter,
        max_examples=config.max_examples_per_value,
        regex_timeout_ms=config.regex_timeout_ms,
        regex_disable_threshold=config.regex_disable_threshold,
        max_values_per_pattern=config.max_values_per_pattern,
        max_total_findings=config.max_total_findings,
        max_total_examples=config.max_total_examples,
        max_example_chars=config.max_example_chars,
        masked_criticality=config.masked_value_criticality,
    )
    start = time.time()
    results, line_count = analyzer.analyze(
        logfiles, config.refresh_status, config.workers,
    )
    duration = time.time() - start
    log.info("Analysis complete: %d lines in %.1f sec", line_count, duration)

    print_results(results, args.examplecount, args.anon, args.full,
                  args.nocolor, args.critical, args.showskipped, anonymizer)

    duration_text = _format_duration(duration)
    _print_statistics(len(logfiles), line_count, duration_text, results,
                      duration, config, critical=args.critical)

    # --- Scan status (Finding 2) ---
    diag = analyzer.diag
    status = diag.status()
    print("Scan-Status")
    for sline in diag.summary_lines():
        print(f"  {sline}")
    print()

    _handle_exports(args, results, logfiles, line_count, duration_text,
                    config, regexp, field, search, anonymizer, diag)

    return _compute_exit_code(status, results, args)


def _compute_exit_code(
    status: ScanStatus, results: OrderedDict, args: argparse.Namespace,
) -> int:
    """Map scan status (and optional --exit-on-findings) to an exit code."""
    if status is ScanStatus.FAILED:
        return EXIT_FAILED
    if status is ScanStatus.PARTIAL:
        return EXIT_PARTIAL
    if getattr(args, "exit_on_findings", False):
        has_findings = any(hits for _, _, hits in results.values())
        if has_findings:
            return EXIT_FINDINGS
    return EXIT_OK


def _resolve_base_dir() -> Path:
    """Determine directory with detecto.ini and pattern files.

    Precedence:
    1. Current working directory (if it contains detecto.ini)
    2. Source/ZIP checkout (repo root relative to this file)
    3. Installed package data (src/detecto/data via importlib.resources)
    """
    cwd = Path.cwd()
    if (cwd / "detecto.ini").is_file():
        return cwd
    repo = Path(__file__).resolve().parent.parent.parent
    if (repo / "detecto.ini").is_file():
        return repo
    try:
        from importlib.resources import files
        data_dir = Path(str(files("detecto") / "data"))
        if (data_dir / "detecto.ini").is_file():
            return data_dir
    except (ImportError, TypeError, FileNotFoundError):  # pragma: no cover
        pass
    return repo


def _load_patterns(
    base_dir: Path, config: DetectoConfig, minlen: int,
) -> tuple[list[RegexpPattern], list[FieldPattern], list[SearchPattern]]:
    """Load all pattern files based on configuration."""
    regexp_path = base_dir / config.regexp_file
    field_path = base_dir / config.field_file
    search_path = base_dir / config.suchmuster_file
    search_dir = base_dir / config.suchmuster_dir

    if not regexp_path.is_file():
        print(f"FEHLER: Regexp-Datei nicht gefunden: {regexp_path}")
        sys.exit(EXIT_CONFIG)
    if not search_path.is_file():
        print(f"FEHLER: Suchmuster-Datei nicht gefunden: {search_path}")
        sys.exit(EXIT_CONFIG)

    # Finding 6: pattern IDs must be globally unique across all pattern types.
    # A collision is a fatal configuration error (no auto-rename, no warning).
    registry: dict[str, tuple[str, str, int]] = {}
    try:
        regexp = load_regexp(regexp_path, registry) if config.search_regexp else []
        field = (
            load_field_patterns(field_path, registry)
            if config.search_field and field_path.is_file()
            else []
        )
        search = (
            load_search_patterns(search_path, str(search_dir), minlen, registry)
            if config.search_suchmuster
            else []
        )
    except DuplicatePatternError as e:
        print(f"FEHLER (Konfiguration): {e}")
        sys.exit(EXIT_CONFIG)
    log.debug("Pattern files: regexp=%s, field=%s, search=%s",
              regexp_path, field_path, search_path)
    return regexp, field, search


def _collect_logfiles(inputs: list[str]) -> list[str]:
    """Collect and deduplicate log files from glob patterns."""
    result: list[str] = []
    for pattern in inputs:
        result.extend(find_logfiles(pattern))
    result = list(dict.fromkeys(result))
    if not result:
        print(f"FEHLER: Keine Logdateien gefunden fuer: {' '.join(inputs)}")
        sys.exit(EXIT_CONFIG)
    return result


def _format_duration(seconds: float) -> str:
    """Format duration as human-readable string."""
    m, s = int(seconds // 60), int(seconds % 60)
    if m > 0:
        return f"{m} min {s} sec.   ({int(seconds)} sec)"
    return f"{s} sec.   ({seconds:.1f} sec)"


def _print_statistics(
    file_count: int, line_count: int, duration: str,
    results: OrderedDict | None = None,
    duration_sec: float = 0.0,
    config: DetectoConfig | None = None,
    critical: int = 5,
) -> None:
    """Print analysis statistics with findings breakdown by criticality."""
    print("Statistik")
    print(f"{'Analysierte Logdateien:':<{LABEL_WIDTH}} {file_count}")

    if results:
        krit_labels = {1: "Kritisch", 2: "Hoch", 3: "Mittel", 4: "Niedrig", 5: "Info"}
        krit_totals: dict[int, int] = {}
        grand_total = 0
        hidden_total = 0

        for krit_level in range(1, 6):
            counts: dict[str, int] = {"regexp": 0, "field": 0, "string": 0}
            for name, (typ, krit, hits) in results.items():
                if krit == krit_level:
                    counts[typ] = counts.get(typ, 0) + len(hits)
            level_total = sum(counts.values())
            if level_total > 0 and krit_level > critical:
                # Consistent with display/exports: filtered by --critical
                hidden_total += level_total
                continue
            if level_total > 0:
                krit_totals[krit_level] = level_total
                grand_total += level_total
                print(
                    f"{'Prio ' + str(krit_level) + ' (' + krit_labels[krit_level] + '):':<{LABEL_WIDTH}} "
                    f"({counts['regexp']}/{counts['field']}/{counts['string']} "
                    f"regexp/field/string)"
                )
        if hidden_total > 0:
            print(f"{'Ausgeblendet:':<{LABEL_WIDTH}} {hidden_total} "
                  f"(Prio > {critical}, siehe --critical)")

        if grand_total > 0:
            print("-" * 60)
            parts = "/".join(
                str(krit_totals.get(k, 0))
                for k in range(1, 6)
                if krit_totals.get(k, 0) > 0
            )
            labels = "/".join(
                krit_labels[k]
                for k in range(1, 6)
                if krit_totals.get(k, 0) > 0
            )
            print(f"{'Total:':<{LABEL_WIDTH}} {grand_total:,} ({parts} {labels})".replace(",", "."))
            print("-" * 60)

    cpu_count = multiprocessing.cpu_count()
    print(f"{'CPU Count:':<{LABEL_WIDTH}} {cpu_count}")
    prefilter_descriptions = {
        "all": "all: Schneller (~30-50%)",
        "regexp_field": "regexp_field: Nur Regexp/Field",
        "off": "off: Kein Pre-Filter",
    }
    if config:
        pf_mode = config.prefilter
        pf_text = prefilter_descriptions.get(pf_mode, pf_mode)
        print(f"{'Pre-Filter-Modus:':<{LABEL_WIDTH}} {pf_text}")
    print(f"{'Anzahl der Zeilen:':<{LABEL_WIDTH}} {line_count:,}".replace(",", "."))
    if duration_sec > 0 and line_count > 0:
        rate = int(line_count / duration_sec)
        print(f"{'Zeilen / sec:':<{LABEL_WIDTH}} {rate:,}".replace(",", "."))
    print(f"{'Analyse-Dauer:':<{LABEL_WIDTH}} {duration}")
    print()


def _handle_exports(
    args: argparse.Namespace, results: OrderedDict,
    logfiles: list[str], line_count: int, duration_text: str,
    config: DetectoConfig,
    regexp: list[RegexpPattern], field: list[FieldPattern],
    search: list[SearchPattern], anonymizer: Anonymizer,
    diagnostics: ScanDiagnostics | None = None,
) -> None:
    """Handle log and Excel exports based on CLI arguments."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    call_str = _build_call_string(args, logfiles, config)

    ctx = ExportContext(
        results=results, example_count=args.examplecount,
        critical=args.critical, call_str=call_str, logfiles=logfiles,
        line_count=line_count, duration_text=duration_text,
        regexp=regexp, field=field, search=search,
        full=args.full, excelanon=args.excelanon, anonymizer=anonymizer,
        diagnostics=diagnostics,
    )

    # --logresult und --logresultanon sind unabhaengig kombinierbar
    if args.logresult is not None:
        log_file = args.logresult or f"detecto_{ts}.log"
        export_log(log_file, ctx, anon=False, show_skipped=args.showskipped)
        print(f"Ergebnis gespeichert in: {log_file}")

    if args.logresultanon is not None:
        log_file = args.logresultanon or f"detecto_{ts}_anon.log"
        export_log(log_file, ctx, anon=True, show_skipped=args.showskipped)
        print(f"Ergebnis gespeichert in: {log_file} (anonymisiert)")

    if args.xlsx is not None:
        xlsx_name = args.xlsx if args.xlsx else f"detecto_{ts}.xlsx"
        export_xlsx(xlsx_name, ctx)
