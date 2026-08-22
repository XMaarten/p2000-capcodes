from __future__ import annotations

from collections import Counter
from pathlib import Path

from p2000_capcodes.merge import MergeResult
from p2000_capcodes.models import AbbreviationRecord, SourceRecord


def _format_source(record: SourceRecord) -> str:
    values = [
        record.discipline,
        record.region,
        record.region_code,
        record.location,
        record.description,
        record.remark,
    ]
    return " | ".join(value or "-" for value in values)


def write_reports(
    result: MergeResult,
    source_records: list[SourceRecord],
    directory: Path,
    abbreviation_records: list[AbbreviationRecord] | None = None,
) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    _write_duplicates(result, directory / "duplicates.md")
    _write_conflicts(result, directory / "conflicts.md")
    _write_missing_from_bommel(result, directory / "missing-from-bommel.md")
    _write_summary(
        result,
        source_records,
        directory / "summary.md",
        abbreviation_records=abbreviation_records or [],
    )


def _write_duplicates(result: MergeResult, path: Path) -> None:
    lines = ["# Duplicate source records", ""]
    lines.append(f"Exact duplicate capcodes: **{len(result.exact_duplicates)}**")
    lines.append(f"Conflicting duplicate capcodes: **{len(result.source_conflicts)}**")
    lines.append("")
    if result.exact_duplicates:
        lines.extend(["## Exact duplicates", ""])
        for capcode, records in result.exact_duplicates.items():
            source = records[0].source
            lines.append(f"- `{capcode}` — {len(records)} identical records from `{source}`")
        lines.append("")
    if result.source_conflicts:
        lines.extend(["## Conflicting duplicates within one source", ""])
        for capcode, records in result.source_conflicts.items():
            lines.append(f"### `{capcode}`")
            lines.append("")
            for record in records:
                lines.append(f"- `{record.source}`: {_format_source(record)}")
            lines.append("")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _write_conflicts(result: MergeResult, path: Path) -> None:
    conflicted = [record for record in result.records if record.conflicts]
    lines = ["# Field conflicts", "", f"Records with conflicts: **{len(conflicted)}**", ""]
    for record in conflicted:
        lines.append(f"## `{record.capcode}`")
        lines.append("")
        lines.append(f"Selected: **{record.discipline or '-'} / {record.region or '-'}**")
        lines.append("")
        for conflict in record.conflicts:
            lines.append(f"### {conflict.field}")
            for value in conflict.values:
                source = value["source"]
                text = value["value"]
                url = value.get("url") or ""
                suffix = f" — {url}" if url else ""
                lines.append(f"- `{source}`: {text}{suffix}")
            lines.append("")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _write_missing_from_bommel(result: MergeResult, path: Path) -> None:
    missing = [record for record in result.records if "bommel" not in record.sources]
    lines = [
        "# Records missing from Bommel",
        "",
        f"Records known only from other configured sources: **{len(missing)}**",
        "",
    ]
    for record in missing:
        description = record.description or record.location or "-"
        sources = ", ".join(record.sources)
        lines.append(
            f"- `{record.capcode}` — {record.discipline or '-'} — "
            f"{description} — sources: {sources}"
        )
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _write_summary(
    result: MergeResult,
    source_records: list[SourceRecord],
    path: Path,
    *,
    abbreviation_records: list[AbbreviationRecord],
) -> None:
    counts = Counter(record.source for record in source_records)
    conflicted = sum(bool(record.conflicts) for record in result.records)
    lines = [
        "# Dataset summary",
        "",
        f"- Unique merged capcodes: **{len(result.records)}**",
        f"- Records with field conflicts: **{conflicted}**",
        f"- Exact duplicate capcodes within a source: **{len(result.exact_duplicates)}**",
        f"- Conflicting duplicate capcodes within a source: **{len(result.source_conflicts)}**",
        f"- Abbreviations: **{len(abbreviation_records)}**",
        "",
        "## Source record counts",
        "",
    ]
    for source, count in sorted(counts.items()):
        lines.append(f"- `{source}`: {count}")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
