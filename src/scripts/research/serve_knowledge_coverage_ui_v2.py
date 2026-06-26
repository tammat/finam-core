#!/usr/bin/env python3
from __future__ import annotations

import os
from http.server import BaseHTTPRequestHandler, HTTPServer

import psycopg2
import psycopg2.extras

PORT = int(os.getenv("KNOWLEDGE_UI_PORT", "8090"))


def db_url() -> str:
    return os.getenv("DATABASE_URL", "postgresql:///finam_core")


def esc(v) -> str:
    return str(v if v is not None else "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def load_coverage():
    with psycopg2.connect(db_url()) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                WITH base AS (
                    SELECT
                      domain,
                      count(*) AS total,
                      count(*) FILTER (WHERE coalesce(object_id,'') <> '') AS has_object_id,
                      count(*) FILTER (WHERE coalesce(source_system,'') <> '') AS has_source_system,
                      count(*) FILTER (WHERE coalesce(payload->>'discovery_source','') <> '') AS has_discovery_source,
                      count(*) FILTER (WHERE coalesce(warehouse_layer,'') <> '') AS has_layer,
                      count(*) FILTER (WHERE health_light='GREEN') AS green
                    FROM warehouse.analytics_asset_catalog_v1
                    GROUP BY domain
                )
                SELECT
                  domain,
                  total,
                  round((has_object_id::numeric / nullif(total,0)) * 100, 2) AS object_id_coverage_pct,
                  round((has_source_system::numeric / nullif(total,0)) * 100, 2) AS source_system_coverage_pct,
                  round((has_discovery_source::numeric / nullif(total,0)) * 100, 2) AS discovery_coverage_pct,
                  round((has_layer::numeric / nullif(total,0)) * 100, 2) AS layer_coverage_pct,
                  round((green::numeric / nullif(total,0)) * 100, 2) AS health_coverage_pct
                FROM base
                ORDER BY domain
            """)
            return cur.fetchall()


def render() -> str:
    rows = load_coverage()
    body = ""
    for r in rows:
        body += (
            "<tr>"
            f"<td>{esc(r['domain'])}</td>"
            f"<td>{esc(r['total'])}</td>"
            f"<td>{esc(r['object_id_coverage_pct'])}%</td>"
            f"<td>{esc(r['source_system_coverage_pct'])}%</td>"
            f"<td>{esc(r['discovery_coverage_pct'])}%</td>"
            f"<td>{esc(r['layer_coverage_pct'])}%</td>"
            f"<td>{esc(r['health_coverage_pct'])}%</td>"
            "</tr>"
        )

    return f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MarketCore Knowledge Coverage</title>
</head>
<body>
<h1>MarketCore Knowledge Coverage</h1>
<p><a href="http://127.0.0.1:8089/">Главное меню</a> <button onclick="history.back()">Назад</button></p>
<table border="1" cellpadding="8" cellspacing="0">
<thead>
<tr>
<th>Домен</th><th>Объекты</th><th>ID</th><th>Source</th><th>Discovery</th><th>Layer</th><th>Health</th>
</tr>
</thead>
<tbody>{body}</tbody>
</table>
<p>source_policy=CATALOG_READ_ONLY</p>
<p>runtime_changed=0 execution_changed=0 orders_changed=0 fills_changed=0 micro_live_allowed=0</p>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            data = render().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except Exception as exc:
            data = f"KNOWLEDGE_COVERAGE_UI_V2_ERROR: {exc}".encode("utf-8")
            self.send_response(500)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(data)


def main() -> int:
    print("=== KNOWLEDGE_COVERAGE_UI_V2 ===")
    print(f"port={PORT}")
    print("source_policy=CATALOG_READ_ONLY")
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
