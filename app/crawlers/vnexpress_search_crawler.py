from __future__ import annotations

from dataclasses import dataclass
from random import uniform
from time import sleep
from urllib.parse import urlencode

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.utils.html_utils import get_text, parse_html
from app.utils.url_utils import is_vnexpress_url, normalize_url


SEARCH_BASE_URL = "https://timkiem.vnexpress.net"


@dataclass(slots=True)
class SearchArticleSummary:
    source_url: str
    title: str
    description: str
    thumbnail_url: str
    published_timestamp_raw: str


@dataclass(slots=True)
class SearchPageResult:
    page_url: str
    keyword: str
    articles: list[SearchArticleSummary]
    next_page_url: str


class VnExpressSearchCrawler:
    def __init__(self, session: requests.Session | None = None, timeout: tuple[int, int] = (15, 45)) -> None:
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
        if session is None:
            retry = Retry(
                total=3,
                connect=3,
                read=3,
                backoff_factor=1.2,
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=["GET"],
            )
            adapter = HTTPAdapter(max_retries=retry)
            self.session.mount("https://", adapter)
            self.session.mount("http://", adapter)

    def search_articles(
        self,
        keyword: str,
        max_pages: int,
        max_articles: int,
    ) -> list[SearchPageResult]:
        results: list[SearchPageResult] = []
        visited_urls: set[str] = set()
        search_url = self.build_search_url(keyword)
        current_url = search_url

        while current_url and len(results) < max_pages:
            if current_url in visited_urls:
                break
            visited_urls.add(current_url)
            page_result = self.crawl_search_page(current_url, keyword)
            results.append(page_result)
            total_articles = sum(len(page.articles) for page in results)
            if max_articles > 0 and total_articles >= max_articles:
                break
            if not page_result.next_page_url:
                break
            current_url = page_result.next_page_url
            self.sleep_between_requests()

        return results

    def crawl_search_page(self, search_url: str, keyword: str) -> SearchPageResult:
        try:
            response = self.session.get(
                SEARCH_BASE_URL,
                params={"q": keyword},
                timeout=self.timeout,
            ) if search_url == self.build_search_url(keyword) else self.session.get(
                search_url,
                timeout=self.timeout,
            )
        except requests.exceptions.Timeout as exc:
            raise RuntimeError(
                "Kết nối tới trang tìm kiếm VnExpress bị timeout. "
                "Hãy thử lại sau hoặc giảm số trang tối đa."
            ) from exc
        except requests.exceptions.RequestException as exc:
            raise RuntimeError(
                f"Không tải được trang tìm kiếm VnExpress: {exc}"
            ) from exc
        response.raise_for_status()
        soup = parse_html(response.text)
        articles = self.extract_search_results(response.text)
        next_page_url = self.resolve_next_search_page(soup, str(response.url))
        return SearchPageResult(
            page_url=str(response.url),
            keyword=keyword,
            articles=articles,
            next_page_url=next_page_url,
        )

    def extract_search_results(self, html: str) -> list[SearchArticleSummary]:
        soup = parse_html(html)
        container = soup.select_one("#result_search")
        if container is None:
            return []

        articles: list[SearchArticleSummary] = []
        seen_urls: set[str] = set()
        for item in container.select("article.item-news[data-url]"):
            source_url = item.get("data-url", "").strip()
            if not source_url:
                link = item.select_one("h3.title-news a[href]") or item.select_one("h2.title-news a[href]")
                source_url = link.get("href", "").strip() if link is not None else ""
            if not self.is_valid_vnexpress_article_url(source_url):
                continue
            if source_url in seen_urls:
                continue

            title_node = item.select_one("h3.title-news a") or item.select_one("h2.title-news a")
            title = get_text(title_node)
            if not title:
                continue

            description_node = item.select_one("p.description a") or item.select_one("p.description")
            description = get_text(description_node)
            thumbnail_url = self._pick_thumbnail(item, source_url)
            seen_urls.add(source_url)
            articles.append(
                SearchArticleSummary(
                    source_url=source_url,
                    title=title,
                    description=description,
                    thumbnail_url=thumbnail_url,
                    published_timestamp_raw=item.get("data-publishtime", "").strip(),
                )
            )
        return articles

    def resolve_next_search_page(self, soup, current_url: str) -> str:
        candidate_selectors = [
            "a[rel='next']",
            "a.btn-page.next-page",
            ".page-next a",
            ".pagination a",
        ]
        for selector in candidate_selectors:
            for link in soup.select(selector):
                href = link.get("href", "").strip()
                if not href:
                    continue
                label = get_text(link).lower()
                rel = " ".join(link.get("rel", [])).lower()
                classes = " ".join(link.get("class", [])).lower()
                if selector == ".pagination a":
                    if "next" not in label and "next" not in rel and "next" not in classes:
                        continue
                next_url = normalize_url(current_url, href)
                if next_url != current_url:
                    return next_url
        return ""

    def is_valid_vnexpress_article_url(self, url: str) -> bool:
        normalized = url.strip().lower()
        if not normalized:
            return False
        if not is_vnexpress_url(normalized):
            return False
        if ".html" not in normalized:
            return False
        blocked_keywords = ("t.eclick.vn", "smartads", "quang-cao", "advertisement")
        return not any(keyword in normalized for keyword in blocked_keywords)

    def build_search_url(self, keyword: str) -> str:
        return f"{SEARCH_BASE_URL}?{urlencode({'q': keyword})}"

    def sleep_between_requests(self) -> None:
        sleep(uniform(0.8, 1.5))

    def _pick_thumbnail(self, item, base_url: str) -> str:
        image = item.select_one(".thumb-art img")
        candidates: list[str] = []
        if image is not None:
            candidates.extend(
                [
                    image.get("data-src", "").strip(),
                    image.get("src", "").strip(),
                ]
            )
        for source_tag in item.select(".thumb-art source"):
            candidates.extend(
                [
                    source_tag.get("srcset", "").strip().split(" ")[0],
                    source_tag.get("data-srcset", "").strip().split(" ")[0],
                ]
            )
        for candidate in candidates:
            if not candidate:
                continue
            normalized = candidate.lower()
            if normalized.startswith("data:image") or "placeholder" in normalized or "base64" in normalized:
                continue
            return normalize_url(base_url, candidate)
        return ""
