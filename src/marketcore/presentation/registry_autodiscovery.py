from __future__ import annotations

import importlib
import pkgutil

from marketcore.presentation.page import Page
import marketcore.presentation.pages as pages_pkg


def discover_pages() -> list[Page]:
    discovered: list[Page] = []

    for module_info in pkgutil.iter_modules(pages_pkg.__path__):
        if module_info.name.startswith("_"):
            continue

        module = importlib.import_module(f"{pages_pkg.__name__}.{module_info.name}")

        for obj in module.__dict__.values():
            if not isinstance(obj, type):
                continue
            if obj is Page or not issubclass(obj, Page):
                continue

            try:
                page = obj()
            except TypeError:
                continue

            discovered.append(page)

    by_route: dict[str, Page] = {}
    for page in discovered:
        by_route[page.route] = page

    return sorted(
        by_route.values(),
        key=lambda p: (getattr(p, "menu_order", 1000), getattr(p, "title", ""), getattr(p, "route", "")),
    )


PAGES = discover_pages()


def menu_pages() -> list[Page]:
    return list(PAGES)


def get_page(route: str) -> Page | None:
    for page in PAGES:
        if page.route == route:
            return page
    return None
