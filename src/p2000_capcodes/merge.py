from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass

from p2000_capcodes.enrich import DerivedFields, derive_fields, normalize_service
from p2000_capcodes.models import FieldConflict, MergedRecord, SourceRecord
from p2000_capcodes.normalize import comparable

FIELDS = ("discipline", "region", "region_code", "location", "description", "remark")
CONFLICT_FIELDS = {"discipline", "region", "region_code", "location"}
DEFAULT_PRIORITY = {"manual": 100, "capcodes_eu": 80, "tomzulu": 70, "bommel": 50}

# Different sources are strongest at different kinds of information. These
# priorities choose the displayed/canonical value without discarding any source text.
FIELD_PRIORITY: dict[str, dict[str, int]] = {
    "discipline": {"manual": 100, "capcodes_eu": 90, "tomzulu": 80, "bommel": 70},
    "service": {"manual": 100, "capcodes_eu": 90, "tomzulu": 80, "bommel": 70},
    "region": {"manual": 100, "capcodes_eu": 90, "tomzulu": 80, "bommel": 70},
    "region_code": {"manual": 100, "bommel": 90, "capcodes_eu": 70, "tomzulu": 60},
    "location": {"manual": 100, "tomzulu": 90, "capcodes_eu": 80, "bommel": 70},
    "station": {"manual": 100, "tomzulu": 95, "capcodes_eu": 90, "bommel": 70},
    "unit_type": {"manual": 100, "tomzulu": 95, "capcodes_eu": 90, "bommel": 80},
    "unit_type_name": {"manual": 100, "bommel": 95, "capcodes_eu": 80, "tomzulu": 70},
    "callsign": {"manual": 100, "capcodes_eu": 95, "tomzulu": 90, "bommel": 75},
    "unit_number": {"manual": 100, "capcodes_eu": 95, "tomzulu": 90, "bommel": 85},
    "description": {"manual": 100, "bommel": 95, "capcodes_eu": 85, "tomzulu": 75},
    "remark": {"manual": 100, "tomzulu": 95, "capcodes_eu": 85, "bommel": 75},
}


@dataclass(slots=True)
class MergeResult:
    records: list[MergedRecord]
    exact_duplicates: dict[str, list[SourceRecord]]
    source_conflicts: dict[str, list[SourceRecord]]


def _record_signature(record: SourceRecord) -> tuple[str, ...]:
    return tuple(getattr(record, field) for field in FIELDS)


def _priorities_for(field: str, priorities: dict[str, int]) -> dict[str, int]:
    return {**priorities, **FIELD_PRIORITY.get(field, {})}


def _candidate_score(
    source: str,
    value: str,
    field: str,
    priorities: dict[str, int],
) -> tuple[int, int]:
    field_priorities = _priorities_for(field, priorities)
    return field_priorities.get(source, 25), len(value)


def _pick_values(
    field: str,
    candidates: list[tuple[SourceRecord, str]],
    priorities: dict[str, int],
    *,
    normalize: Callable[[str], str] | None = None,
    conflict: bool = True,
) -> tuple[str, list[str], FieldConflict | None]:
    populated = [(record, value) for record, value in candidates if value]
    if not populated:
        return "", [], None

    normalize = normalize or comparable
    grouped: dict[str, list[tuple[SourceRecord, str]]] = defaultdict(list)
    for record, value in populated:
        grouped[normalize(value)].append((record, value))

    best_record, best_value = max(
        populated,
        key=lambda pair: _candidate_score(pair[0].source, pair[1], field, priorities),
    )
    selected_key = normalize(best_value)
    supporting_sources = sorted({record.source for record, _ in grouped[selected_key]})

    if len(grouped) == 1 or not conflict:
        return best_value, supporting_sources, None

    values: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for record, value in populated:
        key = (record.source, value)
        if key in seen:
            continue
        seen.add(key)
        values.append({"source": record.source, "value": value, "url": record.source_url})
    return best_value, supporting_sources, FieldConflict(field=field, values=values)


def _source_descriptions(candidates: list[SourceRecord]) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    seen: set[tuple[str, str, str, str, str]] = set()
    for record in sorted(candidates, key=lambda item: (item.source, item.source_record_id)):
        if not any((record.description, record.location, record.remark)):
            continue
        key = (
            record.source,
            record.description,
            record.location,
            record.remark,
            record.source_url,
        )
        if key in seen:
            continue
        seen.add(key)
        items.append(
            {
                "source": record.source,
                "description": record.description,
                "location": record.location,
                "remark": record.remark,
                "url": record.source_url,
            }
        )
    return items


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

        derived: dict[int, DerivedFields] = {
            id(candidate): derive_fields(candidate) for candidate in candidates
        }
        conflicts: list[FieldConflict] = []
        selected: dict[str, str] = {}
        field_sources: dict[str, list[str]] = {}

        raw_field_normalizers: dict[str, Callable[[str], str] | None] = {
            "discipline": lambda value: comparable(normalize_service(value)),
            "region": None,
            "region_code": None,
            "location": None,
            "description": None,
            "remark": None,
        }

        for field in FIELDS:
            pairs = [(record, getattr(record, field)) for record in candidates]
            value, sources, field_conflict = _pick_values(
                field,
                pairs,
                priorities,
                normalize=raw_field_normalizers[field],
                conflict=field in CONFLICT_FIELDS,
            )
            if field == "discipline":
                value = normalize_service(value)
            selected[field] = value
            if value:
                field_sources[field] = sources
            if field_conflict is not None:
                conflicts.append(field_conflict)

        derived_fields = (
            "service",
            "station",
            "unit_type",
            "unit_type_name",
            "callsign",
            "unit_number",
        )
        for field in derived_fields:
            pairs = [(record, getattr(derived[id(record)], field)) for record in candidates]
            value, sources, field_conflict = _pick_values(
                field,
                pairs,
                priorities,
                normalize=lambda item, field=field: (
                    comparable(normalize_service(item))
                    if field == "service"
                    else comparable(item)
                ),
                conflict=field in {"service", "station", "callsign"},
            )

            if field == "service":
                value = normalize_service(value)
            selected[field] = value
            if value:
                field_sources[field] = sources
            if field_conflict is not None:
                conflicts.append(field_conflict)

        if not selected["service"]:
            selected["service"] = selected["discipline"]
            if selected["service"] and "discipline" in field_sources:
                field_sources["service"] = field_sources["discipline"]
        if not selected["discipline"]:
            selected["discipline"] = selected["service"]
            if selected["discipline"] and "service" in field_sources:
                field_sources["discipline"] = field_sources["service"]
        if not selected["station"]:
            selected["station"] = selected["location"]
            if selected["station"] and "location" in field_sources:
                field_sources["station"] = field_sources["location"]

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
                field_sources=field_sources,
                source_descriptions=_source_descriptions(candidates),
                conflicts=conflicts,
                **selected,
            )
        )

    return MergeResult(
        records=merged,
        exact_duplicates=exact_duplicates,
        source_conflicts=source_conflicts,
    )
