from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Category:
    name: str
    url: str
    slug: str
    category_type: str
    parent_id: int | None = None
