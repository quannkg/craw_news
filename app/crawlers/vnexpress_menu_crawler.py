from __future__ import annotations

from dataclasses import dataclass

import requests

from app.models.category import Category
from app.utils.html_utils import get_text, parse_html
from app.utils.url_utils import (
    is_valid_vnexpress_category_url,
    normalize_url,
    slug_from_url,
)


VNEXPRESS_HOME = "https://vnexpress.net"


@dataclass(slots=True)
class CategoryNode:
    category: Category
    children: list[Category]


class VnExpressMenuCrawler:
    def __init__(self, timeout: int = 20) -> None:
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/126.0 Safari/537.36"
                )
            }
        )

    def crawl(self, url: str = VNEXPRESS_HOME) -> list[CategoryNode]:
        response = self.session.get(url, timeout=self.timeout)
        response.raise_for_status()
        soup = parse_html(response.text)
        items = soup.select("ul.parent > li")
        result: list[CategoryNode] = []
        seen_urls: set[str] = set()

        for item in items:
            classes = item.get("class", [])
            if "home" in classes or "all-menu" in classes:
                continue

            parent_link = item.select_one(":scope > a")
            if parent_link is None:
                continue

            parent_name = get_text(parent_link)
            parent_url = normalize_url(url, parent_link.get("href", ""))
            if not parent_name or not is_valid_vnexpress_category_url(parent_url):
                continue
            if parent_url in seen_urls:
                continue

            seen_urls.add(parent_url)
            parent_category = Category(
                name=parent_name,
                url=parent_url,
                slug=slug_from_url(parent_url),
                category_type="MAIN",
            )

            children: list[Category] = []
            child_seen: set[str] = set()
            for child_link in item.select("ul.sub li > a"):
                child_name = get_text(child_link)
                child_url = normalize_url(url, child_link.get("href", ""))
                if not child_name or not is_valid_vnexpress_category_url(child_url):
                    continue
                if child_url in child_seen:
                    continue
                child_seen.add(child_url)
                children.append(
                    Category(
                        name=child_name,
                        url=child_url,
                        slug=slug_from_url(child_url),
                        category_type="SUB",
                    )
                )

            result.append(CategoryNode(category=parent_category, children=children))

        return result
