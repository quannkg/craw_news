from __future__ import annotations

from app.db.database import get_connection
from app.models.category import Category


class CategoryRepository:
    def upsert_category(self, category: Category) -> int:
        with get_connection() as connection:
            row = connection.execute(
                "SELECT id FROM categories WHERE url = ?",
                (category.url,),
            ).fetchone()

            if row is None:
                cursor = connection.execute(
                    """
                    INSERT INTO categories (name, url, slug, parent_id, category_type)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        category.name,
                        category.url,
                        category.slug,
                        category.parent_id,
                        category.category_type,
                    ),
                )
                connection.commit()
                return int(cursor.lastrowid)

            category_id = int(row["id"])
            connection.execute(
                """
                UPDATE categories
                SET name = ?, slug = ?, parent_id = ?, category_type = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    category.name,
                    category.slug,
                    category.parent_id,
                    category.category_type,
                    category_id,
                ),
            )
            connection.commit()
            return category_id

    def list_categories(self) -> list[dict]:
        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT id, name, url, slug, parent_id, category_type, created_at, updated_at
                FROM categories
                ORDER BY id ASC
                """
            ).fetchall()
        return [dict(row) for row in rows]
