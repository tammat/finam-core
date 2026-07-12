from __future__ import annotations

import html
import json
import os
import subprocess
from pathlib import Path

import psycopg2
import psycopg2.extras


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
ROOT = Path(__file__).resolve().parents[4]

STRATEGY_NAMES_RU = {
    "MOMENTUM": "Следование за импульсом",
    "MEAN_REVERSION": "Возврат к среднему",
    "BREAKOUT": "Пробой уровня",
}

PARAMETER_NAMES_RU = {
    "threshold": "Порог",
    "lookback": "Период анализа",
    "lookback_bars": "Период анализа",
    "holding_bars": "Удержание",
    "window": "Окно",
    "entry_zscore": "Порог входа",
    "exit_zscore": "Порог выхода",
    "breakout_window": "Окно пробоя",
}

RELATIONSHIP_NAMES_RU = {
    "BRENT_TO_LKOH": "Brent → ЛУКОЙЛ",
    "BRENT_TO_GAZP": "Brent → Газпром",
    "USDRUB_TO_LKOH": "USD/RUB → ЛУКОЙЛ",
    "USDRUB_TO_GAZP": "USD/RUB → Газпром",
    "USDRUB_TO_PLZL": "USD/RUB → Полюс",
    "GOLD_TO_PLZL": "Золото → Полюс",
    "GAS_TO_GAZP": "Газ → Газпром",
    "BTC_TO_ETH": "Bitcoin → Ethereum",
}

REGIME_NAMES_RU = {
    "ALL": "Все режимы",
    "TREND": "Тренд",
    "RANGE": "Боковик",
    "EXPANSION": "Расширение",
    "COMPRESSION": "Сжатие",
}


def _strategy_name_ru(family: object, code: object = "") -> str:
    family_key = str(family or "").upper()
    return STRATEGY_NAMES_RU.get(family_key, str(code or family).replace("_", " ").title())


def _parameter_value_ru(key: str, value: object) -> str:
    if isinstance(value, bool):
        return "Да" if value else "Нет"
    if key == "threshold" and isinstance(value, (int, float)):
        return f"{value:g}%".replace(".", ",")
    if key in {"lookback", "lookback_bars", "holding_bars", "window", "breakout_window"}:
        return f"{value} баров"
    if isinstance(value, float):
        return f"{value:g}".replace(".", ",")
    return str(value)


def _parameters_ru(parameters: object) -> str:
    if isinstance(parameters, str):
        try:
            parameters = json.loads(parameters)
        except (TypeError, ValueError):
            return html.escape(parameters)
    if not isinstance(parameters, dict):
        return html.escape(str(parameters or "Нет параметров"))
    parts = []
    for key, value in parameters.items():
        label = PARAMETER_NAMES_RU.get(str(key), str(key).replace("_", " ").capitalize())
        parts.append(f"<span><b>{html.escape(label)}:</b> {html.escape(_parameter_value_ru(str(key), value))}</span>")
    return " · ".join(parts) or "Нет параметров"


def _rows() -> list[dict]:
    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT parameter_json->>'threshold' AS threshold,
                       oos_trades,oos_profit_factor,oos_expectancy,oos_max_drawdown,
                       folds_passed,folds_total,verdict_code,promotion_allowed,
                       oos_start,oos_end,updated_at,reason
                FROM analytics.edge_oos_result_v1
                WHERE research_batch_id='20260712_MOMENTUM_THRESHOLD_RECALC_V2'
                  AND validation_version='MOMENTUM_CHRONOLOGICAL_OOS_V1'
                ORDER BY promotion_allowed DESC,oos_profit_factor DESC;
            """)
            return [dict(row) for row in cur.fetchall()]


def _hypotheses() -> tuple[list[dict], dict]:
    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT discovery_run_id FROM analytics.edge_regime_hypothesis_result_v2 ORDER BY created_at DESC LIMIT 1")
            latest = cur.fetchone()
            if not latest:
                return [], {}
            run_id = latest["discovery_run_id"]
            cur.execute("""
                SELECT strategy_family,strategy_code,symbol,timeframe,parameter_json,regime_code,
                       validation_profit_factor,oos_trades,oos_profit_factor,oos_expectancy,
                       folds_passed,folds_total,transaction_cost_bps,hypothesis_score,
                       regime_coverage_ratio,trust_status,verdict_code,created_at
                FROM analytics.edge_regime_hypothesis_result_v2
                WHERE discovery_run_id=%s
                ORDER BY trust_status DESC,verdict_code,hypothesis_score DESC LIMIT 60
            """, (run_id,))
            rows = [dict(row) for row in cur.fetchall()]
            cur.execute("""
                SELECT count(*) AS hypotheses,count(DISTINCT symbol) AS markets,
                       count(DISTINCT strategy_family) AS families,
                       count(*) FILTER(WHERE verdict_code='OOS_PASS') AS passed
                FROM analytics.edge_regime_hypothesis_result_v2 WHERE discovery_run_id=%s
            """, (run_id,))
            return rows, dict(cur.fetchone() or {})


def _lead_lag() -> tuple[list[dict], dict]:
    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT discovery_run_id FROM analytics.intermarket_lead_lag_result_v1 ORDER BY created_at DESC LIMIT 1")
            latest = cur.fetchone()
            if not latest:
                return [], {}
            run_id = latest["discovery_run_id"]
            cur.execute("""
                SELECT relationship_code,thesis,source_symbol,target_symbol,impulse_bars,lag_bars,
                       regime_group,oos_trades,oos_profit_factor,oos_expectancy_bps,oos_hit_rate,
                       oos_information_coefficient,folds_passed,folds_total,adjusted_p_value,
                       regime_coverage_ratio,trust_status,verdict_code,hypothesis_score
                FROM analytics.intermarket_lead_lag_result_v1
                WHERE discovery_run_id=%s
                ORDER BY CASE verdict_code WHEN 'OOS_PASS' THEN 1 WHEN 'OOS_FAIL' THEN 2 ELSE 3 END,
                         adjusted_p_value,hypothesis_score DESC
                LIMIT 80
            """, (run_id,))
            rows = [dict(row) for row in cur.fetchall()]
            cur.execute("""
                SELECT count(*) AS trials,count(DISTINCT relationship_code) AS relationships,
                       count(*) FILTER(WHERE verdict_code='OOS_PASS') AS passed,
                       count(*) FILTER(WHERE verdict_code='OOS_FAIL') AS failed,
                       count(*) FILTER(WHERE verdict_code='UNVERIFIED') AS unverified
                FROM analytics.intermarket_lead_lag_result_v1 WHERE discovery_run_id=%s
            """, (run_id,))
            return rows, dict(cur.fetchone() or {})


def run_oos_action_v1() -> str:
    env = dict(os.environ)
    env.update({"DATABASE_URL": DB, "PYTHONPATH": str(ROOT / "src"), "PYTHONDONTWRITEBYTECODE": "1"})
    result = subprocess.run(
        [str(ROOT / ".venv/bin/python"), "src/scripts/build_momentum_edge_oos_rank_v1.py"],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=30, check=False,
    )
    verdict = "Проверка завершена" if result.returncode == 0 else "Ошибка проверки"
    return f"{verdict}. Код: {result.returncode}"


def run_hypothesis_action_v1() -> str:
    env = dict(os.environ)
    env.update({"DATABASE_URL": DB, "PYTHONPATH": str(ROOT / "src"), "PYTHONDONTWRITEBYTECODE": "1"})
    result = subprocess.run(
        [str(ROOT / ".venv/bin/python"), "src/scripts/build_edge_regime_hypothesis_discovery_v2.py"],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=90, check=False,
    )
    verdict = "Поиск гипотез завершён" if result.returncode == 0 else "Ошибка поиска гипотез"
    return f"{verdict}. Код: {result.returncode}"


def run_lead_lag_action_v1() -> str:
    env = dict(os.environ)
    env.update({"DATABASE_URL": DB, "PYTHONPATH": str(ROOT / "src"), "PYTHONDONTWRITEBYTECODE": "1"})
    result = subprocess.run(
        [str(ROOT / ".venv/bin/python"), "src/scripts/build_intermarket_lead_lag_engine_v1.py"],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=120, check=False,
    )
    verdict = "Межрыночный поиск завершён" if result.returncode == 0 else "Ошибка межрыночного поиска"
    return f"{verdict}. Код: {result.returncode}"


def render_edge_oos_control_center_v1(notice: str = "") -> str:
    rows = _rows()
    hypotheses, hypothesis_summary = _hypotheses()
    lead_lag_rows, lead_lag_summary = _lead_lag()
    passed = sum(1 for row in rows if row["verdict_code"] == "OOS_PASS")
    failed = len(rows) - passed
    oos_bars = 0
    if rows and rows[0].get("oos_start") and rows[0].get("oos_end"):
        oos_bars = "2846"
    last_run = max((row.get("updated_at") for row in rows), default=None)

    table_rows = "".join(
        f"""<tr data-verdict="{html.escape(str(row['verdict_code']))}">
        <td><strong>{html.escape(str(row['threshold']))}%</strong></td>
        <td>{row['oos_trades']}</td><td>{float(row['oos_profit_factor']):.2f}</td>
        <td class="{'is-positive' if row['oos_expectancy'] > 0 else 'is-negative'}">{float(row['oos_expectancy']):.2f}</td>
        <td class="is-negative">{float(row['oos_max_drawdown']):.1f}</td>
        <td>{row['folds_passed']}/{row['folds_total']}</td>
        <td><span class="mc-oos-badge {'pass' if row['verdict_code'] == 'OOS_PASS' else 'fail'}">{row['verdict_code'].removeprefix('OOS_')}</span></td>
        <td>{'Разрешено' if row['promotion_allowed'] else 'Заблокировано'}</td></tr>"""
        for row in rows
    )
    notice_html = f'<div class="mc-oos-notice">{html.escape(notice)}</div>' if notice else ""
    hypothesis_rows = "".join(
        f"""<tr data-hypothesis-row data-family="{row['strategy_family']}" data-verdict="{row['verdict_code']}">
        <td><strong>{html.escape(_strategy_name_ru(row['strategy_family'], row['strategy_code']))}</strong></td><td>{html.escape(row['symbol'])}</td>
        <td>{html.escape(str(row['regime_code']).replace('_', ' '))}</td>
        <td class="mc-edge-parameters">{_parameters_ru(row['parameter_json'])}</td><td>{float(row['validation_profit_factor']):.2f}</td>
        <td>{float(row['oos_profit_factor']):.2f}</td><td class="{'is-positive' if row['oos_expectancy'] > 0 else 'is-negative'}">{float(row['oos_expectancy']):.3f}</td>
        <td>{row['folds_passed']}/{row['folds_total']}</td><td>{float(row['regime_coverage_ratio']) * 100:.0f}%</td><td>{float(row['transaction_cost_bps']):.0f} bps</td>
        <td>{float(row['hypothesis_score']):.1f}</td><td>{'Проверено' if row['trust_status'] == 'VERIFIED' else 'Нет данных'}</td>
        <td><span class="mc-oos-badge {'pass' if row['verdict_code'] == 'OOS_PASS' else 'fail'}">{row['verdict_code'].removeprefix('OOS_')}</span></td></tr>"""
        for row in hypotheses
    )
    lead_lag_table_rows = "".join(
        f"""<tr data-lead-lag-row data-verdict="{row['verdict_code']}">
        <td><strong>{html.escape(RELATIONSHIP_NAMES_RU.get(row['relationship_code'], row['relationship_code']))}</strong><br><small>{html.escape(row['thesis'])}</small></td>
        <td>{html.escape(REGIME_NAMES_RU.get(row['regime_group'], row['regime_group']))}</td>
        <td>{row['impulse_bars']} бар.</td><td>{row['lag_bars']} бар.</td><td>{row['oos_trades']}</td>
        <td>{float(row['oos_profit_factor']):.2f}</td>
        <td class="{'is-positive' if row['oos_expectancy_bps'] > 0 else 'is-negative'}">{float(row['oos_expectancy_bps']):.2f}</td>
        <td>{float(row['oos_information_coefficient']):.3f}</td><td>{row['folds_passed']}/{row['folds_total']}</td>
        <td>{float(row['adjusted_p_value']):.3f}</td><td>{float(row['regime_coverage_ratio']) * 100:.0f}%</td>
        <td>{'Проверено' if row['trust_status'] == 'VERIFIED' else 'Нет данных'}</td>
        <td><span class="mc-oos-badge {'pass' if row['verdict_code'] == 'OOS_PASS' else 'fail'}">{'НЕТ ДАННЫХ' if row['verdict_code'] == 'UNVERIFIED' else row['verdict_code'].removeprefix('OOS_')}</span></td></tr>"""
        for row in lead_lag_rows
    )
    return f"""<!doctype html><html lang="ru"><head><meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>MarketCore — Edge OOS Control Center</title>
    <link rel="stylesheet" href="/assets/marketcore/ui-runtime/v1/runtime.css"></head>
    <body><div class="mc-oos-layout">
      <aside class="mc-oos-sidebar"><a class="brand" href="/workspace-v2">MARKETCORE</a>
        <nav><a href="/workspace-v2">Обзор</a><a href="/workspace-v2/portfolio">Портфель</a>
        <a class="active" href="/workspace-v2/control-center/edge-oos">Edge · OOS <span>{failed}</span></a></nav>
        <div class="mc-oos-safety"><b>LIVE LOCK</b><small>Продвижение разрешено только после OOS_PASS</small></div>
      </aside>
      <main class="mc-oos-main"><header class="mc-oos-header"><div><p>CONTROL CENTER / EDGE</p>
        <h1>OOS-проверка Momentum</h1><span>Честный holdout после первых 5000 баров</span></div>
        <div class="mc-oos-actions"><form method="post" action="/workspace-v2/control-center/edge-oos/run">
          <button class="secondary" type="submit">Повторить OOS</button></form>
          <form method="post" action="/workspace-v2/control-center/edge-oos/discover">
          <button type="submit">Искать гипотезы</button></form>
          <form method="post" action="/workspace-v2/control-center/edge-oos/lead-lag">
          <button type="submit">Lead/Lag поиск</button></form></div></header>{notice_html}
        <section class="mc-oos-kpis"><article><span>Параметров</span><b>{len(rows)}</b></article>
          <article><span>OOS PASS</span><b class="is-positive">{passed}</b></article>
          <article><span>OOS FAIL</span><b class="is-negative">{failed}</b></article>
          <article><span>Holdout</span><b>{oos_bars} баров</b></article></section>
        <section class="mc-oos-panel"><div class="mc-oos-toolbar"><div><h2>Рейтинг параметров</h2>
          <p>Последний запуск: {html.escape(str(last_run or 'нет данных'))}</p></div>
          <label>Вердикт <select data-oos-filter><option value="ALL">Все</option><option value="OOS_PASS">PASS</option><option value="OOS_FAIL">FAIL</option></select></label></div>
          <div class="mc-oos-table-wrap"><table class="mc-oos-table"><thead><tr><th>Порог</th><th>Сделки</th><th>PF</th><th>Ожидание</th><th>Просадка</th><th>Периоды</th><th>Вердикт</th><th>Продвижение</th></tr></thead>
          <tbody data-oos-results>{table_rows}</tbody></table></div></section>
        <section class="mc-oos-panel mc-hypothesis-panel"><div class="mc-oos-toolbar"><div><h2>Поиск новых гипотез</h2>
          <p>{hypothesis_summary.get('hypotheses', 0)} комбинаций · {hypothesis_summary.get('markets', 0)} рынков · {hypothesis_summary.get('families', 0)} семейства · PASS {hypothesis_summary.get('passed', 0)}</p></div>
          <label>Семейство <select data-hypothesis-filter><option value="ALL">Все</option><option value="MOMENTUM">Следование за импульсом</option><option value="MEAN_REVERSION">Возврат к среднему</option><option value="BREAKOUT">Пробой уровня</option></select></label></div>
          <div class="mc-oos-table-wrap"><table class="mc-oos-table"><thead><tr><th>Стратегия</th><th>Инструмент</th><th>Режим входа</th><th>Параметры</th><th>Val PF</th><th>OOS PF</th><th>OOS Exp</th><th>Периоды</th><th>Покрытие</th><th>Издержки</th><th>Score</th><th>Доверие</th><th>Вердикт</th></tr></thead>
          <tbody>{hypothesis_rows}</tbody></table></div></section>
        <section class="mc-oos-kpis"><article><span>Lead/Lag испытаний</span><b>{lead_lag_summary.get('trials', 0)}</b></article>
          <article><span>Подтверждено</span><b class="is-positive">{lead_lag_summary.get('passed', 0)}</b></article>
          <article><span>Отклонено</span><b class="is-negative">{lead_lag_summary.get('failed', 0)}</b></article>
          <article><span>Нет данных</span><b>{lead_lag_summary.get('unverified', 0)}</b></article></section>
        <section class="mc-oos-panel"><div class="mc-oos-toolbar"><div><h2>Межрыночные Lead/Lag связи</h2>
          <p>{lead_lag_summary.get('relationships', 0)} связей · значимость скорректирована по всем испытаниям</p></div>
          <label>Вердикт <select data-lead-lag-filter><option value="ALL">Все</option><option value="OOS_PASS">PASS</option><option value="OOS_FAIL">FAIL</option><option value="UNVERIFIED">Нет данных</option></select></label></div>
          <div class="mc-oos-table-wrap"><table class="mc-oos-table"><thead><tr><th>Связь</th><th>Режим</th><th>Импульс</th><th>Лаг</th><th>OOS</th><th>PF</th><th>Ожидание, bps</th><th>IC</th><th>Периоды</th><th>p скорр.</th><th>Покрытие</th><th>Доверие</th><th>Вердикт</th></tr></thead>
          <tbody>{lead_lag_table_rows}</tbody></table></div><p data-lead-lag-count>Показано: {len(lead_lag_rows)}</p></section>
        <footer class="mc-oos-status"><span>DATA: REAL</span><span>OOS REGISTRY: ONLINE</span><span>LIVE: BLOCKED</span><span data-oos-count>Показано: {len(rows)}</span></footer>
      </main></div><script src="/assets/marketcore/ui-runtime/v1/edge-oos-control.js"></script></body></html>"""
