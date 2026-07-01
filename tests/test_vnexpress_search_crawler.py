from __future__ import annotations

import unittest

from app.crawlers.vnexpress_search_crawler import SEARCH_BASE_URL, VnExpressSearchCrawler


SAMPLE_SEARCH_HTML = """
<div id="result_search">
    <article class="item-news" data-url="https://vnexpress.net/keo-kera-gay-tranh-cai-123.html" data-publishtime="1719999999">
        <h3 class="title-news"><a href="https://vnexpress.net/keo-kera-gay-tranh-cai-123.html">Kẹo Kera gây tranh cãi</a></h3>
        <p class="description"><a href="/mo-ta">Bài mô tả hợp lệ</a></p>
        <div class="thumb-art"><img data-src="https://i1-vnexpress.vnecdn.net/image.jpg" /></div>
    </article>
    <article class="item-news" data-url="https://t.eclick.vn/ad-click">
        <h3 class="title-news"><a href="https://t.eclick.vn/ad-click">Quảng cáo</a></h3>
    </article>
    <article class="item-news" data-url="https://example.com/outside.html">
        <h3 class="title-news"><a href="https://example.com/outside.html">Link ngoài</a></h3>
    </article>
    <article class="item-news" data-url="https://vnexpress.net/keo-kera-gay-tranh-cai-123.html">
        <h3 class="title-news"><a href="https://vnexpress.net/keo-kera-gay-tranh-cai-123.html">Bài trùng URL</a></h3>
    </article>
</div>
<div class="pagination">
    <a href="/?q=k%E1%BA%B9o+Kera&p=2" class="next">Next</a>
</div>
"""


class FakeResponse:
    def __init__(self, text: str, url: str) -> None:
        self.text = text
        self.url = url

    def raise_for_status(self) -> None:
        return None


class FakeSession:
    def __init__(self) -> None:
        self.headers = {}
        self.calls: list[dict] = []

    def get(self, url, params=None, timeout=None):
        self.calls.append({"url": url, "params": params, "timeout": timeout})
        final_url = f"{url}?q=k%E1%BA%B9o+Kera" if params else url
        return FakeResponse(SAMPLE_SEARCH_HTML, final_url)


class VnExpressSearchCrawlerTestCase(unittest.TestCase):
    def test_extract_search_results_filters_invalid_links_and_duplicates(self) -> None:
        crawler = VnExpressSearchCrawler()
        results = crawler.extract_search_results(SAMPLE_SEARCH_HTML)

        self.assertEqual(1, len(results))
        self.assertEqual(
            "https://vnexpress.net/keo-kera-gay-tranh-cai-123.html",
            results[0].source_url,
        )
        self.assertEqual("Kẹo Kera gây tranh cãi", results[0].title)

    def test_resolve_next_search_page_uses_html_selector(self) -> None:
        crawler = VnExpressSearchCrawler()
        from app.utils.html_utils import parse_html

        resolved = crawler.resolve_next_search_page(
            parse_html(SAMPLE_SEARCH_HTML),
            "https://timkiem.vnexpress.net/?q=k%E1%BA%B9o+Kera",
        )
        self.assertIn("p=2", resolved)

    def test_search_request_uses_requests_params_for_unicode_keyword(self) -> None:
        session = FakeSession()
        crawler = VnExpressSearchCrawler(session=session)

        crawler.crawl_search_page(crawler.build_search_url("kẹo Kera"), "kẹo Kera")

        self.assertEqual(1, len(session.calls))
        self.assertEqual(SEARCH_BASE_URL, session.calls[0]["url"])
        self.assertEqual({"q": "kẹo Kera"}, session.calls[0]["params"])


if __name__ == "__main__":
    unittest.main()
