from __future__ import annotations

import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

from marketcore.presentation.router import route


HOST = os.getenv("MARKETCORE_UI_HOST", "127.0.0.1")
PORT = int(os.getenv("MARKETCORE_UI_PORT", "8080"))


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return

    def do_GET(self):
        parsed = urlparse(self.path)
        code, payload = route(parsed.path)

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
