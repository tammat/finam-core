from __future__ import annotations

from collections.abc import Callable

from marketcore.presentation.i18n.catalog_http_v2 import (
    i18n_catalog_http_v2,
)

from marketcore.presentation.ui_runtime.asset_delivery_v2 import (
    load_ui_runtime_asset_v2,
)
from marketcore.presentation.workspace_v2.render_tree_http_v2 import (
    domain_render_tree_http_v2,
)

from marketcore.presentation.action_http_controller_v2 import dispatch_browser_action_http_v2


PageHandler = Callable[[], str]


_RETIRED_RESPONSE = b'{"status":"RETIRED","reason_code":"LEGACY_PRESENTATION_RETIRED","replacement":"/workspace-v2"}'


class ReadOnlyRouter:
    """Compatibility router for the standalone read-only status UI."""

    def __init__(self) -> None:
        self._routes: list[tuple[str, PageHandler]] = []

    def register(self, prefix: str, handler: PageHandler) -> None:
        self._routes.append((prefix, handler))
        self._routes.sort(key=lambda item: len(item[0]), reverse=True)

    def resolve(self, path: str) -> PageHandler | None:
        clean_path = path.split("?", 1)[0]
        for prefix, handler in self._routes:
            if clean_path.startswith(prefix):
                return handler
        return None


def route(path: str, query: dict[str, list[str]] | None = None) -> tuple[int, bytes]:
    query = query or {}
    if path.rstrip("/") == "/api/v2/i18n/catalog":
        response = i18n_catalog_http_v2(
            (query.get("locale") or ["ru-RU"])[0]
        )
        return response.status_code, response.body
    domain_render_tree_routes = {
        "/api/v2/domain-render-tree/home": "HOME",
        "/api/v2/domain-render-tree/portfolio": "PORTFOLIO",
        "/api/v2/domain-render-tree/control-center": "CONTROL_CENTER",
        "/api/v2/domain-render-tree/settings": "SETTINGS",
        "/api/v2/domain-render-tree/capital": "CAPITAL",
        "/api/v2/domain-render-tree/risk": "RISK",
        "/api/v2/domain-render-tree/research": "RESEARCH",
        "/api/v2/domain-render-tree/intraday": "INTRADAY",
        "/api/v2/domain-render-tree/program": "PROGRAM",
    }
    producer_code = domain_render_tree_routes.get(path.rstrip("/"))
    if producer_code is not None:
        response = domain_render_tree_http_v2(
            producer_code,
            timezone_code=(query.get("timezone") or [None])[0],
        )
        return response.status_code, response.body
    if path == "/" or path.rstrip("/") == "/workspace-v2":
        response = load_ui_runtime_asset_v2(
            "/workspace-v2"
        )
        return response.status_code, response.body

    if path.startswith("/assets/marketcore/ui-runtime/v1/"):
        return 410, _RETIRED_RESPONSE

    if path.startswith("/assets/marketcore/ui-runtime/v2/"):
        response = load_ui_runtime_asset_v2(path)
        return response.status_code, response.body

    if path.rstrip("/") == "/api/v1/render-tree/home":
        return 410, b'{"status":"RETIRED","reason_code":"LEGACY_PRESENTATION_RETIRED","replacement":"/api/v2/domain-render-tree/home"}'
    if path.startswith("/api/v1/") or path.startswith("/api/v2/render-tree/"):
        return 410, _RETIRED_RESPONSE
    if path.startswith("/workspace-v2/"):
        return 410, _RETIRED_RESPONSE

    return 404, b"Not found"


def route_post(path: str, body: bytes = b"") -> tuple[int, bytes]:
    if path.rstrip("/") == "/api/v2/actions/dispatch":
        response = dispatch_browser_action_http_v2(body)
        return response.status_code, response.body
    if path.startswith("/workspace-v2/") or path.startswith("/api/v1/"):
        return 410, _RETIRED_RESPONSE
    return 404, b"Not found"
