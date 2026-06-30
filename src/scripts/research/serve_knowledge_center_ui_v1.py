#!/usr/bin/env python3
from __future__ import annotations

from marketcore.ui.quality_lineage_page import render_quality_lineage_page

import os
from http.server import BaseHTTPRequestHandler, HTTPServer

import psycopg2
import psycopg2.extras

PORT = int(os.getenv("KNOWLEDGE_CENTER_PORT", "8091"))


def db_url() -> str:
    return os.getenv("DATABASE_URL", "postgresql:///finam_core")


def esc(v) -> str:
    return str(v if v is not None else "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def query():
    with psycopg2.connect(db_url()) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT domain, count(*) AS total,
                       count(*) FILTER (WHERE health_light='GREEN') AS green
                FROM warehouse.analytics_asset_catalog_v1
                GROUP BY domain
                ORDER BY domain
            """)
            domains = cur.fetchall()

            cur.execute("""
                SELECT payload->>'discovery_source' AS source, count(*) AS total
                FROM warehouse.analytics_asset_catalog_v1
                GROUP BY payload->>'discovery_source'
                ORDER BY source
            """)
            sources = cur.fetchall()

            cur.execute("""
                SELECT category, count(*) AS total
                FROM warehouse.analytics_asset_catalog_v1
                GROUP BY category
                ORDER BY category
            """)
            categories = cur.fetchall()

            cur.execute("""
                SELECT warehouse_layer, count(*) AS total
                FROM warehouse.analytics_asset_catalog_v1
                GROUP BY warehouse_layer
                ORDER BY warehouse_layer
            """)
            layers = cur.fetchall()

    return domains, sources, categories, layers


def rows_html(rows, cols):
    out = ""
    for r in rows:
        out += "<tr>" + "".join(f"<td>{esc(r[c])}</td>" for c in cols) + "</tr>"
    return out


def table(title, rows, cols):
    headers = "".join(f"<th>{esc(c)}</th>" for c in cols)
    return f"""
    <section>
      <h2>{esc(title)}</h2>
      <table border="1" cellpadding="8" cellspacing="0">
        <thead><tr>{headers}</tr></thead>
        <tbody>{rows_html(rows, cols)}</tbody>
      </table>
    </section>
    """


def render() -> str:
    domains, sources, categories, layers = query()
    total = sum(int(r["total"]) for r in domains)
    green = sum(int(r["green"]) for r in domains)
    health = round(green / total * 100, 2) if total else 0

    return f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MarketCore Knowledge Center</title>
</head>
<body>
<h1>MarketCore Knowledge Center</h1>
<p>
  <a href="http://127.0.0.1:8089/">Главное меню</a>
  <a href="http://127.0.0.1:8090/">Knowledge Coverage</a>
  <button onclick="history.back()">Назад</button>
</p>

<section>
<h2>Сводка</h2>
<p>objects={esc(total)}</p>
<p>health={esc(health)}%</p>
<p>source_policy=CATALOG_READ_ONLY</p>
</section>

{table("Домены", domains, ["domain", "total", "green"])}
{table("Discovery Sources", sources, ["source", "total"])}
{table("Категории", categories, ["category", "total"])}
{table("Слои", layers, ["warehouse_layer", "total"])}

<p>runtime_changed=0 execution_changed=0 orders_changed=0 fills_changed=0 micro_live_allowed=0</p>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/knowledge/lineage":
            html = render_quality_lineage_page()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))
            return

        try:
            data = render().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except Exception as exc:
            data = f"KNOWLEDGE_CENTER_UI_V1_ERROR: {exc}".encode("utf-8")
            self.send_response(500)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(data)


def main() -> int:
    print("=== KNOWLEDGE_CENTER_UI_V1 ===")
    print(f"port={PORT}")
    print("source_policy=CATALOG_READ_ONLY")
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
