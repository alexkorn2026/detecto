"""Utility functions: text normalization, file finder, criticality color."""
from __future__ import annotations

import functools
import glob
import os
import unicodedata

from detecto.constants import ANSI_RED, ANSI_YELLOW, ANSI_RESET, KRIT_LABELS, NORMALIZE_CACHE_SIZE

__all__ = ["normalize", "find_logfiles", "krit_color"]


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


def find_logfiles(pattern: str) -> list[str]:
    """Find log files matching a glob pattern."""
    return [p for p in glob.glob(pattern) if os.path.isfile(p)]
