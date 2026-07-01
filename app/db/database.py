from __future__ import annotations

import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "crawbao.db"


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    content TEXT DEFAULT '',
    source_url TEXT NOT NULL UNIQUE,
    thumbnail_url TEXT DEFAULT '',
    author TEXT DEFAULT '',
    search_published_timestamp_raw TEXT DEFAULT '',
    published_time_text TEXT DEFAULT '',
    published_at TEXT DEFAULT '',
    category TEXT DEFAULT '',
    category_id INTEGER,
    crawled_at TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    slug TEXT NOT NULL,
    parent_id INTEGER,
    category_type TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS article_images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id INTEGER NOT NULL,
    image_url TEXT NOT NULL,
    caption TEXT DEFAULT '',
    display_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    external_comment_id TEXT,
    parent_external_comment_id TEXT,
    article_id INTEGER NOT NULL,
    parent_comment_id INTEGER,
    level INTEGER NOT NULL DEFAULT 0,
    username TEXT DEFAULT '',
    profile_url TEXT DEFAULT '',
    avatar_url TEXT DEFAULT '',
    content TEXT NOT NULL,
    like_count INTEGER NOT NULL DEFAULT 0,
    comment_time_text TEXT DEFAULT '',
    reply_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS crawl_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    crawl_type TEXT NOT NULL,
    source_url TEXT NOT NULL,
    keyword TEXT DEFAULT '',
    status TEXT NOT NULL,
    total_pages INTEGER NOT NULL DEFAULT 0,
    crawled_pages INTEGER NOT NULL DEFAULT 0,
    total_articles INTEGER NOT NULL DEFAULT 0,
    crawled_articles INTEGER NOT NULL DEFAULT 0,
    failed_articles INTEGER NOT NULL DEFAULT 0,
    started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finished_at TEXT DEFAULT '',
    error_message TEXT DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_articles_source ON articles(source);
CREATE INDEX IF NOT EXISTS idx_articles_category ON articles(category);
CREATE INDEX IF NOT EXISTS idx_articles_category_id ON articles(category_id);
CREATE INDEX IF NOT EXISTS idx_articles_published_at ON articles(published_at);
CREATE INDEX IF NOT EXISTS idx_articles_crawled_at ON articles(crawled_at);
CREATE INDEX IF NOT EXISTS idx_categories_parent_id ON categories(parent_id);
CREATE INDEX IF NOT EXISTS idx_comments_article_id ON comments(article_id);
CREATE INDEX IF NOT EXISTS idx_comments_parent_comment_id ON comments(parent_comment_id);
CREATE INDEX IF NOT EXISTS idx_comments_external_comment_id ON comments(external_comment_id);
CREATE INDEX IF NOT EXISTS idx_crawl_logs_source_url ON crawl_logs(source_url);
"""

ARTICLE_MIGRATIONS = {
    "description": "ALTER TABLE articles ADD COLUMN description TEXT DEFAULT ''",
    "source_url": "ALTER TABLE articles ADD COLUMN source_url TEXT",
    "search_published_timestamp_raw": "ALTER TABLE articles ADD COLUMN search_published_timestamp_raw TEXT DEFAULT ''",
    "published_time_text": "ALTER TABLE articles ADD COLUMN published_time_text TEXT DEFAULT ''",
    "category_id": "ALTER TABLE articles ADD COLUMN category_id INTEGER",
    "updated_at": "ALTER TABLE articles ADD COLUMN updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP",
}

CRAWL_LOG_MIGRATIONS = {
    "keyword": "ALTER TABLE crawl_logs ADD COLUMN keyword TEXT DEFAULT ''",
}

COMMENT_MIGRATIONS = {
    "parent_external_comment_id": "ALTER TABLE comments ADD COLUMN parent_external_comment_id TEXT",
    "level": "ALTER TABLE comments ADD COLUMN level INTEGER NOT NULL DEFAULT 0",
}


def ensure_database() -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as connection:
        connection.executescript(SCHEMA_SQL)
        _migrate_articles_table(connection)
        _migrate_comments_table(connection)
        _migrate_crawl_logs_table(connection)
        connection.commit()
    return DB_PATH


def get_connection() -> sqlite3.Connection:
    ensure_database()
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def _migrate_articles_table(connection: sqlite3.Connection) -> None:
    initial_columns = {
        row[1]
        for row in connection.execute("PRAGMA table_info(articles)").fetchall()
    }

    for column_name, sql in ARTICLE_MIGRATIONS.items():
        if column_name not in initial_columns:
            connection.execute(sql)

    columns = {
        row[1]
        for row in connection.execute("PRAGMA table_info(articles)").fetchall()
    }

    if "source_url" in columns and "url" in columns:
        connection.execute(
            """
            UPDATE articles
            SET source_url = COALESCE(NULLIF(source_url, ''), url)
            WHERE source_url IS NULL OR source_url = ''
            """
        )

    if "description" in columns and "summary" in columns:
        connection.execute(
            """
            UPDATE articles
            SET description = COALESCE(NULLIF(description, ''), summary)
            WHERE description IS NULL OR description = ''
            """
        )

    connection.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_articles_source_url ON articles(source_url)"
    )


def _migrate_crawl_logs_table(connection: sqlite3.Connection) -> None:
    columns = {
        row[1]
        for row in connection.execute("PRAGMA table_info(crawl_logs)").fetchall()
    }
    for column_name, sql in CRAWL_LOG_MIGRATIONS.items():
        if column_name not in columns:
            connection.execute(sql)


def _migrate_comments_table(connection: sqlite3.Connection) -> None:
    columns = {
        row[1]
        for row in connection.execute("PRAGMA table_info(comments)").fetchall()
    }
    for column_name, sql in COMMENT_MIGRATIONS.items():
        if column_name not in columns:
            connection.execute(sql)
