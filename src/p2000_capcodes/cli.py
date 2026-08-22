from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from p2000_capcodes.abbreviations import load_abbreviations_json
from p2000_capcodes.addon import update_addon_database
from p2000_capcodes.export import (
    export_abbreviations_csv,
    export_abbreviations_json,
    export_csv,
    export_json,
    export_sqlite,
)
from p2000_capcodes.merge import merge_records
from p2000_capcodes.sources import (
    BommelSource,
    CapcodesEuSource,
    LocalCsvSource,
    ManualSource,
    TomZuluAbbreviationsSource,
    TomZuluSource,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="p2000-capcodes")
    sub = parser.add_subparsers(dest="command", required=True)

    update = sub.add_parser("update", help="Fetch sources, merge, validate and export")
    update.add_argument("--output-dir", type=Path, default=Path("data"))
    update.add_argument("--reports-dir", type=Path, default=Path("reports"))
    update.add_argument("--manual", type=Path, default=Path("overrides/manual.yaml"))
    update.add_argument("--bommel-file", type=Path)
    update.add_argument("--min-records", type=int, default=5000)
    update.add_argument("--no-capcodes-eu", action="store_true")
    update.add_argument("--no-tomzulu", action="store_true")
    update.add_argument("--no-abbreviations", action="store_true")
    update.add_argument("--strict-sources", action="store_true")
    update.add_argument("--browser-timeout", type=float, default=30.0)
    update.add_argument("--capcodes-eu-file", type=Path)
    update.add_argument("--tomzulu-homepage-file", type=Path)
    update.add_argument("--tomzulu-pages-dir", type=Path)
    update.add_argument(
        "--extra-csv",
        action="append",
        default=[],
        metavar="NAME:PATH[:URL]",
        help="Import an additional permitted CSV export",
    )

    lookup = sub.add_parser("lookup", help="Lookup a capcode in generated JSON")
    lookup.add_argument("capcode")
    lookup.add_argument("--json", type=Path, default=Path("data/capcodes.json"))

    abbreviation = sub.add_parser("lookup-abbreviation", help="Lookup an abbreviation")
    abbreviation.add_argument("abbreviation")
    abbreviation.add_argument(
        "--json", type=Path, default=Path("data/abbreviations.json")
    )

    addon = sub.add_parser("update-addon-db", help="Safely update only capcodes in add-on DB")
    addon.add_argument("target", type=Path, help="Existing cyberjunky p2000.sqlite3")
    addon.add_argument("--source", type=Path, default=Path("data/capcodes.sqlite3"))
    addon.add_argument("--no-backup", action="store_true")

    return parser


def _parse_extra_csv(spec: str) -> LocalCsvSource:
    parts = spec.split(":", 2)
    if len(parts) < 2:
        raise ValueError("--extra-csv expects NAME:PATH[:URL]")
    name, path = parts[0], parts[1]
    url = parts[2] if len(parts) > 2 else ""
    return LocalCsvSource(Path(path), source_name=name, source_url=url)


def command_update(args: argparse.Namespace) -> int:
    bommel = BommelSource(file=args.bommel_file)
    sources = [bommel]
    if not args.no_capcodes_eu:
        sources.append(
            CapcodesEuSource(
                timeout=args.browser_timeout,
                file=args.capcodes_eu_file,
            )
        )
    if not args.no_tomzulu:
        sources.append(
            TomZuluSource(
                timeout=args.browser_timeout,
                homepage_file=args.tomzulu_homepage_file,
                pages_dir=args.tomzulu_pages_dir,
            )
        )
    sources.append(ManualSource(args.manual))
    sources.extend(_parse_extra_csv(spec) for spec in args.extra_csv)

    source_records = []
    source_errors: dict[str, str] = {}
    for source in sources:
        try:
            records = source.load()
        except Exception as exc:
            if source is bommel or args.strict_sources:
                raise
            source_errors[source.name] = f"{type(exc).__name__}: {exc}"
            print(f"WARNING {source.name}: {source_errors[source.name]}", file=sys.stderr)
            continue
        print(f"{source.name}: {len(records)} source record(s)")
        source_records.extend(records)

    bommel_count = sum(record.source == "bommel" for record in source_records)
    if bommel_count < args.min_records:
        raise RuntimeError(
            f"Bommel returned only {bommel_count} records; expected at least {args.min_records}. "
            "Nothing was exported."
        )

    abbreviation_records = []
    abbreviation_source = TomZuluAbbreviationsSource(timeout=args.browser_timeout)
    abbreviation_json = args.output_dir / "abbreviations.json"
    if args.no_abbreviations:
        abbreviation_records = load_abbreviations_json(abbreviation_json)
    else:
        try:
            abbreviation_records = abbreviation_source.load()
            print(
                f"{abbreviation_source.name}: "
                f"{len(abbreviation_records)} abbreviation record(s)"
            )
        except Exception as exc:
            if args.strict_sources:
                raise
            source_errors[abbreviation_source.name] = f"{type(exc).__name__}: {exc}"
            print(
                f"WARNING {abbreviation_source.name}: "
                f"{source_errors[abbreviation_source.name]}",
                file=sys.stderr,
            )
            abbreviation_records = load_abbreviations_json(abbreviation_json)
            if abbreviation_records:
                print(
                    f"Preserving {len(abbreviation_records)} previously generated "
                    "abbreviation record(s)",
                    file=sys.stderr,
                )

    result = merge_records(source_records)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    export_csv(result.records, args.output_dir / "capcodes.csv")
    export_json(result.records, args.output_dir / "capcodes.json")
    export_abbreviations_csv(abbreviation_records, args.output_dir / "abbreviations.csv")
    export_abbreviations_json(abbreviation_records, abbreviation_json)
    export_sqlite(
        result.records,
        source_records,
        args.output_dir / "capcodes.sqlite3",
        abbreviations=abbreviation_records,
    )

    from p2000_capcodes.reports import write_reports

    write_reports(
        result,
        source_records,
        args.reports_dir,
        abbreviation_records=abbreviation_records,
    )

    manifest = {
        "source_records": len(source_records),
        "unique_capcodes": len(result.records),
        "bommel_records": bommel_count,
        "exact_duplicate_capcodes": len(result.exact_duplicates),
        "conflicting_duplicate_capcodes": len(result.source_conflicts),
        "records_with_field_conflicts": sum(bool(record.conflicts) for record in result.records),
        "abbreviation_records": len(abbreviation_records),
        "source_errors": source_errors,
    }
    if bommel.download_info:
        manifest["bommel_download"] = {
            "url": bommel.download_info.url,
            "sha256": bommel.download_info.sha256,
            "size": bommel.download_info.size,
        }
    (args.output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Merged: {len(result.records)} unique capcodes")
    print(f"Conflicts: {manifest['records_with_field_conflicts']}")
    return 0


def command_lookup(args: argparse.Namespace) -> int:
    from p2000_capcodes.normalize import normalize_capcode

    wanted = normalize_capcode(args.capcode)
    payload = json.loads(args.json.read_text(encoding="utf-8"))
    for record in payload["records"]:
        if record["capcode"] == wanted:
            print(json.dumps(record, ensure_ascii=False, indent=2))
            return 0
    print(f"Capcode {wanted} not found", file=sys.stderr)
    return 1


def command_lookup_abbreviation(args: argparse.Namespace) -> int:
    wanted = args.abbreviation.casefold()
    payload = json.loads(args.json.read_text(encoding="utf-8"))
    matches = [
        record
        for record in payload.get("records", [])
        if record.get("abbreviation", "").casefold() == wanted
    ]
    if not matches:
        print(f"Abbreviation {args.abbreviation!r} not found", file=sys.stderr)
        return 1
    print(json.dumps(matches, ensure_ascii=False, indent=2))
    return 0


def command_addon(args: argparse.Namespace) -> int:
    backup = update_addon_database(args.source, args.target, backup=not args.no_backup)
    print(f"Updated {args.target}")
    if backup:
        print(f"Backup: {backup}")
    return 0


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    commands = {
        "update": command_update,
        "lookup": command_lookup,
        "lookup-abbreviation": command_lookup_abbreviation,
        "update-addon-db": command_addon,
    }
    raise SystemExit(commands[args.command](args))
