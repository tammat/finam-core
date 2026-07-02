from __future__ import annotations

from dataclasses import dataclass
from html import escape
from typing import Protocol


class Widget(Protocol):
    widget_id: str
    title_ru: str
    title_en: str
    priority: int
    refresh_interval_sec: int
    workspace: str

    def render(self, lang: str) -> str:
        ...


def tr(lang: str, ru: str, en: str) -> str:
    return en if lang == "en" else ru


def badge(text: str, kind: str = "ok") -> str:
    css = {
        "ok": "mc-ok",
        "info": "mc-info",
        "off": "mc-off",
        "warn": "mc-warn",
        "bad": "mc-bad",
    }.get(kind, "mc-off")
    return f'<span class="mc-badge {css}">{escape(text)}</span>'


def row(label: str, value: str) -> str:
    return (
        '<div class="mc-row">'
        f'<span class="mc-label">{escape(label)}</span>'
        f'<span class="mc-value">{value}</span>'
        '</div>'
    )


@dataclass(frozen=True)
class SimpleWidget:
    widget_id: str
    title_ru: str
    title_en: str
    priority: int
    refresh_interval_sec: int = 30
    workspace: str = "workspace"

    def title(self, lang: str) -> str:
        return tr(lang, self.title_ru, self.title_en)

    def body(self, lang: str) -> str:
        return ""

    def render(self, lang: str) -> str:
        return (
            '<section class="mc-card" '
            f'data-widget-id="{escape(self.widget_id)}" '
            f'data-refresh="{self.refresh_interval_sec}">'
            f'<h3>{escape(self.title(lang))}</h3>'
            f'{self.body(lang)}'
            '</section>'
        )
