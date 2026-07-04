"""Utility functions: text normalization, file finder, criticality color."""
from __future__ import annotations

import functools
import glob
import os
import unicodedata

from detecto.constants import ANSI_RED, ANSI_RESET, ANSI_YELLOW, NORMALIZE_CACHE_SIZE

__all__ = ["normalize", "normalize_with_offsets", "find_logfiles", "krit_color"]


def krit_color(level: int) -> str:
    """Return the ANSI color code for a criticality level (1-5)."""
    if level <= 2:
        return ANSI_RED
    if level == 3:
        return ANSI_YELLOW
    return ANSI_RESET


@functools.lru_cache(maxsize=NORMALIZE_CACHE_SIZE)
def normalize(text: str) -> str:
    """Normalize text: lowercase, remove umlauts/accents, convert ß to ss.

    Results are cached (LRU, 100k entries) for performance with repetitive tokens.
    Uses ASCII fast-path to skip expensive NFD decomposition for ~80% of tokens.
    """
    lower = text.lower()
    # Fast path: pure ASCII — no accent processing needed (~80% of log tokens)
    if lower.isascii():
        return lower
    # Slow path: handle ß, umlauts, accents via NFD decomposition
    lower = lower.replace("\u00df", "ss")
    lower = unicodedata.normalize("NFD", lower)
    return "".join(c for c in lower if unicodedata.category(c) != "Mn")


def normalize_with_offsets(text: str) -> tuple[str, list[int]]:
    """Normalize text and return (normalized, offsets).

    ``offsets[i]`` is the index in the *original* ``text`` of the character
    that produced ``normalized[i]``. This lets callers map a match position in
    the normalized string back to the original substring even when
    normalization changes the length (Finding 7): ``ß`` -> ``ss`` (1->2) and
    accent stripping (2->1). Combining marks are dropped and contribute no
    normalized character.
    """
    norm_chars: list[str] = []
    offsets: list[int] = []
    for orig_idx, ch in enumerate(text):
        lower = ch.lower()
        if lower.isascii():
            for c in lower:
                norm_chars.append(c)
                offsets.append(orig_idx)
            continue
        lower = lower.replace("ß", "ss")
        decomposed = unicodedata.normalize("NFD", lower)
        for c in decomposed:
            if unicodedata.category(c) == "Mn":
                continue
            norm_chars.append(c)
            offsets.append(orig_idx)
    return "".join(norm_chars), offsets


def find_logfiles(pattern: str) -> list[str]:
    """Find log files matching a glob pattern."""
    return [p for p in glob.glob(pattern) if os.path.isfile(p)]
