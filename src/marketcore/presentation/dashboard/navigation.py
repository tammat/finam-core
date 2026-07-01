from __future__ import annotations

from marketcore.presentation.dashboard.registry import registry


def navigation_items() -> list[dict[str, object]]:
    return [
        {
            "key": page.key,
            "title_key": page.title_key,
            "path": page.path,
            "icon": page.icon,
            "enabled": page.enabled,
        }
        for page in registry.list_pages()
    ]
