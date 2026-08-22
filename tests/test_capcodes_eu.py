from pathlib import Path

from p2000_capcodes.sources.capcodes_eu import CapcodesEuSource

FIXTURES = Path(__file__).parent / "fixtures"


def test_capcodes_eu_table_parser() -> None:
    records = CapcodesEuSource(file=FIXTURES / "capcodes_eu.html").load()
    assert [record.capcode for record in records] == ["001123101", "000723153"]
    assert records[0].discipline == "Ambulance"
    assert records[0].region == "Brabant Zuid-Oost"
    assert records[0].description == "Ambulance 22-101"
