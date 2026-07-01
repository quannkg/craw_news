from __future__ import annotations

from app.db.database import get_connection
from app.models.comment import Comment


class CommentRepository:
    def save_comments(self, comments: list[Comment]) -> int:
        saved = 0
        local_id_map: dict[int, int] = {}
        with get_connection() as connection:
            if comments:
                article_id = comments[0].article_id
                connection.execute("DELETE FROM comments WHERE article_id = ?", (article_id,))
            for comment in comments:
                parent_comment_id = comment.parent_comment_id
                if parent_comment_id is not None and parent_comment_id in local_id_map:
                    parent_comment_id = local_id_map[parent_comment_id]

                cursor = connection.execute(
                    """
                    INSERT INTO comments (
                        external_comment_id,
                        parent_external_comment_id,
                        article_id,
                        parent_comment_id,
                        level,
                        username,
                        profile_url,
                        avatar_url,
                        content,
                        like_count,
                        comment_time_text,
                        reply_count,
                        updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """,
                    (
                        comment.external_comment_id,
                        comment.parent_external_comment_id,
                        comment.article_id,
                        parent_comment_id,
                        comment.level,
                        comment.username,
                        comment.profile_url,
                        comment.avatar_url,
                        comment.content,
                        comment.like_count,
                        comment.comment_time_text,
                        comment.reply_count,
                    ),
                )
                local_id_map[comment.local_id] = int(cursor.lastrowid)
                saved += 1
            connection.commit()
        return saved
