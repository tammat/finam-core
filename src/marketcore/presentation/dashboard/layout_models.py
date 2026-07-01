from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LayoutState:
    lang: str = "ru"
    timezone: str = "Europe/Moscow"
    theme: str = "light"
    user_label: str = "Observer"


@dataclass(frozen=True)
class LayoutContent:
    title: str
    body_html: str
