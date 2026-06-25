#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import os
from http.server import BaseHTTPRequestHandler, HTTPServer

import psycopg2
import psycopg2.extras


PORT = int(os.getenv("READONLY_UI_PORT", "8089"))


def db_url() -> str:
    return os.getenv("DATABASE_URL", "postgresql:///finam_core")


def load_rows():
    with psycopg2.connect(db_url()) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT section_code, section_title_ru, metric_code, metric_label_ru,
                       metric_value, health_score, health_light, health_icon,
                       health_reason_code, payload, updated_at
                FROM warehouse.mart_workflow_dashboard_v1
                ORDER BY (payload->>'display_order')::int
            """)
            dashboard = cur.fetchall()

            cur.execute("""
                SELECT candidate_id, display_symbol, strategy_code, timeframe,
                       workflow_status_code, workflow_status_label_ru,
                       current_stage_code, current_stage_label_ru,
                       next_stage_code, next_stage_label_ru,
                       health_score, health_light, health_icon,
                       health_reason_code, updated_at
                FROM warehouse.mart_candidate_workflow_v1
                ORDER BY updated_at DESC
                LIMIT 1
            """)
            candidate = cur.fetchone()

    return dashboard, candidate


def light_class(light: str | None) -> str:
    return (light or "BLUE").lower()


def html_escape(v) -> str:
    return str(v if v is not None else "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render_page() -> str:
    dashboard, candidate = load_rows()

    cards = []
    for r in dashboard:
        cards.append(f"""
        <section class="card {light_class(r['health_light'])}">
            <div class="card-top">
                <span class="icon">{html_escape(r['health_icon'])}</span>
                <span class="title">{html_escape(r['section_title_ru'])}</span>
            </div>
            <div class="metric">{html_escape(r['metric_label_ru'])}</div>
            <div class="value">{html_escape(r['metric_value'])}</div>
            <div class="reason">{html_escape(r['health_reason_code'])}</div>
        </section>
        """)

    if candidate:
        candidate_block = f"""
        <section class="candidate {light_class(candidate['health_light'])}">
            <h2>{html_escape(candidate['health_icon'])} Кандидат</h2>
            <div class="grid">
                <div>ID</div><strong>{html_escape(candidate['candidate_id'])}</strong>
                <div>Инструмент</div><strong>{html_escape(candidate['display_symbol'])}</strong>
                <div>Стратегия</div><strong>{html_escape(candidate['strategy_code'])}</strong>
                <div>Таймфрейм</div><strong>{html_escape(candidate['timeframe'])}</strong>
                <div>Статус</div><strong>{html_escape(candidate['workflow_status_label_ru'])}</strong>
                <div>Этап</div><strong>{html_escape(candidate['current_stage_label_ru'])}</strong>
                <div>Следующий этап</div><strong>{html_escape(candidate['next_stage_label_ru'])}</strong>
                <div>Здоровье</div><strong>{html_escape(candidate['health_score'])} / {html_escape(candidate['health_light'])}</strong>
            </div>
        </section>
        """
    else:
        candidate_block = "<section class='candidate blue'><h2>Кандидат не найден</h2></section>"

    return f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Finam Core — Read Only Status</title>
<style>
body {{
    margin: 0;
    font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    background: #0f172a;
    color: #e5e7eb;
}}
header {{
    position: sticky;
    top: 0;
    background: #111827;
    border-bottom: 1px solid #334155;
    padding: 12px 16px;
    z-index: 10;
}}
.nav {{
    display: flex;
    gap: 12px;
    align-items: center;
    justify-content: space-between;
}}
.nav-left {{
    display: flex;
    gap: 10px;
    align-items: center;
}}
button, a.navbtn {{
    border: 1px solid #475569;
    background: #1e293b;
    color: #e5e7eb;
    border-radius: 10px;
    padding: 8px 10px;
    text-decoration: none;
    font-size: 14px;
}}
main {{
    padding: 16px;
    max-width: 1180px;
    margin: 0 auto;
}}
h1 {{
    font-size: 22px;
    margin: 8px 0 16px;
}}
.cards {{
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;
}}
.card, .candidate {{
    background: #111827;
    border: 1px solid #334155;
    border-left-width: 6px;
    border-radius: 14px;
    padding: 14px;
}}
.card-top {{
    display: flex;
    gap: 8px;
    align-items: center;
    font-weight: 700;
}}
.metric {{
    margin-top: 12px;
    color: #94a3b8;
    font-size: 13px;
}}
.value {{
    margin-top: 4px;
    font-size: 20px;
    font-weight: 700;
}}
.reason {{
    margin-top: 8px;
    color: #94a3b8;
    font-size: 12px;
}}
.green {{ border-left-color: #1f9d55; }}
.blue {{ border-left-color: #3b82f6; }}
.yellow {{ border-left-color: #facc15; }}
.orange {{ border-left-color: #fb923c; }}
.red {{ border-left-color: #ef4444; }}
.black {{ border-left-color: #111827; }}
.white {{ border-left-color: #f8fafc; }}
.candidate {{
    margin-top: 16px;
}}
.grid {{
    display: grid;
    grid-template-columns: 160px 1fr;
    gap: 8px 14px;
}}
.grid div {{
    color: #94a3b8;
}}
footer {{
    color: #64748b;
    font-size: 12px;
    margin-top: 18px;
}}
@media (max-width: 760px) {{
    .cards {{ grid-template-columns: 1fr; }}
    .grid {{ grid-template-columns: 1fr; }}
    .nav {{ align-items: flex-start; flex-direction: column; }}
}}
</style>
</head>
<body>
<header>
    <div class="nav">
        <div class="nav-left">
            <a class="navbtn" href="/">🏠 Главное меню</a>
            <button onclick="history.back()">← Назад</button>
        </div>
        <div>Finam Core · Read Only UI V1</div>
    </div>
</header>
<main>
    <h1>Состояние системы</h1>
    <div class="cards">
        {''.join(cards)}
    </div>
    {candidate_block}
    <footer>
        Источник: warehouse.mart_workflow_dashboard_v1 и warehouse.mart_candidate_workflow_v1.
        Только просмотр. Управление, заявки и execution недоступны.
    </footer>
</main>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            body = render_page().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception as exc:
            body = f"READ_ONLY_SYSTEM_STATUS_UI_V1_ERROR: {exc}".encode("utf-8")
            self.send_response(500)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)


def main() -> int:
    print("=== READ_ONLY_SYSTEM_STATUS_UI_V1 ===")
    print(f"port={PORT}")
    print("source_policy=MART_ONLY")
    print("mode=read_only")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
