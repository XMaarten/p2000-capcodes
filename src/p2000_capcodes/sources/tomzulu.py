from __future__ import annotations

import re
import time
from dataclasses import dataclass
from pathlib import Path

from bs4 import BeautifulSoup

from p2000_capcodes.models import SourceRecord
from p2000_capcodes.sources.html import (
    BrowserRenderer,
    absolute_url,
    parse_capcode_tables,
    read_html_file,
)

TOMZULU_URL = "https://www.tomzulu10capcodes-brandweervoertuignummers.nl/"
REGION_LINK_RE = re.compile(r"^(\d{2})\s+(.+?)\s+capcodes$", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class TomZuluPage:
    url: str
    region: str


def discover_tomzulu_pages(html: str, *, base_url: str = TOMZULU_URL) -> list[TomZuluPage]:
    soup = BeautifulSoup(html, "html.parser")
    pages: dict[str, TomZuluPage] = {}
    for anchor in soup.find_all("a", href=True):
        label = " ".join(anchor.get_text(" ", strip=True).split())
        match = REGION_LINK_RE.match(label)
        if match:
            region = match.group(2).strip()
        elif "knrm" in label.casefold() and "capcodes" in label.casefold():
            region = "Landelijk"
        else:
            continue
        if "voertuignummer" in label.casefold():
            continue
        href = absolute_url(base_url, anchor["href"])
        pages[href] = TomZuluPage(url=href, region=region)
    return sorted(pages.values(), key=lambda page: page.url)


class TomZuluSource:
    name = "tomzulu"

    def __init__(
        self,
        *,
        url: str = TOMZULU_URL,
        timeout: float = 30.0,
        delay: float = 0.35,
        homepage_file: Path | None = None,
        pages_dir: Path | None = None,
    ) -> None:
        self.url = url
        self.timeout = timeout
        self.delay = delay
        self.homepage_file = homepage_file
        self.pages_dir = pages_dir

    def _offline_load(self) -> list[SourceRecord]:
        assert self.homepage_file is not None
        homepage = read_html_file(self.homepage_file)
        pages = discover_tomzulu_pages(homepage, base_url=self.url)
        records: list[SourceRecord] = []
        if self.pages_dir is None:
            return records
        for page in pages:
            slug = page.url.rstrip("/").rsplit("/", 1)[-1]
            path = self.pages_dir / f"{slug}.html"
            if not path.exists():
                continue
            records.extend(
                parse_capcode_tables(
                    read_html_file(path),
                    source=self.name,
                    source_url=page.url,
                    default_region=page.region,
                    record_prefix=slug,
                )
            )
        return records

    def load(self) -> list[SourceRecord]:
        if self.homepage_file is not None:
            records = self._offline_load()
            if not records:
                raise RuntimeError("TomZulu offline fixtures returned no parseable capcodes")
            return records

        records: list[SourceRecord] = []
        with BrowserRenderer(timeout=self.timeout) as renderer:
            home = renderer.render(self.url)
            pages = discover_tomzulu_pages(home.main_html, base_url=self.url)
            if not pages:
                raise RuntimeError("Could not discover TomZulu region pages")

            for page_info in pages:
                page = renderer.render(page_info.url)
                documents = [(page.url, page.main_html), *page.frame_html]
                for frame_index, (source_url, html) in enumerate(documents):
                    records.extend(
                        parse_capcode_tables(
                            html,
                            source=self.name,
                            source_url=source_url or page_info.url,
                            default_region=page_info.region,
                            record_prefix=f"{page_info.region}:{frame_index}",
                        )
                    )
                if self.delay:
                    time.sleep(self.delay)

        if not records:
            raise RuntimeError("TomZulu returned no parseable capcodes")

        # The same embedded table can occasionally be exposed through more than one frame.
        unique: dict[tuple[str, str, str, str, str, str], SourceRecord] = {}
        for record in records:
            key = (
                record.capcode,
                record.discipline,
                record.region,
                record.location,
                record.description,
                record.remark,
            )
            unique.setdefault(key, record)
        return list(unique.values())
