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
