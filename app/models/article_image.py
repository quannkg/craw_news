from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ArticleImage:
    article_id: int
    image_url: str
    caption: str = ""
    display_order: int = 0
