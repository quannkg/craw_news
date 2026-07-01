from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class CrawlResult:
    fetched: int = 0
    inserted: int = 0
    skipped: int = 0
    failed: int = 0
