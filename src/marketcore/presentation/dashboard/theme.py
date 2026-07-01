from __future__ import annotations

SUPPORTED_THEMES = ("light", "dark", "auto")
DEFAULT_THEME = "light"


def normalize_theme(value: str | None) -> str:
    if value in SUPPORTED_THEMES:
        return value
    return DEFAULT_THEME
