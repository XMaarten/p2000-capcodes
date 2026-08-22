from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from p2000_capcodes.models import FieldConflict, MergedRecord, SourceRecord
from p2000_capcodes.normalize import comparable

FIELDS = ("discipline", "region", "region_code", "location", "description", "remark")
DEFAULT_PRIORITY = {"manual": 100, "capcodes_eu": 80, "tomzulu": 70, "bommel": 50}


@dataclass(slots=True)
class MergeResult:
    records: list[MergedRecord]
    exact_duplicates: dict[str, list[SourceRecord]]
    source_conflicts: dict[str, list[SourceRecord]]


def _record_signature(record: SourceRecord) -> tuple[str, ...]:
    return tuple(getattr(record, field) for field in FIELDS)


def _candidate_score(record: SourceRecord, priorities: dict[str, int]) -> tuple[int, int, int]:
    priority = priorities.get(record.source, 25)
    populated = sum(bool(getattr(record, field)) for field in FIELDS)
    text_size = sum(len(getattr(record, field)) for field in FIELDS)
    return priority, populated, text_size


def _pick_field(
    field: str,
    candidates: list[SourceRecord],
    priorities: dict[str, int],
) -> tuple[str, FieldConflict | None]:
    populated = [record for record in candidates if getattr(record, field)]
    if not populated:
        return "", None

    grouped: dict[str, list[SourceRecord]] = defaultdict(list)
    for record in populated:
        grouped[comparable(getattr(record, field))].append(record)

    if len(grouped) == 1:
        best = max(populated, key=lambda record: _candidate_score(record, priorities))
        return getattr(best, field), None

    manual = [record for record in populated if record.source == "manual"]
    if manual:
        best = max(manual, key=lambda record: _candidate_score(record, priorities))
    else:
        best = max(populated, key=lambda record: _candidate_score(record, priorities))

    values: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for record in populated:
        value = getattr(record, field)
        key = (record.source, value)
        if key in seen:
            continue
        seen.add(key)
        values.append({"source": record.source, "value": value, "url": record.source_url})
    return getattr(best, field), FieldConflict(field=field, values=values)


def merge_records(
    source_records: list[SourceRecord],
    *,
    priorities: dict[str, int] | None = None,
) -> MergeResult:
    priorities = {**DEFAULT_PRIORITY, **(priorities or {})}
    grouped: dict[str, list[SourceRecord]] = defaultdict(list)
    for record in source_records:
        grouped[record.capcode].append(record)

    exact_duplicates: dict[str, list[SourceRecord]] = {}
    source_conflicts: dict[str, list[SourceRecord]] = {}
    merged: list[MergedRecord] = []

    for capcode, candidates in sorted(grouped.items()):
        by_source: dict[str, list[SourceRecord]] = defaultdict(list)
        for candidate in candidates:
            by_source[candidate.source].append(candidate)
        for source_candidates in by_source.values():
            if len(source_candidates) <= 1:
                continue
            signatures = {_record_signature(record) for record in source_candidates}
            if len(signatures) == 1:
                exact_duplicates[capcode] = source_candidates
            else:
                source_conflicts[capcode] = source_candidates

        conflicts: list[FieldConflict] = []
        selected: dict[str, str] = {}
        for field in FIELDS:
            value, conflict = _pick_field(field, candidates, priorities)
            selected[field] = value
            if conflict is not None:
                conflicts.append(conflict)

        source_names = sorted({record.source for record in candidates})
        source_urls = sorted({record.source_url for record in candidates if record.source_url})
        status = "conflict" if conflicts else "ok"
        if any(record.source == "manual" for record in candidates):
            confidence = "high"
        elif conflicts:
            confidence = "low"
        elif len(source_names) >= 2:
            confidence = "high"
        else:
            confidence = "high" if source_names == ["bommel"] else "medium"

        merged.append(
            MergedRecord(
                capcode=capcode,
                status=status,
                confidence=confidence,
                sources=source_names,
                source_urls=source_urls,
                conflicts=conflicts,
                **selected,
            )
        )

    return MergeResult(
        records=merged,
        exact_duplicates=exact_duplicates,
        source_conflicts=source_conflicts,
    )
