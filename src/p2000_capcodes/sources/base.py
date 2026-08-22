from __future__ import annotations

from typing import Protocol

from p2000_capcodes.models import SourceRecord


class Source(Protocol):
    name: str

    def load(self) -> list[SourceRecord]: ...
