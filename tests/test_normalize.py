import pytest

from p2000_capcodes.normalize import normalize_capcode


def test_normalize_7_digit_capcode_to_multimon_9_digits() -> None:
    assert normalize_capcode("1123101") == "001123101"


def test_normalize_preserves_9_digit_capcode() -> None:
    assert normalize_capcode("001123101") == "001123101"


def test_invalid_capcode() -> None:
    with pytest.raises(ValueError):
        normalize_capcode("abc")
