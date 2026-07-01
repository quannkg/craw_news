from __future__ import annotations

import math
from typing import Iterable

from app.db.database import get_connection
from app.models.article import Article


class ArticleRepository:
    def save_articles(
        self, articles: Iterable[Article], force_refresh: bool = False
    ) -> tuple[int, int]:
        inserted = 0
        skipped = 0

        with get_connection() as connection:
            for article in articles:
                article.ensure_crawled_at()
                existed = self._find_article_id_by_url(connection, article.source_url)
                if existed is None:
                    connection.execute(
                        """
                        INSERT INTO articles (
                            source,
                            title,
                            description,
                            content,
                            source_url,
                            thumbnail_url,
                            author,
                            search_published_timestamp_raw,
                            published_time_text,
                            published_at,
                            category,
                            category_id,
                            crawled_at,
                            updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                        """,
                        (
                            article.source,
                            article.title,
                            article.description,
                            article.content,
                            article.source_url,
                            article.thumbnail_url,
                            article.author,
                            article.search_published_timestamp_raw,
                            article.published_time_text,
                            article.published_at,
                            article.category,
                            article.category_id,
                            article.crawled_at,
                        ),
                    )
                    inserted += 1
                    continue

                if force_refresh:
                    connection.execute(
                        """
                        UPDATE articles
                        SET title = ?,
                            description = ?,
                            content = ?,
                            thumbnail_url = ?,
                            author = ?,
                            search_published_timestamp_raw = ?,
                            published_time_text = ?,
                            published_at = ?,
                            category = ?,
                            category_id = ?,
                            crawled_at = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                        """,
                        (
                            article.title,
                            article.description,
                            article.content,
                            article.thumbnail_url,
                            article.author,
                            article.search_published_timestamp_raw,
                            article.published_time_text,
                            article.published_at,
                            article.category,
                            article.category_id,
                            article.crawled_at,
                            existed,
                        ),
                    )
                skipped += 1

            connection.commit()

        return inserted, skipped

    def upsert_article(self, article: Article, force_refresh: bool = False) -> tuple[int, bool]:
        article.ensure_crawled_at()
        with get_connection() as connection:
            existed = self._find_article_id_by_url(connection, article.source_url)
            if existed is None:
                cursor = connection.execute(
                    """
                    INSERT INTO articles (
                        source,
                        title,
                        description,
                        content,
                        source_url,
                        thumbnail_url,
                        author,
                        search_published_timestamp_raw,
                        published_time_text,
                        published_at,
                        category,
                        category_id,
                        crawled_at,
                        updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """,
                    (
                        article.source,
                        article.title,
                        article.description,
                        article.content,
                        article.source_url,
                        article.thumbnail_url,
                        article.author,
                        article.search_published_timestamp_raw,
                        article.published_time_text,
                        article.published_at,
                        article.category,
                        article.category_id,
                        article.crawled_at,
                    ),
                )
                connection.commit()
                return int(cursor.lastrowid), True

            if force_refresh:
                connection.execute(
                    """
                    UPDATE articles
                    SET title = ?,
                        description = ?,
                        content = ?,
                        thumbnail_url = ?,
                        author = ?,
                        search_published_timestamp_raw = ?,
                        published_time_text = ?,
                        published_at = ?,
                        category = ?,
                        category_id = ?,
                        crawled_at = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (
                        article.title,
                        article.description,
                        article.content,
                        article.thumbnail_url,
                        article.author,
                        article.search_published_timestamp_raw,
                        article.published_time_text,
                        article.published_at,
                        article.category,
                        article.category_id,
                        article.crawled_at,
                        existed,
                    ),
                )
                connection.commit()
            return existed, False

    def list_recent_articles(self, limit: int = 100) -> list[dict]:
        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT id, source, category, title, source_url, published_at, crawled_at
                FROM articles
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [dict(row) for row in rows]

    def list_articles_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        keyword: str = "",
        category: str = "",
        source: str = "",
    ) -> dict:
        page = max(1, page)
        page_size = max(1, page_size)
        where_clauses = ["1 = 1"]
        params: list = []

        if keyword.strip():
            where_clauses.append(
                "(title LIKE ? OR description LIKE ? OR content LIKE ? OR source_url LIKE ?)"
            )
            keyword_value = f"%{keyword.strip()}%"
            params.extend([keyword_value, keyword_value, keyword_value, keyword_value])

        if category.strip():
            where_clauses.append("category = ?")
            params.append(category.strip())

        if source.strip():
            where_clauses.append("source = ?")
            params.append(source.strip())

        where_sql = " AND ".join(where_clauses)
        offset = (page - 1) * page_size

        with get_connection() as connection:
            total_items = int(
                connection.execute(
                    f"SELECT COUNT(*) FROM articles WHERE {where_sql}",
                    tuple(params),
                ).fetchone()[0]
            )
            rows = connection.execute(
                f"""
                SELECT
                    id,
                    source,
                    category,
                    title,
                    description,
                    source_url,
                    search_published_timestamp_raw,
                    published_time_text,
                    published_at,
                    crawled_at
                FROM articles
                WHERE {where_sql}
                ORDER BY id DESC
                LIMIT ? OFFSET ?
                """,
                tuple([*params, page_size, offset]),
            ).fetchall()

        total_pages = max(1, math.ceil(total_items / page_size)) if total_items else 1
        return {
            "items": [dict(row) for row in rows],
            "page": page,
            "page_size": page_size,
            "total_items": total_items,
            "total_pages": total_pages,
        }

    def list_categories(self) -> list[str]:
        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT DISTINCT category
                FROM articles
                WHERE category IS NOT NULL AND category != ''
                ORDER BY category COLLATE NOCASE ASC
                """
            ).fetchall()
        return [str(row[0]) for row in rows]

    def get_article_detail(self, article_id: int) -> dict | None:
        with get_connection() as connection:
            article = connection.execute(
                """
                SELECT
                    id,
                    source,
                    category,
                    title,
                    description,
                    content,
                    source_url,
                    thumbnail_url,
                    author,
                    search_published_timestamp_raw,
                    published_time_text,
                    published_at,
                    crawled_at
                FROM articles
                WHERE id = ?
                """,
                (article_id,),
            ).fetchone()
            if article is None:
                return None

            images = connection.execute(
                """
                SELECT image_url, caption, display_order
                FROM article_images
                WHERE article_id = ?
                ORDER BY display_order ASC, id ASC
                """,
                (article_id,),
            ).fetchall()

            comments = connection.execute(
                """
                SELECT
                    id,
                    external_comment_id,
                    parent_external_comment_id,
                    parent_comment_id,
                    level,
                    username,
                    profile_url,
                    avatar_url,
                    content,
                    like_count,
                    comment_time_text,
                    reply_count
                FROM comments
                WHERE article_id = ?
                ORDER BY id ASC
                """,
                (article_id,),
            ).fetchall()

        detail = dict(article)
        detail["images"] = [dict(row) for row in images]
        detail["comments"] = [dict(row) for row in comments]
        return detail

    def search_articles(
        self,
        keyword: str,
        category_id: int | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        normalized_keyword = keyword.strip()
        if not normalized_keyword:
            return []

        where_clauses = [
            "(LOWER(title) LIKE LOWER(?) OR LOWER(description) LIKE LOWER(?) OR LOWER(content) LIKE LOWER(?))"
        ]
        params: list = [f"%{normalized_keyword}%", f"%{normalized_keyword}%", f"%{normalized_keyword}%"]

        if category_id is not None:
            where_clauses.append("category_id = ?")
            params.append(category_id)

        with get_connection() as connection:
            rows = connection.execute(
                f"""
                SELECT
                    id,
                    source,
                    category,
                    title,
                    description,
                    source_url,
                    published_time_text,
                    published_at,
                    crawled_at
                FROM articles
                WHERE {' AND '.join(where_clauses)}
                ORDER BY
                    CASE
                        WHEN LOWER(title) LIKE LOWER(?) THEN 1
                        WHEN LOWER(description) LIKE LOWER(?) THEN 2
                        ELSE 3
                    END,
                    id DESC
                LIMIT ? OFFSET ?
                """,
                tuple([
                    *params,
                    f"%{normalized_keyword}%",
                    f"%{normalized_keyword}%",
                    limit,
                    offset,
                ]),
            ).fetchall()

        return [dict(row) for row in rows]

    def count_search_articles(
        self,
        keyword: str,
        category_id: int | None = None,
    ) -> int:
        normalized_keyword = keyword.strip()
        if not normalized_keyword:
            return 0

        where_clauses = [
            "(LOWER(title) LIKE LOWER(?) OR LOWER(description) LIKE LOWER(?) OR LOWER(content) LIKE LOWER(?))"
        ]
        params: list = [f"%{normalized_keyword}%", f"%{normalized_keyword}%", f"%{normalized_keyword}%"]

        if category_id is not None:
            where_clauses.append("category_id = ?")
            params.append(category_id)

        with get_connection() as connection:
            row = connection.execute(
                f"SELECT COUNT(*) FROM articles WHERE {' AND '.join(where_clauses)}",
                tuple(params),
            ).fetchone()
        return int(row[0]) if row is not None else 0

    def delete_articles_by_ids(self, article_ids: list[int]) -> int:
        normalized_ids = sorted({int(article_id) for article_id in article_ids if int(article_id) > 0})
        if not normalized_ids:
            return 0

        placeholders = ", ".join("?" for _ in normalized_ids)
        with get_connection() as connection:
            connection.execute(
                f"DELETE FROM article_images WHERE article_id IN ({placeholders})",
                tuple(normalized_ids),
            )
            connection.execute(
                f"DELETE FROM comments WHERE article_id IN ({placeholders})",
                tuple(normalized_ids),
            )
            cursor = connection.execute(
                f"DELETE FROM articles WHERE id IN ({placeholders})",
                tuple(normalized_ids),
            )
            connection.commit()
        return int(cursor.rowcount or 0)

    def _find_article_id_by_url(self, connection, source_url: str) -> int | None:
        row = connection.execute(
            "SELECT id FROM articles WHERE source_url = ?",
            (source_url,),
        ).fetchone()
        if row is None:
            return None
        return int(row["id"])
