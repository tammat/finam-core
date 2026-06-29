from __future__ import annotations

from marketcore.presentation.pages.common import fetchall, fetchone, html_escape, simple_table


def render_registry_relationships() -> str:
    summary = fetchone("""
        SELECT count(*) AS total,
               count(*) FILTER (WHERE validation_status='VALIDATED') AS validated,
               count(*) FILTER (WHERE validation_status <> 'VALIDATED') AS not_validated
        FROM warehouse.registry_relationship_v1
    """)

    counts = fetchall("""
        SELECT relationship_type, count(*) AS total
        FROM warehouse.registry_relationship_v1
        GROUP BY relationship_type
        ORDER BY relationship_type
    """)

    health = fetchone("""
        SELECT count(*) AS total,
               count(*) FILTER (WHERE coalesce(source_code,'')='') AS missing_source_code,
               count(*) FILTER (WHERE coalesce(target_code,'')='') AS missing_target_code,
               count(*) FILTER (WHERE validation_status <> 'VALIDATED') AS not_validated
        FROM warehouse.registry_relationship_v1
    """)

    return f"""<!doctype html>
<html lang="ru">
<head><meta charset="utf-8"><title>MarketCore Registry Relationships</title></head>
<body>
<h1>MarketCore Registry Relationships</h1>
<p><a href="/">Главное меню</a> | <a href="/knowledge">Knowledge Center</a></p>

<h2>Сводка</h2>
<p>total={html_escape(summary['total'])}</p>
<p>validated={html_escape(summary['validated'])}</p>
<p>not_validated={html_escape(summary['not_validated'])}</p>

<h2>Типы связей</h2>
{simple_table(counts, ['relationship_type', 'total'])}

<h2>Health</h2>
<p>missing_source_code={html_escape(health['missing_source_code'])}</p>
<p>missing_target_code={html_escape(health['missing_target_code'])}</p>
<p>not_validated={html_escape(health['not_validated'])}</p>

<p>политика=СВЯЗИ_БЕЗ_КОПИРОВАНИЯ_ДАННЫХ</p>
<p>source_policy=REGISTRY_RELATIONSHIP_READ_ONLY</p>
<p>runtime_changed=0 execution_changed=0 orders_changed=0 fills_changed=0 micro_live_allowed=0</p>
</body></html>"""
