from __future__ import annotations

from app.db.article_repository import ArticleRepository
from app.services.vnexpress_crawl_service import VnExpressCrawlService


class CrawlService:
    def __init__(self) -> None:
        self.repository = ArticleRepository()
        self.vnexpress_service = VnExpressCrawlService()

    def crawl_source(
        self,
        source_name: str,
        url: str,
        crawl_type: str = "article",
        max_pages: int = 1,
        max_articles: int = 0,
        crawl_comments: bool = False,
        force_refresh: bool = False,
    ) -> dict:
        if source_name != "vnexpress":
            raise ValueError(f"Nguồn không được hỗ trợ: {source_name}")
        return self._crawl_vnexpress(
            crawl_type=crawl_type,
            url=url,
            max_pages=max_pages,
            max_articles=max_articles,
            crawl_comments=crawl_comments,
            force_refresh=force_refresh,
        )

    def list_recent_articles(self, limit: int = 100) -> list[dict]:
        return self.repository.list_recent_articles(limit=limit)

    def list_articles_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        keyword: str = "",
        category: str = "",
        source: str = "",
    ) -> dict:
        return self.repository.list_articles_paginated(
            page=page,
            page_size=page_size,
            keyword=keyword,
            category=category,
            source=source,
        )

    def list_article_categories(self) -> list[str]:
        return self.repository.list_categories()

    def get_article_detail(self, article_id: int) -> dict | None:
        return self.repository.get_article_detail(article_id)

    def search_local_articles(
        self,
        keyword: str,
        category_id: int | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        return self.repository.search_articles(
            keyword=keyword,
            category_id=category_id,
            limit=limit,
            offset=offset,
        )

    def count_local_search_articles(
        self,
        keyword: str,
        category_id: int | None = None,
    ) -> int:
        return self.repository.count_search_articles(
            keyword=keyword,
            category_id=category_id,
        )

    def delete_articles_by_ids(self, article_ids: list[int]) -> int:
        return self.repository.delete_articles_by_ids(article_ids)

    def stop_current_crawl(self, source_name: str) -> None:
        if source_name == "vnexpress":
            self.vnexpress_service.stop_current_crawl()

    def get_crawl_progress(self, source_name: str) -> dict:
        if source_name == "vnexpress":
            return self.vnexpress_service.get_crawl_progress()
        return {}

    def _crawl_vnexpress(
        self,
        crawl_type: str,
        url: str,
        max_pages: int,
        max_articles: int,
        crawl_comments: bool,
        force_refresh: bool,
    ) -> dict:
        if crawl_type == "menu":
            return self.vnexpress_service.crawl_menu()
        if crawl_type == "keyword":
            return self.vnexpress_service.crawl_keyword(
                keyword=url,
                max_pages=max_pages,
                max_articles=max_articles,
                crawl_comments=crawl_comments,
                force_refresh=force_refresh,
            )
        if crawl_type == "category":
            return self.vnexpress_service.crawl_category(
                category_url=url,
                max_pages=max_pages,
                max_articles=max_articles,
                crawl_comments=crawl_comments,
                force_refresh=force_refresh,
            )
        return self.vnexpress_service.crawl_article(
            article_url=url,
            crawl_comments=crawl_comments,
            force_refresh=force_refresh,
        )
