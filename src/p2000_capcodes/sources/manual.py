from __future__ import annotations

from pathlib import Path

import yaml

from p2000_capcodes.models import SourceRecord
from p2000_capcodes.normalize import clean, normalize_capcode


class ManualSource:
    name = "manual"

    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> list[SourceRecord]:
        if not self.path.exists():
            return []
        document = yaml.safe_load(self.path.read_text(encoding="utf-8")) or {}
        if isinstance(document, list):
            entries = document
        elif isinstance(document, dict):
            entries = document.get("records", [])
        else:
            raise ValueError("Manual override file must be a mapping or list")
        if not isinstance(entries, list):
            raise ValueError("Manual override file must contain a 'records' list")

        result: list[SourceRecord] = []
        for index, item in enumerate(entries, 1):
            if not isinstance(item, dict):
                raise ValueError(f"Manual record {index} must be a mapping")
            source = clean(item.get("source")) or "manual"
            source_url = clean(item.get("source_url"))
            if source != "manual" and not source_url:
                raise ValueError(f"Manual record {index}: source_url is required for {source!r}")
            result.append(
                SourceRecord(
                    capcode=normalize_capcode(item.get("capcode", "")),
                    source=source,
                    discipline=clean(item.get("discipline")),
                    region=clean(item.get("region")),
                    region_code=clean(item.get("region_code")),
                    location=clean(item.get("location")),
                    description=clean(item.get("description")),
                    remark=clean(item.get("remark")),
                    source_url=source_url,
                    source_record_id=clean(item.get("source_record_id")) or f"manual:{index}",
                    observed_at=clean(item.get("observed_at")),
                )
            )
        return result
