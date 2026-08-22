from pathlib import Path

from p2000_capcodes.sources.manual import ManualSource


def test_manual_accepts_top_level_list(tmp_path: Path) -> None:
    path = tmp_path / "manual.yaml"
    path.write_text(
        "- capcode: '1123101'\n"
        "  discipline: Ambulance\n"
        "  source: manual\n",
        encoding="utf-8",
    )
    records = ManualSource(path).load()
    assert records[0].capcode == "001123101"
    assert records[0].discipline == "Ambulance"
