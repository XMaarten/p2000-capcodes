from pathlib import Path

from p2000_capcodes.merge import merge_records
from p2000_capcodes.models import SourceRecord
from p2000_capcodes.sources.bommel import parse_bommel_csv


def test_detect_exact_and_conflicting_duplicates() -> None:
    records = parse_bommel_csv(Path("tests/fixtures/bommel.csv").read_bytes())
    result = merge_records(records)
    assert "000120359" in result.exact_duplicates
    assert "000103071" in result.source_conflicts
    assert "000200818" in result.source_conflicts


def test_manual_field_wins_but_conflict_is_preserved() -> None:
    records = [
        SourceRecord(capcode="001123101", source="bommel", discipline="Brandweer"),
        SourceRecord(capcode="001123101", source="manual", discipline="Ambulance"),
    ]
    merged = merge_records(records).records[0]
    assert merged.discipline == "Ambulance"
    assert merged.status == "conflict"
    assert merged.conflicts[0].field == "discipline"


def test_sources_are_combined_as_complementary_fields() -> None:
    records = [
        SourceRecord(
            capcode="000100001",
            source="tomzulu",
            discipline="BRW",
            region="Amsterdam-Amstelland",
            location="Aalsmeer",
            description="Bezetting TS",
            source_url="https://tomzulu.example/aalsmeer",
        ),
        SourceRecord(
            capcode="000100001",
            source="capcodes_eu",
            discipline="Brandweer",
            region="Amsterdam-Amstelland",
            description="BRW Amsterdam-Amstelland/Kazerne Aalsmeer ( TS-3531 )",
            source_url="https://capcodes.example/",
        ),
        SourceRecord(
            capcode="000100001",
            source="bommel",
            discipline="Brandweer",
            region="Amsterdam-Amstelland",
            location="Aalsmeer",
            description="Tankautospuit-612",
            source_url="https://bommel.example/",
        ),
    ]

    merged = merge_records(records).records[0]
    assert merged.status == "ok"
    assert merged.service == "Brandweer"
    assert merged.discipline == "Brandweer"
    assert merged.station == "Aalsmeer"
    assert merged.unit_type == "TS"
    assert merged.unit_type_name == "Tankautospuit"
    assert merged.callsign == "TS-3531"
    assert merged.unit_number == "612"
    assert merged.description == "Tankautospuit-612"
    assert len(merged.source_descriptions) == 3
    assert merged.field_sources["station"] == ["bommel", "capcodes_eu", "tomzulu"]


def test_service_aliases_do_not_create_false_conflict() -> None:
    records = [
        SourceRecord(capcode="000100001", source="tomzulu", discipline="BRW"),
        SourceRecord(capcode="000100001", source="capcodes_eu", discipline="Brandweer"),
    ]
    merged = merge_records(records).records[0]
    assert merged.discipline == "Brandweer"
    assert merged.service == "Brandweer"
    assert merged.status == "ok"
