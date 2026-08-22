import json
import sqlite3
from pathlib import Path

from p2000_capcodes.abbreviations import parse_abbreviation_tables
from p2000_capcodes.export import (
    export_abbreviations_csv,
    export_abbreviations_json,
    export_sqlite,
)
from p2000_capcodes.models import MergedRecord, SourceRecord
from p2000_capcodes.sources.tomzulu_abbreviations import TomZuluAbbreviationsSource

FIXTURES = Path(__file__).parent / "fixtures" / "tomzulu_abbreviations"


def test_parse_google_sheet_style_abbreviation_table() -> None:
    html = (FIXTURES / "page1-frame.html").read_text()
    records = parse_abbreviation_tables(
        html,
        source="tomzulu_abbreviations",
        source_url="https://example.invalid/sheet",
        category="Hulpdiensten",
    )
    assert records[0].abbreviation == "TS"
    assert records[0].meaning == "Tankautospuit"
    assert records[0].notes == "Brandweer"
    assert records[1].abbreviation == "OvD"


def test_tomzulu_abbreviation_source_deduplicates() -> None:
    records = TomZuluAbbreviationsSource(fixtures_dir=FIXTURES).load()
    assert [(record.abbreviation, record.meaning) for record in records] == [
        ("KHV", "Kusthulpverleningsvoertuig"),
        ("OvD", "Officier van Dienst"),
        ("RWC", "Rescue Water Craft"),
        ("TS", "Tankautospuit"),
    ]
    assert records[0].category == "Kustwacht/KNRM/Reddingsbrigade"


def test_abbreviation_exports_and_sqlite(tmp_path: Path) -> None:
    abbreviations = TomZuluAbbreviationsSource(fixtures_dir=FIXTURES).load()
    csv_path = tmp_path / "abbreviations.csv"
    json_path = tmp_path / "abbreviations.json"
    db_path = tmp_path / "capcodes.sqlite3"

    export_abbreviations_csv(abbreviations, csv_path)
    export_abbreviations_json(abbreviations, json_path)
    export_sqlite(
        [MergedRecord(capcode="001234567", discipline="Brandweer")],
        [SourceRecord(capcode="001234567", source="test")],
        db_path,
        abbreviations=abbreviations,
    )

    payload = json.loads(json_path.read_text())
    assert payload["record_count"] == 4
    assert "Tankautospuit" in csv_path.read_text()

    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT meaning, category FROM abbreviations WHERE abbreviation = ?",
            ("TS",),
        ).fetchone()
    finally:
        conn.close()
    assert row == ("Tankautospuit", "Hulpdiensten")
