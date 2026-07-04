"""Findings 11-17: validators for CC/IBAN/SteuerID/JWT/private key/street.

Only synthetic test data is used - no real personal identifiers.
"""
from __future__ import annotations

import base64
import json

import pytest

from detecto.validators import (
    credit_card_valid,
    iban_valid,
    jwt_structure_valid,
    luhn_valid,
    private_key_status,
    steuer_id_valid,
    street_status,
)

# --- Finding 11: credit card / Luhn ---------------------------------------

@pytest.mark.parametrize("card", ["4111 1111 1111 1111", "4111-1111-1111-1111",
                                  "5500005555555559", "340000000000009"])
def test_valid_cards(card):
    assert credit_card_valid(card)


@pytest.mark.parametrize("card", ["4111111111111112", "1234567890123456",
                                  "12345", "abcd"])
def test_invalid_cards(card):
    assert not credit_card_valid(card)


def test_luhn_basic():
    assert luhn_valid("79927398713")
    assert not luhn_valid("79927398714")


# --- Finding 12: IBAN ------------------------------------------------------

@pytest.mark.parametrize("iban", ["DE89 3704 0044 0532 0130 00",
                                  "GB82 WEST 1234 5698 7654 32"])
def test_valid_iban(iban):
    assert iban_valid(iban)


@pytest.mark.parametrize("iban", ["DE00 3704 0044 0532 0130 00",
                                  "DE89 3704 0044 0532 0130",  # wrong length
                                  "XX00 1234"])
def test_invalid_iban(iban):
    assert not iban_valid(iban)


# --- Finding 13: German tax ID --------------------------------------------

def test_valid_steuer_id():
    assert steuer_id_valid("86095742719")  # synthetic, valid checksum


@pytest.mark.parametrize("sid", ["12345678901",   # bad distribution/checksum
                                  "11111111111",   # too many repeats
                                  "00000000000",   # leading zero
                                  "8609574271",     # too short
                                  "8609574271A"])   # non-digit
def test_invalid_steuer_id(sid):
    assert not steuer_id_valid(sid)


# --- Finding 16: JWT structure --------------------------------------------

def _jwt(header, payload, sig="sig"):
    def enc(o):
        return base64.urlsafe_b64encode(json.dumps(o).encode()).rstrip(b"=").decode()
    return f"{enc(header)}.{enc(payload)}.{sig}"


def test_valid_jwt_structure():
    assert jwt_structure_valid(_jwt({"alg": "HS256"}, {"sub": "1"}))


@pytest.mark.parametrize("tok", [
    "a.b",                                   # two segments
    "a.b.c.d",                               # four segments
    "notbase64!.notbase64!.sig",             # invalid base64/JSON
])
def test_invalid_jwt_structure(tok):
    assert not jwt_structure_valid(tok)


def test_jwt_header_without_json():
    # valid base64 but not JSON
    seg = base64.urlsafe_b64encode(b"hello").rstrip(b"=").decode()
    assert not jwt_structure_valid(f"{seg}.{seg}.sig")


def test_oversized_jwt_rejected():
    huge = "e" * 20000
    assert not jwt_structure_valid(f"{huge}.{huge}.{huge}")


# --- Finding 17: private key completeness ---------------------------------

def test_complete_private_key():
    pem = "-----BEGIN RSA PRIVATE KEY-----\n" + ("A" * 64 + "\n") * 3 + \
          "-----END RSA PRIVATE KEY-----"
    assert private_key_status(pem) == "complete"


def test_header_only_is_not_complete():
    assert private_key_status("-----BEGIN RSA PRIVATE KEY-----") == "header_only"


def test_no_key():
    assert private_key_status("just a normal log line") == "none"


@pytest.mark.parametrize("ktype", ["PRIVATE KEY", "EC PRIVATE KEY",
                                   "OPENSSH PRIVATE KEY"])
def test_various_key_types(ktype):
    pem = f"-----BEGIN {ktype}-----\n" + "QUJD" * 20 + f"\n-----END {ktype}-----"
    assert private_key_status(pem) == "complete"


# --- Finding 14: street context -------------------------------------------

def test_street_drop_false_positives():
    for word in ["Speicherplatz", "Arbeitsplatz", "Fluchtweg", "Lösungsweg"]:
        assert street_status(word, word) == "drop"


def test_street_high_with_number_or_field():
    assert street_status("Hauptstraße", "Hauptstraße 12") == "high"
    assert street_status("Rheinufer", "Rheinufer 5") == "high"
    assert street_status("Bahnhofstraße", "street=Bahnhofstraße") == "high"


def test_street_low_without_context():
    assert street_status("Hauptstraße", "Hauptstraße") == "low"
