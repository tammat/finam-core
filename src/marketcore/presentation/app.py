from __future__ import annotations

import os
import sys
import traceback
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse


HOST = os.getenv("MARKETCORE_UI_HOST", "127.0.0.1")
PORT = int(os.getenv("MARKETCORE_UI_PORT", "8080"))


def _fallback_error_page(message: str) -> bytes:
    safe = (
        message
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )

    return f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<title>Ошибка MarketCore UI</title>
</head>
<body style="font-family:system-ui;background:#0f172a;color:#e5e7eb;padding:24px;">
<h1>Ошибка MarketCore UI</h1>
<p>Сервер ответил, но страница не была отрендерена штатно.</p>
<pre>{safe}</pre>
<p>MARKETCORE_UI_SHELL_V1</p>
</body>
</html>""".encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return

    def do_GET(self):
        try:
            from marketcore.presentation.router import route

            parsed = urlparse(self.path)
            code, payload = route(parsed.path)

        except Exception as exc:
            traceback.print_exc(file=sys.stderr)
            code = 500
            payload = _fallback_error_page(f"{type(exc).__name__}: {exc}")

        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def main() -> None:
    print(f"MARKETCORE_UI_SHELL_V1_START host={HOST} port={PORT}", flush=True)
    HTTPServer((HOST, PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
