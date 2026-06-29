from __future__ import annotations

from marketcore.presentation.pages.common import fetchall, fetchone, html_escape, simple_table
from marketcore.registry.ui import registry_policy_block


def render_ai_registry() -> str:
    summary = fetchone("""
        SELECT count(*)::int AS total
        FROM warehouse.ai_registry_v1
    """)

    type_rows = fetchall("""
        SELECT ai_type, count(*)::int AS total
        FROM warehouse.ai_registry_v1
        GROUP BY ai_type
        ORDER BY ai_type
    """)

    rows = fetchall("""
        SELECT ai_code, ai_name, ai_type, status, maturity_level, description
        FROM warehouse.ai_registry_v1
        ORDER BY ai_code
    """)

    health = fetchone("""
        SELECT
            (SELECT count(*)::int FROM warehouse.ai_registry_v1) AS total,
            (SELECT count(*)::int FROM warehouse.ai_registry_v1 WHERE approved_for_live=true) AS unsafe_live_rows,
            (SELECT count(*)::int FROM warehouse.ai_registry_v1 WHERE execution_policy='AI_RECOMMENDS_ONLY_NO_DIRECT_EXECUTION') AS execution_policy_valid,
            (SELECT count(*)::int FROM warehouse.ai_registry_v1 WHERE market_knowledge_policy='AI_REGISTRY_STORES_AI_KNOWLEDGE_ONLY') AS market_policy_valid,
            (SELECT count(*)::int FROM warehouse.ai_registry_v1 WHERE graph_required=true) AS graph_required_valid,
            (SELECT count(*)::int FROM warehouse.ai_registry_v1 WHERE payload->>'registry_framework_version'='V1') AS framework_version_valid,
            (SELECT count(*)::int FROM warehouse.ai_registry_v1 WHERE payload->>'domain_types_version'='V1') AS domain_types_version_valid,
            (SELECT count(*)::int FROM warehouse.ai_registry_v1
              WHERE payload ? 'feature_code'
                 OR payload ? 'model_code'
                 OR payload ? 'experiment_code'
                 OR payload ? 'dataset_code'
                 OR payload::text ILIKE '%%feature_code%%'
                 OR payload::text ILIKE '%%model_code%%'
                 OR payload::text ILIKE '%%experiment_code%%'
                 OR payload::text ILIKE '%%dataset_code%%') AS forbidden_market_fields
    """)

    graph_health = "OK" if (
        int(health["unsafe_live_rows"]) == 0
        and int(health["forbidden_market_fields"]) == 0
        and int(health["execution_policy_valid"]) == int(health["total"])
        and int(health["market_policy_valid"]) == int(health["total"])
        and int(health["graph_required_valid"]) == int(health["total"])
    ) else "FAILED"

    return f"""<!doctype html>
<html lang="ru">
<head><meta charset="utf-8"><title>MarketCore AI Registry</title></head>
<body>
<h1>MarketCore AI Registry</h1>
<p><a href="/">Главное меню</a> | <a href="/knowledge">Knowledge Center</a></p>

<h2>Summary</h2>
<p>ai_registry_total={html_escape(summary['total'])}</p>
{simple_table(type_rows, ['ai_type', 'total'])}

<h2>Health</h2>
<p>ai_registry_health={html_escape(graph_health)}</p>
<p>unsafe_live_rows={html_escape(health['unsafe_live_rows'])}</p>
<p>execution_policy_valid={html_escape(health['execution_policy_valid'])}</p>
<p>market_policy_valid={html_escape(health['market_policy_valid'])}</p>
<p>graph_required_valid={html_escape(health['graph_required_valid'])}</p>
<p>framework_version_valid={html_escape(health['framework_version_valid'])}</p>
<p>domain_types_version_valid={html_escape(health['domain_types_version_valid'])}</p>
<p>forbidden_market_fields={html_escape(health['forbidden_market_fields'])}</p>

<h2>AI Components</h2>
{simple_table(rows, ['ai_code', 'ai_name', 'ai_type', 'status', 'maturity_level', 'description'])}

<h2>Policies</h2>
<p>policy=READ_ONLY</p>
<p>commands=summary,list,search,health</p>
<p>forbidden_commands=add,update,delete,edit</p>
<p>framework=REGISTRY_FRAMEWORK_V1</p>
<p>bootstrap_policy=AI_BOOTSTRAP_POLICY_V1</p>
<p>execution_policy=AI_RECOMMENDS_ONLY_NO_DIRECT_EXECUTION</p>
<p>market_knowledge_policy=AI_REGISTRY_STORES_AI_KNOWLEDGE_ONLY</p>
<p>source_policy=AI_REGISTRY_DOES_NOT_STORE_MARKET_KNOWLEDGE</p>
{registry_policy_block("AI_REGISTRY_STORES_AI_KNOWLEDGE_ONLY")}

<p>ui_policy=READ_ONLY_SINGLE_PORT_8089</p>
<p>runtime_changed=0 execution_changed=0 orders_changed=0 fills_changed=0 micro_live_allowed=0</p>
</body></html>"""
