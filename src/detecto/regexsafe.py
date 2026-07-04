"""Safe regular-expression compilation and matching with runtime timeouts.

Finding 1: the previous ``_safe_compile`` only ran each pattern *once* against
a fixed test string at load time. That does not protect against catastrophic
backtracking triggered by real log lines during the scan.

This module prefers the third-party :mod:`regex` package, whose ``search`` /
``finditer`` / ``match`` accept a ``timeout`` argument enforced *while the
match runs*. If :mod:`regex` is not installed we transparently fall back to the
standard library :mod:`re`; in that case runtime timeouts are unavailable and a
warning is emitted, but Detecto keeps working (the load-time compile check
still runs as a first line of defence).
"""
from __future__ import annotations

import logging
import re
from typing import Any, Iterator

log = logging.getLogger(__name__)

try:  # pragma: no cover - exercised indirectly
    import regex as _regex

    HAS_REGEX = True
    _REGEX_PATTERN_TYPE: type | None = type(_regex.compile(""))
except ImportError:  # pragma: no cover
    _regex = None  # type: ignore[assignment]
    HAS_REGEX = False
    _REGEX_PATTERN_TYPE = None


def _supports_timeout(compiled: object) -> bool:
    """True only for compiled patterns that accept a ``timeout=`` argument.

    A stdlib :mod:`re` pattern (e.g. from a test fixture) does not, so we must
    check the concrete pattern object rather than the global ``HAS_REGEX``.
    """
    return _REGEX_PATTERN_TYPE is not None and isinstance(
        compiled, _REGEX_PATTERN_TYPE
    )

__all__ = [
    "HAS_REGEX",
    "RegexTimeout",
    "compile_pattern",
    "safe_search",
    "safe_finditer",
]


class RegexTimeout(Exception):
    """Raised when a regex operation exceeds its runtime budget."""


def compile_pattern(pattern: str) -> Any:
    """Compile ``pattern`` with the timeout-capable engine when available.

    Raises ``re.error`` (or ``regex.error``, a subclass-compatible error) on an
    invalid pattern, so callers can handle it exactly as before.
    """
    try:
        if HAS_REGEX:
            # VERSION0 keeps behaviour compatible with the ``re`` module.
            return _regex.compile(pattern, flags=_regex.VERSION0)
        return re.compile(pattern)
    except re.error:
        raise
    except Exception as exc:  # normalise regex.error -> re.error for callers
        raise re.error(str(exc)) from exc


def safe_search(compiled: Any, text: str, timeout_ms: int) -> Any:
    """Run ``compiled.search(text)`` with a runtime timeout.

    Returns the match object or ``None``. Raises :class:`RegexTimeout` if the
    engine supports timeouts and the budget is exceeded.
    """
    if timeout_ms > 0 and _supports_timeout(compiled):
        try:
            return compiled.search(text, timeout=timeout_ms / 1000.0)
        except TimeoutError as exc:  # regex raises builtin TimeoutError
            raise RegexTimeout() from exc
    return compiled.search(text)


def safe_finditer(compiled: Any, text: str, timeout_ms: int) -> Iterator[Any]:
    """Materialise ``compiled.finditer(text)`` under a runtime timeout.

    Returns a *list* (not a lazy iterator) so the timeout is fully enforced
    before the caller processes any match. Raises :class:`RegexTimeout` on
    timeout.
    """
    if timeout_ms > 0 and _supports_timeout(compiled):
        try:
            return list(compiled.finditer(text, timeout=timeout_ms / 1000.0))
        except TimeoutError as exc:
            raise RegexTimeout() from exc
    return list(compiled.finditer(text))
