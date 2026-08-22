from __future__ import annotations

import re
import unicodedata


CAPCODE_DIGITS = 9


def normalize_capcode(value: str | int) -> str:
    digits = re.sub(r"\D", "", str(value))
    if not digits:
        raise ValueError(f"Invalid capcode: {value!r}")
    if len(digits) > CAPCODE_DIGITS:
        raise ValueError(f"Capcode has more than {CAPCODE_DIGITS} digits: {value!r}")
    return digits.zfill(CAPCODE_DIGITS)


def clean(value: object) -> str:
    if value is None:
        return ""
    return " ".join(str(value).replace("\xa0", " ").strip().split())


def comparable(value: str) -> str:
    value = unicodedata.normalize("NFKC", clean(value)).casefold()
    value = value.replace("&", "en")
    value = re.sub(r"[\s\-_./]+", " ", value)
    return value.strip()
