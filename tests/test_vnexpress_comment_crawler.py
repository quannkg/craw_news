from __future__ import annotations

import unittest

from app.crawlers.vnexpress_comment_crawler import VnExpressCommentCrawler


SAMPLE_COMMENT_HTML = """
<div id="list_comment">
    <div class="comment_item">
        <a class="nickname" href="/u/a">User A</a>
        <p class="full_content">Comment cha</p>
        <a class="link_reply" rel="60912411" parent="60912411"></a>
        <a class="link_thich" rel="60912411"></a>
        <span class="time-com">1 giờ trước</span>
        <span class="reactions-total"><span class="number">12</span></span>
        <p class="count-reply"><a class="view_all_reply" rel="60912411" data-total="2"><span class="num_reply_cmt">2</span></a></p>
        <div class="sub_comment">
            <div class="sub_comment_item comment_item">
                <a class="nickname" href="/u/b">User B</a>
                <p class="full_content">Reply 1</p>
                <a class="link_reply" rel="60913823" parent="60912411"></a>
                <span class="time-com">45 phút trước</span>
                <span class="reactions-total"><span class="number"></span></span>
                <div class="sub_comment">
                    <div class="sub_comment_item comment_item">
                        <a class="nickname" href="/u/d">User D</a>
                        <p class="full_content">Reply của reply</p>
                        <a class="link_reply" rel="60913825" parent="60913823"></a>
                        <span class="time-com">10 phút trước</span>
                    </div>
                </div>
            </div>
            <div class="sub_comment_item comment_item">
                <a class="nickname" href="/u/c">User C</a>
                <p class="full_content">Reply 2</p>
                <a class="link_reply" rel="60913824" parent="60912411"></a>
                <span class="time-com">20 phút trước</span>
            </div>
        </div>
    </div>
</div>
"""


class VnExpressCommentCrawlerTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.crawler = VnExpressCommentCrawler()

    def test_parent_comment_is_null_when_parent_equals_external_id(self) -> None:
        comments = self.crawler._parse_comments_html(1, SAMPLE_COMMENT_HTML)
        parent = comments[0]
        self.assertEqual("60912411", parent.external_comment_id)
        self.assertEqual("60912411", parent.parent_external_comment_id)
        self.assertIsNone(parent.parent_comment_id)
        self.assertEqual(0, parent.level)

    def test_child_comment_points_to_local_parent_from_external_id(self) -> None:
        comments = self.crawler._parse_comments_html(1, SAMPLE_COMMENT_HTML)
        parent = comments[0]
        child = comments[1]
        self.assertEqual("60913823", child.external_comment_id)
        self.assertEqual("60912411", child.parent_external_comment_id)
        self.assertEqual(parent.local_id, child.parent_comment_id)
        self.assertEqual(1, child.level)

    def test_like_empty_defaults_to_zero(self) -> None:
        comments = self.crawler._parse_comments_html(1, SAMPLE_COMMENT_HTML)
        child = comments[1]
        self.assertEqual(0, child.like_count)

    def test_multiple_children_share_same_parent_without_duplicates(self) -> None:
        comments = self.crawler._parse_comments_html(1, SAMPLE_COMMENT_HTML)
        parent = comments[0]
        child_one = comments[1]
        child_two = comments[3]
        self.assertEqual(parent.local_id, child_one.parent_comment_id)
        self.assertEqual(parent.local_id, child_two.parent_comment_id)
        external_ids = [comment.external_comment_id for comment in comments]
        self.assertEqual(len(external_ids), len(set(external_ids)))

    def test_reply_of_reply_uses_direct_parent_and_level_two(self) -> None:
        comments = self.crawler._parse_comments_html(1, SAMPLE_COMMENT_HTML)
        nested = comments[2]
        direct_parent = comments[1]
        self.assertEqual("60913823", nested.parent_external_comment_id)
        self.assertEqual(direct_parent.local_id, nested.parent_comment_id)
        self.assertEqual(2, nested.level)


if __name__ == "__main__":
    unittest.main()
