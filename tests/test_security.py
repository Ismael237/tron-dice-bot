from decimal import Decimal
import base64

import pytest
from hypothesis import given, strategies as st

from utils import encryption as enc
from utils.validators import is_valid_tron_address, is_valid_amount
from utils.helpers import escape_markdown_v2


# --- Encryption roundtrip (bytes) --------------------------------------------
@given(data=st.binary(min_size=0, max_size=256))
def test_encrypt_decrypt_bytes_roundtrip(data):
    token = enc.encrypt_data(data)
    assert isinstance(token, str)
    out = enc.decrypt_data(token)
    assert out == data


# --- Encryption roundtrip (text) ---------------------------------------------
@given(text=st.text(max_size=128))
def test_encrypt_decrypt_text_roundtrip(text):
    token = enc.encrypt_text(text)
    assert isinstance(token, str)
    out = enc.decrypt_text(token)
    assert out == text


# --- Validators ---------------------------------------------------------------
@pytest.mark.parametrize(
    "addr,ok",
    [
        ("T9yD14Nj9j7xAB4dbGeiX9h8unkKHxuWwb", True),  # example valid base58-like
        ("T123456789012345678901234567890123", False),  # contains '0' which is excluded in Base58 regex
        ("D123456789012345678901234567890123", False),  # wrong prefix
        ("T0_________________________________", False),  # contains invalid chars
        ("TtooShort", False),
    ],
)
def test_tron_address_regex(addr, ok):
    assert is_valid_tron_address(addr) is ok


@pytest.mark.parametrize(
    "amount,minv,ok",
    [
        (1, 0, True),
        (0.0, 0, True),
        (-1, 0, False),
        ("notnum", 0, False),
        (1.5, 2, False),
    ],
)
def test_is_valid_amount(amount, minv, ok):
    assert is_valid_amount(amount, minv) is ok


# --- MarkdownV2 escaping ------------------------------------------------------
@given(text=st.text(max_size=120))
def test_escape_markdown_v2_idempotent(text):
    once = escape_markdown_v2(text)
    twice = escape_markdown_v2(once)
    assert once == twice


@given(text=st.text(alphabet="\\`*_[]()~>#+=|{}.!-abcXYZ0123456789 ", max_size=80))
def test_escape_markdown_v2_contains_no_raw_control_chars(text):
    escaped = escape_markdown_v2(text)
    special = set("\\`*_[]()~>#+=|{}.!-")
    i = 0
    while i < len(escaped):
        ch = escaped[i]
        if ch in special:
            assert i > 0 and escaped[i - 1] == "\\"
        i += 1
