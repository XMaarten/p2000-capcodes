from __future__ import annotations

import csv
import hashlib
import io
from dataclasses import dataclass
from pathlib import Path

import requests

from p2000_capcodes.models import SourceRecord
from p2000_capcodes.normalize import clean, normalize_capcode

BOMMEL_URL = "https://p2000.bommel.net/cap2csv.php"
BOMMEL_HOME = "https://p2000.bommel.net/"


@dataclass(slots=True)
class DownloadInfo:
    url: str
    sha256: str
    size: int


class BommelSource:
    name = "bommel"

    def __init__(
        self,
        *,
        url: str = BOMMEL_URL,
        timeout: float = 30.0,
        file: Path | None = None,
    ) -> None:
        self.url = url
        self.timeout = timeout
        self.file = file
        self.download_info: DownloadInfo | None = None

    def _payload(self) -> bytes:
        if self.file is not None:
            payload = self.file.read_bytes()
            source_url = self.file.as_uri() if self.file.is_absolute() else str(self.file)
        else:
            response = requests.get(
                self.url,
                timeout=self.timeout,
                headers={"User-Agent": "p2000-capcodes/0.1 (+https://github.com/XMaarten)"},
            )
            response.raise_for_status()
            payload = response.content
            source_url = self.url

        self.download_info = DownloadInfo(
            url=source_url,
            sha256=hashlib.sha256(payload).hexdigest(),
            size=len(payload),
        )
        return payload

    def load(self) -> list[SourceRecord]:
        return parse_bommel_csv(self._payload(), source_url=self.url)


def _decode(payload: bytes) -> str:
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return payload.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("Could not decode Bommel CSV")


def parse_bommel_csv(payload: bytes, *, source_url: str = BOMMEL_URL) -> list[SourceRecord]:
    text = _decode(payload)
    sample = text[:16384]
    dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
    rows = csv.reader(io.StringIO(text), dialect=dialect)

    result: list[SourceRecord] = []
    for line_number, row in enumerate(rows, 1):
        if not row:
            continue
        first = clean(row[0])
        if first.casefold() == "capcode":
            continue
        try:
            capcode = normalize_capcode(first)
        except ValueError:
            continue

        values = [clean(value) for value in row]
        # The current CSV export contains 6 columns:
        # capcode, discipline, region, location/korps, description, short.
        # The documentation also describes a 7-column form with region_code.
        if len(values) >= 7:
            discipline, region, region_code, location, description, remark = values[1:7]
        else:
            values.extend([""] * max(0, 6 - len(values)))
            discipline, region, location, description, remark = values[1:6]
            region_code = ""

        result.append(
            SourceRecord(
                capcode=capcode,
                source="bommel",
                discipline=discipline,
                region=region,
                region_code=region_code,
                location=location,
                description=description,
                remark=remark,
                source_url=source_url,
                source_record_id=f"line:{line_number}",
                raw=tuple(values),
            )
        )
    return result
