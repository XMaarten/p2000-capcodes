from __future__ import annotations

import shutil
import sqlite3
from datetime import datetime
from pathlib import Path


def update_addon_database(source_db: Path, target_db: Path, *, backup: bool = True) -> Path | None:
    if not source_db.exists():
        raise FileNotFoundError(source_db)
    if not target_db.exists():
        raise FileNotFoundError(target_db)

    backup_path: Path | None = None
    if backup:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_path = target_db.with_name(f"{target_db.name}.{timestamp}.bak")
        src = sqlite3.connect(target_db)
        dst = sqlite3.connect(backup_path)
        try:
            src.backup(dst)
        finally:
            dst.close()
            src.close()

    source = sqlite3.connect(source_db)
    target = sqlite3.connect(target_db)
    try:
        rows = source.execute(
            "SELECT capcode, discipline, region, location, description, remark FROM capcodes"
        ).fetchall()
        if len(rows) < 1000:
            raise RuntimeError(f"Refusing to install unexpectedly small dataset ({len(rows)} rows)")

        columns = {
            row[1]
            for row in target.execute("PRAGMA table_info(capcodes)").fetchall()
        }
        required = {"capcode", "discipline", "region", "location", "description", "remark"}
        if not required.issubset(columns):
            missing = sorted(required - columns)
            raise RuntimeError(f"Target capcodes table missing columns: {missing}")

        with target:
            target.execute("DROP TABLE IF EXISTS capcodes_staging")
            target.execute(
                """
                CREATE TEMP TABLE capcodes_staging (
                    capcode TEXT PRIMARY KEY,
                    discipline TEXT,
                    region TEXT,
                    location TEXT,
                    description TEXT,
                    remark TEXT
                )
                """
            )
            target.executemany(
                "INSERT INTO capcodes_staging VALUES (?, ?, ?, ?, ?, ?)",
                rows,
            )
            target.execute("DELETE FROM capcodes")
            target.execute(
                """
                INSERT INTO capcodes(capcode, discipline, region, location, description, remark)
                SELECT capcode, discipline, region, location, description, remark
                FROM capcodes_staging
                """
            )
    except Exception:
        target.close()
        source.close()
        if backup_path is not None and backup_path.exists():
            shutil.copy2(backup_path, target_db)
        raise
    else:
        target.close()
        source.close()
    return backup_path
