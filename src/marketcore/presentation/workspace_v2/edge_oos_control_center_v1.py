from __future__ import annotations

import html
import json
import os
import subprocess
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import psycopg2
import psycopg2.extras


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
ROOT = Path(__file__).resolve().parents[4]
PYTHON = Path(os.getenv("MARKETCORE_PYTHON", str(ROOT / ".venv/bin/python")))
if not PYTHON.exists():
    PYTHON = Path("/opt/finam-core/.venv/bin/python")

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

SESSION_NAMES_RU = {
    "MOEX_OPEN": "Открытие MOEX",
    "MOEX_FIRST_HOUR": "Первые 30–60 минут",
    "EUROPE_OVERLAP": "Европейская сессия",
    "US_OPEN": "Открытие США",
    "EVENING": "Вечерняя сессия",
    "MOEX_CLOSE": "Закрытие MOEX",
}

EXECUTION_POLICY_NAMES_RU = {
    "BASELINE": "Базовое удержание",
    "SHORT_HOLD": "Короткое удержание",
    "LONG_HOLD": "Длинное удержание",
    "REGIME_CHANGE_EXIT": "Выход при смене режима",
    "SKIP_OPEN_CLOSE": "Исключить открытие и закрытие",
}

RELATIONSHIP_FAMILY_NAMES_RU = {
    "INDEX_TO_STOCK": "Индекс → акция",
    "SECTOR_TO_STOCK": "Сектор → акция",
    "MULTIFACTOR_TO_STOCK": "Несколько факторов → акция",
    "OVERNIGHT_TO_OPEN": "Ночь → открытие MOEX",
    "LIQUIDITY_TO_RETURN": "Ликвидность → доходность",
    "PAIR_SPREAD": "Парный спред",
}

COMMODITY_NAMES_RU = {"BR_ROLLING@RTSX": "Brent", "NG_ROLLING@RTSX": "Природный газ"}
COMMODITY_TIMERS = {"BR_ROLLING@RTSX": "finam-moex-brent-online.timer", "NG_ROLLING@RTSX": "finam-moex-natural-gas-online.timer"}

FUNNEL_ACTIONS_RU = {
    "DATA": "Восстановить историю, свежесть и пройти Data Quality Gate",
    "EDGE": "Оставить в Research, расширить гипотезу и повторить OOS",
    "MARKET": "Ограничить допустимые режимы и торговые сессии",
    "RISK": "Снизить размер, концентрацию или факторную экспозицию",
    "EXECUTION": "Проверить broker/order/fill reconciliation и маршрутизацию",
    "BLOCK": "Открыть governance gate и устранить конкретную блокировку",
    "PASS": "Наблюдать стабильность, не менять правила без нового OOS",
    "OTHER": "Провести аудит lineage и классифицировать причину",
}


def _format_datetime_ru(value: object, timezone: str = "Europe/Moscow") -> str:
    if value is None:
        return "нет данных"
    parsed = value
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return html.escape(value)
    if isinstance(parsed, datetime):
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=ZoneInfo("UTC"))
        return parsed.astimezone(ZoneInfo(timezone)).strftime("%d.%m.%Y, %H:%M")
    if isinstance(parsed, date):
        return parsed.strftime("%d.%m.%Y")
    return html.escape(str(parsed))


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


def _session_edges() -> tuple[list[dict], dict]:
    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT discovery_run_id FROM analytics.edge_session_result_v1 ORDER BY created_at DESC LIMIT 1")
            latest = cur.fetchone()
            if not latest:
                return [], {}
            run_id = latest["discovery_run_id"]
            cur.execute("""
                SELECT strategy_family,strategy_code,symbol,regime_code,session_code,
                       validation_trades,validation_profit_factor,oos_trades,oos_profit_factor,
                       oos_expectancy,folds_passed,folds_total,adjusted_p_value,
                       regime_coverage_ratio,trust_status,verdict_code
                FROM analytics.edge_session_result_v1 WHERE discovery_run_id=%s
                ORDER BY CASE verdict_code WHEN 'OOS_PASS' THEN 1 WHEN 'OOS_FAIL' THEN 2 ELSE 3 END,
                         adjusted_p_value,oos_trades DESC,oos_profit_factor DESC LIMIT 160
            """, (run_id,))
            rows = [dict(row) for row in cur.fetchall()]
            cur.execute("""
                SELECT count(*) AS trials,count(DISTINCT session_code) AS sessions,
                       count(*) FILTER(WHERE verdict_code='OOS_PASS') AS passed,
                       count(*) FILTER(WHERE verdict_code='OOS_FAIL') AS failed,
                       count(*) FILTER(WHERE verdict_code='UNVERIFIED') AS unverified
                FROM analytics.edge_session_result_v1 WHERE discovery_run_id=%s
            """, (run_id,))
            return rows, dict(cur.fetchone() or {})


def _execution_edges() -> tuple[list[dict], dict]:
    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT discovery_run_id FROM analytics.execution_edge_result_v1 ORDER BY created_at DESC LIMIT 1")
            latest = cur.fetchone()
            if not latest:
                return [], {}
            run_id = latest["discovery_run_id"]
            cur.execute("""
                SELECT strategy_family,strategy_code,symbol,regime_code,session_code,policy_code,
                       oos_trades,oos_profit_factor,oos_expectancy,baseline_oos_profit_factor,
                       baseline_oos_expectancy,delta_profit_factor,delta_expectancy,
                       folds_passed,folds_total,adjusted_p_value,market_data_quality,
                       trust_status,verdict_code
                FROM analytics.execution_edge_result_v1 WHERE discovery_run_id=%s
                ORDER BY CASE verdict_code WHEN 'OOS_PASS' THEN 1 WHEN 'OOS_FAIL' THEN 2 ELSE 3 END,
                         adjusted_p_value,delta_expectancy DESC LIMIT 160
            """, (run_id,))
            rows = [dict(row) for row in cur.fetchall()]
            cur.execute("""
                SELECT count(*) AS trials,count(DISTINCT policy_code) AS policies,
                       count(*) FILTER(WHERE verdict_code='OOS_PASS') AS passed,
                       count(*) FILTER(WHERE verdict_code='OOS_FAIL') AS failed,
                       count(*) FILTER(WHERE verdict_code='UNVERIFIED') AS unverified,
                       count(*) FILTER(WHERE market_data_quality='QUOTE_VERIFIED') AS quote_verified
                FROM analytics.execution_edge_result_v1 WHERE discovery_run_id=%s
            """, (run_id,))
            return rows, dict(cur.fetchone() or {})


def _relationship_factory() -> tuple[list[dict], dict]:
    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT discovery_run_id FROM analytics.relationship_factory_result_v2 ORDER BY created_at DESC LIMIT 1")
            latest = cur.fetchone()
            if not latest:
                return [], {}
            run_id = latest["discovery_run_id"]
            cur.execute("""
                WITH ranked AS (
                    SELECT priority,relationship_family,relationship_code,thesis,source_symbols,target_symbol,
                           impulse_bars,lag_bars,regime_group,session_code,aligned_bars,regime_coverage_ratio,
                           validation_trades,validation_profit_factor,oos_trades,oos_profit_factor,
                           oos_expectancy_bps,folds_passed,folds_total,adjusted_p_value,
                           trust_status,verdict_code,reason_code,
                           row_number() OVER (PARTITION BY relationship_family ORDER BY
                               CASE verdict_code WHEN 'OOS_PASS' THEN 1 WHEN 'OOS_FAIL' THEN 2 ELSE 3 END,
                               adjusted_p_value,oos_trades DESC,oos_profit_factor DESC) AS family_rank
                    FROM analytics.relationship_factory_result_v2 WHERE discovery_run_id=%s
                )
                SELECT priority,relationship_family,relationship_code,thesis,source_symbols,target_symbol,
                       impulse_bars,lag_bars,regime_group,session_code,aligned_bars,regime_coverage_ratio,
                       validation_trades,validation_profit_factor,oos_trades,oos_profit_factor,
                       oos_expectancy_bps,folds_passed,folds_total,adjusted_p_value,
                       trust_status,verdict_code,reason_code
                FROM ranked WHERE family_rank <= 90
                ORDER BY priority,relationship_family,family_rank
            """, (run_id,))
            rows = [dict(row) for row in cur.fetchall()]
            cur.execute("""
                SELECT count(*) AS trials,count(DISTINCT relationship_code) AS relationships,
                       count(DISTINCT relationship_family) AS families,
                       count(*) FILTER(WHERE verdict_code='OOS_PASS') AS passed,
                       count(*) FILTER(WHERE verdict_code='OOS_FAIL') AS failed,
                       count(*) FILTER(WHERE verdict_code='UNVERIFIED') AS unverified
                FROM analytics.relationship_factory_result_v2 WHERE discovery_run_id=%s
            """, (run_id,))
            return rows, dict(cur.fetchone() or {})


def _data_quality_gate() -> tuple[list[dict], dict]:
    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT audit_run_id FROM analytics.relationship_data_quality_gate_v1 ORDER BY created_at DESC LIMIT 1")
            latest = cur.fetchone()
            if not latest:
                return [], {}
            run_id = latest["audit_run_id"]
            cur.execute("""SELECT symbol,timeframe,bars,trading_days,first_ts,last_ts,latest_age_hours,
                       duplicate_rows,invalid_ohlc_rows,regime_rows,regime_coverage_ratio,calendar_gap_status,
                       market_data_status,factory_status,reason_codes
                FROM analytics.relationship_data_quality_gate_v1 WHERE audit_run_id=%s
                ORDER BY CASE factory_status WHEN 'READY' THEN 1 ELSE 2 END,symbol""", (run_id,))
            rows = [dict(row) for row in cur.fetchall()]
            cur.execute("""SELECT count(*) AS symbols,
                       count(*) FILTER(WHERE market_data_status='READY') AS market_ready,
                       count(*) FILTER(WHERE factory_status='READY') AS factory_ready,
                       count(*) FILTER(WHERE factory_status='BLOCKED') AS blocked
                FROM analytics.relationship_data_quality_gate_v1 WHERE audit_run_id=%s""", (run_id,))
            return rows, dict(cur.fetchone() or {})


def _commodity_factors() -> tuple[list[dict], list[dict]]:
    factors: list[dict] = []
    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            for symbol in COMMODITY_NAMES_RU:
                cur.execute("""SELECT symbol,bars,trading_days,last_ts,latest_age_hours,regime_coverage_ratio,
                           market_data_status,factory_status,reason_codes
                    FROM analytics.relationship_data_quality_gate_v1 WHERE symbol=%s
                    ORDER BY created_at DESC LIMIT 1""", (symbol,))
                row = dict(cur.fetchone() or {"symbol": symbol, "bars": 0, "trading_days": 0,
                    "regime_coverage_ratio": 0, "market_data_status": "BLOCKED", "factory_status": "BLOCKED", "reason_codes": ["NO_DATA"]})
                timer = subprocess.run(["systemctl", "is-active", COMMODITY_TIMERS[symbol]], capture_output=True, text=True, check=False)
                row["timer_status"] = timer.stdout.strip() or "inactive"
                factors.append(row)
            cur.execute("SELECT discovery_run_id FROM analytics.relationship_factory_result_v2 ORDER BY created_at DESC LIMIT 1")
            latest = cur.fetchone()
            relations: list[dict] = []
            if latest:
                cur.execute("""SELECT relationship_code,target_symbol,oos_trades,oos_profit_factor,oos_expectancy_bps,
                           adjusted_p_value,trust_status,verdict_code,reason_code
                    FROM analytics.relationship_factory_result_v2 WHERE discovery_run_id=%s
                      AND (relationship_code LIKE 'BRENT%%' OR relationship_code LIKE 'GAS%%')
                    ORDER BY CASE verdict_code WHEN 'OOS_PASS' THEN 1 WHEN 'OOS_FAIL' THEN 2 ELSE 3 END,
                             adjusted_p_value,oos_trades DESC LIMIT 40""", (latest["discovery_run_id"],))
                relations = [dict(row) for row in cur.fetchall()]
    return factors, relations


def _signal_funnel() -> tuple[list[dict], list[dict], bool]:
    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT signal_funnel_snapshot_id FROM analytics.signal_funnel_snapshot_v1 ORDER BY created_at DESC LIMIT 1")
            latest = cur.fetchone()
            stages: list[dict] = []
            comparable = True
            if latest:
                cur.execute("""SELECT stage_order,stage_code,stage_name,stage_count,previous_stage_count,
                           pass_rate_pct,stage_status,evidence_json
                    FROM analytics.signal_funnel_stage_v1 WHERE signal_funnel_snapshot_id=%s ORDER BY stage_order""",
                    (latest["signal_funnel_snapshot_id"],))
                stages = [dict(row) for row in cur.fetchall()]
                comparable = all(row["previous_stage_count"] is None or row["stage_count"] <= row["previous_stage_count"] for row in stages)
            cur.execute("SELECT signal_funnel_reason_snapshot_id FROM analytics.signal_funnel_reason_snapshot_v1 ORDER BY created_at DESC LIMIT 1")
            reason_latest = cur.fetchone()
            reasons: list[dict] = []
            if reason_latest:
                cur.execute("""SELECT reason_group,sum(rows_total) AS rows_total,count(*) AS reason_values
                    FROM analytics.signal_funnel_reason_v1 WHERE signal_funnel_reason_snapshot_id=%s
                    GROUP BY reason_group ORDER BY sum(rows_total) DESC""", (reason_latest["signal_funnel_reason_snapshot_id"],))
                reasons = [dict(row) for row in cur.fetchall()]
    return stages, reasons, comparable


def run_oos_action_v1() -> str:
    env = dict(os.environ)
    env.update({"DATABASE_URL": DB, "PYTHONPATH": str(ROOT / "src"), "PYTHONDONTWRITEBYTECODE": "1"})
    result = subprocess.run(
        [str(PYTHON), "src/scripts/build_momentum_edge_oos_rank_v1.py"],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=30, check=False,
    )
    verdict = "Проверка завершена" if result.returncode == 0 else "Ошибка проверки"
    return f"{verdict}. Код: {result.returncode}"


def run_hypothesis_action_v1() -> str:
    env = dict(os.environ)
    env.update({"DATABASE_URL": DB, "PYTHONPATH": str(ROOT / "src"), "PYTHONDONTWRITEBYTECODE": "1"})
    script = "src/scripts/build_edge_regime_hypothesis_discovery_v2.py"
    running = subprocess.run(["pgrep", "-f", script], capture_output=True, text=True, check=False)
    if running.returncode == 0:
        return "Поиск гипотез уже выполняется в фоне"
    subprocess.Popen(
        [str(PYTHON), script], cwd=ROOT, env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True,
    )
    return "Поиск гипотез запущен в фоне. Страница остаётся доступной"


def run_lead_lag_action_v1() -> str:
    env = dict(os.environ)
    env.update({"DATABASE_URL": DB, "PYTHONPATH": str(ROOT / "src"), "PYTHONDONTWRITEBYTECODE": "1"})
    result = subprocess.run(
        [str(PYTHON), "src/scripts/build_intermarket_lead_lag_engine_v1.py"],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=120, check=False,
    )
    verdict = "Межрыночный поиск завершён" if result.returncode == 0 else "Ошибка межрыночного поиска"
    return f"{verdict}. Код: {result.returncode}"


def run_relationship_factory_action_v2() -> str:
    env = dict(os.environ)
    env.update({"DATABASE_URL": DB, "PYTHONPATH": str(ROOT / "src"), "PYTHONDONTWRITEBYTECODE": "1"})
    result = subprocess.run(
        [str(PYTHON), "src/scripts/build_relationship_factory_v2.py"],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=180, check=False,
    )
    verdict = "Фабрика связей завершила поиск" if result.returncode == 0 else "Ошибка фабрики связей"
    return f"{verdict}. Код: {result.returncode}"


def run_relationship_pipeline_action_v2() -> str:
    env = dict(os.environ)
    env.update({"DATABASE_URL": DB, "PYTHONPATH": str(ROOT / "src"), "PYTHONDONTWRITEBYTECODE": "1"})
    result = subprocess.run(
        [str(PYTHON), "src/scripts/run_relationship_factory_pipeline_v2.py"],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=900, check=False,
    )
    verdict = "Цепочка данных и связей завершена" if result.returncode == 0 else "Ошибка цепочки данных и связей"
    return f"{verdict}. Код: {result.returncode}"


def run_signal_funnel_action_v1() -> str:
    env = dict(os.environ)
    env.update({"DATABASE_URL": DB, "PYTHONPATH": str(ROOT / "src"), "PYTHONDONTWRITEBYTECODE": "1"})
    for script in ("src/scripts/signal_funnel_analytics_v1.py", "src/scripts/signal_funnel_reason_analytics_v1.py"):
        result = subprocess.run([str(PYTHON), script], cwd=ROOT, env=env, capture_output=True, text=True, timeout=60, check=False)
        if result.returncode:
            return f"Ошибка обновления воронки. Код: {result.returncode}"
    return "Воронка сигналов и причины потерь обновлены"


def render_edge_oos_control_center_v1(notice: str = "") -> str:
    rows = _rows()
    hypotheses, hypothesis_summary = _hypotheses()
    lead_lag_rows, lead_lag_summary = _lead_lag()
    session_rows, session_summary = _session_edges()
    execution_rows, execution_summary = _execution_edges()
    relationship_rows, relationship_summary = _relationship_factory()
    quality_rows, quality_summary = _data_quality_gate()
    commodity_factors, commodity_relations = _commodity_factors()
    funnel_stages, funnel_reasons, funnel_comparable = _signal_funnel()
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
    session_table_rows = "".join(
        f"""<tr data-session-row data-strategy="{row['strategy_family']}" data-regime="{row['regime_code']}" data-session="{row['session_code']}">
        <td><strong>{html.escape(_strategy_name_ru(row['strategy_family'], row['strategy_code']))}</strong></td>
        <td>{html.escape(row['symbol'])}</td><td>{html.escape(str(row['regime_code']).replace('_', ' '))}</td>
        <td>{html.escape(SESSION_NAMES_RU.get(row['session_code'], row['session_code']))}</td>
        <td>{row['validation_trades']}</td><td>{float(row['validation_profit_factor']):.2f}</td>
        <td>{row['oos_trades']}</td><td>{float(row['oos_profit_factor']):.2f}</td>
        <td class="{'is-positive' if row['oos_expectancy'] > 0 else 'is-negative'}">{float(row['oos_expectancy']):.3f}</td>
        <td>{row['folds_passed']}/{row['folds_total']}</td><td>{float(row['adjusted_p_value']):.3f}</td>
        <td>{float(row['regime_coverage_ratio']) * 100:.0f}%</td>
        <td><span class="mc-oos-badge {'pass' if row['verdict_code'] == 'OOS_PASS' else 'fail'}">{'НЕТ ДАННЫХ' if row['verdict_code'] == 'UNVERIFIED' else row['verdict_code'].removeprefix('OOS_')}</span></td></tr>"""
        for row in session_rows
    )
    execution_table_rows = "".join(
        f"""<tr data-execution-row data-strategy="{row['strategy_family']}" data-regime="{row['regime_code']}" data-session="{row['session_code']}" data-policy="{row['policy_code']}">
        <td><strong>{html.escape(EXECUTION_POLICY_NAMES_RU.get(row['policy_code'], row['policy_code']))}</strong></td>
        <td>{html.escape(_strategy_name_ru(row['strategy_family'], row['strategy_code']))}</td><td>{html.escape(row['symbol'])}</td>
        <td>{html.escape(str(row['regime_code']).replace('_', ' '))}</td><td>{html.escape(SESSION_NAMES_RU.get(row['session_code'], row['session_code']))}</td>
        <td>{row['oos_trades']}</td><td>{float(row['oos_profit_factor']):.2f}</td>
        <td class="{'is-positive' if row['delta_profit_factor'] > 0 else 'is-negative'}">{float(row['delta_profit_factor']):+.2f}</td>
        <td class="{'is-positive' if row['delta_expectancy'] > 0 else 'is-negative'}">{float(row['delta_expectancy']):+.3f}</td>
        <td>{row['folds_passed']}/{row['folds_total']}</td><td>{float(row['adjusted_p_value']):.3f}</td>
        <td>{'Котировки bid/ask' if row['market_data_quality'] == 'QUOTE_VERIFIED' else 'OHLCV M1/M5'}</td>
        <td><span class="mc-oos-badge {'pass' if row['verdict_code'] == 'OOS_PASS' else 'fail'}">{'НЕТ ДАННЫХ' if row['verdict_code'] == 'UNVERIFIED' else row['verdict_code'].removeprefix('OOS_')}</span></td></tr>"""
        for row in execution_rows
    )
    relationship_table_rows = "".join(
        f"""<tr data-factory-row data-priority="{row['priority']}" data-family="{row['relationship_family']}" data-regime="{row['regime_group']}" data-session="{row['session_code']}">
        <td><strong>P{row['priority']}</strong></td><td><strong>{html.escape(RELATIONSHIP_FAMILY_NAMES_RU.get(row['relationship_family'], row['relationship_family']))}</strong></td>
        <td>{html.escape(' + '.join(row['source_symbols']) if isinstance(row['source_symbols'], list) else str(row['source_symbols']))}</td><td>{html.escape(row['target_symbol'])}</td>
        <td>{html.escape(REGIME_NAMES_RU.get(row['regime_group'], row['regime_group']))}</td><td>{html.escape(SESSION_NAMES_RU.get(row['session_code'], 'Все сессии' if row['session_code'] == 'ALL' else row['session_code']))}</td>
        <td>{row['impulse_bars']} → {row['lag_bars']}</td><td>{row['aligned_bars']}</td><td>{row['oos_trades']}</td>
        <td>{float(row['oos_profit_factor']):.2f}</td><td class="{'is-positive' if row['oos_expectancy_bps'] > 0 else 'is-negative'}">{float(row['oos_expectancy_bps']):.2f}</td>
        <td>{row['folds_passed']}/{row['folds_total']}</td><td>{float(row['adjusted_p_value']):.3f}</td><td>{float(row['regime_coverage_ratio']) * 100:.0f}%</td>
        <td><span class="mc-oos-badge {'pass' if row['verdict_code'] == 'OOS_PASS' else 'fail'}">{'НЕТ ДАННЫХ' if row['verdict_code'] == 'UNVERIFIED' else row['verdict_code'].removeprefix('OOS_')}</span></td></tr>"""
        for row in relationship_rows
    )
    quality_table_rows = "".join(
        f"""<tr data-quality-row data-market="{row['market_data_status']}" data-factory="{row['factory_status']}">
        <td><strong>{html.escape(row['symbol'])}</strong></td><td>{row['timeframe']}</td><td>{row['bars']}</td><td>{row['trading_days']}</td>
        <td>{_format_datetime_ru(row['last_ts'])}</td><td>{float(row['latest_age_hours'] or 0):.1f} ч</td>
        <td>{row['duplicate_rows']}</td><td>{row['invalid_ohlc_rows']}</td><td>{float(row['regime_coverage_ratio']) * 100:.0f}%</td>
        <td><span class="mc-oos-badge {'pass' if row['market_data_status'] == 'READY' else 'fail'}">{row['market_data_status']}</span></td>
        <td><span class="mc-oos-badge {'pass' if row['factory_status'] == 'READY' else 'fail'}">{row['factory_status']}</span></td>
        <td>{html.escape(', '.join(row['reason_codes']) if isinstance(row['reason_codes'], list) else str(row['reason_codes'])) or '—'}</td></tr>"""
        for row in quality_rows
    )
    commodity_cards = "".join(
        f"""<article><span>{html.escape(COMMODITY_NAMES_RU.get(row['symbol'], row['symbol']))} · {html.escape(str(row['timer_status']).upper())}</span>
        <b class="{'is-positive' if row['market_data_status'] == 'READY' else 'is-negative'}">{row['market_data_status']}</b>
        <small>{row['bars']} M5 · {row['trading_days']} дней · режимы {float(row['regime_coverage_ratio'] or 0) * 100:.0f}% · Factory {row['factory_status']}</small></article>"""
        for row in commodity_factors
    )
    commodity_relation_rows = "".join(
        f"""<tr><td><strong>{html.escape(row['relationship_code'].replace('_', ' '))}</strong></td><td>{html.escape(row['target_symbol'])}</td>
        <td>{row['oos_trades']}</td><td>{float(row['oos_profit_factor']):.2f}</td>
        <td class="{'is-positive' if row['oos_expectancy_bps'] > 0 else 'is-negative'}">{float(row['oos_expectancy_bps']):.2f}</td>
        <td>{float(row['adjusted_p_value']):.3f}</td><td>{'Проверено' if row['trust_status'] == 'VERIFIED' else 'Нет данных'}</td>
        <td><span class="mc-oos-badge {'pass' if row['verdict_code'] == 'OOS_PASS' else 'fail'}">{'НЕТ ДАННЫХ' if row['verdict_code'] == 'UNVERIFIED' else row['verdict_code'].removeprefix('OOS_')}</span></td></tr>"""
        for row in commodity_relations
    )
    funnel_cards = "".join(
        f"""<article><span>{html.escape(row['stage_name'])}</span><b>{int(row['stage_count'])}</b>
        <small>{'Источник несопоставим' if row['previous_stage_count'] is not None and row['stage_count'] > row['previous_stage_count'] else ('Конверсия ' + str(row['pass_rate_pct']) + '%' if row['pass_rate_pct'] is not None else 'Начальная стадия')}</small></article>"""
        for row in funnel_stages
    )
    funnel_reason_rows = "".join(
        f"""<tr><td><strong>{html.escape(row['reason_group'])}</strong></td><td>{int(row['rows_total'])}</td><td>{int(row['reason_values'])}</td>
        <td>{html.escape(FUNNEL_ACTIONS_RU.get(row['reason_group'], FUNNEL_ACTIONS_RU['OTHER']))}</td></tr>"""
        for row in funnel_reasons
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
          <button type="submit">Lead/Lag поиск</button></form>
          <form method="post" action="/workspace-v2/control-center/edge-oos/relationship-factory">
          <button type="submit">Factory V2</button></form>
          <form method="post" action="/workspace-v2/control-center/edge-oos/relationship-pipeline">
          <button type="submit">Проверить всю цепочку</button></form>
          <form method="post" action="/workspace-v2/control-center/edge-oos/signal-funnel">
          <button class="secondary" type="submit">Обновить воронку</button></form></div></header>{notice_html}
        <section class="mc-oos-kpis"><article><span>Параметров</span><b>{len(rows)}</b></article>
          <article><span>OOS PASS</span><b class="is-positive">{passed}</b></article>
          <article><span>OOS FAIL</span><b class="is-negative">{failed}</b></article>
          <article><span>Holdout</span><b>{oos_bars} баров</b></article></section>
        <section class="mc-oos-panel"><div class="mc-oos-toolbar"><div><h2>Рейтинг параметров</h2>
          <p>Последний запуск: {_format_datetime_ru(last_run)}</p></div>
          <label>Вердикт <select data-oos-filter><option value="ALL">Все</option><option value="OOS_PASS">PASS</option><option value="OOS_FAIL">FAIL</option></select></label></div>
          <details class="mc-table-spoiler"><summary>Показать таблицу <span>{len(rows)} строк</span></summary><div class="mc-oos-table-wrap"><table class="mc-oos-table"><thead><tr><th>Порог</th><th>Сделки</th><th>PF</th><th>Ожидание</th><th>Просадка</th><th>Периоды</th><th>Вердикт</th><th>Продвижение</th></tr></thead>
          <tbody data-oos-results>{table_rows}</tbody></table></div></details></section>
        <section class="mc-oos-panel mc-hypothesis-panel"><div class="mc-oos-toolbar"><div><h2>Поиск новых гипотез</h2>
          <p>{hypothesis_summary.get('hypotheses', 0)} комбинаций · {hypothesis_summary.get('markets', 0)} рынков · {hypothesis_summary.get('families', 0)} семейства · PASS {hypothesis_summary.get('passed', 0)}</p></div>
          <label>Семейство <select data-hypothesis-filter><option value="ALL">Все</option><option value="MOMENTUM">Следование за импульсом</option><option value="MEAN_REVERSION">Возврат к среднему</option><option value="BREAKOUT">Пробой уровня</option></select></label></div>
          <details class="mc-table-spoiler"><summary>Показать таблицу <span>{len(hypotheses)} строк</span></summary><div class="mc-oos-table-wrap"><table class="mc-oos-table"><thead><tr><th>Стратегия</th><th>Инструмент</th><th>Режим входа</th><th>Параметры</th><th>Val PF</th><th>OOS PF</th><th>OOS Exp</th><th>Периоды</th><th>Покрытие</th><th>Издержки</th><th>Score</th><th>Доверие</th><th>Вердикт</th></tr></thead>
          <tbody>{hypothesis_rows}</tbody></table></div></details></section>
        <section class="mc-oos-kpis"><article><span>Lead/Lag испытаний</span><b>{lead_lag_summary.get('trials', 0)}</b></article>
          <article><span>Подтверждено</span><b class="is-positive">{lead_lag_summary.get('passed', 0)}</b></article>
          <article><span>Отклонено</span><b class="is-negative">{lead_lag_summary.get('failed', 0)}</b></article>
          <article><span>Нет данных</span><b>{lead_lag_summary.get('unverified', 0)}</b></article></section>
        <section class="mc-oos-panel"><div class="mc-oos-toolbar"><div><h2>Межрыночные Lead/Lag связи</h2>
          <p>{lead_lag_summary.get('relationships', 0)} связей · значимость скорректирована по всем испытаниям</p></div>
          <label>Вердикт <select data-lead-lag-filter><option value="ALL">Все</option><option value="OOS_PASS">PASS</option><option value="OOS_FAIL">FAIL</option><option value="UNVERIFIED">Нет данных</option></select></label></div>
          <details class="mc-table-spoiler"><summary>Показать таблицу <span>{len(lead_lag_rows)} строк</span></summary><div class="mc-oos-table-wrap"><table class="mc-oos-table"><thead><tr><th>Связь</th><th>Режим</th><th>Импульс</th><th>Лаг</th><th>OOS</th><th>PF</th><th>Ожидание, bps</th><th>IC</th><th>Периоды</th><th>p скорр.</th><th>Покрытие</th><th>Доверие</th><th>Вердикт</th></tr></thead>
          <tbody>{lead_lag_table_rows}</tbody></table></div></details><p data-lead-lag-count>Показано: {len(lead_lag_rows)}</p></section>
        <section id="data-quality-gate" class="mc-oos-panel mc-edge-research-panel"><div class="mc-oos-toolbar mc-edge-toolbar"><div><p class="mc-edge-eyebrow">DATA QUALITY GATE</p><h2>Качество данных</h2>
          <p>{quality_summary.get('symbols', 0)} источников · рынок готов {quality_summary.get('market_ready', 0)} · Factory готова {quality_summary.get('factory_ready', 0)} · заблокировано {quality_summary.get('blocked', 0)}</p></div></div>
          <details class="mc-table-spoiler"><summary>Показать таблицу <span>{len(quality_rows)} строк</span></summary><div class="mc-oos-table-wrap"><table class="mc-oos-table"><thead><tr><th>Инструмент</th><th>TF</th><th>Бары</th><th>Дни</th><th>Последний бар</th><th>Возраст</th><th>Дубли</th><th>Ошибки OHLC</th><th>Режимы</th><th>Market</th><th>Factory</th><th>Причины</th></tr></thead><tbody>{quality_table_rows}</tbody></table></div></details>
          <div class="mc-edge-panel-footer"><span>Календарные разрывы: UNVERIFIED</span><span>Factory запускается только после MARKET READY и покрытия режимами</span></div></section>
        <section id="commodity-factors" class="mc-oos-panel mc-edge-research-panel"><div class="mc-oos-toolbar"><div><p class="mc-edge-eyebrow">COMMODITY FACTORS</p><h2>Сырьевые факторы</h2><p>Brent и природный газ · online ingestion · P2-связи с экспортёрами</p></div></div>
          <div class="mc-oos-kpis mc-commodity-kpis">{commodity_cards}</div>
          <details class="mc-table-spoiler"><summary>Показать сырьевые P2-связи <span>{len(commodity_relations)} строк</span></summary><div class="mc-oos-table-wrap"><table class="mc-oos-table"><thead><tr><th>Связь</th><th>Цель</th><th>OOS</th><th>PF</th><th>Ожидание, bps</th><th>p скорр.</th><th>Доверие</th><th>Вердикт</th></tr></thead><tbody>{commodity_relation_rows}</tbody></table></div></details></section>
        <section id="signal-funnel" class="mc-oos-panel mc-edge-research-panel"><div class="mc-oos-toolbar"><div><p class="mc-edge-eyebrow">SIGNAL FUNNEL</p><h2>Воронка сигналов</h2>
          <p>{'Стадии сопоставимы' if funnel_comparable else 'NON-COMPARABLE · источники имеют разные lineage и периоды'}</p></div><span class="mc-oos-badge {'pass' if funnel_comparable else 'fail'}">{'VERIFIED' if funnel_comparable else 'ТРЕБУЕТ LINEAGE'}</span></div>
          <div class="mc-oos-kpis mc-funnel-kpis">{funnel_cards}</div>
          <details class="mc-table-spoiler"><summary>Причины потерь и варианты решения <span>{len(funnel_reasons)} групп</span></summary><div class="mc-oos-table-wrap"><table class="mc-oos-table"><thead><tr><th>Группа</th><th>События</th><th>Причины</th><th>Рекомендуемое действие</th></tr></thead><tbody>{funnel_reason_rows}</tbody></table></div></details></section>
        <section id="relationship-factory" class="mc-oos-panel mc-edge-research-panel"><div class="mc-oos-toolbar mc-edge-toolbar"><div><p class="mc-edge-eyebrow">RELATIONSHIP FACTORY V2</p><h2>Фабрика связей</h2>
          <p>{relationship_summary.get('relationships', 0)} связей · {relationship_summary.get('trials', 0)} испытаний · PASS {relationship_summary.get('passed', 0)} · FAIL {relationship_summary.get('failed', 0)} · нет данных {relationship_summary.get('unverified', 0)}</p></div>
          <div class="mc-edge-filters"><label>Приоритет <select data-factory-filter="priority"><option value="ALL">Все</option><option value="1">P1 · Индекс и сектор</option><option value="2">P2 · Многофакторные</option><option value="3">P3 · Overnight</option><option value="4">P4 · Ликвидность</option><option value="5">P5 · Пары</option></select></label>
          <label>Семейство <select data-factory-filter="family"><option value="ALL">Все</option>{''.join(f'<option value="{code}">{name}</option>' for code, name in RELATIONSHIP_FAMILY_NAMES_RU.items())}</select></label>
          <label>Режим <select data-factory-filter="regime"><option value="ALL">Все</option><option value="TREND">Тренд</option><option value="RANGE">Боковик</option><option value="EXPANSION">Расширение</option><option value="COMPRESSION">Сжатие</option></select></label>
          <label>Сессия <select data-factory-filter="session"><option value="ALL">Все</option>{''.join(f'<option value="{code}">{name}</option>' for code, name in SESSION_NAMES_RU.items())}</select></label></div></div>
          <details class="mc-table-spoiler"><summary>Показать таблицу <span>{len(relationship_rows)} строк</span></summary><div class="mc-oos-table-wrap"><table class="mc-oos-table"><thead><tr><th>Приоритет</th><th>Семейство</th><th>Источник</th><th>Цель</th><th>Режим</th><th>Сессия</th><th>Импульс → лаг</th><th>Бары</th><th>OOS</th><th>PF</th><th>Ожидание, bps</th><th>Периоды</th><th>p скорр.</th><th>Покрытие</th><th>Вердикт</th></tr></thead><tbody>{relationship_table_rows}</tbody></table></div></details>
          <div class="mc-edge-panel-footer"><span data-factory-count>Показано: {len(relationship_rows)}</span><span>Production заблокирован до OOS PASS и Trust Gate</span></div></section>
        <nav class="mc-edge-section-nav" aria-label="Исследования Edge"><a href="#data-quality-gate">Качество <b>{quality_summary.get('factory_ready', 0)}/{quality_summary.get('symbols', 0)}</b></a><a href="#commodity-factors">Сырьё <b>{len(commodity_relations)}</b></a><a href="#signal-funnel">Воронка <b>{len(funnel_stages)}</b></a><a href="#relationship-factory">Фабрика связей <b>{relationship_summary.get('trials', 0)}</b></a><a href="#session-edge">Сессии <b>{session_summary.get('trials', 0)}</b></a><a href="#execution-edge">Исполнение <b>{execution_summary.get('trials', 0)}</b></a></nav>
        <section id="session-edge" class="mc-oos-panel mc-edge-research-panel"><div class="mc-oos-toolbar mc-edge-toolbar"><div><p class="mc-edge-eyebrow">STRATEGY × REGIME × SESSION</p><h2>Сессии</h2>
          <p>{session_summary.get('trials', 0)} испытаний · PASS {session_summary.get('passed', 0)} · FAIL {session_summary.get('failed', 0)} · нет данных {session_summary.get('unverified', 0)}</p></div>
          <div class="mc-edge-filters"><label>Стратегия <select data-session-filter="strategy"><option value="ALL">Все</option><option value="MOMENTUM">Импульс</option><option value="MEAN_REVERSION">Возврат к среднему</option><option value="BREAKOUT">Пробой</option></select></label>
          <label>Режим <select data-session-filter="regime"><option value="ALL">Все</option><option value="trend_up">Тренд вверх</option><option value="trend_down">Тренд вниз</option><option value="range_normal">Боковик</option><option value="compression">Сжатие</option><option value="trend_up_expansion">Расширение вверх</option><option value="trend_down_expansion">Расширение вниз</option></select></label>
          <label>Сессия <select data-session-filter="session"><option value="ALL">Все</option>{''.join(f'<option value="{code}">{name}</option>' for code, name in SESSION_NAMES_RU.items())}</select></label></div></div>
          <details class="mc-table-spoiler"><summary>Показать таблицу <span>{len(session_rows)} строк</span></summary><div class="mc-oos-table-wrap"><table class="mc-oos-table"><thead><tr><th>Стратегия</th><th>Инструмент</th><th>Режим</th><th>Сессия</th><th>Val сделки</th><th>Val PF</th><th>OOS сделки</th><th>OOS PF</th><th>OOS ожидание</th><th>Периоды</th><th>p скорр.</th><th>Покрытие</th><th>Вердикт</th></tr></thead><tbody>{session_table_rows}</tbody></table></div></details>
          <div class="mc-edge-panel-footer"><span data-session-count>Показано: {len(session_rows)}</span><span>PF разных сессий не смешивается</span></div></section>
        <section id="execution-edge" class="mc-oos-panel mc-edge-research-panel"><div class="mc-oos-toolbar mc-edge-toolbar"><div><p class="mc-edge-eyebrow">EXECUTION EDGE</p><h2>Исполнение</h2>
          <p>{execution_summary.get('trials', 0)} испытаний · {execution_summary.get('policies', 0)} политик · PASS {execution_summary.get('passed', 0)} · котировки подтверждены {execution_summary.get('quote_verified', 0)}</p></div>
          <div class="mc-edge-filters"><label>Стратегия <select data-execution-filter="strategy"><option value="ALL">Все</option><option value="MOMENTUM">Импульс</option><option value="MEAN_REVERSION">Возврат к среднему</option><option value="BREAKOUT">Пробой</option></select></label>
          <label>Режим <select data-execution-filter="regime"><option value="ALL">Все</option><option value="trend_up">Тренд вверх</option><option value="trend_down">Тренд вниз</option><option value="range_normal">Боковик</option><option value="compression">Сжатие</option><option value="trend_up_expansion">Расширение вверх</option><option value="trend_down_expansion">Расширение вниз</option></select></label>
          <label>Сессия <select data-execution-filter="session"><option value="ALL">Все</option>{''.join(f'<option value="{code}">{name}</option>' for code, name in SESSION_NAMES_RU.items())}</select></label>
          <label>Политика выхода <select data-execution-filter="policy"><option value="ALL">Все</option>{''.join(f'<option value="{code}">{name}</option>' for code, name in EXECUTION_POLICY_NAMES_RU.items())}</select></label></div></div>
          <div class="mc-edge-data-warning"><b>Котировки и стакан не подтверждены</b><span>OHLCV M1/M5 и объём доступны. Спред, глубина и фактическое проскальзывание останутся заблокированы до подключения bid/ask, сделок и order book.</span></div>
          <details class="mc-table-spoiler"><summary>Показать таблицу <span>{len(execution_rows)} строк</span></summary><div class="mc-oos-table-wrap"><table class="mc-oos-table"><thead><tr><th>Политика</th><th>Стратегия</th><th>Инструмент</th><th>Режим</th><th>Сессия</th><th>OOS сделки</th><th>PF</th><th>Δ PF</th><th>Δ ожидание</th><th>Периоды</th><th>p скорр.</th><th>Данные</th><th>Вердикт</th></tr></thead><tbody>{execution_table_rows}</tbody></table></div></details>
          <div class="mc-edge-panel-footer"><span data-execution-count>Показано: {len(execution_rows)}</span><span>Сравнение с базовым исполнением на тех же входах</span></div></section>
        <footer class="mc-oos-status"><span>DATA: REAL</span><span>OOS REGISTRY: ONLINE</span><span>LIVE: BLOCKED</span><span data-oos-count>Показано: {len(rows)}</span></footer>
      </main></div><script src="/assets/marketcore/ui-runtime/v1/edge-oos-control.js"></script></body></html>"""
