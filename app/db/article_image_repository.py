from __future__ import annotations

from app.db.database import get_connection
from app.models.article_image import ArticleImage


class ArticleImageRepository:
    def replace_images(self, article_id: int, images: list[ArticleImage]) -> int:
        with get_connection() as connection:
            connection.execute("DELETE FROM article_images WHERE article_id = ?", (article_id,))
            for image in images:
                connection.execute(
                    """
                    INSERT INTO article_images (article_id, image_url, caption, display_order)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        article_id,
                        image.image_url,
                        image.caption,
                        image.display_order,
                    ),
                )
            connection.commit()
        return len(images)
