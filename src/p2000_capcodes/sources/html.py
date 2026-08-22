from __future__ import annotations

import re
from collections.abc import Iterable
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from p2000_capcodes.models import SourceRecord
from p2000_capcodes.normalize import clean, normalize_capcode

CAPCODE_RE = re.compile(r"(?<!\d)(\d{7,9})(?!\d)")
SERVICE_NAMES = (
    "Brandweer",
    "Ambulance",
    "Politie",
    "GHOR",
    "Bevolkingszorg",
    "Reddingsbrigade",
    "KNRM",
    "Kustwacht",
    "Multidisciplinair",
    "Defensie",
)

HEADER_ALIASES = {
    "capcode": {"capcode", "code", "pager", "pagercode"},
    "discipline": {"discipline", "hulpdienst", "dienst", "service"},
    "region": {"regio", "region", "veiligheidsregio"},
    "location": {"plaats", "locatie", "location", "korps", "post", "kazerne"},
    "description": {"omschrijving", "description", "functie", "benaming", "eenheid"},
    "remark": {"short", "opmerking", "remark", "roepnummer", "roepnr"},
}


def _header_key(value: str) -> str:
    value = clean(value).casefold().replace("-", " ").replace("_", " ")
    return " ".join(value.split())


def _header_mapping(headers: list[str]) -> dict[str, int]:
    mapping: dict[str, int] = {}
    for index, header in enumerate(headers):
        normalized = _header_key(header)
        for field, aliases in HEADER_ALIASES.items():
            if normalized in aliases:
                mapping[field] = index
                break
    return mapping


def _cell(cells: list[str], mapping: dict[str, int], field: str) -> str:
    index = mapping.get(field)
    if index is None or index >= len(cells):
        return ""
    return clean(cells[index])


def _infer_service(cells: Iterable[str]) -> str:
    for cell in cells:
        normalized = clean(cell).casefold()
        for service in SERVICE_NAMES:
            if normalized == service.casefold():
                return service
    return ""


def _find_capcode(cells: list[str], preferred_index: int | None = None) -> tuple[str, int] | None:
    indexes: Iterable[int]
    if preferred_index is not None and preferred_index < len(cells):
        indexes = [preferred_index, *[i for i in range(len(cells)) if i != preferred_index]]
    else:
        indexes = range(len(cells))
    for index in indexes:
        match = CAPCODE_RE.search(clean(cells[index]))
        if match:
            try:
                return normalize_capcode(match.group(1)), index
            except ValueError:
                continue
    return None


def parse_capcode_tables(
    html: str,
    *,
    source: str,
    source_url: str,
    default_region: str = "",
    record_prefix: str = "row",
) -> list[SourceRecord]:
    """Parse capcode rows from ordinary HTML tables.

    Header names are mapped when present. A conservative fallback is used for
    tables without useful headers: capcode + exact service name are detected,
    while the remaining text is preserved as description instead of guessing
    locations or regions.
    """

    soup = BeautifulSoup(html, "html.parser")
    records: list[SourceRecord] = []
    seen: set[tuple[str, str, str, str, str, str]] = set()

    for table_index, table in enumerate(soup.find_all("table"), 1):
        rows = table.find_all("tr")
        if not rows:
            continue

        headers: list[str] = []
        header_row = table.find("thead")
        if header_row:
            headers = [
                clean(cell.get_text(" ", strip=True))
                for cell in header_row.find_all(["th", "td"])
            ]
        elif rows:
            first = rows[0].find_all("th")
            if first:
                headers = [clean(cell.get_text(" ", strip=True)) for cell in first]
        mapping = _header_mapping(headers)

        for row_index, row in enumerate(rows, 1):
            cells = [clean(cell.get_text(" ", strip=True)) for cell in row.find_all(["td", "th"])]
            if not cells:
                continue
            found = _find_capcode(cells, mapping.get("capcode"))
            if found is None:
                continue
            capcode, capcode_index = found

            discipline = _cell(cells, mapping, "discipline") or _infer_service(cells)
            region = _cell(cells, mapping, "region") or default_region
            location = _cell(cells, mapping, "location")
            description = _cell(cells, mapping, "description")
            remark = _cell(cells, mapping, "remark")

            if not description:
                excluded = {capcode_index}
                excluded.update(mapping.values())
                remainder = [
                    value
                    for index, value in enumerate(cells)
                    if index not in excluded and value and value != discipline and value != region
                ]
                description = " | ".join(remainder)

            signature = (capcode, discipline, region, location, description, remark)
            if signature in seen:
                continue
            seen.add(signature)
            records.append(
                SourceRecord(
                    capcode=capcode,
                    source=source,
                    discipline=discipline,
                    region=region,
                    location=location,
                    description=description,
                    remark=remark,
                    source_url=source_url,
                    source_record_id=f"{record_prefix}:{table_index}:{row_index}",
                    raw=tuple(cells),
                )
            )
    return records


@dataclass(slots=True)
class RenderedPage:
    url: str
    main_html: str
    frame_html: list[tuple[str, str]]


class BrowserRenderer:
    """Small Playwright wrapper used only by scrape-enabled source providers."""

    def __init__(self, *, timeout: float = 30.0) -> None:
        self.timeout_ms = int(timeout * 1000)
        self._playwright = None
        self._browser = None

    def __enter__(self) -> BrowserRenderer:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:  # pragma: no cover - depends on optional extra
            raise RuntimeError(
                "Playwright is required for web sources; install p2000-capcodes[scrape]"
            ) from exc
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=True)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._browser is not None:
            self._browser.close()
        if self._playwright is not None:
            self._playwright.stop()

    def render(self, url: str, *, wait_selector: str | None = None) -> RenderedPage:
        assert self._browser is not None
        page = self._browser.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=self.timeout_ms)
            if wait_selector:
                # Some sites render an empty table when no selector becomes visible.
                with suppress(Exception):
                    page.wait_for_selector(wait_selector, timeout=self.timeout_ms)
            with suppress(Exception):
                page.wait_for_load_state("networkidle", timeout=min(self.timeout_ms, 10000))
            frame_html: list[tuple[str, str]] = []
            for frame in page.frames:
                if frame == page.main_frame:
                    continue
                try:
                    frame_html.append((frame.url, frame.content()))
                except Exception:
                    continue
            return RenderedPage(url=page.url, main_html=page.content(), frame_html=frame_html)
        finally:
            page.close()

    def render_table_pages(self, url: str) -> list[str]:
        """Render all visible pages of a DataTables-like table.

        The method first tries to select an "all"/largest page size. If pagination
        remains, it walks the Next control and returns one HTML snapshot per page.
        """

        assert self._browser is not None
        page = self._browser.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=self.timeout_ms)
            try:
                page.wait_for_selector("table tbody tr", timeout=self.timeout_ms)
            except Exception:
                return [page.content()]

            for selector in (".dataTables_length select", 'select[name$="_length"]'):
                control = page.locator(selector).first
                if not control.count():
                    continue
                try:
                    options = control.locator("option").evaluate_all(
                        "els => els.map(e => ({value: e.value, text: e.textContent}))"
                    )
                    values = [str(option["value"]) for option in options]
                    if "-1" in values:
                        control.select_option("-1")
                    else:
                        numeric = [int(value) for value in values if value.isdigit()]
                        if numeric:
                            control.select_option(str(max(numeric)))
                    page.wait_for_timeout(500)
                    break
                except Exception:
                    continue

            snapshots: list[str] = []
            seen_first_rows: set[str] = set()
            for _ in range(1000):
                first_row = ""
                rows = page.locator("table tbody tr")
                if rows.count():
                    first_row = clean(rows.first.inner_text())
                if first_row in seen_first_rows and first_row:
                    break
                if first_row:
                    seen_first_rows.add(first_row)
                snapshots.append(page.content())

                next_control = None
                for selector in (
                    ".dataTables_paginate .next:not(.disabled)",
                    "a.paginate_button.next:not(.disabled)",
                    'button[aria-label="Next"]:not([disabled])',
                    'button[aria-label="Volgende"]:not([disabled])',
                ):
                    candidate = page.locator(selector).first
                    if candidate.count() and candidate.is_visible():
                        next_control = candidate
                        break
                if next_control is None:
                    break
                try:
                    next_control.click()
                    page.wait_for_timeout(250)
                except Exception:
                    break
            return snapshots
        finally:
            page.close()


def read_html_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def absolute_url(base: str, href: str) -> str:
    return urljoin(base, href)
