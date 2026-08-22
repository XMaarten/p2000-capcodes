from __future__ import annotations

import csv
from pathlib import Path

from p2000_capcodes.models import SourceRecord
from p2000_capcodes.normalize import clean, normalize_capcode


class LocalCsvSource:
    """Import a permitted CSV export from another provider.

    Expected headers: capcode and optionally discipline, region, region_code,
    location, description, remark, source_url, source_record_id, observed_at.
    """

    name = "local_csv"

    def __init__(self, path: Path, *, source_name: str, source_url: str = "") -> None:
        self.path = path
        self.source_name = source_name
        self.source_url = source_url

    def load(self) -> list[SourceRecord]:
        with self.path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames or "capcode" not in {x.strip() for x in reader.fieldnames}:
                raise ValueError(f"{self.path}: CSV requires a capcode header")
            result: list[SourceRecord] = []
            for index, row in enumerate(reader, 2):
                result.append(
                    SourceRecord(
                        capcode=normalize_capcode(row.get("capcode", "")),
                        source=self.source_name,
                        discipline=clean(row.get("discipline")),
                        region=clean(row.get("region")),
                        region_code=clean(row.get("region_code")),
                        location=clean(row.get("location")),
                        description=clean(row.get("description")),
                        remark=clean(row.get("remark")),
                        source_url=clean(row.get("source_url")) or self.source_url,
                        source_record_id=clean(row.get("source_record_id")) or f"line:{index}",
                        observed_at=clean(row.get("observed_at")),
                    )
                )
        return result
