from __future__ import annotations

from marketcore.presentation.pages.common import fetchall, fetchone, html_escape, simple_table


def render_model_registry() -> str:
    summary = fetchone("""
        SELECT count(*) AS total,
               count(*) FILTER (WHERE status='DISCOVERED') AS discovered,
               count(*) FILTER (WHERE maturity_level='RESEARCH') AS research,
               count(*) FILTER (WHERE approved_for_live=true) AS live_approved
        FROM warehouse.model_registry_v1
    """)

    classes = fetchall("""
        SELECT model_class, count(*) AS total
        FROM warehouse.model_registry_v1
        GROUP BY model_class
        ORDER BY total DESC, model_class
        LIMIT 30
    """)

    return f"""<!doctype html>
<html lang="ru">
<head><meta charset="utf-8"><title>MarketCore Model Registry</title></head>
<body>
<h1>MarketCore Model Registry</h1>
<p><a href="/">Главное меню</a> | <a href="/knowledge">Knowledge Center</a> | <a href="/knowledge/models/health">Model Health</a></p>
<p>total={html_escape(summary['total'])}</p>
<p>discovered={html_escape(summary['discovered'])}</p>
<p>research={html_escape(summary['research'])}</p>
<p>live_approved={html_escape(summary['live_approved'])}</p>
<h2>Классы Model</h2>
{simple_table(classes, ['model_class', 'total'])}
<p>source_policy=MODEL_REGISTRY_READ_ONLY</p>
<p>ai_policy=AI_RECOMMENDS_ONLY_NO_DIRECT_EXECUTION</p>
<p>model_policy=MODEL_NO_DIRECT_EXECUTION</p>
<p>runtime_changed=0 execution_changed=0 orders_changed=0 fills_changed=0 micro_live_allowed=0</p>
</body></html>"""


def render_model_registry_health() -> str:
    h = fetchone("""
        SELECT count(*) AS total,
               count(*) FILTER (WHERE coalesce(model_code,'')='') AS missing_model_code,
               count(*) FILTER (WHERE coalesce(status,'')='') AS missing_status,
               count(*) FILTER (WHERE approved_for_live=true OR approved_for_paper=true OR approved_for_shadow=true) AS unsafe_approvals
        FROM warehouse.model_registry_v1
    """)

    return f"""<!doctype html>
<html lang="ru">
<head><meta charset="utf-8"><title>MarketCore Model Registry Health</title></head>
<body>
<h1>MarketCore Model Registry Health</h1>
<p><a href="/">Главное меню</a> | <a href="/knowledge/models">Model Registry</a></p>
<p>total={html_escape(h['total'])}</p>
<p>missing_model_code={html_escape(h['missing_model_code'])}</p>
<p>missing_status={html_escape(h['missing_status'])}</p>
<p>unsafe_approvals={html_escape(h['unsafe_approvals'])}</p>
<p>source_policy=MODEL_REGISTRY_READ_ONLY</p>
<p>runtime_changed=0 execution_changed=0 orders_changed=0 fills_changed=0 micro_live_allowed=0</p>
</body></html>"""
