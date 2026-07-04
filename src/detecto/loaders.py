"""Loading of regexp, field and search pattern files."""
from __future__ import annotations

import csv
import io
import logging
import os
import re
import signal
import stat
from pathlib import Path

from detecto.constants import (
    PATTERN_DELIMITER,
    REGEX_LOADCHECK_MS,
    REGEX_TEST_STRING,
    REGEX_TIMEOUT_SEC,
)
from detecto.regexsafe import HAS_REGEX, RegexTimeout, compile_pattern, safe_search
from detecto.utils import normalize

__all__ = [
    "load_regexp", "load_field_patterns", "load_search_patterns", "load_stopwords",
    "RegexpPattern", "FieldPattern", "SearchPattern",
    "DuplicatePatternError", "register_pattern_id",
]

log = logging.getLogger(__name__)

# Finding 8: regexp patterns carry an explicit scope ("token" | "line") as an
# optional 5th field. The tuple keeps 4 leading elements for compatibility.
RegexpPattern = tuple[str, int, str, re.Pattern, str]
FieldPattern = tuple[str, int, str, re.Pattern, int]
SearchPattern = tuple[str, int, set[str]]

VALID_SCOPES = ("token", "line")
DEFAULT_SCOPE = "line"  # Finding 8: safe default for legacy (unscoped) entries


def _parse_scope(value: str, source: str, raw: str) -> str:
    """Validate an explicit scope value ("token" | "line")."""
    scope = value.strip().lower()
    if scope not in VALID_SCOPES:
        log.warning("Invalid scope '%s' in %s (%s), using '%s'",
                    value, source, raw[:60], DEFAULT_SCOPE)
        return DEFAULT_SCOPE
    return scope


class DuplicatePatternError(Exception):
    """Raised when a pattern ID is not globally unique (Finding 6)."""

    def __init__(
        self, name: str, typ: str, source: str, lineno: int,
        existing: tuple[str, str, int],
    ) -> None:
        prev_typ, prev_src, prev_line = existing
        super().__init__(
            f"Doppelte Pattern-ID '{name}': "
            f"{typ} in {source}:{lineno} kollidiert mit "
            f"{prev_typ} in {prev_src}:{prev_line}. "
            "Pattern-IDs muessen ueber alle Musterarten hinweg eindeutig sein."
        )
        self.name = name
        self.typ = typ
        self.source = source
        self.lineno = lineno
        self.existing = existing


def register_pattern_id(
    registry: dict[str, tuple[str, str, int]] | None,
    name: str, typ: str, source: str, lineno: int,
) -> None:
    """Record a pattern ID and enforce global uniqueness (Finding 6)."""
    if registry is None:
        return
    if name in registry:
        raise DuplicatePatternError(name, typ, str(source), lineno, registry[name])
    registry[name] = (typ, str(source), lineno)


def _safe_open_text(filepath: str | Path) -> io.TextIOWrapper:
    """Open a pattern file rejecting symlinks and non-regular files (Finding 41).

    Uses ``O_NOFOLLOW`` so a symlinked final path component fails to open, then
    verifies the *actually opened* file descriptor is a regular file via
    ``fstat`` (closing the TOCTOU window between check and open). On platforms
    without ``O_NOFOLLOW`` this degrades to an fstat check only (documented
    residual risk).
    """
    # O_NONBLOCK so opening a FIFO/device does not block waiting for a writer;
    # O_NOFOLLOW so a symlinked final component fails to open.
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    fd = os.open(str(filepath), flags)
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            raise OSError(f"not a regular file: {filepath}")
        # Clear O_NONBLOCK for normal buffered reads on the regular file.
        if hasattr(os, "get_blocking"):
            os.set_blocking(fd, True)
    except Exception:
        os.close(fd)
        raise
    return os.fdopen(fd, "r", encoding="utf-8")


def _read_lines(filepath: str | Path) -> list[tuple[int, str, list[str]]]:
    """Read a pattern file, skip empty lines, split by delimiter.

    Returns (lineno, raw_line, parts) with 1-based line numbers so loaders can
    report exact positions (Finding 6).
    """
    result: list[tuple[int, str, list[str]]] = []
    try:
        f = _safe_open_text(filepath)
    except OSError as e:
        log.warning("Refusing to load pattern file %s: %s", filepath, e)
        return result
    with f:
        for lineno, raw in enumerate(f, 1):
            line = raw.strip()
            if line:
                result.append((lineno, line, line.split(PATTERN_DELIMITER)))
    return result


class _RegexTimeout(Exception):
    pass


def _timeout_handler(signum: int, frame: object) -> None:
    raise _RegexTimeout()


def _safe_compile(pattern: str, source: str):
    """Compile a regex with a load-time DoS pre-check.

    This is only the *first* line of defence (Finding 1). The authoritative
    protection is the per-match runtime timeout applied during the scan
    (see :mod:`detecto.regexsafe` and the analyzer). We still reject patterns
    that already blow up on a trivial test string here.
    """
    try:
        compiled = compile_pattern(pattern)
    except re.error as e:
        log.warning("Invalid regex in %s: %s (%s)", source, pattern, e)
        return None

    if HAS_REGEX:
        # Cross-platform runtime-enforced pre-check via the regex engine.
        try:
            safe_search(compiled, REGEX_TEST_STRING, REGEX_LOADCHECK_MS)
        except RegexTimeout:
            log.warning("Regex DoS risk (load pre-check) in %s: %s", source, pattern)
            return None
    elif hasattr(signal, "SIGALRM"):
        # Fallback for the re-only build: coarse SIGALRM guard.
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


def load_regexp(
    filepath: str | Path,
    registry: dict[str, tuple[str, str, int]] | None = None,
) -> list[RegexpPattern]:
    """Load regexp patterns.

    Format: ``name::krit::description::pattern[::scope]`` where ``scope`` is
    ``token`` or ``line`` (Finding 8). Entries without a scope field still load
    (a warning is logged and the safe default ``line`` is used), so old files
    remain usable during the migration.
    """
    result: list[RegexpPattern] = []
    warned_legacy = False
    for lineno, raw, parts in _read_lines(filepath):
        if len(parts) < 4:
            log.warning("Invalid format in %s: %s", filepath, raw)
            continue
        compiled = _safe_compile(parts[3], str(filepath))
        if compiled is None:
            continue
        if len(parts) >= 5 and parts[4].strip():
            scope = _parse_scope(parts[4], str(filepath), raw)
        else:
            scope = DEFAULT_SCOPE
            if not warned_legacy:
                log.warning(
                    "%s: regexp entries without an explicit scope field are "
                    "deprecated; defaulting to '%s'. Add '::token' or '::line'.",
                    filepath, DEFAULT_SCOPE,
                )
                warned_legacy = True
        try:
            register_pattern_id(registry, parts[0], "regexp", filepath, lineno)
            result.append((parts[0], _parse_krit(parts[1], str(filepath), raw),
                           parts[2], compiled, scope))
        except ValueError as e:
            log.warning("Invalid criticality in %s: %s (%s)", filepath, raw, e)
    log.info("Regexp patterns loaded: %d from %s", len(result), filepath)
    return result


def load_field_patterns(
    filepath: str | Path,
    registry: dict[str, tuple[str, str, int]] | None = None,
) -> list[FieldPattern]:
    """Load field patterns. Format: name::krit::description::pattern[::offset]"""
    result: list[FieldPattern] = []
    for lineno, raw, parts in _read_lines(filepath):
        if len(parts) < 4:
            log.warning("Invalid format in %s: %s", filepath, raw)
            continue
        compiled = _safe_compile(parts[3], str(filepath))
        if compiled is None:
            continue
        try:
            offset = int(parts[4]) if len(parts) >= 5 else 1
            register_pattern_id(registry, parts[0], "field", filepath, lineno)
            result.append((parts[0], _parse_krit(parts[1], str(filepath), raw),
                           parts[2], compiled, offset))
        except ValueError as e:
            log.warning("Invalid value in %s: %s (%s)", filepath, raw, e)
    log.info("Field patterns loaded: %d from %s", len(result), filepath)
    return result


def load_search_patterns(
    filepath: str | Path, directory: str | Path, minlen: int = 5,
    registry: dict[str, tuple[str, str, int]] | None = None,
) -> list[SearchPattern]:
    """Load search pattern index. Format: name::krit::filename.csv"""
    result: list[SearchPattern] = []
    for lineno, raw, parts in _read_lines(filepath):
        if len(parts) < 3:
            log.warning("Invalid format in %s: %s", filepath, raw)
            continue
        name, krit_str, csv_name = parts[0], parts[1], parts[2]
        # Register the declared ID for global-uniqueness even if the CSV is
        # missing/empty (the ID was still declared here). Finding 6.
        register_pattern_id(registry, name, "string", filepath, lineno)
        csv_path = _validate_path(directory, csv_name)
        if csv_path is None or not csv_path.is_file():
            if csv_path is not None:
                log.warning("File not found: %s", csv_path)
            continue
        values: set[str] = set()
        try:
            csv_f = _safe_open_text(csv_path)
        except OSError as e:
            log.warning("Refusing to load search list %s: %s", csv_path, e)
            continue
        with csv_f:
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
    with open(filepath, encoding="utf-8") as f:
        for line in f:
            word = line.strip()
            if word:
                result.add(normalize(word))
    log.debug("Stopwords loaded: %d from %s", len(result), filepath)
    return result
