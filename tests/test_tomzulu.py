from pathlib import Path

from p2000_capcodes.sources.tomzulu import TomZuluSource, discover_tomzulu_pages

FIXTURES = Path(__file__).parent / "fixtures"


def test_discover_tomzulu_region_pages() -> None:
    pages = discover_tomzulu_pages((FIXTURES / "tomzulu_home.html").read_text())
    assert len(pages) == 1
    assert pages[0].region == "Noord-Holland Noord"
    assert pages[0].url.endswith("/10-noord-holland-noord-capcodes")


def test_tomzulu_offline_parser() -> None:
    records = TomZuluSource(
        homepage_file=FIXTURES / "tomzulu_home.html",
        pages_dir=FIXTURES / "tomzulu_pages",
    ).load()
    assert [record.capcode for record in records] == ["000200818", "000200051"]
    assert records[0].discipline == "Brandweer"
    assert records[0].region == "Noord-Holland Noord"
    assert records[0].location == "Opmeer"
    assert records[0].remark == "10W002"
