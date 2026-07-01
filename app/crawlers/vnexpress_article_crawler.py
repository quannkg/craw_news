from __future__ import annotations

from dataclasses import dataclass

import requests

from app.models.article import Article
from app.models.article_image import ArticleImage
from app.utils.date_utils import parse_iso_datetime
from app.utils.html_utils import get_text, parse_html
from app.utils.url_utils import is_vnexpress_url, normalize_url


@dataclass(slots=True)
class ArticleDetail:
    article: Article
    images: list[ArticleImage]


class VnExpressArticleCrawler:
    def __init__(self, session: requests.Session | None = None, timeout: int = 20) -> None:
        self.timeout = timeout
        self.session = session or requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/126.0 Safari/537.36"
                )
            }
        )

    def crawl(self, article_url: str, category: str = "", category_id: int | None = None) -> ArticleDetail:
        response = self.session.get(article_url, timeout=self.timeout)
        response.raise_for_status()
        soup = parse_html(response.text)

        title = self._pick_text(
            soup,
            [
                "article.fck_detail h1.title-detail",
                "h1.title-detail",
                "article h1",
            ],
        )
        published_time_text = self._pick_text(
            soup,
            [
                "section.page-detail .date",
                ".time",
                "span.date",
            ],
        )
        description = self._pick_text(soup, ["article.fck_detail p.description"])
        author = self._pick_text(soup, ["article.fck_detail p.Normal[style*='text-align:right']"])
        content = self._extract_content(soup)

        article = Article(
            source="vnexpress",
            title=title,
            source_url=article_url,
            description=description,
            content=content,
            author=author,
            thumbnail_url="",
            category=category,
            category_id=category_id,
            published_time_text=published_time_text,
            published_at=parse_iso_datetime(published_time_text),
        )
        images = self._extract_images(soup, article_url)
        if images:
            article.thumbnail_url = images[0].image_url

        return ArticleDetail(article=article, images=images)

    def _extract_content(self, soup) -> str:
        article_root = soup.select_one("article.fck_detail") or soup
        paragraphs: list[str] = []
        for paragraph in article_root.select("p.Normal"):
            if paragraph.find_parent(id="article-end") is not None:
                break
            style = paragraph.get("style", "")
            if "text-align:right" in style.replace(" ", "").lower():
                continue
            if paragraph.find_parent(class_="box-tinlienquanv2") is not None:
                continue
            text = get_text(paragraph)
            if text:
                paragraphs.append(text)
        return "\n\n".join(paragraphs)

    def _extract_images(self, soup, base_url: str) -> list[ArticleImage]:
        images: list[ArticleImage] = []
        for index, figure in enumerate(soup.select("article.fck_detail figure")):
            image_url = ""
            image_tag = figure.select_one("img")
            if image_tag is not None:
                image_url = image_tag.get("data-src", "").strip() or image_tag.get("src", "").strip()
            if not image_url:
                meta_tag = figure.select_one("meta[itemprop='url']")
                if meta_tag is not None:
                    image_url = meta_tag.get("content", "").strip()
            if not image_url or image_url.startswith("data:image"):
                continue
            if "placeholder" in image_url.lower():
                continue
            full_url = normalize_url(base_url, image_url)
            if not is_vnexpress_url(full_url):
                continue
            caption = self._pick_text(
                figure,
                [
                    "figcaption p.Image",
                    "figcaption",
                    "p.Image",
                ],
            )
            images.append(
                ArticleImage(
                    article_id=0,
                    image_url=full_url,
                    caption=caption,
                    display_order=index,
                )
            )
        return images

    def _pick_text(self, root, selectors: list[str]) -> str:
        for selector in selectors:
            node = root.select_one(selector)
            text = get_text(node)
            if text:
                return text
        return ""
