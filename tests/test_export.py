import sqlite3
from pathlib import Path

from p2000_capcodes.export import export_sqlite
from p2000_capcodes.merge import merge_records
from p2000_capcodes.models import SourceRecord


def test_sqlite_is_addon_compatible(tmp_path: Path) -> None:
    source = SourceRecord(
        capcode="001123101",
        source="manual",
        discipline="Ambulance",
        region="Brabant-Zuidoost",
        location="Eindhoven",
        description="Ambulance 22-101",
    )
    records = merge_records([source]).records
    db = tmp_path / "capcodes.sqlite3"
    export_sqlite(records, [source], db)
    conn = sqlite3.connect(db)
    try:
        row = conn.execute(
            "SELECT discipline, region, location, description, remark "
            "FROM capcodes WHERE capcode = ?",
            ("001123101",),
        ).fetchone()
        assert row == ("Ambulance", "Brabant-Zuidoost", "Eindhoven", "Ambulance 22-101", "")
    finally:
        conn.close()


def test_sqlite_contains_enriched_metadata(tmp_path: Path) -> None:
    sources = [
        SourceRecord(
            capcode="000100001",
            source="capcodes_eu",
            discipline="Brandweer",
            region="Amsterdam-Amstelland",
            description="BRW Amsterdam-Amstelland/Kazerne Aalsmeer ( TS-3531 )",
        ),
        SourceRecord(
            capcode="000100001",
            source="bommel",
            discipline="Brandweer",
            description="Tankautospuit-612",
        ),
    ]
    records = merge_records(sources).records
    db = tmp_path / "capcodes.sqlite3"
    export_sqlite(records, sources, db)
    conn = sqlite3.connect(db)
    try:
        row = conn.execute(
            "SELECT service, station, unit_type, unit_type_name, callsign, unit_number "
            "FROM capcodes_meta WHERE capcode = ?",
            ("000100001",),
        ).fetchone()
        assert row == ("Brandweer", "Aalsmeer", "TS", "Tankautospuit", "TS-3531", "612")
    finally:
        conn.close()
