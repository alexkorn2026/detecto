"""Tokenization of log lines with JSON fragment detection."""
from __future__ import annotations

import json
import logging
import re
from urllib.parse import unquote, urlsplit

from detecto.constants import (
    FIELD_SEPARATORS,
    FIELD_VALUE_LOOKAHEAD,
    MAX_JSON_DEPTH,
    MAX_JSON_VALUES_PER_LINE,
)

__all__ = [
    "tokenize", "extract_json_fragments", "extract_json_values",
    "extract_json_pairs", "find_field_value", "split_inline_field",
    "extract_url_tokens",
]

log = logging.getLogger(__name__)

_SPLIT_RE = re.compile(r"[\s?&=,;|]+")
_TOKEN_RE = re.compile(r"[^\s?&=,;|]+")  # Inverse: match non-separator runs
# Finding 9: query parameter names may contain '-', '.', '_' and '[...]'.
# The value runs to the next '&'/'#'/newline so space-containing raw log values
# stay intact (Finding 9 point 11).
_QUERY_RE = re.compile(r"[?&]([\w.\-\[\]]+)=([^&\n#]+)")
# Candidate absolute URL (scheme://...). urlsplit does the structured parsing.
_URL_RE = re.compile(r"[A-Za-z][A-Za-z0-9+.\-]*://[^\s]+")
_JSON_DECODER = json.JSONDecoder()
# Key must be a plausible identifier (no embedded ':'/'='), so URLs, JDBC
# strings, IPv6 literals and timestamps are not mis-split (Finding 9).
# Optional wrapper chars (quotes/braces) around the key are tolerated so
# JSON-style '"password":"x"' still splits.
_INLINE_KV_RE = re.compile(r"""^[\s"'{[(]*([\w.\-]{1,60})[\s"'}\])]*([:=])(.+)$""")


def split_inline_field(token: str) -> tuple[str, str] | None:
    """Split a ``key:value`` / ``key=value`` token into (name, value).

    The tokenizer does not split on ':', so a field name and its value can end
    up in the same token (e.g. 'RVNR:65170839J008', '"password":"x"'). Only a
    *plausible* field name (identifier characters, no further ':' / '=') is
    accepted, so URLs, JDBC connection strings, IPv6 literals and 'HH:MM:SS'
    timestamps are not treated as fields (Finding 9). Returns (name, value) or
    ``None``.
    """
    # Never treat a URL / JDBC connection string as a key:value field.
    if "://" in token:
        return None
    m = _INLINE_KV_RE.match(token)
    if not m:
        return None
    sep = m.group(2)
    name_part = m.group(1).strip("\"'{}[](),.;!? ")
    value = m.group(3).strip("\"'{}[](),.:;!?")
    if not name_part or not value:
        return None
    # A colon-separated pair whose key is purely numeric and whose value still
    # contains ':' is almost certainly a time/IPv6 fragment, not a field.
    if sep == ":" and name_part.isdigit() and ":" in value:
        return None
    return name_part, value


def extract_json_values(obj: object, _depth: int = 0) -> list[str]:
    """Recursively extract all string values from a JSON object.

    Bounded by MAX_JSON_DEPTH and MAX_JSON_VALUES_PER_LINE (Finding 10) to
    prevent pathological nesting or huge arrays from exhausting resources.
    """
    if _depth > MAX_JSON_DEPTH:
        return []
    out: list[str] = []
    if isinstance(obj, dict):
        for val in obj.values():
            out.extend(extract_json_values(val, _depth + 1))
            if len(out) >= MAX_JSON_VALUES_PER_LINE:
                return out[:MAX_JSON_VALUES_PER_LINE]
    elif isinstance(obj, list):
        for item in obj:
            out.extend(extract_json_values(item, _depth + 1))
            if len(out) >= MAX_JSON_VALUES_PER_LINE:
                return out[:MAX_JSON_VALUES_PER_LINE]
    elif isinstance(obj, str):
        out.append(obj)
    return out


def extract_json_pairs(obj: object) -> list[tuple[str, str]]:
    """Recursively extract (key, value) pairs with scalar values from JSON.

    Needed so field detection keeps the key context: without pairs,
    {"password":"x"} with parse_json=true would only yield the value 'x'
    and the field name 'password' would be lost (false negative).
    """
    return _extract_json_pairs(obj, 0)


def _extract_json_pairs(obj: object, depth: int) -> list[tuple[str, str]]:
    if depth > MAX_JSON_DEPTH:
        return []
    pairs: list[tuple[str, str]] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, (dict, list)):
                pairs.extend(_extract_json_pairs(v, depth + 1))
            elif isinstance(v, str):
                if v:
                    pairs.append((str(k), v))
            elif isinstance(v, (int, float)) and not isinstance(v, bool):
                pairs.append((str(k), str(v)))
            if len(pairs) >= MAX_JSON_VALUES_PER_LINE:
                return pairs[:MAX_JSON_VALUES_PER_LINE]
    elif isinstance(obj, list):
        for item in obj:
            pairs.extend(_extract_json_pairs(item, depth + 1))
            if len(pairs) >= MAX_JSON_VALUES_PER_LINE:
                return pairs[:MAX_JSON_VALUES_PER_LINE]
    return pairs


def extract_json_fragments(text: str) -> list[tuple[str, int, int]]:
    """Extract embedded JSON objects from text.

    Uses json.JSONDecoder.raw_decode for valid JSON,
    bracket-balancing as fallback for non-standard fragments.
    Returns list of (json_string, start_pos, end_pos).
    """
    fragments: list[tuple[str, int, int]] = []
    i = 0
    while i < len(text):
        if text[i] != "{":
            i += 1
            continue
        try:
            _, end_pos = _JSON_DECODER.raw_decode(text, i)
            fragments.append((text[i:end_pos], i, end_pos))
            log.debug("JSON via raw_decode: pos %d-%d", i, end_pos)
            i = end_pos
            continue
        except (json.JSONDecodeError, ValueError):
            pass
        end = _bracket_balance(text, i)
        if end > i:
            fragments.append((text[i:end], i, end))
            log.debug("JSON via bracket-balancing: pos %d-%d", i, end)
            i = end
        else:
            i += 1
    return fragments


def _bracket_balance(text: str, start: int) -> int:
    """Find the end of a balanced {...} block. Returns end+1 or start if unbalanced."""
    depth, in_str, esc = 0, False, False
    for j in range(start, len(text)):
        ch = text[j]
        if esc:
            esc = False
            continue
        if ch == "\\" and in_str:
            esc = True
            continue
        if ch == '"' and not esc:
            in_str = not in_str
            continue
        if in_str:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return j + 1
    return start


def extract_url_tokens(text: str) -> list[str]:
    """Extract userinfo and query-parameter values from URLs in ``text``.

    Uses :func:`urllib.parse.urlsplit` for structured parsing (handles IPv6
    hosts like ``[2001:db8::1]`` and userinfo without greedy regex groups) and
    percent-decodes each value exactly once - no unbounded recursive decoding
    (Finding 9). Query parameter names may contain ``-``, ``.``, ``_`` and
    ``[...]``.
    """
    out: list[str] = []

    def _add(value: str | None) -> None:
        if value:
            decoded = unquote(value)  # single controlled percent-decode
            if decoded:
                out.append(decoded)
            if decoded != value:
                out.append(value)  # keep the raw form too

    if "://" in text:
        for m in _URL_RE.finditer(text):
            url = m.group(0).rstrip(".,;)]}\"'>")
            try:
                parts = urlsplit(url)
            except ValueError:
                continue
            _add(parts.username)
            _add(parts.password)

    if "?" in text or "&" in text:
        for m in _QUERY_RE.finditer(text):
            _add(m.group(2).strip())

    return out


def find_field_value(
    tokens: list[str], start_pos: int,
) -> tuple[str | None, str | None]:
    """Find the actual value after a field match, skipping separators.

    Looks ahead up to 3 tokens, skipping separators (->  =>  :  = etc.)
    and empty wrapper tokens.

    Returns:
        (cleaned_value, original_token) or (None, None).
    """
    max_pos = min(start_pos + FIELD_VALUE_LOOKAHEAD, len(tokens))
    for j in range(start_pos, max_pos):
        candidate = tokens[j]
        if candidate in FIELD_SEPARATORS:
            continue
        cleaned = candidate.strip("\"'{}[](),.:;!?")
        if not cleaned:
            continue
        return cleaned, candidate
    return None, None


def tokenize(line: str, parse_json: bool = True) -> list[str]:
    """Split a log line into tokens.

    Args:
        line: The log line to tokenize.
        parse_json: If False, skip JSON parsing for faster processing.
            Only set to True if logs contain embedded JSON fragments.
    """
    # Fast path: no JSON parsing needed
    if not parse_json:
        result = _TOKEN_RE.findall(line)
        for val in extract_url_tokens(line):
            if val not in result:
                result.append(val)
        return result

    text_parts = [line]
    json_pairs: list[tuple[str, str]] = []
    if line.startswith("{"):
        try:
            json_obj = json.loads(line)
            text_parts = extract_json_values(json_obj)
            json_pairs = extract_json_pairs(json_obj)
            log.debug("JSON log line: %d text parts extracted", len(text_parts))
        except (json.JSONDecodeError, ValueError):
            pass

    result: list[str] = []
    _findall = _TOKEN_RE.findall
    for text in text_parts:
        # Pre-check: only search for JSON fragments if '{' is present
        fragments = extract_json_fragments(text) if "{" in text else []
        if fragments:
            last_end = 0
            for frag_text, frag_start, frag_end in fragments:
                before = text[last_end:frag_start]
                if before.strip():
                    result.extend(_findall(before))
                result.append(frag_text)
                try:
                    obj = json.loads(frag_text)
                    for val in extract_json_values(obj):
                        result.extend(_findall(val))
                    json_pairs.extend(extract_json_pairs(obj))
                except (json.JSONDecodeError, ValueError):
                    result.extend(_findall(frag_text))
                last_end = frag_end
            rest = text[last_end:]
            if rest.strip():
                result.extend(_findall(rest))
        else:
            result.extend(_findall(text))

        # URL userinfo + query values (urllib-based, single-decode) - Finding 9
        for val in extract_url_tokens(text):
            if val not in result:
                result.append(val)

    # Synthetic key:value tokens keep the JSON key context for field
    # detection (inline split handles them like 'password:Secret123').
    for k, v in json_pairs:
        kv = f"{k}:{v}"
        if kv not in result:
            result.append(kv)

    return result
