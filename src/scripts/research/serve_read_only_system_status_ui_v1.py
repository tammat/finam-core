#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import os
from http.server import BaseHTTPRequestHandler, HTTPServer

import psycopg2
import psycopg2.extras
from marketcore.presentation.router import ReadOnlyRouter
from marketcore.presentation.pages.knowledge import render_knowledge_center_v2
from marketcore.presentation.pages.models import render_model_registry, render_model_registry_health
from marketcore.presentation.pages.experiments import render_experiment_registry, render_experiment_registry_health
from marketcore.presentation.pages.relationships import render_registry_relationships
from marketcore.presentation.pages.knowledge_graph import render_knowledge_graph



ROUTER = ReadOnlyRouter()
ROUTER.register("/knowledge/relationships", render_registry_relationships)
ROUTER.register("/knowledge/graph", render_knowledge_graph)
ROUTER.register("/knowledge/experiments/health", render_experiment_registry_health)
ROUTER.register("/knowledge/experiments", render_experiment_registry)
ROUTER.register("/knowledge/models/health", render_model_registry_health)
ROUTER.register("/knowledge/models", render_model_registry)
ROUTER.register("/knowledge", render_knowledge_center_v2)

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



def load_knowledge_summary():
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

            return domains, sources


def load_knowledge_coverage():
    with psycopg2.connect(db_url()) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                WITH base AS (
                    SELECT domain,
                           count(*) AS total,
                           count(*) FILTER (WHERE coalesce(object_id,'') <> '') AS has_object_id,
                           count(*) FILTER (WHERE coalesce(source_system,'') <> '') AS has_source_system,
                           count(*) FILTER (WHERE coalesce(payload->>'discovery_source','') <> '') AS has_discovery_source,
                           count(*) FILTER (WHERE coalesce(warehouse_layer,'') <> '') AS has_layer,
                           count(*) FILTER (WHERE health_light='GREEN') AS green
                    FROM warehouse.analytics_asset_catalog_v1
                    GROUP BY domain
                )
                SELECT domain, total,
                       round((has_object_id::numeric / nullif(total,0)) * 100, 2) AS object_id_coverage_pct,
                       round((has_source_system::numeric / nullif(total,0)) * 100, 2) AS source_system_coverage_pct,
                       round((has_discovery_source::numeric / nullif(total,0)) * 100, 2) AS discovery_coverage_pct,
                       round((has_layer::numeric / nullif(total,0)) * 100, 2) AS layer_coverage_pct,
                       round((green::numeric / nullif(total,0)) * 100, 2) AS health_coverage_pct
                FROM base
                ORDER BY domain
            """)
            return cur.fetchall()


def simple_table(rows, cols):
    head = ''.join(f'<th>{html_escape(c)}</th>' for c in cols)
    body = ''
    for r in rows:
        body += '<tr>' + ''.join(f'<td>{html_escape(r[c])}</td>' for c in cols) + '</tr>'
    return f'<table border="1" cellpadding="8" cellspacing="0"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'


def render_knowledge_center():
    domains, sources = load_knowledge_summary()
    return f"""<!doctype html>
<html lang="ru">
<head><meta charset="utf-8"><title>MarketCore Knowledge Center</title></head>
<body>
<h1>MarketCore Knowledge Center</h1>
<p><a href="/">Главное меню</a> | <a href="/knowledge/coverage">Knowledge Coverage</a> <button onclick="history.back()">Назад</button></p>
<h2>Домены</h2>
{simple_table(domains, ['domain', 'total', 'green'])}
<h2>Discovery Sources</h2>
{simple_table(sources, ['source', 'total'])}
<p>source_policy=CATALOG_READ_ONLY</p>
<p>runtime_changed=0 execution_changed=0 orders_changed=0 fills_changed=0 micro_live_allowed=0</p>
</body></html>"""


def render_knowledge_coverage():
    coverage = load_knowledge_coverage()
    return f"""<!doctype html>
<html lang="ru">
<head><meta charset="utf-8"><title>MarketCore Knowledge Coverage</title></head>
<body>
<h1>MarketCore Knowledge Coverage</h1>
<p><a href="/">Главное меню</a> | <a href="/knowledge">Knowledge Center</a> <button onclick="history.back()">Назад</button></p>
{simple_table(coverage, ['domain', 'total', 'object_id_coverage_pct', 'source_system_coverage_pct', 'discovery_coverage_pct', 'layer_coverage_pct', 'health_coverage_pct'])}
<p>source_policy=CATALOG_READ_ONLY</p>
<p>runtime_changed=0 execution_changed=0 orders_changed=0 fills_changed=0 micro_live_allowed=0</p>
</body></html>"""



def load_feature_registry_summary():
    with psycopg2.connect(db_url()) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT count(*) AS total,
                       count(*) FILTER (WHERE status='DISCOVERED') AS discovered,
                       count(*) FILTER (WHERE maturity_level='RESEARCH') AS research,
                       count(*) FILTER (WHERE approved_for_live=true) AS live_approved
                FROM warehouse.feature_registry_v1
            """)
            summary = cur.fetchone()

            cur.execute("""
                SELECT feature_class, count(*) AS total
                FROM warehouse.feature_registry_v1
                GROUP BY feature_class
                ORDER BY total DESC, feature_class
                LIMIT 30
            """)
            classes = cur.fetchall()

            return summary, classes


def load_feature_registry_health():
    with psycopg2.connect(db_url()) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT count(*) AS total,
                       count(*) FILTER (WHERE coalesce(feature_code,'')='') AS missing_feature_code,
                       count(*) FILTER (WHERE coalesce(status,'')='') AS missing_status,
                       count(*) FILTER (WHERE approved_for_live=true OR approved_for_paper=true OR approved_for_shadow=true) AS unsafe_approvals
                FROM warehouse.feature_registry_v1
            """)
            return cur.fetchone()


def render_feature_registry():
    summary, classes = load_feature_registry_summary()
    return f"""<!doctype html>
<html lang="ru">
<head><meta charset="utf-8"><title>MarketCore Feature Registry</title></head>
<body>
<h1>MarketCore Feature Registry</h1>
<p><a href="/">Главное меню</a> | <a href="/knowledge">Knowledge Center</a> | <a href="/knowledge/features/health">Feature Health</a> <button onclick="history.back()">Назад</button></p>
<h2>Сводка</h2>
<p>total={html_escape(summary['total'])}</p>
<p>discovered={html_escape(summary['discovered'])}</p>
<p>research={html_escape(summary['research'])}</p>
<p>live_approved={html_escape(summary['live_approved'])}</p>
<h2>Классы Feature</h2>
{simple_table(classes, ['feature_class', 'total'])}
<p>source_policy=FEATURE_REGISTRY_READ_ONLY</p>
<p>runtime_changed=0 execution_changed=0 orders_changed=0 fills_changed=0 micro_live_allowed=0</p>
</body></html>"""


def render_feature_registry_health():
    h = load_feature_registry_health()
    return f"""<!doctype html>
<html lang="ru">
<head><meta charset="utf-8"><title>MarketCore Feature Registry Health</title></head>
<body>
<h1>MarketCore Feature Registry Health</h1>
<p><a href="/">Главное меню</a> | <a href="/knowledge/features">Feature Registry</a> <button onclick="history.back()">Назад</button></p>
<p>total={html_escape(h['total'])}</p>
<p>missing_feature_code={html_escape(h['missing_feature_code'])}</p>
<p>missing_status={html_escape(h['missing_status'])}</p>
<p>unsafe_approvals={html_escape(h['unsafe_approvals'])}</p>
<p>source_policy=FEATURE_REGISTRY_READ_ONLY</p>
<p>runtime_changed=0 execution_changed=0 orders_changed=0 fills_changed=0 micro_live_allowed=0</p>
</body></html>"""



def load_knowledge_center_v2():
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
                SELECT
                  count(*) AS total,
                  count(*) FILTER (WHERE status='DISCOVERED') AS discovered,
                  count(*) FILTER (WHERE maturity_level='RESEARCH') AS research,
                  count(*) FILTER (WHERE approved_for_live=true) AS live_approved
                FROM warehouse.feature_registry_v1
            """)
            features = cur.fetchone()

            cur.execute("""
                SELECT
                  count(*) AS total,
                  count(*) FILTER (WHERE status='DISCOVERED') AS discovered,
                  count(*) FILTER (WHERE maturity_level='RESEARCH') AS research,
                  count(*) FILTER (WHERE approved_for_live=true) AS live_approved
                FROM warehouse.model_registry_v1
            """)
            models = cur.fetchone()

            cur.execute("""
                WITH base AS (
                    SELECT domain,
                           count(*) AS total,
                           count(*) FILTER (WHERE coalesce(object_id,'') <> '') AS has_object_id,
                           count(*) FILTER (WHERE coalesce(source_system,'') <> '') AS has_source_system,
                           count(*) FILTER (WHERE coalesce(payload->>'discovery_source','') <> '') AS has_discovery_source,
                           count(*) FILTER (WHERE coalesce(warehouse_layer,'') <> '') AS has_layer,
                           count(*) FILTER (WHERE health_light='GREEN') AS green
                    FROM warehouse.analytics_asset_catalog_v1
                    GROUP BY domain
                )
                SELECT domain, total,
                       round((has_object_id::numeric / nullif(total,0)) * 100, 2) AS object_id_coverage_pct,
                       round((has_source_system::numeric / nullif(total,0)) * 100, 2) AS source_system_coverage_pct,
                       round((has_discovery_source::numeric / nullif(total,0)) * 100, 2) AS discovery_coverage_pct,
                       round((has_layer::numeric / nullif(total,0)) * 100, 2) AS layer_coverage_pct,
                       round((green::numeric / nullif(total,0)) * 100, 2) AS health_coverage_pct
                FROM base
                ORDER BY domain
            """)
            coverage = cur.fetchall()

    return domains, sources, features, models, coverage


def render_knowledge_center_v2():
    domains, sources, features, models, coverage = load_knowledge_center_v2()

    catalog_total = sum(int(r['total']) for r in domains)
    catalog_green = sum(int(r['green']) for r in domains)
    health = round(catalog_green / catalog_total * 100, 2) if catalog_total else 0

    return f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<title>MarketCore Knowledge Center V2</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 24px; }}
.grid {{ display: grid; grid-template-columns: 220px 1fr; gap: 24px; }}
nav {{ border-right: 1px solid #ddd; padding-right: 16px; }}
section {{ margin-bottom: 28px; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
.card {{ display: inline-block; border: 1px solid #ddd; padding: 12px; margin: 6px; min-width: 160px; }}
</style>
</head>
<body>
<h1>MarketCore Knowledge Center V2</h1>
<p><a href="/">Главное меню</a> <button onclick="history.back()">Назад</button></p>

<div class="grid">
<nav>
<h3>Knowledge</h3>
<p><a href="#overview">Overview</a></p>
<p><a href="#discovery">Discovery</a></p>
<p><a href="#coverage">Coverage</a></p>
<p><a href="#features">Features</a></p>
<p><a href="#models">Models</a></p>
</nav>

<main>
<section id="overview">
<h2>Overview</h2>
<div class="card">catalog_objects={html_escape(catalog_total)}</div>
<div class="card">catalog_health={html_escape(health)}%</div>
<div class="card">features={html_escape(features['total'])}</div>
<div class="card">models={html_escape(models['total'])}</div>
</section>

<section id="discovery">
<h2>Discovery</h2>
<h3>Домены</h3>
{simple_table(domains, ['domain', 'total', 'green'])}
<h3>Источники</h3>
{simple_table(sources, ['source', 'total'])}
</section>

<section id="coverage">
<h2>Coverage</h2>
{simple_table(coverage, ['domain', 'total', 'object_id_coverage_pct', 'source_system_coverage_pct', 'discovery_coverage_pct', 'layer_coverage_pct', 'health_coverage_pct'])}
</section>

<section id="features">
<h2>Features</h2>
<p>total={html_escape(features['total'])}</p>
<p>discovered={html_escape(features['discovered'])}</p>
<p>research={html_escape(features['research'])}</p>
<p>live_approved={html_escape(features['live_approved'])}</p>
<p><a href="/knowledge/features">Feature Registry detail</a></p>
</section>

<section id="models">
<h2>Models</h2>
<p>total={html_escape(models['total'])}</p>
<p>discovered={html_escape(models['discovered'])}</p>
<p>research={html_escape(models['research'])}</p>
<p>live_approved={html_escape(models['live_approved'])}</p>
</section>

<p>source_policy=KNOWLEDGE_CENTER_READ_ONLY</p>
<p>runtime_changed=0 execution_changed=0 orders_changed=0 fills_changed=0 micro_live_allowed=0</p>
</main>
</div>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            handler = ROUTER.resolve(self.path)
            if handler:
                html = handler()
            elif self.path.startswith("/knowledge/features/health"):
                html = render_feature_registry_health()
            elif self.path.startswith("/knowledge/features"):
                html = render_feature_registry()
            elif self.path.startswith("/knowledge/coverage"):
                html = render_knowledge_coverage()
            elif self.path.startswith("/knowledge"):
                html = render_knowledge_center_v2()
            else:
                html = render_page()

            data = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except Exception as exc:
            data = f"READ_ONLY_UI_ROUTER_V1_ERROR: {exc}".encode("utf-8")
            self.send_response(500)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(data)


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
