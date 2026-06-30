from __future__ import annotations

from collections.abc import Callable


PageHandler = Callable[[], str]


class ReadOnlyRouter:
    def __init__(self) -> None:
        self._routes: list[tuple[str, PageHandler]] = []

    def register(self, prefix: str, handler: PageHandler) -> None:
        self._routes.append((prefix, handler))
        self._routes.sort(key=lambda x: len(x[0]), reverse=True)

    def resolve(self, path: str) -> PageHandler | None:
        clean = path.split("?", 1)[0]
        for prefix, handler in self._routes:
            if clean.startswith(prefix):
                return handler
        return None
