from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class SourceRecord:
    capcode: str
    source: str
    discipline: str = ""
    region: str = ""
    region_code: str = ""
    location: str = ""
    description: str = ""
    remark: str = ""
    source_url: str = ""
    source_record_id: str = ""
    observed_at: str = ""
    raw: tuple[str, ...] = field(default_factory=tuple, compare=False)

    def public_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("raw", None)
        return data


@dataclass(frozen=True, slots=True)
class AbbreviationRecord:
    abbreviation: str
    meaning: str
    source: str
    category: str = ""
    notes: str = ""
    source_url: str = ""
    source_record_id: str = ""
    observed_at: str = ""
    raw: tuple[str, ...] = field(default_factory=tuple, compare=False)

    def public_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("raw", None)
        return data


@dataclass(slots=True)
class FieldConflict:
    field: str
    values: list[dict[str, str]]

    def as_dict(self) -> dict[str, Any]:
        return {"field": self.field, "values": self.values}


@dataclass(slots=True)
class MergedRecord:
    capcode: str
    discipline: str = ""
    region: str = ""
    region_code: str = ""
    location: str = ""
    description: str = ""
    remark: str = ""
    status: str = "ok"
    confidence: str = "high"
    sources: list[str] = field(default_factory=list)
    source_urls: list[str] = field(default_factory=list)
    conflicts: list[FieldConflict] = field(default_factory=list)

    @property
    def capcode_short(self) -> str:
        return self.capcode[-7:]

    def as_dict(self) -> dict[str, Any]:
        return {
            "capcode": self.capcode,
            "capcode_short": self.capcode_short,
            "discipline": self.discipline,
            "region": self.region,
            "region_code": self.region_code,
            "location": self.location,
            "description": self.description,
            "remark": self.remark,
            "status": self.status,
            "confidence": self.confidence,
            "sources": self.sources,
            "source_urls": self.source_urls,
            "conflicts": [conflict.as_dict() for conflict in self.conflicts],
        }
