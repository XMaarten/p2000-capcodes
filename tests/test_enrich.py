from p2000_capcodes.enrich import derive_fields
from p2000_capcodes.models import SourceRecord


def test_tomzulu_functional_description_is_enriched() -> None:
    record = SourceRecord(
        capcode="000100001",
        source="tomzulu",
        discipline="BRW",
        region="Amsterdam-Amstelland",
        location="Aalsmeer",
        description="Bezetting TS",
    )
    derived = derive_fields(record)
    assert derived.service == "Brandweer"
    assert derived.station == "Aalsmeer"
    assert derived.unit_type == "TS"


def test_capcodes_eu_callsign_and_station_are_enriched() -> None:
    record = SourceRecord(
        capcode="000100001",
        source="capcodes_eu",
        discipline="Brandweer",
        region="Amsterdam-Amstelland",
        description="BRW Amsterdam-Amstelland/Kazerne Aalsmeer ( TS-3531 )",
    )
    derived = derive_fields(record)
    assert derived.station == "Aalsmeer"
    assert derived.unit_type == "TS"
    assert derived.callsign == "TS-3531"


def test_bommel_spelled_vehicle_is_enriched() -> None:
    record = SourceRecord(
        capcode="000100001",
        source="bommel",
        discipline="Brandweer",
        description="Tankautospuit-612",
    )
    derived = derive_fields(record)
    assert derived.unit_type == "TS"
    assert derived.unit_type_name == "Tankautospuit"
    assert derived.unit_number == "612"
