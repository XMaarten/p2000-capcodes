# p2000-capcodes

A provenance-aware builder for a Dutch P2000 capcode database.

The project combines multiple public capcode sources, normalizes capcodes, detects duplicates
and conflicting metadata, applies explicit corrections, and publishes reusable CSV, JSON and
SQLite artifacts.

## Why this project exists

Public P2000 capcode lists can contain stale records, duplicates, conflicting disciplines and
missing capcodes. Instead of silently allowing the last source to win, this project keeps the
origin of every value and generates conflict reports.

## Sources

### Bommel — mandatory baseline

- Home: https://p2000.bommel.net/
- CSV: https://p2000.bommel.net/cap2csv.php
- Documentation: https://p2000.bommel.net/manual.php

Bommel is the primary bulk source and is required for an update. It explicitly describes the
capcode data as freely usable and suitable as a basis for other programs.

### Capcodes.eu — enabled by default

- https://capcodes.eu/

Capcodes.eu publishes capcode, region, service and description in a searchable table. Because
the table is rendered dynamically, this provider uses Playwright/Chromium and handles
DataTables-style pagination or an available "show all" option.

Records are stored with source name `capcodes_eu` and retain the source URL.

### TomZulu10 — enabled by default

- https://www.tomzulu10capcodes-brandweervoertuignummers.nl/

TomZulu10 maintains capcodes per safety region. The provider discovers the region pages from
the homepage, visits them at a deliberately low request rate, and parses both the page itself
and embedded frames/tables. This avoids hard-coding every individual capcode URL.

Records are stored with source name `tomzulu` and retain their exact source page/frame URL.

### TomZulu10 abbreviations — enabled by default

Two separate TomZulu10 glossaries are collected during each update:

- https://www.tomzulu10capcodes-brandweervoertuignummers.nl/afkortingen-hulpdiensten-klik-hier
- https://www.tomzulu10capcodes-brandweervoertuignummers.nl/afkortingen-kustwacht-knrm-reddingsbrigade-klik-hier

The pages embed published Google Sheets. The provider renders the page and its embedded frames,
then extracts abbreviation, meaning and optional notes. Duplicate rows are removed while the
original source URL remains attached to every entry.

Abbreviations are deliberately kept separate from capcode merging. They are intended for
message enrichment, so consumers can show for example `TS = Tankautospuit` without rewriting
the original P2000 message.

### p2000.page — not scraped

`p2000.page` has useful per-capcode pages, but without a verified bulk endpoint a complete
import would require requesting a very large number of individual pages. This project does not
do that. A native provider can be added later if a suitable bulk/API interface becomes
available.

See [NOTICE.md](NOTICE.md) for attribution notes.

## Source precedence

When sources disagree, the selected value follows this default priority while every differing
value remains visible as a conflict:

1. `manual`
2. `capcodes_eu`
3. `tomzulu`
4. `bommel`

Agreement between multiple sources is reflected in provenance. No conflicting source value is
discarded from JSON/SQLite metadata.

## Generated artifacts

Running an update creates:

```text
data/
├── capcodes.csv
├── capcodes.json
├── capcodes.sqlite3
├── abbreviations.csv
├── abbreviations.json
└── manifest.json

reports/
├── conflicts.md
├── duplicates.md
├── missing-from-bommel.md
└── summary.md
```

The SQLite `capcodes` table is deliberately compatible with the lookup used by
`cyberjunky/addon-p2000_rtlsdr`. The same database also contains an independent
`abbreviations` table for consumers that want to enrich P2000 message text:

```sql
SELECT discipline, region, location, description, remark
FROM capcodes
WHERE capcode = ?;
```

Capcodes are stored as the **9-digit form emitted by multimon-ng**. For example, `1123101`
becomes `001123101`. CSV/JSON also include `capcode_short`.

The abbreviation table can contain more than one meaning for the same abbreviation when the
source distinguishes contexts. Consumers should use `category` and display the original
message alongside any expansion.

## Quick start

The two rendered web sources require Chromium:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[scrape,dev]'
python -m playwright install chromium

p2000-capcodes update
```

If you only want the Bommel baseline without browser-based sources:

```bash
pip install -e .
p2000-capcodes update --no-capcodes-eu --no-tomzulu
```

Lookup a generated capcode:

```bash
p2000-capcodes lookup 1123101
```

Lookup an abbreviation:

```bash
p2000-capcodes lookup-abbreviation TS
```

Run checks:

```bash
ruff check .
pytest -q
```

## Resilience

Bommel is mandatory and must return at least 5,000 records by default. Capcodes.eu and
TomZulu are supplementary sources: if one is temporarily unavailable, the build continues and
stores the failure in `data/manifest.json` under `source_errors`.

To require every configured source to succeed:

```bash
p2000-capcodes update --strict-sources
```

Providers can be disabled separately:

```bash
p2000-capcodes update --no-capcodes-eu
p2000-capcodes update --no-tomzulu
p2000-capcodes update --no-abbreviations
```

If the abbreviation source is temporarily unavailable, an existing `data/abbreviations.json`
is preserved instead of replacing the glossary with an empty dataset. With `--strict-sources`,
a failed abbreviation update aborts the build just like another configured source.

## Manual corrections

Use `overrides/manual.yaml` for verified corrections or records that are missing from all
configured automated sources:

```yaml
records:
  - capcode: "001234567"
    discipline: Ambulance
    region: Example region
    description: Example description
    source: example-provider
    source_url: https://example.invalid/capcode/1234567
    source_record_id: verified-2026-08-22
```

A manual value has the highest merge priority, but a differing source value remains present in
`conflicts` so the disagreement is auditable.

## Import an additional permitted CSV

A permitted CSV export can also be supplied with:

```text
capcode,discipline,region,region_code,location,description,remark
```

Then run:

```bash
p2000-capcodes update \
  --extra-csv 'provider:data/provider.csv:https://provider.example/'
```

Extra columns `source_url`, `source_record_id` and `observed_at` are optional.

## Safely update Cyberjunky add-on database

The generated SQLite file intentionally contains only capcode data and provenance. Do **not**
replace Cyberjunky's complete `/data/p2000.sqlite3`, because that file also contains `places`
and `geocodes`.

Instead use:

```bash
p2000-capcodes update-addon-db /data/p2000.sqlite3 \
  --source data/capcodes.sqlite3
```

This:

1. creates a SQLite backup;
2. validates the source dataset;
3. replaces only the `capcodes` table inside a transaction;
4. preserves `places` and `geocodes`.

## Automated updates

`.github/workflows/update.yml` runs every Monday and can also be started with
**Actions → Update capcode dataset → Run workflow**.

The workflow installs Chromium, fetches all configured sources and commits changed `data/` and
`reports/` files. Browser-based providers are scraped only once per weekly build, not
continuously.

## Merge behaviour

- Exact duplicate rows within one source are deduplicated and reported.
- Different non-empty values are retained as conflicts.
- Empty versus non-empty prefers the populated value.
- Explicit source priority chooses the displayed value when sources disagree.
- `manual` overrides have highest priority.
- JSON and SQLite metadata keep the alternatives and their source URLs.

## License

Software: MIT. Source data remains attributable to and subject to the permissions/terms of its
source. See [NOTICE.md](NOTICE.md).
