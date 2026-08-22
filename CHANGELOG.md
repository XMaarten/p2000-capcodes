# Changelog

## 0.4.0

- Change merging from whole-record source precedence to field-based enrichment.
- Normalize common service aliases such as `BRW` to `Brandweer`.
- Add enriched fields: `service`, `station`, `unit_type`, `unit_type_name`, `callsign` and `unit_number`.
- Preserve every provider's original description/location/remark in `source_descriptions`.
- Track provenance per selected field in `field_sources`.
- Treat differing descriptive text as complementary rather than automatically conflicting.
- Prefer TomZulu for station/unit type, Capcodes.eu for callsigns, and Bommel for spelled-out vehicle descriptions.
- Extend CSV/JSON/SQLite exports with enriched metadata while keeping the Cyberjunky-compatible `capcodes` table unchanged.
- Include the corrected generated-data commit logic in the scheduled GitHub Action.
- Add regression tests for complementary Aalsmeer-style source records.

## 0.3.0

- Fetch the TomZulu10 general emergency-service abbreviation glossary.
- Fetch the separate Kustwacht/KNRM/Reddingsbrigade abbreviation glossary.
- Export `data/abbreviations.csv` and `data/abbreviations.json`.
- Add an `abbreviations` table to `capcodes.sqlite3`.
- Preserve source URL, category, notes and provenance for abbreviations.
- Preserve the previous abbreviation dataset when the supplementary source is temporarily unavailable.
- Add `lookup-abbreviation` and `--no-abbreviations` CLI options.
- Add parser/export/SQLite tests for abbreviations.

## 0.2.0

- Add Capcodes.eu as a browser-rendered supplementary source.
- Add TomZulu10 capcodes per safety region as a browser-rendered supplementary source.
- Add source priority, provenance and resilient source error handling.

## 0.1.0

- Initial provenance-aware Bommel importer, merge logic, reports, exports and Cyberjunky updater.
