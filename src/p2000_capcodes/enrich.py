from __future__ import annotations

import re
from dataclasses import dataclass

from p2000_capcodes.models import SourceRecord
from p2000_capcodes.normalize import clean

SERVICE_ALIASES = {
    "brw": "Brandweer",
    "br": "Brandweer",
    "brandweer": "Brandweer",
    "ambu": "Ambulance",
    "amb": "Ambulance",
    "ambulance": "Ambulance",
    "pol": "Politie",
    "politie": "Politie",
    "ghor": "GHOR",
    "bevolkingszorg": "Bevolkingszorg",
    "reddingsbrigade": "Reddingsbrigade",
    "knrm": "KNRM",
    "kustwacht": "Kustwacht",
    "multidisciplinair": "Multidisciplinair",
    "defensie": "Defensie",
}

# Common Dutch emergency-service unit names. This is intentionally small; the
# generated abbreviations dataset remains the authoritative expansion source.
UNIT_NAME_TO_CODE = {
    "tankautospuit": "TS",
    "hoogwerker": "HW",
    "autoladder": "AL",
    "hulpverleningsvoertuig": "HV",
    "dienstauto": "DA",
    "dienstbus": "DB",
}

CALLSIGN_RE = re.compile(r"\b([A-Z]{1,6})[ -]?(\d{2,5}(?:-\d{1,4})?)\b", re.IGNORECASE)
PAREN_CALLSIGN_RE = re.compile(r"\(\s*([A-Z]{1,6}[ -]?\d{2,5}(?:-\d{1,4})?)\s*\)", re.IGNORECASE)
STATION_RE = re.compile(r"\b(?:kazerne|post)\s+([^(/|]+)", re.IGNORECASE)
BEZETTING_RE = re.compile(r"\bbezetting\s+([A-Z]{1,8})\b", re.IGNORECASE)
FULL_UNIT_RE = re.compile(
    r"\b(" + "|".join(re.escape(name) for name in UNIT_NAME_TO_CODE) + r")[ -]?(\d{2,5})?\b",
    re.IGNORECASE,
)
AMBULANCE_RE = re.compile(r"\bambulance[- ]?(\d{2,3}-\d{2,3})\b", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class DerivedFields:
    service: str = ""
    station: str = ""
    unit_type: str = ""
    unit_type_name: str = ""
    callsign: str = ""
    unit_number: str = ""


def normalize_service(value: str) -> str:
    cleaned = clean(value)
    if not cleaned:
        return ""
    return SERVICE_ALIASES.get(cleaned.casefold(), cleaned)


def _clean_callsign(value: str) -> str:
    value = clean(value).upper().replace(" ", "-")
    value = re.sub(r"-+", "-", value)
    return value


def derive_fields(record: SourceRecord) -> DerivedFields:
    service = normalize_service(record.discipline)
    station = clean(record.location)
    unit_type = ""
    unit_type_name = ""
    callsign = ""
    unit_number = ""

    text = " | ".join(
        part for part in (record.description, record.remark, record.location) if clean(part)
    )
    if not service:
        leading = re.match(r"^([A-Za-z]{2,6})\b", clean(record.description))
        if leading:
            service = normalize_service(leading.group(1))
            if service == leading.group(1):
                service = ""

    # TomZulu often describes a functional pager as "Bezetting TS".
    match = BEZETTING_RE.search(record.description)
    if match:
        unit_type = match.group(1).upper()

    # Capcodes.eu commonly includes "Kazerne <place>" and a callsign in parentheses.
    match = STATION_RE.search(record.description)
    if match:
        station = clean(match.group(1))

    match = PAREN_CALLSIGN_RE.search(record.description)
    if match:
        callsign = _clean_callsign(match.group(1))

    # A dedicated remark/roepnummer is stronger evidence than free text.
    if record.remark:
        remark_match = CALLSIGN_RE.search(record.remark)
        if remark_match:
            callsign = _clean_callsign(remark_match.group(0))

    # General callsign fallback, e.g. TS-3531.
    if not callsign:
        match = CALLSIGN_RE.search(text)
        if match:
            candidate = _clean_callsign(match.group(0))
            # Avoid treating obvious service abbreviations without a vehicle prefix as callsigns.
            if any(char.isalpha() for char in candidate):
                callsign = candidate

    if callsign:
        prefix = re.match(r"([A-Z]{1,8})", callsign)
        if prefix and not unit_type:
            unit_type = prefix.group(1)
    # Bommel often spells out the vehicle type, e.g. "Tankautospuit-612".
    match = FULL_UNIT_RE.search(record.description)
    if match:
        unit_type_name = clean(match.group(1)).title()
        unit_type = unit_type or UNIT_NAME_TO_CODE.get(match.group(1).casefold(), "")
        if match.group(2) and not unit_number:
            unit_number = match.group(2)

    match = AMBULANCE_RE.search(record.description)
    if match:
        unit_type_name = unit_type_name or "Ambulance"
        if not callsign:
            callsign = match.group(1)
        if not unit_number:
            unit_number = match.group(1)

    return DerivedFields(
        service=service,
        station=station,
        unit_type=unit_type,
        unit_type_name=unit_type_name,
        callsign=callsign,
        unit_number=unit_number,
    )
