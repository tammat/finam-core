from __future__ import annotations

from html import escape


def t(resource_key: str) -> str:
    return f'<span data-i18n-key="{escape(resource_key)}">{escape(resource_key)}</span>'


def attr_t(resource_key: str) -> str:
    return escape(resource_key)
