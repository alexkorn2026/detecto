"""Robust, bounded file reading (Findings 26, 27, 28).

Handles encoding selection, oversized single lines, and non-regular / binary /
compressed inputs, recording everything noteworthy into the scan diagnostics
so nothing is dropped silently.
"""
from __future__ import annotations

import gzip
import logging
import os
import stat
from dataclasses import dataclass
from typing import BinaryIO, Iterator

from detecto.diagnostics import ScanDiagnostics

log = logging.getLogger(__name__)

__all__ = ["ReaderOptions", "classify_file", "iter_file_lines"]


@dataclass
class ReaderOptions:
    """All knobs that control how a file is read."""

    encoding: str = "auto"           # auto | utf-8 | windows-1252 | iso-8859-1 | ...
    errors: str = "replace"          # strict | replace | ignore
    max_line_bytes: int = 1_048_576  # Finding 27
    oversized_policy: str = "truncate"  # truncate | skip | fail
    follow_symlinks: bool = False    # Finding 28
    skip_binary: bool = True
    max_decompressed_bytes: int = 512 * 1024 * 1024  # gz bomb guard


# --- Finding 28: file classification --------------------------------------

def classify_file(path: str, follow_symlinks: bool) -> str | None:
    """Return a skip-reason for a non-regular file, or None if it is fine."""
    try:
        lst = os.lstat(path)
    except OSError as e:
        return f"stat failed: {e}"
    if stat.S_ISLNK(lst.st_mode) and not follow_symlinks:
        return "symlink (follow_input_symlinks=false)"
    try:
        st = os.stat(path)  # follows symlink
    except OSError as e:
        return f"stat failed: {e}"
    mode = st.st_mode
    if stat.S_ISDIR(mode):
        return "directory"
    if not stat.S_ISREG(mode):
        # FIFO, socket, device, ...
        return "not a regular file"
    return None


def _looks_binary(sample: bytes) -> bool:
    """Heuristic: NUL bytes or a high ratio of non-text bytes => binary."""
    if b"\x00" in sample:
        return True
    if not sample:
        return False
    text_bytes = bytes(range(32, 127)) + b"\r\n\t\f\b"
    nontext = sum(b not in text_bytes for b in sample)
    return nontext / len(sample) > 0.30


# --- encoding (Finding 26) -------------------------------------------------

_BOMS = (
    (b"\xef\xbb\xbf", "utf-8-sig"),
    (b"\xff\xfe\x00\x00", "utf-32"),
    (b"\x00\x00\xfe\xff", "utf-32"),
    (b"\xff\xfe", "utf-16"),
    (b"\xfe\xff", "utf-16"),
)


def _detect_encoding(head: bytes, requested: str) -> str:
    """Resolve the effective encoding for a file (deterministic rules)."""
    if requested != "auto":
        return requested
    for bom, enc in _BOMS:
        if head.startswith(bom):
            return enc
    # No BOM: validate as UTF-8, else fall back to windows-1252 (byte-complete).
    try:
        head.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        return "windows-1252"


# --- bounded line reader (Finding 27) --------------------------------------

def _read_limited_lines(
    stream: BinaryIO, max_line_bytes: int, budget: list[int],
) -> Iterator[tuple[bytes, bool, int]]:
    """Yield (raw_line_without_newline, oversized, original_len).

    Reads incrementally so a single unterminated giant line cannot exhaust
    memory: at most ``max_line_bytes`` are buffered; the remainder up to the
    next newline is consumed and discarded. ``budget`` is a 1-element list
    tracking remaining decompressed bytes (gz bomb guard).
    """
    buf = bytearray()
    oversized = False
    original_len = 0

    def _accumulate(segment: bytes) -> None:
        nonlocal oversized, original_len
        original_len += len(segment)
        if oversized:
            return
        room = max_line_bytes - len(buf)
        if len(segment) > room:
            buf.extend(segment[:room])
            oversized = True
        else:
            buf.extend(segment)

    while True:
        chunk = stream.read(65536)
        if not chunk:
            break
        budget[0] -= len(chunk)
        if budget[0] < 0:
            log.warning("Decompressed size budget exceeded; stopping read")
            break
        idx = 0
        while True:
            nl = chunk.find(b"\n", idx)
            if nl == -1:
                _accumulate(chunk[idx:])
                break
            _accumulate(chunk[idx:nl])
            yield bytes(buf).rstrip(b"\r"), oversized, original_len
            buf.clear()
            oversized = False
            original_len = 0
            idx = nl + 1
    if buf or oversized or original_len:
        yield bytes(buf).rstrip(b"\r"), oversized, original_len


def _open_binary(path: str) -> BinaryIO:
    if path.endswith(".gz"):
        return gzip.open(path, "rb")  # type: ignore[return-value]
    return open(path, "rb")


def iter_file_lines(
    filepath: str, diag: ScanDiagnostics, opts: ReaderOptions,
) -> Iterator[str]:
    """Iterate decoded, stripped lines with encoding + size + type handling."""
    skip = classify_file(filepath, opts.follow_symlinks)
    if skip is not None:
        diag.skipped_files.append((filepath, skip))
        log.info("Skipping %s: %s", filepath, skip)
        return

    try:
        with open(filepath, "rb") as probe:
            head = probe.read(4096)
    except OSError as e:
        diag.record_file_error(filepath, str(e), partial=False)
        return

    if opts.skip_binary and not filepath.endswith(".gz") and _looks_binary(head):
        diag.skipped_files.append((filepath, "binary content"))
        log.info("Skipping binary file %s", filepath)
        return

    encoding = _detect_encoding(head, opts.encoding)
    diag.encodings_used[filepath] = encoding
    budget = [opts.max_decompressed_bytes]
    yielded = False
    lineno = 0
    try:
        with _open_binary(filepath) as stream:
            for raw, oversized, original_len in _read_limited_lines(
                stream, opts.max_line_bytes, budget
            ):
                lineno += 1
                if oversized:
                    diag.lines_oversized += 1
                    if opts.oversized_policy == "skip":
                        diag.record_file_error(
                            filepath,
                            f"line {lineno} oversized ({original_len} B) - skipped",
                            partial=True,
                        )
                        continue
                    if opts.oversized_policy == "fail":
                        diag.record_file_error(
                            filepath,
                            f"line {lineno} oversized ({original_len} B) - aborting file",
                            partial=True,
                        )
                        return
                    # truncate: fall through, analyse the truncated prefix
                text, had_error = _decode(raw, encoding, opts, diag)
                if had_error and opts.errors == "strict":
                    diag.record_file_error(
                        filepath, f"decode error on line {lineno} (strict)",
                        partial=True,
                    )
                    return
                yielded = True
                yield text.strip()
    except (OSError, EOFError) as e:  # includes gzip.BadGzipFile
        log.warning("Error reading %s: %s", filepath, e)
        diag.record_file_error(filepath, str(e), partial=yielded)
        return
    diag.files_complete += 1


def _decode(
    raw: bytes, encoding: str, opts: ReaderOptions, diag: ScanDiagnostics,
) -> tuple[str, bool]:
    """Decode a raw line, updating diagnostics. Returns (text, had_error)."""
    base = "utf-8" if encoding == "utf-8-sig" else encoding
    if opts.errors == "strict":
        try:
            return raw.decode(base, errors="strict"), False
        except UnicodeDecodeError:
            diag.decode_errors += 1
            return raw.decode(base, errors="replace"), True
    text = raw.decode(base, errors=opts.errors)
    replaced = text.count("�")
    if replaced:
        diag.decode_errors += 1
        diag.replaced_chars += replaced
    return text, replaced > 0
