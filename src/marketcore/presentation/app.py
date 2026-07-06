from __future__ import annotations

import os
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from marketcore.presentation.router import route


HOST = os.getenv("MARKETCORE_UI_HOST", "0.0.0.0")
PORT = int(os.getenv("MARKETCORE_UI_PORT", "8080"))


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
    def _send_html(self, code: int, body: bytes) -> None:
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        try:
            parsed = urlparse(self.path)
            code, payload = route(parsed.path)
            body = _to_bytes(payload)
            self._send_html(code, body)
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
