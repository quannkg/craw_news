from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Comment:
    article_id: int
    content: str
    local_id: int = 0
    level: int = 0
    username: str = ""
    external_comment_id: str | None = None
    parent_external_comment_id: str | None = None
    parent_comment_id: int | None = None
    profile_url: str = ""
    avatar_url: str = ""
    like_count: int = 0
    comment_time_text: str = ""
    reply_count: int = 0
