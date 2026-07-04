"""Scan diagnostics and status tracking.

Central, lightweight container that records everything the scan needs to
report transparently: per-file success/failure counts, regex timeouts and
disabled patterns, limit-based drops, JSON-parsing statistics and encoding
information. The object is created per analyzer instance, mutated during
analysis and merged across multiprocessing workers.

This is a *small, additive* structure - it does not replace the existing
results data structure (see project constraint: no architectural rewrite).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

__all__ = [
    "ScanStatus",
    "ScanDiagnostics",
    "EXIT_OK",
    "EXIT_FINDINGS",
    "EXIT_CONFIG",
    "EXIT_PARTIAL",
    "EXIT_FAILED",
    "EXIT_INTERNAL",
]


class ScanStatus(str, Enum):
    """Overall outcome of a scan."""

    COMPLETE = "complete"
    PARTIAL = "partial"
    FAILED = "failed"


# --- Exit codes (Finding 2) ---------------------------------------------
# 0 = complete scan
# 1 = reserved for "findings present" (kept for backwards compatibility;
#     Detecto historically always exited 0 on a successful scan, so this
#     code is only emitted when explicitly enabled via --exit-on-findings)
# 2 = configuration / invocation error
# 3 = partial scan (some files unreadable/truncated)
# 4 = scan completely failed
# 5 = internal error
EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_CONFIG = 2
EXIT_PARTIAL = 3
EXIT_FAILED = 4
EXIT_INTERNAL = 5


@dataclass
class ScanDiagnostics:
    """Mutable record of everything noteworthy that happened during a scan."""

    # --- File processing outcome (Finding 2) ---
    files_complete: int = 0
    files_partial: int = 0
    files_unreadable: int = 0
    other_errors: int = 0
    # (path, human-readable message)
    file_errors: list[tuple[str, str]] = field(default_factory=list)
    # Files skipped before reading (binary/pipe/symlink) - Finding 28
    skipped_files: list[tuple[str, str]] = field(default_factory=list)

    # --- Regex runtime protection (Finding 1) ---
    regex_timeouts: dict[str, int] = field(default_factory=dict)
    disabled_patterns: set[str] = field(default_factory=set)

    # --- Limits (Findings 4 / 27) ---
    findings_stored: int = 0
    findings_dropped_global: int = 0
    findings_dropped_pattern: int = 0
    examples_truncated: int = 0
    lines_oversized: int = 0
    global_limit_hit: str = ""  # name of the first global limit that fired

    # --- JSON parsing (Finding 10) ---
    json_candidates: int = 0
    json_parsed: int = 0
    json_failed: int = 0

    # --- Encoding (Finding 26) ---
    decode_errors: int = 0
    replaced_chars: int = 0
    encodings_used: dict[str, str] = field(default_factory=dict)

    # ------------------------------------------------------------------
    def record_timeout(self, pattern_name: str) -> int:
        """Count a regex timeout for a pattern; return the new total."""
        count = self.regex_timeouts.get(pattern_name, 0) + 1
        self.regex_timeouts[pattern_name] = count
        return count

    def record_file_error(self, path: str, message: str, *, partial: bool) -> None:
        """Record an I/O problem with a file."""
        if partial:
            self.files_partial += 1
        else:
            self.files_unreadable += 1
        self.file_errors.append((path, message))

    def merge(self, other: "ScanDiagnostics") -> None:
        """Merge another diagnostics object (e.g. from a worker) into self."""
        self.files_complete += other.files_complete
        self.files_partial += other.files_partial
        self.files_unreadable += other.files_unreadable
        self.other_errors += other.other_errors
        self.file_errors.extend(other.file_errors)
        self.skipped_files.extend(other.skipped_files)

        for name, count in other.regex_timeouts.items():
            self.regex_timeouts[name] = self.regex_timeouts.get(name, 0) + count
        self.disabled_patterns |= other.disabled_patterns

        self.findings_stored += other.findings_stored
        self.findings_dropped_global += other.findings_dropped_global
        self.findings_dropped_pattern += other.findings_dropped_pattern
        self.examples_truncated += other.examples_truncated
        self.lines_oversized += other.lines_oversized
        if other.global_limit_hit and not self.global_limit_hit:
            self.global_limit_hit = other.global_limit_hit

        self.json_candidates += other.json_candidates
        self.json_parsed += other.json_parsed
        self.json_failed += other.json_failed

        self.decode_errors += other.decode_errors
        self.replaced_chars += other.replaced_chars
        self.encodings_used.update(other.encodings_used)

    def status(self) -> ScanStatus:
        """Derive the overall scan status from the recorded counters.

        - ``failed``   : nothing could be evaluated at all.
        - ``partial``  : at least one file could not be fully processed but
          others were analysed.
        - ``complete`` : every requested file was processed without error.
        """
        evaluated = self.files_complete + self.files_partial
        if evaluated == 0:
            return ScanStatus.FAILED
        if (
            self.files_partial
            or self.files_unreadable
            or self.other_errors
            or self.disabled_patterns
        ):
            return ScanStatus.PARTIAL
        return ScanStatus.COMPLETE

    def summary_lines(self) -> list[str]:
        """Human-readable multi-line summary for console/log/export output."""
        lines: list[str] = []
        status = self.status()
        lines.append(f"Scan-Status: {status.value}")
        lines.append(
            "Dateien: "
            f"{self.files_complete} vollstaendig, "
            f"{self.files_partial} teilweise, "
            f"{self.files_unreadable} nicht lesbar, "
            f"{self.other_errors} sonstige Fehler"
        )
        if self.skipped_files:
            lines.append(f"Uebersprungene Dateien: {len(self.skipped_files)}")
        if self.regex_timeouts:
            total = sum(self.regex_timeouts.values())
            lines.append(
                f"Regex-Timeouts: {total} "
                f"({len(self.regex_timeouts)} Muster betroffen, "
                f"{len(self.disabled_patterns)} deaktiviert)"
            )
            for name, count in sorted(self.regex_timeouts.items()):
                disabled = " [deaktiviert]" if name in self.disabled_patterns else ""
                lines.append(f"  - {name}: {count} Timeout(s){disabled}")
        if self.findings_dropped_global or self.findings_dropped_pattern:
            lines.append(
                "Verworfene Findings (Limits): "
                f"{self.findings_dropped_global} global, "
                f"{self.findings_dropped_pattern} pro Muster"
            )
        if self.global_limit_hit:
            lines.append(f"Ausgeloestes globales Limit: {self.global_limit_hit}")
        if self.examples_truncated:
            lines.append(f"Gekuerzte Beispiele: {self.examples_truncated}")
        if self.lines_oversized:
            lines.append(f"Ueberlange Zeilen: {self.lines_oversized}")
        if self.json_candidates:
            lines.append(
                "JSON: "
                f"{self.json_candidates} Kandidaten, "
                f"{self.json_parsed} geparst, {self.json_failed} fehlgeschlagen"
            )
        if self.decode_errors or self.replaced_chars:
            lines.append(
                "Encoding: "
                f"{self.decode_errors} Decodierungsfehler, "
                f"{self.replaced_chars} ersetzte Zeichen"
            )
        if self.file_errors:
            lines.append("Fehlerhafte Dateien:")
            for path, msg in self.file_errors[:50]:
                lines.append(f"  - {path}: {msg}")
        return lines
