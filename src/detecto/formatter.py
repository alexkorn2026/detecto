"""Console output: formatting, color highlighting, status report."""
from __future__ import annotations

import re
from collections import OrderedDict
from datetime import date

from detecto import VERSION
from detecto.anonymizer import Anonymizer
from detecto.constants import (
    COPYRIGHT_YEAR, LABEL_WIDTH, KRIT_LABELS,
    ANSI_RED, ANSI_DARK_GREEN, ANSI_YELLOW, ANSI_RESET, ANSI_TYPE_MAP,
)
from detecto.config import DetectoConfig
from detecto.loaders import RegexpPattern, FieldPattern, SearchPattern
from detecto.utils import krit_color

__all__ = [
    "print_header", "print_status", "highlight",
    "build_result_lines", "print_results",
]


def print_header() -> None:
    """Print the Detecto header with version and copyright."""
    print(f"Detecto v{VERSION}  ({date.today().isoformat()})")
    print(f"Copyright (c) {COPYRIGHT_YEAR} Alexander Kornbrust  |  MIT License")
    print()


def highlight(
    line: str,
    token: str,
    anon: bool = False,
    color: bool = True,
    field_token: str | None = None,
    anonymizer: Anonymizer | None = None,
) -> str:
    """Highlight occurrences of token in a log line.

    Args:
        line: The complete log line.
        token: The value to highlight (e.g. a password).
        anon: If True, redact the value before inserting.
        color: If False, no ANSI codes are inserted.
        field_token: Optional field name (e.g. 'password'), highlighted in dark green.
        anonymizer: Anonymizer instance for redaction.
    """
    display = anonymizer.redact(token) if (anon and anonymizer) else token
    # Prefer token-boundary matches to avoid marking substrings of other
    # words (e.g. value 'anna' inside 'Susanna'); fall back to substring.
    pat = re.compile(r"(?<!\w)" + re.escape(token) + r"(?!\w)", re.IGNORECASE)
    if not pat.search(line):
        pat = re.compile(re.escape(token), re.IGNORECASE)
    if color:
        # Replacement via lambda: values containing backslashes (e.g.
        # 'DOMAIN\\user') would otherwise raise re.error ("bad escape").
        result = pat.sub(lambda m: f"{ANSI_RED}{display}{ANSI_RESET}", line)
        if field_token:
            fp = re.compile(
                r"(?<!\w)" + re.escape(field_token) + r"(?!\w)", re.IGNORECASE,
            )
            result = fp.sub(
                lambda m: f"{ANSI_DARK_GREEN}{m.group(0)}{ANSI_RESET}",
                result, count=1,
            )
        return result
    return pat.sub(lambda m: display, line)


def _format_line(
    typ: str, krit: int, name: str, suffix: str, color: bool,
) -> str:
    """Format a result line: [type] [criticality] name: suffix."""
    label = KRIT_LABELS.get(krit, str(krit))
    if color:
        tc = ANSI_TYPE_MAP.get(typ, "")
        kc = krit_color(krit)
        return (
            f"{tc}[{typ}]{ANSI_RESET} "
            f"{kc}[{label}]{ANSI_RESET} "
            f"{ANSI_YELLOW}{name}{ANSI_RESET}: {suffix}"
        )
    return f"[{typ}] [{label}] {name}: {suffix}"


def build_result_lines(
    results: OrderedDict,
    example_count: int = 3,
    anon: bool = False,
    full: bool = False,
    color: bool = True,
    critical: int = 5,
    show_skipped: bool = False,
    anonymizer: Anonymizer | None = None,
) -> list[str]:
    """Build formatted result lines as a list of strings."""
    lines = ["", "=== Detecto - Ergebnisse ===", ""]
    found = False

    for name, (typ, krit, hits) in results.items():
        if krit > critical:
            continue
        if hits:
            found = True
            keys = sorted(hits.keys())[:example_count]
            display = (
                [anonymizer.redact(k) for k in keys] if anon and anonymizer else keys
            )
            lines.append(_format_line(typ, krit, name, ", ".join(display), color))
            if full:
                for token in keys:
                    entry = hits[token][0]
                    ftk = entry[2] if len(entry) > 2 else None
                    marked = highlight(entry[1], token, anon, color, ftk, anonymizer)
                    lines.append(f"  \u2192 [{entry[0]}] {marked}")
                lines.append("")
        elif show_skipped:
            lines.append(_format_line(typ, krit, name, "<nothing found>", color))

    if not found and not show_skipped:
        lines.append("Keine kritischen Daten gefunden.")
    lines.append("")
    return lines


def print_results(
    results: OrderedDict,
    example_count: int = 3,
    anon: bool = False,
    full: bool = False,
    nocolor: bool = False,
    critical: int = 5,
    show_skipped: bool = False,
    anonymizer: Anonymizer | None = None,
) -> None:
    """Print results to stdout."""
    for line in build_result_lines(
        results, example_count, anon, full,
        color=not nocolor, critical=critical,
        show_skipped=show_skipped, anonymizer=anonymizer,
    ):
        print(line)


def print_status(
    config: DetectoConfig,
    regexp: list[RegexpPattern],
    field: list[FieldPattern],
    search: list[SearchPattern],
) -> None:
    """Print the --status report with INI defaults and pattern overview."""
    def _krit_label(krit: int) -> str:
        return f"{krit_color(krit)}[{KRIT_LABELS[krit]}]{ANSI_RESET}"

    print("=== Detecto - Status ===\n")
    print("Default-Werte (detecto.ini):")
    for key in [
        "examplecount", "minlen", "critical", "anon", "full",
        "nocolor", "showskipped", "verbose", "anon_muster",
        "search_regexp", "search_field", "search_suchmuster",
        "parse_json", "workers", "refresh_status", "prefilter",
    ]:
        print(f"  {key + ':':<{LABEL_WIDTH}} {getattr(config, key)}")
    print()

    print(f"Regexp: {len(regexp)}")
    for name, krit, desc, _ in regexp:
        print(f"  {_krit_label(krit)} {name}: {desc}")

    print(f"Field: {len(field)}")
    for name, krit, desc, _, offset in field:
        print(f"  {_krit_label(krit)} {name}: {desc} (offset: {offset})")

    print(f"Suchmuster: {len(search)}")
    for name, krit, values in search:
        print(f"  {_krit_label(krit)} {name}: {len(values)} Eintr\u00e4ge")
