from __future__ import annotations

from marketcore.presentation.ui_runtime.asset_delivery_v1 import (
    ui_runtime_asset_content_type_v1,
)
from marketcore.presentation.ui_runtime.asset_delivery_v2 import (
    ui_runtime_asset_content_type_v2,
)

import os
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from marketcore.presentation.router import route, route_post


HOST = os.getenv("MARKETCORE_UI_HOST", "0.0.0.0")
PORT = int(os.getenv("MARKETCORE_UI_PORT", "8080"))
LOCAL_CONTROL_HOSTS = {"127.0.0.1", "localhost", "::1"}


def _request_hostname(value: str | None) -> str:
    if not value:
        return ""
    parsed = urlparse(value if "://" in value else f"http://{value}")
    return (parsed.hostname or "").lower()


def _to_bytes(payload: object) -> bytes:
    if isinstance(payload, bytes):
        return payload
    return str(payload).encode("utf-8")


def _error_page(exc: BaseException) -> bytes:
    body = f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<title>Ошибка MarketCore UI</title>
</head>
<body style="font-family:system-ui;background:#0f172a;color:#e5e7eb;padding:24px;">
<h1>Ошибка MarketCore UI</h1>
<p>Сервер ответил, но страница не была отрендерена штатно.</p>
<pre>{type(exc).__name__}: {exc}</pre>
<p>MARKETCORE_UI_SHELL_V1</p>
</body>
</html>"""
    return body.encode("utf-8")


class MarketCoreUiHandler(BaseHTTPRequestHandler):
    def _is_local_control_request(self) -> bool:
        if self.client_address[0] in {"127.0.0.1", "::1"}:
            return True

        if _request_hostname(self.headers.get("Host")) not in LOCAL_CONTROL_HOSTS:
            return False

        fetch_site = (self.headers.get("Sec-Fetch-Site") or "").lower()
        if fetch_site and fetch_site not in {"same-origin", "same-site", "none"}:
            return False

        for header in ("Origin", "Referer"):
            value = self.headers.get(header)
            if value and _request_hostname(value) not in LOCAL_CONTROL_HOSTS:
                return False

        return True

    def _send_html(self, code: int, body: bytes) -> None:
        self.send_response(code)
        asset_content_type = ui_runtime_asset_content_type_v1(
            self.path
        )
        if asset_content_type is None:
            asset_content_type = ui_runtime_asset_content_type_v2(
                self.path
            )

        if asset_content_type is not None:
            content_type = asset_content_type
        elif self.path.startswith("/api/v2/domain-render-tree/"):
            content_type = (
                "application/vnd.marketcore.render-tree+json; charset=utf-8"
            )
        elif self.path.startswith("/api/v1/"):
            content_type = "application/json; charset=utf-8"
        else:
            content_type = "text/html; charset=utf-8"

        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        try:
            parsed = urlparse(self.path)
            code, payload = route(parsed.path, parse_qs(parsed.query))
            body = _to_bytes(payload)
            self._send_html(code, body)
        except Exception as exc:
            traceback.print_exc()
            self._send_html(500, _error_page(exc))

    def do_POST(self) -> None:
        try:
            if not self._is_local_control_request():
                self._send_html(403, b"Local control only")
                return
            parsed = urlparse(self.path)
            code, payload = route_post(parsed.path)
            self._send_html(code, _to_bytes(payload))
        except Exception as exc:
            traceback.print_exc()
            self._send_html(500, _error_page(exc))

    def log_message(self, fmt: str, *args: object) -> None:
        return


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), MarketCoreUiHandler)
    print(f"MARKETCORE_UI_SHELL_V1_START host={HOST} port={PORT}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
