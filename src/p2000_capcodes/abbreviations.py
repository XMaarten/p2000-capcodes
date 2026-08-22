from __future__ import annotations

import json
from pathlib import Path

from bs4 import BeautifulSoup

from p2000_capcodes.models import AbbreviationRecord
from p2000_capcodes.normalize import clean

HEADER_ABBREVIATIONS = {
    "afkorting",
    "afkortingen",
    "afk",
    "code",
    "term",
}
HEADER_MEANINGS = {
    "betekenis",
    "omschrijving",
    "uitleg",
    "beschrijving",
    "description",
}
HEADER_NOTES = {
    "opmerking",
    "opmerkingen",
    "toelichting",
    "notes",
}


def _key(value: str) -> str:
    return " ".join(clean(value).casefold().replace("-", " ").replace("_", " ").split())


def _looks_like_abbreviation(value: str) -> bool:
    value = clean(value)
    if not value or len(value) > 40:
        return False
    if _key(value) in HEADER_ABBREVIATIONS | HEADER_MEANINGS | HEADER_NOTES:
        return False
    if value.isdigit():
        return False
    return any(character.isalpha() for character in value)


def _strip_row_number(cells: list[str]) -> list[str]:
    if len(cells) >= 3 and cells[0].strip().isdigit():
        return cells[1:]
    return cells


def _header_mapping(cells: list[str]) -> dict[str, int]:
    mapping: dict[str, int] = {}
    for index, cell in enumerate(cells):
        normalized = _key(cell)
        if normalized in HEADER_ABBREVIATIONS:
            mapping["abbreviation"] = index
        elif normalized in HEADER_MEANINGS:
            mapping["meaning"] = index
        elif normalized in HEADER_NOTES:
            mapping["notes"] = index
    return mapping


def parse_abbreviation_tables(
    html: str,
    *,
    source: str,
    source_url: str,
    category: str,
    record_prefix: str = "row",
) -> list[AbbreviationRecord]:
    """Parse an abbreviation glossary from ordinary or Google Sheets HTML tables."""

    soup = BeautifulSoup(html, "html.parser")
    records: list[AbbreviationRecord] = []
    seen: set[tuple[str, str, str]] = set()

    for table_index, table in enumerate(soup.find_all("table"), 1):
        rows = table.find_all("tr")
        if not rows:
            continue

        mapping: dict[str, int] = {}
        for row_index, row in enumerate(rows, 1):
            cells = [clean(cell.get_text(" ", strip=True)) for cell in row.find_all(["td", "th"])]
            cells = _strip_row_number(cells)
            if not cells:
                continue

            possible_mapping = _header_mapping(cells)
            if "abbreviation" in possible_mapping and "meaning" in possible_mapping:
                mapping = possible_mapping
                continue

            if mapping:
                abbreviation_index = mapping["abbreviation"]
                meaning_index = mapping["meaning"]
                if abbreviation_index >= len(cells) or meaning_index >= len(cells):
                    continue
                abbreviation = clean(cells[abbreviation_index])
                meaning = clean(cells[meaning_index])
                notes_index = mapping.get("notes")
                notes = (
                    clean(cells[notes_index])
                    if notes_index is not None and notes_index < len(cells)
                    else ""
                )
            else:
                populated = [cell for cell in cells if cell]
                if len(populated) < 2:
                    continue
                abbreviation = populated[0]
                meaning = populated[1]
                notes = " | ".join(populated[2:])

            if not _looks_like_abbreviation(abbreviation) or not meaning:
                continue
            if _key(meaning) in HEADER_MEANINGS:
                continue

            signature = (abbreviation.casefold(), meaning.casefold(), category.casefold())
            if signature in seen:
                continue
            seen.add(signature)
            records.append(
                AbbreviationRecord(
                    abbreviation=abbreviation,
                    meaning=meaning,
                    source=source,
                    category=category,
                    notes=notes,
                    source_url=source_url,
                    source_record_id=f"{record_prefix}:{table_index}:{row_index}",
                    raw=tuple(cells),
                )
            )

    return records


def deduplicate_abbreviations(records: list[AbbreviationRecord]) -> list[AbbreviationRecord]:
    unique: dict[tuple[str, str, str], AbbreviationRecord] = {}
    for record in records:
        key = (
            record.abbreviation.casefold(),
            record.meaning.casefold(),
            record.category.casefold(),
        )
        unique.setdefault(key, record)
    return sorted(
        unique.values(),
        key=lambda record: (
            record.abbreviation.casefold(),
            record.category.casefold(),
            record.meaning.casefold(),
        ),
    )


def load_abbreviations_json(path: Path) -> list[AbbreviationRecord]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [
        AbbreviationRecord(
            abbreviation=item["abbreviation"],
            meaning=item["meaning"],
            source=item.get("source", ""),
            category=item.get("category", ""),
            notes=item.get("notes", ""),
            source_url=item.get("source_url", ""),
            source_record_id=item.get("source_record_id", ""),
            observed_at=item.get("observed_at", ""),
        )
        for item in payload.get("records", [])
    ]
