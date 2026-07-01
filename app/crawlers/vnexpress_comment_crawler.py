from __future__ import annotations

from contextlib import AbstractContextManager

from bs4 import BeautifulSoup

from app.models.comment import Comment


class VnExpressCommentCrawler(AbstractContextManager):
    def __init__(self) -> None:
        self._next_local_id = -1
        self._playwright = None
        self._browser = None

    def __enter__(self) -> "VnExpressCommentCrawler":
        self.open()
        return self

    def __exit__(self, exc_type, exc, exc_tb) -> None:
        self.close()

    def open(self) -> None:
        if self._browser is not None:
            return
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError(
                "Chưa cài Playwright. Hãy chạy: pip install -r requirements.txt"
            ) from exc

        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=True)

    def close(self) -> None:
        if self._browser is not None:
            self._browser.close()
            self._browser = None
        if self._playwright is not None:
            self._playwright.stop()
            self._playwright = None

    def crawl(self, article_id: int, article_url: str) -> list[Comment]:
        try:
            from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        except ImportError as exc:
            raise RuntimeError(
                "Chưa cài Playwright. Hãy chạy: pip install -r requirements.txt"
            ) from exc

        if self._browser is None:
            self.open()

        comments: list[Comment] = []
        context = self._browser.new_context()
        page = context.new_page()
        try:
            page.goto(article_url, wait_until="domcontentloaded", timeout=30000)
            comment_box = page.locator("#box_comment")
            if comment_box.count() == 0:
                return []
            comment_box.scroll_into_view_if_needed(timeout=6000)

            self._click_all(page, ".continue-reading")
            self._expand_show_more_comments(page)
            self._expand_all_reply_trees(page)
            page.wait_for_timeout(1000)

            comments = self._parse_comments_html(article_id, page.content())
        except PlaywrightTimeoutError as exc:
            raise RuntimeError(
                "Khu vực comment tải quá chậm hoặc chưa phản hồi."
            ) from exc
        except Exception as exc:
            message = str(exc)
            if "Executable doesn't exist" in message or "browserType.launch" in message:
                raise RuntimeError(
                    "Chưa cài Chromium cho Playwright. Hãy chạy: python -m playwright install chromium"
                ) from exc
            raise RuntimeError(f"Lỗi khi crawl comment: {exc}") from exc
        finally:
            page.close()
            context.close()

        return comments

    def _expand_show_more_comments(self, page) -> None:
        previous_count = -1
        while True:
            current_count = page.locator("#list_comment > .comment_item").count()
            if current_count == previous_count:
                break
            previous_count = current_count
            button = page.locator("#show_more_coment")
            if button.count() == 0:
                break
            try:
                button.first.click(timeout=2000)
                page.wait_for_timeout(900)
                self._click_all(page, ".continue-reading")
            except Exception:
                break

    def _expand_all_reply_trees(self, page) -> None:
        while True:
            buttons = page.locator(".comment_item > p.count-reply > .view_all_reply")
            count = buttons.count()
            if count == 0:
                break
            clicked = False
            for index in range(count):
                button = buttons.nth(index)
                try:
                    button.click(timeout=1500)
                    page.wait_for_timeout(600)
                    self._click_all(page, ".continue-reading")
                    clicked = True
                except Exception:
                    continue
            if not clicked:
                break

    def _click_all(self, page, selector: str) -> None:
        while True:
            locator = page.locator(selector)
            count = locator.count()
            if count == 0:
                break
            clicked = False
            for index in range(count):
                try:
                    locator.nth(index).click(timeout=1200)
                    page.wait_for_timeout(200)
                    clicked = True
                except Exception:
                    continue
            if not clicked:
                break

    def _parse_comments_html(self, article_id: int, html: str) -> list[Comment]:
        self._next_local_id = -1
        soup = BeautifulSoup(html, "lxml")
        root = soup.select_one("#list_comment")
        if root is None:
            return []

        comments: list[Comment] = []
        external_map: dict[str, Comment] = {}
        for item in root.select(":scope > .comment_item"):
            self._parse_comment_node(
                article_id=article_id,
                comment_element=item,
                output=comments,
                external_map=external_map,
            )
        return comments

    def _parse_comment_node(
        self,
        article_id: int,
        comment_element,
        output: list[Comment],
        external_map: dict[str, Comment],
    ) -> None:
        comment = self._build_comment(article_id, comment_element, external_map)
        if comment is None:
            return

        output.append(comment)
        if comment.external_comment_id:
            external_map[comment.external_comment_id] = comment

        for child in comment_element.select(":scope > .sub_comment > .sub_comment_item.comment_item"):
            self._parse_comment_node(
                article_id=article_id,
                comment_element=child,
                output=output,
                external_map=external_map,
            )

    def _build_comment(self, article_id: int, node, external_map: dict[str, Comment]) -> Comment | None:
        local_id = self._next_comment_local_id()
        username_node = node.select_one(".nickname")
        avatar_node = node.select_one(".avata_coment img")
        content_node = (
            node.select_one("p.content_more")
            or node.select_one("p.full_content")
            or node.select_one("p.content_less")
        )
        like_node = node.select_one(".reactions-total .number")
        reply_node = node.select_one(":scope > p.count-reply > .view_all_reply .num_reply_cmt")
        link_reply = node.select_one(".link_reply[rel]")
        link_like = node.select_one(".link_thich[rel]")

        external_comment_id = ""
        if link_reply is not None:
            external_comment_id = link_reply.get("rel", "").strip()
        if not external_comment_id and link_like is not None:
            external_comment_id = link_like.get("rel", "").strip()
        if not external_comment_id:
            return None

        parent_external_comment_id = ""
        if link_reply is not None:
            parent_external_comment_id = link_reply.get("parent", "").strip()

        parent_comment_id: int | None = None
        level = 0
        if parent_external_comment_id and parent_external_comment_id != external_comment_id:
            parent_comment = external_map.get(parent_external_comment_id)
            if parent_comment is not None:
                parent_comment_id = parent_comment.local_id
                level = parent_comment.level + 1

        return Comment(
            article_id=article_id,
            content=self._clean_text(content_node.get_text(" ", strip=True) if content_node else ""),
            local_id=local_id,
            level=level,
            username=self._clean_text(username_node.get_text(" ", strip=True) if username_node else ""),
            external_comment_id=external_comment_id,
            parent_external_comment_id=parent_external_comment_id or None,
            parent_comment_id=parent_comment_id,
            profile_url=username_node.get("href", "").strip() if username_node else "",
            avatar_url=avatar_node.get("src", "").strip() if avatar_node else "",
            like_count=self._parse_int(like_node.get_text(" ", strip=True) if like_node else ""),
            comment_time_text=self._clean_text(
                node.select_one(".time-com").get_text(" ", strip=True)
                if node.select_one(".time-com")
                else ""
            ),
            reply_count=self._parse_int(reply_node.get_text(" ", strip=True) if reply_node else ""),
        )

    def _next_comment_local_id(self) -> int:
        self._next_local_id -= 1
        return self._next_local_id

    def _parse_int(self, value: str) -> int:
        digits = "".join(ch for ch in value if ch.isdigit())
        return int(digits) if digits else 0

    def _clean_text(self, value: str) -> str:
        return " ".join(value.split())
