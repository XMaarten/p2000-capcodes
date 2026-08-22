from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from p2000_capcodes.abbreviations import deduplicate_abbreviations, parse_abbreviation_tables
from p2000_capcodes.models import AbbreviationRecord
from p2000_capcodes.sources.html import BrowserRenderer, read_html_file

TOMZULU_GENERAL_ABBREVIATIONS_URL = (
    "https://www.tomzulu10capcodes-brandweervoertuignummers.nl/"
    "afkortingen-hulpdiensten-klik-hier"
)
TOMZULU_MARITIME_ABBREVIATIONS_URL = (
    "https://www.tomzulu10capcodes-brandweervoertuignummers.nl/"
    "afkortingen-kustwacht-knrm-reddingsbrigade-klik-hier"
)


@dataclass(frozen=True, slots=True)
class AbbreviationPage:
    url: str
    category: str


DEFAULT_PAGES = (
    AbbreviationPage(TOMZULU_GENERAL_ABBREVIATIONS_URL, "Hulpdiensten"),
    AbbreviationPage(TOMZULU_MARITIME_ABBREVIATIONS_URL, "Kustwacht/KNRM/Reddingsbrigade"),
)


class TomZuluAbbreviationsSource:
    name = "tomzulu_abbreviations"

    def __init__(
        self,
        *,
        timeout: float = 30.0,
        pages: tuple[AbbreviationPage, ...] = DEFAULT_PAGES,
        fixtures_dir: Path | None = None,
    ) -> None:
        self.timeout = timeout
        self.pages = pages
        self.fixtures_dir = fixtures_dir

    def _parse_documents(
        self,
        page_info: AbbreviationPage,
        documents: list[tuple[str, str]],
    ) -> list[AbbreviationRecord]:
        records: list[AbbreviationRecord] = []
        for document_index, (source_url, html) in enumerate(documents):
            records.extend(
                parse_abbreviation_tables(
                    html,
                    source=self.name,
                    source_url=source_url or page_info.url,
                    category=page_info.category,
                    record_prefix=f"{page_info.category}:{document_index}",
                )
            )
        return records

    def _offline_load(self) -> list[AbbreviationRecord]:
        assert self.fixtures_dir is not None
        records: list[AbbreviationRecord] = []
        for index, page_info in enumerate(self.pages, 1):
            main_path = self.fixtures_dir / f"page{index}.html"
            frame_path = self.fixtures_dir / f"page{index}-frame.html"
            documents: list[tuple[str, str]] = []
            if main_path.exists():
                documents.append((page_info.url, read_html_file(main_path)))
            if frame_path.exists():
                documents.append((f"{page_info.url}#frame", read_html_file(frame_path)))
            records.extend(self._parse_documents(page_info, documents))
        return deduplicate_abbreviations(records)

    def load(self) -> list[AbbreviationRecord]:
        if self.fixtures_dir is not None:
            records = self._offline_load()
            if not records:
                raise RuntimeError("TomZulu abbreviation fixtures returned no parseable records")
            return records

        records: list[AbbreviationRecord] = []
        with BrowserRenderer(timeout=self.timeout) as renderer:
            for page_info in self.pages:
                page = renderer.render(page_info.url)
                documents = [(page.url, page.main_html), *page.frame_html]
                records.extend(self._parse_documents(page_info, documents))

        records = deduplicate_abbreviations(records)
        if not records:
            raise RuntimeError("TomZulu returned no parseable abbreviations")
        return records
