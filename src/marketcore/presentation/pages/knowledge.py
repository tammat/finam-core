from __future__ import annotations

from marketcore.presentation.pages.common import fetchall, fetchone, html_escape, simple_table


def render_knowledge_center_v2() -> str:
    domains = fetchall("""
        SELECT domain, count(*) AS total,
               count(*) FILTER (WHERE health_light='GREEN') AS green
        FROM warehouse.analytics_asset_catalog_v1
        GROUP BY domain
        ORDER BY domain
    """)

    sources = fetchall("""
        SELECT payload->>'discovery_source' AS source, count(*) AS total
        FROM warehouse.analytics_asset_catalog_v1
        GROUP BY payload->>'discovery_source'
        ORDER BY source
    """)

    features = fetchone("""
        SELECT count(*) AS total,
               count(*) FILTER (WHERE status='DISCOVERED') AS discovered,
               count(*) FILTER (WHERE maturity_level='RESEARCH') AS research,
               count(*) FILTER (WHERE approved_for_live=true) AS live_approved
        FROM warehouse.feature_registry_v1
    """)

    models = fetchone("""
        SELECT count(*) AS total,
               count(*) FILTER (WHERE status='DISCOVERED') AS discovered,
               count(*) FILTER (WHERE maturity_level='RESEARCH') AS research,
               count(*) FILTER (WHERE approved_for_live=true) AS live_approved
        FROM warehouse.model_registry_v1
    """)

    catalog_total = sum(int(r["total"]) for r in domains)
    catalog_green = sum(int(r["green"]) for r in domains)
    health = round(catalog_green / catalog_total * 100, 2) if catalog_total else 0

    return f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<title>MarketCore Knowledge Center V2</title>
</head>
<body>
<h1>MarketCore Knowledge Center V2</h1>
<p><a href="/">Главное меню</a></p>

<h2>Overview</h2>
<p>catalog_objects={html_escape(catalog_total)}</p>
<p>catalog_health={html_escape(health)}%</p>
<p>features={html_escape(features['total'])}</p>
<p>models={html_escape(models['total'])}</p>

<h2>Discovery</h2>
<h3>Домены</h3>
{simple_table(domains, ['domain', 'total', 'green'])}

<h3>Источники</h3>
{simple_table(sources, ['source', 'total'])}

<h2>Features</h2>
<p>total={html_escape(features['total'])}</p>
<p>discovered={html_escape(features['discovered'])}</p>
<p>live_approved={html_escape(features['live_approved'])}</p>
<p><a href="/knowledge/features">Feature Registry</a></p>

<h2>Models</h2>
<p>total={html_escape(models['total'])}</p>
<p>discovered={html_escape(models['discovered'])}</p>
<p>live_approved={html_escape(models['live_approved'])}</p>
<p><a href="/knowledge/models">Model Registry</a></p>

<p>source_policy=KNOWLEDGE_CENTER_READ_ONLY</p>
<p>runtime_changed=0 execution_changed=0 orders_changed=0 fills_changed=0 micro_live_allowed=0</p>
</body>
</html>"""
