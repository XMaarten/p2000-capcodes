from __future__ import annotations

from pathlib import Path

from p2000_capcodes.models import SourceRecord
from p2000_capcodes.sources.html import BrowserRenderer, parse_capcode_tables, read_html_file

CAPCODES_EU_URL = "https://capcodes.eu/"


class CapcodesEuSource:
    name = "capcodes_eu"

    def __init__(
        self,
        *,
        url: str = CAPCODES_EU_URL,
        timeout: float = 30.0,
        file: Path | None = None,
    ) -> None:
        self.url = url
        self.timeout = timeout
        self.file = file

    def load(self) -> list[SourceRecord]:
        if self.file is not None:
            html = read_html_file(self.file)
        else:
            with BrowserRenderer(timeout=self.timeout) as renderer:
                pages = renderer.render_table_pages(self.url)
            records_by_key: dict[tuple[str, str, str, str, str, str], SourceRecord] = {}
            for page_number, page_html in enumerate(pages, 1):
                for record in parse_capcode_tables(
                    page_html,
                    source=self.name,
                    source_url=self.url,
                    record_prefix=f"capcodes-eu:{page_number}",
                ):
                    key = (
                        record.capcode,
                        record.discipline,
                        record.region,
                        record.location,
                        record.description,
                        record.remark,
                    )
                    records_by_key.setdefault(key, record)
            records = list(records_by_key.values())
            if not records:
                raise RuntimeError("capcodes.eu returned no parseable capcode rows")
            return records

        records = parse_capcode_tables(
            html,
            source=self.name,
            source_url=self.url,
            record_prefix="capcodes-eu",
        )
        if not records:
            raise RuntimeError("capcodes.eu returned no parseable capcode rows")
        return records
