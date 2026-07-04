"""Anonymization: Anonymizer class with configurable pattern."""
from __future__ import annotations

from detecto.config import ANON_PATTERN_DEFAULT

__all__ = ["Anonymizer"]


class Anonymizer:
    """Redacts strings using a configurable character pattern.

    Pattern syntax:
        s = keep original character
        * or x = replace with asterisk
        <redacted> = replace entire string
    """

    def __init__(self, pattern: str = ANON_PATTERN_DEFAULT) -> None:
        self._pattern_str = pattern
        self._groups = self._parse(pattern)

    @staticmethod
    def _parse(pattern: str) -> list[tuple[str, int]] | None:
        """Parse pattern into list of (type, length) tuples. None means <redacted>."""
        if pattern.strip().lower() == "<redacted>":
            return None
        groups: list[tuple[str, int]] = []
        i = 0
        while i < len(pattern):
            ch = pattern[i]
            if ch == "s":
                count = 0
                while i < len(pattern) and pattern[i] == "s":
                    count += 1
                    i += 1
                groups.append(("s", count))
            elif ch in ("*", "x"):
                count = 0
                while i < len(pattern) and pattern[i] in ("*", "x"):
                    count += 1
                    i += 1
                groups.append(("*", count))
            else:
                i += 1
        if not groups:
            return Anonymizer._parse(ANON_PATTERN_DEFAULT)
        return groups

    def redact(self, text: str) -> str:
        """Redact a string according to the configured pattern."""
        if not self._groups:
            return "<redacted>"
        # Short values would stay (almost) fully readable when the pattern
        # starts with a keep-group (e.g. 'sss**...' + 'Anna' -> 'Ann*').
        # Mask them completely instead.
        if self._groups[0][0] == "s" and len(text) <= self._groups[0][1] + 1:
            return "*" * len(text)
        parts: list[str] = []
        i, g = 0, 0
        while i < len(text):
            kind, length = self._groups[g % len(self._groups)]
            if kind == "s":
                parts.append(text[i : i + length])
                i += length
            else:
                remaining = min(length, len(text) - i)
                parts.append("*" * remaining)
                i += remaining
            g += 1
        return "".join(parts)[: len(text)]
