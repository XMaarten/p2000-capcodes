from pathlib import Path

from p2000_capcodes.sources.bommel import parse_bommel_csv


def test_parse_current_six_column_export() -> None:
    payload = Path("tests/fixtures/bommel.csv").read_bytes()
    records = parse_bommel_csv(payload)
    assert len(records) == 6
    assert records[0].capcode == "000103071"
    assert records[-1].remark == "10W002"


def test_parse_seven_column_export() -> None:
    payload = b"0100001,Brandweer,Amsterdam-Amstelland,BAA,Aalsmeer,Bevelvoerders,BV\n"
    records = parse_bommel_csv(payload)
    assert records[0].capcode == "000100001"
    assert records[0].location == "Aalsmeer"
    assert records[0].remark == "BV"
