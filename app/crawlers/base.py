from __future__ import annotations

from abc import ABC, abstractmethod

from app.models.article import Article


class BaseCrawler(ABC):
    source_name: str = ""

    @abstractmethod
    def crawl(self, url: str) -> list[Article]:
        raise NotImplementedError
