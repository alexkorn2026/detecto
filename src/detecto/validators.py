"""Small, dependency-free validators used to confirm regex candidates.

These turn broad regex *candidate* matches into *validated* findings
(Findings 11-13, 16, 17). Each function is pure and side-effect free, so they
are trivially testable and safe to call in the hot analysis path.
"""
from __future__ import annotations

import base64
import binascii
import json
import re

__all__ = [
    "luhn_valid",
    "credit_card_valid",
    "iban_valid",
    "steuer_id_valid",
    "jwt_structure_valid",
    "private_key_status",
    "street_status",
]


# --- Finding 14: street context sensitivity --------------------------------

# Small, maintainable exclusion list of common technical false positives
# (not a giant blacklist). Compared in lowercased, ß->ss form.
_STREET_EXCLUDE = {
    "speicherplatz", "arbeitsplatz", "fluchtweg", "loesungsweg",
    "rettungsweg", "irrweg", "holzweg", "ausweg", "loesungswege",
}
# An explicit address *field* (key followed by ':' or '=') is strong context.
_ADDR_FIELD_RE = re.compile(
    r"(?i)\b(street|stra(?:ss|ß)e|address|adresse|anschrift)\s*[:=]"
)
# A house number anywhere on the line (crude but effective context signal).
_HOUSE_RE = re.compile(r"\b\d{1,4}\s?[a-z]?\b")


def street_status(value: str, line: str) -> str:
    """Classify a street-pattern candidate (Finding 14).

    Returns ``"drop"`` for known technical false positives, ``"high"`` when a
    house number or an explicit address field provides context, otherwise
    ``"low"`` (a bare street-suffix word is only a weak signal).
    """
    norm = value.strip().lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        norm = norm.replace(a, b)
    if norm in _STREET_EXCLUDE:
        return "drop"
    if _ADDR_FIELD_RE.search(line) or _HOUSE_RE.search(line):
        return "high"
    return "low"


# --- Finding 11: credit card (Luhn) ---------------------------------------

def luhn_valid(digits: str) -> bool:
    """Return True if a pure digit string passes the Luhn checksum."""
    if not digits or not digits.isdigit():
        return False
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = ord(ch) - 48
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def credit_card_valid(candidate: str) -> bool:
    """Validate a credit-card candidate: strip separators, length + Luhn."""
    cleaned = re.sub(r"[ \-]", "", candidate)
    if not cleaned.isdigit() or not (13 <= len(cleaned) <= 19):
        return False
    return luhn_valid(cleaned)


# --- Finding 12: IBAN (country length + mod 97) ---------------------------

# ISO 13616 IBAN length per country (common subset; unknown -> length only).
_IBAN_LENGTHS = {
    "DE": 22, "AT": 20, "CH": 21, "FR": 27, "GB": 22, "NL": 18, "BE": 16,
    "LU": 20, "IT": 27, "ES": 24, "PL": 28, "CZ": 24, "DK": 18, "SE": 24,
    "NO": 15, "FI": 18, "PT": 25, "IE": 22, "LI": 21, "SK": 24, "SI": 19,
    "EE": 20, "LV": 21, "LT": 20, "HU": 28, "HR": 21, "RO": 24, "BG": 22,
    "GR": 27, "CY": 28, "MT": 31, "IS": 26,
}


def iban_valid(candidate: str) -> bool:
    """Validate an IBAN: normalize, country length check, ISO 7064 mod 97."""
    iban = re.sub(r"\s", "", candidate).upper()
    if not re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]+", iban or ""):
        return False
    if not (15 <= len(iban) <= 34):
        return False
    country = iban[:2]
    expected = _IBAN_LENGTHS.get(country)
    if expected is not None and len(iban) != expected:
        return False
    # Move first four chars to the end, convert letters to numbers, mod 97.
    rearranged = iban[4:] + iban[:4]
    digits = "".join(
        str(ord(c) - 55) if c.isalpha() else c for c in rearranged
    )
    try:
        return int(digits) % 97 == 1
    except ValueError:  # pragma: no cover - guarded by the regex above
        return False


# --- Finding 13: German tax ID (Steuer-IdNr) ------------------------------

def steuer_id_valid(candidate: str) -> bool:
    """Validate a German tax identification number (11 digits, ISO 7064 MOD 11,10).

    Checks: exactly 11 digits, leading digit non-zero, the distribution rule
    (exactly one digit repeated in the first ten), and the check digit.
    """
    s = candidate.strip()
    if not s.isdigit() or len(s) != 11 or s[0] == "0":
        return False

    first_ten = s[:10]
    counts: dict[str, int] = {}
    for ch in first_ten:
        counts[ch] = counts.get(ch, 0) + 1
    repeated = [d for d, c in counts.items() if c >= 2]
    # Exactly one digit repeats; it may appear 2 or 3 times (post-2016 rule).
    if len(repeated) != 1 or counts[repeated[0]] > 3:
        return False

    # ISO/IEC 7064 MOD 11,10 check digit over the first ten digits.
    product = 10
    for ch in first_ten:
        s_ = (int(ch) + product) % 10
        if s_ == 0:
            s_ = 10
        product = (s_ * 2) % 11
    check = (11 - product) % 10
    return check == int(s[10])


# --- Finding 16: JWT structure ---------------------------------------------

_MAX_JWT_SEGMENT = 8192  # guard against pathological tokens (DoS)


def _b64url_json(segment: str) -> object | None:
    """Base64URL-decode a JWT segment and parse it as JSON, or return None."""
    if not segment or len(segment) > _MAX_JWT_SEGMENT:
        return None
    padding = "=" * (-len(segment) % 4)
    try:
        raw = base64.urlsafe_b64decode(segment + padding)
        return json.loads(raw.decode("utf-8"))
    except (binascii.Error, ValueError, UnicodeDecodeError):
        return None


def jwt_structure_valid(candidate: str) -> bool:
    """Validate JWT *structure* only (no signature verification, Finding 16).

    Requires exactly three Base64URL segments whose header and payload both
    decode to JSON objects. This confirms a well-formed JWT structure, not a
    trusted or verified token.
    """
    parts = candidate.split(".")
    if len(parts) != 3:
        return False
    header = _b64url_json(parts[0])
    payload = _b64url_json(parts[1])
    if not isinstance(header, dict) or not isinstance(payload, dict):
        return False
    # Signature segment must be non-empty Base64URL (not decoded/verified).
    if not parts[2] or len(parts[2]) > _MAX_JWT_SEGMENT:
        return False
    return True


# --- Finding 17: private key completeness ----------------------------------

_PEM_BEGIN = re.compile(
    r"-----BEGIN (?P<type>[A-Z0-9 ]*PRIVATE KEY)-----", re.IGNORECASE
)


def private_key_status(text: str) -> str:
    """Classify a PEM private-key occurrence (Finding 17).

    Returns one of:
      - ``"complete"``      : matching BEGIN/END plus plausible base64 body
      - ``"incomplete"``    : a BEGIN header but no matching END / body
      - ``"header_only"``   : only a header mention, no block
      - ``"none"``          : no private-key header at all
    """
    m = _PEM_BEGIN.search(text)
    if not m:
        return "none"
    key_type = m.group("type").upper().strip()
    end_re = re.compile(
        r"-----END " + re.escape(key_type) + r"-----", re.IGNORECASE
    )
    end = end_re.search(text, m.end())
    if not end:
        return "header_only"
    body = text[m.end():end.start()]
    # Plausible base64 body between header and footer.
    b64 = re.sub(r"\s+", "", body)
    if len(b64) >= 32 and re.fullmatch(r"[A-Za-z0-9+/=]+", b64 or ""):
        return "complete"
    return "incomplete"
