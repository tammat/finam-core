from __future__ import annotations

import html
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
HOST = os.getenv("KG_VIEW_HOST", "127.0.0.1")
PORT = int(os.getenv("KG_VIEW_PORT", "8096"))


def fetch_all(sql: str, params=()):
    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            return [dict(r) for r in cur.fetchall()]


def page(title: str, body: str) -> bytes:
    return f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<title>{html.escape(title)}</title>
<style>
body {{ font-family: system-ui, -apple-system, sans-serif; margin: 24px; background:#0f172a; color:#e5e7eb; }}
a {{ color:#93c5fd; margin-right:16px; }}
.card {{ background:#111827; border:1px solid #374151; border-radius:12px; padding:16px; margin:14px 0; }}
table {{ border-collapse:collapse; width:100%; margin-top:12px; }}
th,td {{ border-bottom:1px solid #374151; padding:8px; text-align:left; font-size:14px; }}
th {{ color:#bfdbfe; }}
.badge {{ padding:3px 8px; border-radius:999px; background:#1f2937; }}
input {{ padding:8px; width:320px; }}
button {{ padding:8px 12px; }}
</style>
</head>
<body>
<h1>{html.escape(title)}</h1>
<nav>
<a href="/">Сводка</a>
<a href="/entities">Сущности</a>
<a href="/relations">Связи</a>
<a href="/search">Семантический поиск</a>
<a href="/validation">Валидация</a>
</nav>
{body}
</body>
</html>""".encode("utf-8")


def table(rows):
    if not rows:
        return "<p>Нет данных.</p>"
    cols = list(rows[0].keys())
    head = "".join(f"<th>{html.escape(str(c))}</th>" for c in cols)
    body = ""
    for r in rows:
        body += "<tr>" + "".join(f"<td>{html.escape(str(r.get(c,'')))}</td>" for c in cols) + "</tr>"
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return

    def send_html(self, payload: bytes):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        parsed = urlparse(self.path)
        q = parse_qs(parsed.query)
        path = parsed.path

        if path == "/":
            stats = fetch_all("SELECT domain,nodes,edges,entity_types,edge_types FROM knowledge_graph.v_api_kg_statistics_v1 ORDER BY domain;")
            latest = fetch_all("SELECT domain,status,total_findings,finished_at FROM knowledge_graph.v_api_kg_validation_latest_v1 ORDER BY domain;")
            body = '<div class="card"><h2>Статистика графа</h2>' + table(stats) + '</div>'
            body += '<div class="card"><h2>Последняя валидация</h2>' + table(latest) + '</div>'
            self.send_html(page("MarketCore Knowledge Graph View V1", body))
            return

        if path == "/entities":
            rows = fetch_all("""
                SELECT node_id, entity_type, label_ru, symbol, strategy, timeframe, confidence
                FROM knowledge_graph.v_api_kg_entity_summary_v1
                WHERE domain='PAPER_RUNTIME'
                ORDER BY node_id DESC
                LIMIT 100;
            """)
            self.send_html(page("Сущности Knowledge Graph", '<div class="card">' + table(rows) + '</div>'))
            return

        if path == "/relations":
            rows = fetch_all("""
                SELECT edge_id, edge_type, label_ru, from_entity_type, to_entity_type, confidence
                FROM knowledge_graph.v_api_kg_relation_summary_v1
                WHERE domain='PAPER_RUNTIME'
                ORDER BY edge_id DESC
                LIMIT 100;
            """)
            self.send_html(page("Связи Knowledge Graph", '<div class="card">' + table(rows) + '</div>'))
            return

        if path == "/search":
            term = (q.get("q", [""])[0] or "").strip().lower()
            body = """<div class="card"><form>
<input name="q" placeholder="например: сделки, риск, эдж" value="%s">
<button>Искать</button>
</form></div>""" % html.escape(term)
            if term:
                rows = fetch_all("""
                    SELECT locale, raw_term, object_type, object_key, match_type, confidence
                    FROM knowledge_graph.v_api_kg_semantic_search_v1
                    WHERE locale='ru'
                      AND (%s ILIKE '%%' || normalized_term || '%%'
                           OR normalized_term ILIKE '%%' || %s || '%%')
                    ORDER BY confidence DESC
                    LIMIT 50;
                """, (term, term))
                body += '<div class="card"><h2>Результаты</h2>' + table(rows) + '</div>'
            self.send_html(page("Семантический поиск", body))
            return

        if path == "/validation":
            runs = fetch_all("""
                SELECT run_id, domain, status, total_findings, started_at, finished_at
                FROM knowledge_graph.validation_runs
                ORDER BY run_id DESC
                LIMIT 20;
            """)
            findings = fetch_all("""
                SELECT check_code, severity, count(*) AS findings
                FROM knowledge_graph.validation_findings
                GROUP BY check_code, severity
                ORDER BY severity, check_code;
            """)
            body = '<div class="card"><h2>Запуски</h2>' + table(runs) + '</div>'
            body += '<div class="card"><h2>Нарушения</h2>' + table(findings) + '</div>'
            self.send_html(page("Валидация Knowledge Graph", body))
            return

        self.send_response(404)
        self.end_headers()


def main():
    print(f"MARKETCORE_KNOWLEDGE_GRAPH_VIEW_V1_START host={HOST} port={PORT}", flush=True)
    HTTPServer((HOST, PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
