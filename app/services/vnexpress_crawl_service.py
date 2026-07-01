from __future__ import annotations

from dataclasses import asdict
from threading import Event

from app.crawlers.vnexpress_article_crawler import VnExpressArticleCrawler
from app.crawlers.vnexpress_category_crawler import VnExpressCategoryCrawler
from app.crawlers.vnexpress_comment_crawler import VnExpressCommentCrawler
from app.crawlers.vnexpress_menu_crawler import VnExpressMenuCrawler
from app.crawlers.vnexpress_search_crawler import VnExpressSearchCrawler
from app.db.article_image_repository import ArticleImageRepository
from app.db.article_repository import ArticleRepository
from app.db.category_repository import CategoryRepository
from app.db.comment_repository import CommentRepository
from app.db.crawl_log_repository import CrawlLogRepository
from app.models.crawl_result import CrawlResult


class VnExpressCrawlService:
    def __init__(self) -> None:
        self.category_repository = CategoryRepository()
        self.article_repository = ArticleRepository()
        self.article_image_repository = ArticleImageRepository()
        self.comment_repository = CommentRepository()
        self.crawl_log_repository = CrawlLogRepository()
        self.menu_crawler = VnExpressMenuCrawler()
        self.category_crawler = VnExpressCategoryCrawler()
        self.article_crawler = VnExpressArticleCrawler()
        self.search_crawler = VnExpressSearchCrawler()
        self.comment_crawler = VnExpressCommentCrawler()
        self.stop_event = Event()
        self.progress = {
            "current_url": "",
            "total_pages": 0,
            "crawled_pages": 0,
            "total_articles": 0,
            "crawled_articles": 0,
            "failed_articles": 0,
            "comment_error": "",
            "last_error": "",
            "last_error_type": "",
            "last_error_url": "",
            "last_error_title": "",
        }

    def crawl_menu(self) -> dict:
        self.stop_event.clear()
        nodes = self.menu_crawler.crawl()
        saved_main = 0
        saved_sub = 0

        for node in nodes:
            parent_id = self.category_repository.upsert_category(node.category)
            saved_main += 1
            for child in node.children:
                child.parent_id = parent_id
                self.category_repository.upsert_category(child)
                saved_sub += 1

        return {
            "main_categories": saved_main,
            "sub_categories": saved_sub,
            "total": saved_main + saved_sub,
        }

    def crawl_category(
        self,
        category_url: str,
        max_pages: int,
        max_articles: int,
        crawl_comments: bool,
        force_refresh: bool,
    ) -> dict:
        self.stop_event.clear()
        self.progress.update(
            {
                "current_url": category_url,
                "total_pages": max_pages,
                "crawled_pages": 0,
                "total_articles": 0,
                "crawled_articles": 0,
                "failed_articles": 0,
                "comment_error": "",
                "last_error": "",
                "last_error_type": "",
                "last_error_url": "",
                "last_error_title": "",
            }
        )
        log_id = self.crawl_log_repository.start_log("CATEGORY", category_url)
        result = CrawlResult()
        visited_pages: set[str] = set()
        visited_articles: set[str] = set()
        current_url = category_url
        crawled_pages = 0

        try:
            comment_context = self.comment_crawler if crawl_comments else None
            if comment_context is not None:
                comment_context.open()
            while current_url and crawled_pages < max_pages and not self.stop_event.is_set():
                if current_url in visited_pages:
                    break
                visited_pages.add(current_url)
                self.progress["current_url"] = current_url
                page_result = self._crawl_category_page(
                    current_url=current_url,
                    visited_articles=visited_articles,
                    max_articles=max_articles,
                    crawl_comments=crawl_comments,
                    force_refresh=force_refresh,
                    result=result,
                )
                crawled_pages += 1
                self.progress["crawled_pages"] = crawled_pages
                current_url = page_result["next_page_url"]
                if max_articles > 0 and result.fetched >= max_articles:
                    break
                if current_url:
                    self.category_crawler.sleep_between_requests()

            self.crawl_log_repository.finish_log(
                log_id=log_id,
                status="STOPPED" if self.stop_event.is_set() else "SUCCESS",
                total_pages=max_pages,
                crawled_pages=crawled_pages,
                total_articles=result.fetched,
                crawled_articles=result.inserted,
                failed_articles=result.failed,
            )
            return asdict(result)
        except Exception as exc:
            self.crawl_log_repository.finish_log(
                log_id=log_id,
                status="FAILED",
                total_pages=max_pages,
                crawled_pages=crawled_pages,
                total_articles=result.fetched,
                crawled_articles=result.inserted,
                failed_articles=result.failed,
                error_message=str(exc),
            )
            raise
        finally:
            if crawl_comments:
                self.comment_crawler.close()

    def crawl_article(
        self,
        article_url: str,
        crawl_comments: bool,
        force_refresh: bool,
    ) -> dict:
        self.stop_event.clear()
        self.progress.update(
            {
                "current_url": article_url,
                "total_pages": 1,
                "crawled_pages": 1,
                "total_articles": 1,
                "crawled_articles": 0,
                "failed_articles": 0,
                "comment_error": "",
                "last_error": "",
                "last_error_type": "",
                "last_error_url": "",
                "last_error_title": "",
            }
        )
        log_id = self.crawl_log_repository.start_log("ARTICLE", article_url)
        result = CrawlResult()
        try:
            if crawl_comments:
                self.comment_crawler.open()
            article_id, inserted = self._save_article_detail(
                article_url=article_url,
                category="",
                category_id=None,
                crawl_comments=crawl_comments,
                force_refresh=force_refresh,
            )
            result.fetched = 1
            result.inserted = 1 if inserted else 0
            result.skipped = 0 if inserted else 1
            self.progress["crawled_articles"] = 1
            self.crawl_log_repository.finish_log(
                log_id=log_id,
                status="SUCCESS",
                total_pages=1,
                crawled_pages=1,
                total_articles=1,
                crawled_articles=1,
                failed_articles=0,
            )
            return {"article_id": article_id, **asdict(result)}
        except Exception as exc:
            self.progress["failed_articles"] = 1
            self.crawl_log_repository.finish_log(
                log_id=log_id,
                status="FAILED",
                total_pages=1,
                crawled_pages=1,
                total_articles=1,
                crawled_articles=0,
                failed_articles=1,
                error_message=str(exc),
            )
            raise
        finally:
            if crawl_comments:
                self.comment_crawler.close()

    def crawl_keyword(
        self,
        keyword: str,
        max_pages: int,
        max_articles: int,
        crawl_comments: bool,
        force_refresh: bool,
    ) -> dict:
        self.stop_event.clear()
        search_url = self.search_crawler.build_search_url(keyword)
        self.progress.update(
            {
                "current_url": search_url,
                "keyword": keyword,
                "status_text": f"Đang tìm kiếm từ khóa: {keyword}",
                "current_article_title": "",
                "page_results": 0,
                "total_pages": max_pages,
                "crawled_pages": 0,
                "total_articles": 0,
                "crawled_articles": 0,
                "failed_articles": 0,
                "comment_error": "",
                "last_error": "",
                "last_error_type": "",
                "last_error_url": "",
                "last_error_title": "",
            }
        )
        log_id = self.crawl_log_repository.start_log("KEYWORD", search_url, keyword=keyword)
        result = CrawlResult()
        visited_pages: set[str] = set()
        visited_articles: set[str] = set()
        current_url = search_url
        crawled_pages = 0

        try:
            if crawl_comments:
                self.comment_crawler.open()
            while current_url and crawled_pages < max_pages and not self.stop_event.is_set():
                if current_url in visited_pages:
                    break
                visited_pages.add(current_url)
                page_result = self.search_crawler.crawl_search_page(current_url, keyword)
                self.progress["current_url"] = page_result.page_url
                self.progress["page_results"] = len(page_result.articles)
                self.progress["status_text"] = (
                    f"Đã lấy {len(page_result.articles)} kết quả từ trang {crawled_pages + 1}"
                )
                for article_summary in page_result.articles:
                    if self.stop_event.is_set():
                        break
                    if article_summary.source_url in visited_articles:
                        continue
                    if max_articles > 0 and result.fetched >= max_articles:
                        break

                    visited_articles.add(article_summary.source_url)
                    result.fetched += 1
                    self.progress["total_articles"] = result.fetched
                    self.progress["current_article_title"] = article_summary.title
                    self.progress["status_text"] = f"Đang crawl bài: {article_summary.title}"
                    try:
                        _, inserted = self._save_article_detail(
                            article_url=article_summary.source_url,
                            category="",
                            category_id=None,
                            crawl_comments=crawl_comments,
                            force_refresh=force_refresh,
                            search_published_timestamp_raw=article_summary.published_timestamp_raw,
                            fallback_title=article_summary.title,
                            fallback_description=article_summary.description,
                            fallback_thumbnail_url=article_summary.thumbnail_url,
                        )
                        if inserted:
                            result.inserted += 1
                        else:
                            result.skipped += 1
                        self.progress["crawled_articles"] = result.inserted + result.skipped
                    except Exception as exc:
                        result.failed += 1
                        self.progress["failed_articles"] = result.failed
                        self.progress["status_text"] = f"Lỗi bài: {article_summary.title}"
                        self.progress["last_error"] = str(exc)
                        self.progress["last_error_type"] = "article"
                        self.progress["last_error_url"] = article_summary.source_url
                        self.progress["last_error_title"] = article_summary.title
                        self.crawl_log_repository.finish_log(
                            log_id=log_id,
                            status="FAILED_ARTICLE",
                            total_pages=max_pages,
                            crawled_pages=crawled_pages,
                            total_articles=result.fetched,
                            crawled_articles=result.inserted,
                            failed_articles=result.failed,
                            error_message=str(exc),
                        )

                crawled_pages += 1
                self.progress["crawled_pages"] = crawled_pages
                current_url = page_result.next_page_url
                if max_articles > 0 and result.fetched >= max_articles:
                    break
                if current_url:
                    self.search_crawler.sleep_between_requests()

            self.crawl_log_repository.finish_log(
                log_id=log_id,
                status="STOPPED" if self.stop_event.is_set() else "SUCCESS",
                total_pages=max_pages,
                crawled_pages=crawled_pages,
                total_articles=result.fetched,
                crawled_articles=result.inserted,
                failed_articles=result.failed,
            )
            return asdict(result)
        except Exception as exc:
            self.crawl_log_repository.finish_log(
                log_id=log_id,
                status="FAILED",
                total_pages=max_pages,
                crawled_pages=crawled_pages,
                total_articles=result.fetched,
                crawled_articles=result.inserted,
                failed_articles=result.failed,
                error_message=str(exc),
            )
            self.progress["last_error"] = str(exc)
            self.progress["last_error_type"] = "search"
            self.progress["last_error_url"] = current_url
            self.progress["last_error_title"] = ""
            raise
        finally:
            if crawl_comments:
                self.comment_crawler.close()

    def stop_current_crawl(self) -> None:
        self.stop_event.set()

    def get_crawl_progress(self) -> dict:
        return dict(self.progress)

    def _crawl_category_page(
        self,
        current_url: str,
        visited_articles: set[str],
        max_articles: int,
        crawl_comments: bool,
        force_refresh: bool,
        result: CrawlResult,
    ) -> dict:
        page_result = self.category_crawler.crawl_page(current_url)
        for article_summary in page_result.articles:
            if self.stop_event.is_set():
                break
            if article_summary.source_url in visited_articles:
                continue
            if max_articles > 0 and result.fetched >= max_articles:
                break

            visited_articles.add(article_summary.source_url)
            result.fetched += 1
            self.progress["total_articles"] = result.fetched
            try:
                _, inserted = self._save_article_detail(
                    article_url=article_summary.source_url,
                    category="",
                    category_id=None,
                    crawl_comments=crawl_comments,
                    force_refresh=force_refresh,
                )
                if inserted:
                    result.inserted += 1
                else:
                    result.skipped += 1
                self.progress["crawled_articles"] = result.inserted + result.skipped
            except Exception:
                result.failed += 1
                self.progress["failed_articles"] = result.failed
                self.progress["last_error"] = "Lỗi khi crawl bài trong category."
                self.progress["last_error_type"] = "article"
                self.progress["last_error_url"] = article_summary.source_url
                self.progress["last_error_title"] = article_summary.title
        return {"next_page_url": page_result.next_page_url}

    def _save_article_detail(
        self,
        article_url: str,
        category: str,
        category_id: int | None,
        crawl_comments: bool,
        force_refresh: bool,
        search_published_timestamp_raw: str = "",
        fallback_title: str = "",
        fallback_description: str = "",
        fallback_thumbnail_url: str = "",
    ) -> tuple[int, bool]:
        detail = self.article_crawler.crawl(
            article_url=article_url,
            category=category,
            category_id=category_id,
        )
        if not detail.article.title:
            detail.article.title = fallback_title
        if not detail.article.description:
            detail.article.description = fallback_description
        if not detail.article.thumbnail_url:
            detail.article.thumbnail_url = fallback_thumbnail_url
        detail.article.search_published_timestamp_raw = search_published_timestamp_raw
        article_id, inserted = self.article_repository.upsert_article(
            detail.article,
            force_refresh=force_refresh,
        )
        self.article_image_repository.replace_images(article_id, detail.images)
        if crawl_comments:
            try:
                comments = self.comment_crawler.crawl(article_id=article_id, article_url=article_url)
                self.comment_repository.save_comments(comments)
            except Exception as exc:
                self.progress["comment_error"] = str(exc)
                self.progress["last_error"] = str(exc)
                self.progress["last_error_type"] = "comment"
                self.progress["last_error_url"] = article_url
                self.progress["last_error_title"] = detail.article.title
        return article_id, inserted
