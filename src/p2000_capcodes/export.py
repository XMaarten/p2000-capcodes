from __future__ import annotations

import csv
import json
import sqlite3
from pathlib import Path

from p2000_capcodes.models import AbbreviationRecord, MergedRecord, SourceRecord

CSV_FIELDS = [
    "capcode",
    "capcode_short",
    "discipline",
    "service",
    "region",
    "region_code",
    "location",
    "station",
    "unit_type",
    "unit_type_name",
    "callsign",
    "unit_number",
    "description",
    "remark",
    "status",
    "confidence",
    "sources",
    "source_urls",
]

ABBREVIATION_CSV_FIELDS = [
    "abbreviation",
    "meaning",
    "category",
    "notes",
    "source",
    "source_url",
    "source_record_id",
    "observed_at",
]


def export_csv(records: list[MergedRecord], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for record in records:
            row = record.as_dict()
            row["sources"] = ";".join(record.sources)
            row["source_urls"] = ";".join(record.source_urls)
            row.pop("conflicts", None)
            writer.writerow({field: row.get(field, "") for field in CSV_FIELDS})


def export_json(records: list[MergedRecord], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "record_count": len(records),
        "records": [record.as_dict() for record in records],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def export_abbreviations_csv(records: list[AbbreviationRecord], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=ABBREVIATION_CSV_FIELDS)
        writer.writeheader()
        for record in records:
            payload = record.public_dict()
            writer.writerow({field: payload.get(field, "") for field in ABBREVIATION_CSV_FIELDS})


def export_abbreviations_json(records: list[AbbreviationRecord], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "record_count": len(records),
        "records": [record.public_dict() for record in records],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def export_sqlite(
    records: list[MergedRecord],
    source_records: list[SourceRecord],
    path: Path,
    abbreviations: list[AbbreviationRecord] | None = None,
) -> None:
    abbreviation_records = abbreviations or []
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.unlink(missing_ok=True)
    conn = sqlite3.connect(tmp)
    try:
        with conn:
            conn.executescript(
                """
                CREATE TABLE capcodes (
                    capcode TEXT PRIMARY KEY,
                    discipline TEXT NOT NULL DEFAULT '',
                    region TEXT NOT NULL DEFAULT '',
                    location TEXT NOT NULL DEFAULT '',
                    description TEXT NOT NULL DEFAULT '',
                    remark TEXT NOT NULL DEFAULT ''
                );
                CREATE TABLE capcodes_meta (
                    capcode TEXT PRIMARY KEY,
                    capcode_short TEXT NOT NULL,
                    service TEXT NOT NULL DEFAULT '',
                    region_code TEXT NOT NULL DEFAULT '',
                    station TEXT NOT NULL DEFAULT '',
                    unit_type TEXT NOT NULL DEFAULT '',
                    unit_type_name TEXT NOT NULL DEFAULT '',
                    callsign TEXT NOT NULL DEFAULT '',
                    unit_number TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL,
                    confidence TEXT NOT NULL,
                    sources_json TEXT NOT NULL,
                    source_urls_json TEXT NOT NULL,
                    field_sources_json TEXT NOT NULL,
                    source_descriptions_json TEXT NOT NULL,
                    conflicts_json TEXT NOT NULL,
                    FOREIGN KEY(capcode) REFERENCES capcodes(capcode)
                );
                CREATE TABLE source_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    capcode TEXT NOT NULL,
                    source TEXT NOT NULL,
                    discipline TEXT NOT NULL DEFAULT '',
                    region TEXT NOT NULL DEFAULT '',
                    region_code TEXT NOT NULL DEFAULT '',
                    location TEXT NOT NULL DEFAULT '',
                    description TEXT NOT NULL DEFAULT '',
                    remark TEXT NOT NULL DEFAULT '',
                    source_url TEXT NOT NULL DEFAULT '',
                    source_record_id TEXT NOT NULL DEFAULT '',
                    observed_at TEXT NOT NULL DEFAULT ''
                );
                CREATE INDEX idx_source_records_capcode ON source_records(capcode);
                CREATE INDEX idx_source_records_source ON source_records(source);
                CREATE TABLE abbreviations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    abbreviation TEXT NOT NULL,
                    meaning TEXT NOT NULL,
                    category TEXT NOT NULL DEFAULT '',
                    notes TEXT NOT NULL DEFAULT '',
                    source TEXT NOT NULL DEFAULT '',
                    source_url TEXT NOT NULL DEFAULT '',
                    source_record_id TEXT NOT NULL DEFAULT '',
                    observed_at TEXT NOT NULL DEFAULT ''
                );
                CREATE INDEX idx_abbreviations_abbreviation ON abbreviations(abbreviation);
                CREATE INDEX idx_abbreviations_category ON abbreviations(category);
                """
            )
            conn.executemany(
                """
                INSERT INTO capcodes(capcode, discipline, region, location, description, remark)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        record.capcode,
                        record.discipline,
                        record.region,
                        record.location,
                        record.description,
                        record.remark,
                    )
                    for record in records
                ],
            )
            conn.executemany(
                """
                INSERT INTO capcodes_meta(
                    capcode, capcode_short, service, region_code, station,
                    unit_type, unit_type_name, callsign, unit_number,
                    status, confidence, sources_json, source_urls_json,
                    field_sources_json, source_descriptions_json, conflicts_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        record.capcode,
                        record.capcode_short,
                        record.service,
                        record.region_code,
                        record.station,
                        record.unit_type,
                        record.unit_type_name,
                        record.callsign,
                        record.unit_number,
                        record.status,
                        record.confidence,
                        json.dumps(record.sources, ensure_ascii=False),
                        json.dumps(record.source_urls, ensure_ascii=False),
                        json.dumps(record.field_sources, ensure_ascii=False),
                        json.dumps(record.source_descriptions, ensure_ascii=False),
                        json.dumps(
                            [conflict.as_dict() for conflict in record.conflicts],
                            ensure_ascii=False,
                        ),
                    )
                    for record in records
                ],
            )
            conn.executemany(
                """
                INSERT INTO source_records(
                    capcode, source, discipline, region, region_code, location,
                    description, remark, source_url, source_record_id, observed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        record.capcode,
                        record.source,
                        record.discipline,
                        record.region,
                        record.region_code,
                        record.location,
                        record.description,
                        record.remark,
                        record.source_url,
                        record.source_record_id,
                        record.observed_at,
                    )
                    for record in source_records
                ],
            )
            conn.executemany(
                """
                INSERT INTO abbreviations(
                    abbreviation, meaning, category, notes, source, source_url,
                    source_record_id, observed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        record.abbreviation,
                        record.meaning,
                        record.category,
                        record.notes,
                        record.source,
                        record.source_url,
                        record.source_record_id,
                        record.observed_at,
                    )
                    for record in abbreviation_records
                ],
            )
    finally:
        conn.close()
    tmp.replace(path)
