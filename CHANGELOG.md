# Changelog

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
