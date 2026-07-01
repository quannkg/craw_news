from __future__ import annotations

from app.db.database import get_connection


class CrawlLogRepository:
    def start_log(
        self,
        crawl_type: str,
        source_url: str,
        status: str = "RUNNING",
        keyword: str = "",
    ) -> int:
        with get_connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO crawl_logs (crawl_type, source_url, keyword, status)
                VALUES (?, ?, ?, ?)
                """,
                (crawl_type, source_url, keyword, status),
            )
            connection.commit()
            return int(cursor.lastrowid)

    def finish_log(
        self,
        log_id: int,
        status: str,
        total_pages: int = 0,
        crawled_pages: int = 0,
        total_articles: int = 0,
        crawled_articles: int = 0,
        failed_articles: int = 0,
        error_message: str = "",
    ) -> None:
        with get_connection() as connection:
            connection.execute(
                """
                UPDATE crawl_logs
                SET status = ?,
                    total_pages = ?,
                    crawled_pages = ?,
                    total_articles = ?,
                    crawled_articles = ?,
                    failed_articles = ?,
                    finished_at = CURRENT_TIMESTAMP,
                    error_message = ?
                WHERE id = ?
                """,
                (
                    status,
                    total_pages,
                    crawled_pages,
                    total_articles,
                    crawled_articles,
                    failed_articles,
                    error_message,
                    log_id,
                ),
            )
            connection.commit()
