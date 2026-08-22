import sqlite3
from pathlib import Path

import pytest

from p2000_capcodes.addon import update_addon_database
from p2000_capcodes.export import export_sqlite
from p2000_capcodes.merge import merge_records
from p2000_capcodes.models import SourceRecord


def _target_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    with conn:
        conn.executescript(
            """
            CREATE TABLE capcodes (
                capcode TEXT PRIMARY KEY, discipline TEXT, region TEXT,
                location TEXT, description TEXT, remark TEXT
            );
            CREATE TABLE places (city TEXT);
            CREATE TABLE geocodes (query TEXT);
            INSERT INTO capcodes VALUES ('000000001','','','','old','');
            INSERT INTO places VALUES ('Alkmaar');
            INSERT INTO geocodes VALUES ('cache');
            """
        )
    conn.close()


def test_addon_updater_preserves_other_tables(tmp_path: Path) -> None:
    # The safety threshold is intentionally high in production; build enough rows here.
    source_records = [
        SourceRecord(capcode=str(i).zfill(9), source="manual", description=f"r{i}")
        for i in range(1000, 2001)
    ]
    merged = merge_records(source_records).records
    source_db = tmp_path / "source.sqlite3"
    target_db = tmp_path / "target.sqlite3"
    export_sqlite(merged, source_records, source_db)
    _target_db(target_db)

    update_addon_database(source_db, target_db, backup=False)
    conn = sqlite3.connect(target_db)
    try:
        assert conn.execute("SELECT city FROM places").fetchone()[0] == "Alkmaar"
        assert conn.execute("SELECT query FROM geocodes").fetchone()[0] == "cache"
        assert conn.execute("SELECT COUNT(*) FROM capcodes").fetchone()[0] == 1001
    finally:
        conn.close()


def test_addon_updater_rejects_small_source(tmp_path: Path) -> None:
    record = SourceRecord(capcode="001123101", source="manual")
    source_db = tmp_path / "source.sqlite3"
    target_db = tmp_path / "target.sqlite3"
    export_sqlite(merge_records([record]).records, [record], source_db)
    _target_db(target_db)
    with pytest.raises(RuntimeError):
        update_addon_database(source_db, target_db, backup=False)
