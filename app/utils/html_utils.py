from __future__ import annotations

from bs4 import BeautifulSoup, Tag


def parse_html(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


def get_text(node: Tag | None) -> str:
    if node is None:
        return ""
    return node.get_text(" ", strip=True)
