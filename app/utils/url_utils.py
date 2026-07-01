from __future__ import annotations

from urllib.parse import urljoin, urlparse


def normalize_url(base_url: str, raw_url: str) -> str:
    return urljoin(base_url, raw_url.strip())


def is_vnexpress_url(url: str) -> bool:
    hostname = urlparse(url).netloc.lower()
    return hostname.endswith("vnexpress.net")


def is_valid_vnexpress_category_url(url: str) -> bool:
    if not url:
        return False
    normalized = url.lower()
    if not is_vnexpress_url(normalized):
        return False
    if normalized.startswith("javascript:"):
        return False
    blocked_hosts = ("video.vnexpress.net", "esportsfan.net")
    if any(host in normalized for host in blocked_hosts):
        return False
    blocked_keywords = ("dang-nhap", "login")
    if any(keyword in normalized for keyword in blocked_keywords):
        return False
    return ".html" not in normalized and "#" not in normalized


def slug_from_url(url: str) -> str:
    path = urlparse(url).path.strip("/")
    if not path:
        return "home"
    return path.split("/")[-1]
