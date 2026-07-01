from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class Article:
    source: str
    title: str
    source_url: str
    description: str = ""
    content: str = ""
    author: str = ""
    thumbnail_url: str = ""
    category: str = ""
    category_id: int | None = None
    search_published_timestamp_raw: str = ""
    published_time_text: str = ""
    published_at: str = ""
    crawled_at: str = ""
    updated_at: str = ""

    def ensure_crawled_at(self) -> None:
        if not self.crawled_at:
            self.crawled_at = datetime.now().isoformat(timespec="seconds")

    @property
    def url(self) -> str:
        return self.source_url

    @property
    def summary(self) -> str:
        return self.description
