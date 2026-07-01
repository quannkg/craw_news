from __future__ import annotations

from dataclasses import dataclass
from random import uniform
from time import sleep

import requests

from app.utils.html_utils import get_text, parse_html
from app.utils.url_utils import is_vnexpress_url, normalize_url


@dataclass(slots=True)
class CategoryArticleSummary:
    title: str
    source_url: str
    description: str
    thumbnail_url: str


@dataclass(slots=True)
class CategoryPageResult:
    page_url: str
    next_page_url: str
    articles: list[CategoryArticleSummary]


class VnExpressCategoryCrawler:
    def __init__(self, session: requests.Session | None = None, timeout: int = 20) -> None:
        self.timeout = timeout
        self.session = session or requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/126.0 Safari/537.36"
                )
            }
        )

    def crawl_page(self, page_url: str) -> CategoryPageResult:
        response = self.session.get(page_url, timeout=self.timeout)
        response.raise_for_status()
        soup = parse_html(response.text)
        items = soup.select("article.item-news")
        articles: list[CategoryArticleSummary] = []
        seen_urls: set[str] = set()

        for item in items:
            link = self._pick_link(item)
            if not link:
                continue
            source_url = normalize_url(page_url, link.get("href", ""))
            if not self._is_valid_article_url(source_url):
                continue
            if source_url in seen_urls:
                continue

            title = get_text(link)
            description = self._pick_description(item)
            thumbnail_url = self._pick_thumbnail(item, page_url)
            seen_urls.add(source_url)
            articles.append(
                CategoryArticleSummary(
                    title=title,
                    source_url=source_url,
                    description=description,
                    thumbnail_url=thumbnail_url,
                )
            )

        next_page_url = ""
        next_page = soup.select_one("a.btn-page.next-page")
        if next_page is not None:
            next_href = next_page.get("href", "").strip()
            if next_href:
                next_page_url = normalize_url(page_url, next_href)

        return CategoryPageResult(
            page_url=page_url,
            next_page_url=next_page_url,
            articles=articles,
        )

    def sleep_between_requests(self) -> None:
        sleep(uniform(0.8, 1.5))

    def _pick_link(self, item):
        for selector in ["h3.title-news a", "h2.title-news a", "h4.title-news a"]:
            node = item.select_one(selector)
            if node is not None and node.get("href"):
                return node
        return None

    def _pick_description(self, item) -> str:
        node = item.select_one("p.description a") or item.select_one("p.description")
        return get_text(node)

    def _pick_thumbnail(self, item, base_url: str) -> str:
        image = item.select_one(".thumb-art img")
        if image is None:
            return ""
        image_url = image.get("data-src", "").strip() or image.get("src", "").strip()
        if not image_url or image_url.startswith("data:image"):
            return ""
        if "placeholder" in image_url.lower():
            return ""
        return normalize_url(base_url, image_url)

    def _is_valid_article_url(self, url: str) -> bool:
        normalized = url.lower()
        if not is_vnexpress_url(normalized):
            return False
        if ".html" not in normalized:
            return False
        if "#" in normalized:
            return False
        blocked_keywords = ("quang-cao", "advertisement")
        return not any(keyword in normalized for keyword in blocked_keywords)
