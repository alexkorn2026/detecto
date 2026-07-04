"""Tokenization of log lines with JSON fragment detection."""
from __future__ import annotations

import json
import logging
import re

from detecto.constants import FIELD_SEPARATORS, FIELD_VALUE_LOOKAHEAD

__all__ = [
    "tokenize", "extract_json_fragments", "extract_json_values",
    "extract_json_pairs", "find_field_value", "split_inline_field",
]

log = logging.getLogger(__name__)

_SPLIT_RE = re.compile(r"[\s?&=,;|]+")
_TOKEN_RE = re.compile(r"[^\s?&=,;|]+")  # Inverse: match non-separator runs
_URL_PARAM_RE = re.compile(r"[?&](\w+=([^&\n]+))")
_CRED_IN_URL_RE = re.compile(r"://([^:/?#]+):(.+)@([^@:/?#]+)")
_JSON_DECODER = json.JSONDecoder()
_INLINE_KV_RE = re.compile(r"^(.*?)[:=](.+)$")


def split_inline_field(token: str) -> tuple[str, str] | None:
    """Split a key:value token (e.g. 'RVNR:65170839J008', '"password":"x"').

    The tokenizer does not split on ':', so field name and value can end
    up in the same token. Returns (name_part, value) or None.
    """
    m = _INLINE_KV_RE.match(token)
    if not m:
        return None
    name_part = m.group(1).strip("\"'{}[](),.;!? ")
    value = m.group(2).strip("\"'{}[](),.:;!?")
    if not name_part or not value:
        return None
    return name_part, value


def extract_json_values(obj: object) -> list[str]:
    """Recursively extract all string values from a JSON object."""
    if isinstance(obj, dict):
        return [v for val in obj.values() for v in extract_json_values(val)]
    if isinstance(obj, list):
        return [v for item in obj for v in extract_json_values(item)]
    if isinstance(obj, str):
        return [obj]
    return []


def extract_json_pairs(obj: object) -> list[tuple[str, str]]:
    """Recursively extract (key, value) pairs with scalar values from JSON.

    Needed so field detection keeps the key context: without pairs,
    {"password":"x"} with parse_json=true would only yield the value 'x'
    and the field name 'password' would be lost (false negative).
    """
    pairs: list[tuple[str, str]] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, (dict, list)):
                pairs.extend(extract_json_pairs(v))
            elif isinstance(v, str):
                if v:
                    pairs.append((str(k), v))
            elif isinstance(v, (int, float)) and not isinstance(v, bool):
                pairs.append((str(k), str(v)))
    elif isinstance(obj, list):
        for item in obj:
            pairs.extend(extract_json_pairs(item))
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
        if "?" in line or "&" in line:
            for m in _URL_PARAM_RE.finditer(line):
                val = m.group(2).strip()
                if val and val not in result:
                    result.append(val)
        if "://" in line:
            for m in _CRED_IN_URL_RE.finditer(line):
                user, password = m.group(1), m.group(2)
                if user and user not in result:
                    result.append(user)
                if password and password not in result:
                    result.append(password)
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

        # URL parameters (only if query string indicators present)
        if "?" in text or "&" in text:
            for m in _URL_PARAM_RE.finditer(text):
                val = m.group(2).strip()
                if val and val not in result:
                    result.append(val)
        # Credentials embedded in URLs (only if protocol present)
        if "://" in text:
            for m in _CRED_IN_URL_RE.finditer(text):
                user, password = m.group(1), m.group(2)
                if user and user not in result:
                    result.append(user)
                if password and password not in result:
                    result.append(password)
                log.debug("URL credentials extracted: user=%s", user)

    # Synthetic key:value tokens keep the JSON key context for field
    # detection (inline split handles them like 'password:Secret123').
    for k, v in json_pairs:
        kv = f"{k}:{v}"
        if kv not in result:
            result.append(kv)

    return result
