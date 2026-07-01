from __future__ import annotations

from datetime import datetime


def parse_iso_datetime(value: str) -> str:
    if not value:
        return ""
    text = value.strip()
    for pattern in ("%d/%m/%Y, %H:%M", "%d/%m/%Y %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text, pattern).isoformat(timespec="seconds")
        except ValueError:
            continue
    return ""
