from __future__ import annotations

from marketcore.presentation.pages.common import fetchall, fetchone, html_escape, simple_table


def render_experiment_registry() -> str:
    summary = fetchone("""
        SELECT count(*) AS total,
               count(*) FILTER (WHERE status='REGISTERED') AS registered,
               count(*) FILTER (WHERE maturity_level='RESEARCH') AS research,
               count(*) FILTER (WHERE approved_for_live=true) AS live_approved
        FROM warehouse.experiment_registry_v1
    """)

    rows = fetchall("""
        SELECT experiment_code, symbol, timeframe, strategy_code,
               status, maturity_level, decision, profit_factor, expectancy, win_rate
        FROM warehouse.experiment_registry_v1
        ORDER BY updated_at DESC, experiment_code
        LIMIT 30
    """)

    return f"""<!doctype html>
<html lang="ru">
<head><meta charset="utf-8"><title>MarketCore Experiment Registry</title></head>
<body>
<h1>MarketCore Experiment Registry</h1>
<p><a href="/">Главное меню</a> | <a href="/knowledge">Knowledge Center</a> | <a href="/knowledge/experiments/health">Experiment Health</a></p>
<p>total={html_escape(summary['total'])}</p>
<p>registered={html_escape(summary['registered'])}</p>
<p>research={html_escape(summary['research'])}</p>
<p>live_approved={html_escape(summary['live_approved'])}</p>
<h2>Эксперименты</h2>
{simple_table(rows, ['experiment_code', 'symbol', 'timeframe', 'strategy_code', 'status', 'maturity_level', 'decision', 'profit_factor', 'expectancy', 'win_rate'])}
<p>source_policy=EXPERIMENT_REGISTRY_READ_ONLY</p>
<p>runtime_changed=0 execution_changed=0 orders_changed=0 fills_changed=0 micro_live_allowed=0</p>
</body></html>"""


def render_experiment_registry_health() -> str:
    h = fetchone("""
        SELECT count(*) AS total,
               count(*) FILTER (WHERE coalesce(experiment_code,'')='') AS missing_experiment_code,
               count(*) FILTER (WHERE coalesce(status,'')='') AS missing_status,
               count(*) FILTER (WHERE approved_for_live=true OR approved_for_paper=true OR approved_for_shadow=true) AS unsafe_approvals
        FROM warehouse.experiment_registry_v1
    """)

    return f"""<!doctype html>
<html lang="ru">
<head><meta charset="utf-8"><title>MarketCore Experiment Registry Health</title></head>
<body>
<h1>MarketCore Experiment Registry Health</h1>
<p><a href="/">Главное меню</a> | <a href="/knowledge/experiments">Experiment Registry</a></p>
<p>total={html_escape(h['total'])}</p>
<p>missing_experiment_code={html_escape(h['missing_experiment_code'])}</p>
<p>missing_status={html_escape(h['missing_status'])}</p>
<p>unsafe_approvals={html_escape(h['unsafe_approvals'])}</p>
<p>source_policy=EXPERIMENT_REGISTRY_READ_ONLY</p>
<p>runtime_changed=0 execution_changed=0 orders_changed=0 fills_changed=0 micro_live_allowed=0</p>
</body></html>"""
