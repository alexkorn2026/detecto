"""Loading of regexp, field and search pattern files."""
from __future__ import annotations

import csv
import logging
import os
import re
import signal
from pathlib import Path

from detecto.constants import PATTERN_DELIMITER, REGEX_TIMEOUT_SEC, REGEX_TEST_STRING
from detecto.utils import normalize

__all__ = [
    "load_regexp", "load_field_patterns", "load_search_patterns", "load_stopwords",
    "RegexpPattern", "FieldPattern", "SearchPattern",
]

log = logging.getLogger(__name__)

RegexpPattern = tuple[str, int, str, re.Pattern]
FieldPattern = tuple[str, int, str, re.Pattern, int]
SearchPattern = tuple[str, int, set[str]]


def _read_lines(filepath: str | Path) -> list[tuple[str, list[str]]]:
    """Read a pattern file, skip empty lines, split by delimiter."""
    result: list[tuple[str, list[str]]] = []
    with open(filepath, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if line:
                result.append((line, line.split(PATTERN_DELIMITER)))
    return result


class _RegexTimeout(Exception):
    pass


def _timeout_handler(signum: int, frame: object) -> None:
    raise _RegexTimeout()


def _safe_compile(pattern: str, source: str) -> re.Pattern | None:
    """Compile a regex with DoS protection (SIGALRM timeout on Unix)."""
    try:
        compiled = re.compile(pattern)
    except re.error as e:
        log.warning("Invalid regex in %s: %s (%s)", source, pattern, e)
        return None
    if hasattr(signal, "SIGALRM"):
        old = signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(REGEX_TIMEOUT_SEC)
        try:
            compiled.search(REGEX_TEST_STRING)
        except _RegexTimeout:
            log.warning("Regex DoS risk in %s: %s", source, pattern)
            return None
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old)
    return compiled


def _parse_krit(value: str, source: str, raw: str) -> int:
    """Parse criticality and clamp to 1-5 (typo 'krit=6' would otherwise
    make the pattern invisible: krit > critical(5) is always true)."""
    krit = int(value)
    if not 1 <= krit <= 5:
        clamped = max(1, min(5, krit))
        log.warning("Criticality %d out of range 1-5 in %s (%s), using %d",
                    krit, source, raw[:60], clamped)
        return clamped
    return krit


def _validate_path(base_dir: str | Path, filename: str) -> Path | None:
    """Validate that a file path stays within base_dir (path traversal protection).

    Uses Path.relative_to() instead of a string prefix check: the prefix
    variant let '/x/baseevil' pass for base '/x/base'.
    """
    base = Path(base_dir).resolve()
    target = (base / filename).resolve()
    try:
        target.relative_to(base)
    except ValueError:
        log.warning("Path traversal blocked: %s", filename)
        return None
    return target


def load_regexp(filepath: str | Path) -> list[RegexpPattern]:
    """Load regexp patterns. Format: name::krit::description::pattern"""
    result: list[RegexpPattern] = []
    for raw, parts in _read_lines(filepath):
        if len(parts) < 4:
            log.warning("Invalid format in %s: %s", filepath, raw)
            continue
        compiled = _safe_compile(parts[3], str(filepath))
        if compiled is None:
            continue
        try:
            result.append((parts[0], _parse_krit(parts[1], str(filepath), raw),
                           parts[2], compiled))
        except ValueError as e:
            log.warning("Invalid criticality in %s: %s (%s)", filepath, raw, e)
    log.info("Regexp patterns loaded: %d from %s", len(result), filepath)
    return result


def load_field_patterns(filepath: str | Path) -> list[FieldPattern]:
    """Load field patterns. Format: name::krit::description::pattern[::offset]"""
    result: list[FieldPattern] = []
    for raw, parts in _read_lines(filepath):
        if len(parts) < 4:
            log.warning("Invalid format in %s: %s", filepath, raw)
            continue
        compiled = _safe_compile(parts[3], str(filepath))
        if compiled is None:
            continue
        try:
            offset = int(parts[4]) if len(parts) >= 5 else 1
            result.append((parts[0], _parse_krit(parts[1], str(filepath), raw),
                           parts[2], compiled, offset))
        except ValueError as e:
            log.warning("Invalid value in %s: %s (%s)", filepath, raw, e)
    log.info("Field patterns loaded: %d from %s", len(result), filepath)
    return result


def load_search_patterns(
    filepath: str | Path, directory: str | Path, minlen: int = 5,
) -> list[SearchPattern]:
    """Load search pattern index. Format: name::krit::filename.csv"""
    result: list[SearchPattern] = []
    for raw, parts in _read_lines(filepath):
        if len(parts) < 3:
            log.warning("Invalid format in %s: %s", filepath, raw)
            continue
        name, krit_str, csv_name = parts[0], parts[1], parts[2]
        csv_path = _validate_path(directory, csv_name)
        if csv_path is None or not csv_path.is_file():
            if csv_path is not None:
                log.warning("File not found: %s", csv_path)
            continue
        values: set[str] = set()
        with open(csv_path, "r", encoding="utf-8") as csv_f:
            reader = csv.reader(csv_f)
            next(reader, None)
            for row in reader:
                if row and row[0].strip() and len(row[0].strip()) >= minlen:
                    values.add(normalize(row[0].strip()))
        if values:
            try:
                result.append((name, _parse_krit(krit_str, str(filepath), raw),
                               values))
            except ValueError as e:
                log.warning("Invalid criticality in %s: %s (%s)", filepath, raw, e)
            log.debug("Search pattern '%s': %d entries", name, len(values))
    log.info("Search patterns loaded: %d categories from %s", len(result), filepath)
    return result


def load_stopwords(filepath: str | Path) -> set[str]:
    """Load stopwords from a text file (one word per line, normalized)."""
    if not os.path.isfile(filepath):
        return set()
    result: set[str] = set()
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            word = line.strip()
            if word:
                result.add(normalize(word))
    log.debug("Stopwords loaded: %d from %s", len(result), filepath)
    return result
