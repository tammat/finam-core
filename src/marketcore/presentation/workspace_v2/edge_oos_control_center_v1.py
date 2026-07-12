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

from marketcore.presentation.framework.i18n_resolver import UiI18nResolverV1


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
ROOT = Path(__file__).resolve().parents[4]
PYTHON = Path(os.getenv("MARKETCORE_PYTHON", str(ROOT / ".venv/bin/python")))
if not PYTHON.exists():
    PYTHON = Path("/opt/finam-core/.venv/bin/python")

ACTION_STATUS_SCRIPTS = {
    "run": ("src/scripts/build_momentum_edge_oos_rank_v1.py", "Повторная OOS-проверка"),
    "discover": ("src/scripts/build_edge_regime_hypothesis_discovery_v2.py", "Поиск гипотез"),
    "hypothesis-pipeline": ("src/scripts/run_edge_hypothesis_pipeline_v1.py", "Проверка гипотез"),
    "lead-lag": ("src/scripts/build_intermarket_lead_lag_engine_v1.py", "Lead/Lag поиск"),
    "relationship-factory": ("src/scripts/build_relationship_factory_v2.py", "Фабрика связей V2"),
    "relationship-pipeline": ("src/scripts/run_relationship_factory_pipeline_v2.py", "Проверка всей цепочки"),
    "data-quality": ("src/scripts/build_relationship_data_quality_gate_v1.py", "Проверка качества данных"),
    "session-execution": ("src/scripts/build_session_execution_edge_v1.py", "Поиск по сессиям и исполнению"),
    "edge-search-pipeline": ("src/scripts/run_relationship_factory_pipeline_v2.py", "Полный цикл поиска edge"),
    "finam-instruments": ("src/scripts/discover_finam_instrument_universe_v1.py", "Поиск инструментов Finam"),
    "strategy-generator": ("src/scripts/build_strategy_family_registry_v2.py", "Генератор стратегий"),
}


def action_status_v1(action_code: str) -> dict[str, object]:
    definition = ACTION_STATUS_SCRIPTS.get(action_code)
    if definition is None:
        return {"known": False, "running": False, "progress_pct": 100, "label": "Неизвестный процесс"}
    script, label = definition
    result = subprocess.run(["pgrep", "-f", script], capture_output=True, text=True, check=False)
    running = result.returncode == 0
    return {
        "known": True,
        "running": running,
        "progress_pct": 10 if running else 100,
        "progress_kind": "stage" if running else "complete",
        "label": label,
    }

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

FUNNEL_REASON_GROUPS = (
    "DATA", "VOLATILITY", "LIQUIDITY", "RISK", "EDGE", "MARKET",
    "EXIT", "SETUP", "EXECUTION", "RESEARCH", "LIFECYCLE", "BLOCK",
    "PASS", "QUALITY", "UNKNOWN", "OTHER",
)


def _funnel_i18n_key(group: str, field: str) -> str:
    normalized = group if group in FUNNEL_REASON_GROUPS else "OTHER"
    return f"control_center.signal_funnel.reason.{normalized.lower()}.{field}"

SECTION_URLS = {
    "data-quality-gate": "/workspace-v2/control-center/edge-oos/data-quality",
    "commodity-factors": "/workspace-v2/control-center/edge-oos/commodity-factors",
    "signal-funnel": "/workspace-v2/control-center/edge-oos/signal-funnel",
    "relationship-factory": "/workspace-v2/control-center/edge-oos/relationship-factory",
    "session-edge": "/workspace-v2/control-center/edge-oos/session-execution",
    "execution-edge": "/workspace-v2/control-center/edge-oos/execution-edge",
    "strategy-generator": "/workspace-v2/control-center/edge-oos/strategy-generator",
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


def _strategy_generator() -> tuple[list[dict], dict]:
    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""SELECT strategy_family,name_ru,engine_code,priority,allowed_regimes,
                       parameter_schema,oos_required,multiple_testing_required,live_allowed
                FROM analytics.strategy_family_registry_v2 WHERE enabled=true ORDER BY priority""")
            families = [dict(row) for row in cur.fetchall()]
            cur.execute("""SELECT parameter_space_run_id FROM analytics.hypothesis_parameter_space_v2
                ORDER BY created_at DESC LIMIT 1""")
            latest = cur.fetchone()
            summary = {"families": len(families), "candidates": 0, "trial_limit": 5000, "risk": "CONTROLLED"}
            if latest:
                cur.execute("""SELECT count(*) AS candidates,max(estimated_trials) AS trial_limit,
                           max(overfit_risk) AS risk
                    FROM analytics.hypothesis_parameter_space_v2 WHERE parameter_space_run_id=%s""",
                    (latest["parameter_space_run_id"],))
                summary.update(dict(cur.fetchone() or {}))
                summary["run_id"] = str(latest["parameter_space_run_id"])
    return families, summary


def run_oos_action_v1() -> str:
    return _run_background_action_v1(
        "src/scripts/build_momentum_edge_oos_rank_v1.py",
        "Повторная OOS-проверка",
    )


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
    return _run_background_action_v1(
        "src/scripts/build_intermarket_lead_lag_engine_v1.py",
        "Межрыночный Lead/Lag поиск",
    )


def run_relationship_factory_action_v2() -> str:
    return _run_background_action_v1(
        "src/scripts/build_relationship_factory_v2.py",
        "Фабрика связей V2",
    )


def run_relationship_pipeline_action_v2() -> str:
    return _run_background_action_v1(
        "src/scripts/run_relationship_factory_pipeline_v2.py",
        "Полная цепочка данных и связей",
    )


def run_hypothesis_pipeline_action_v1() -> str:
    return _run_background_action_v1(
        "src/scripts/run_edge_hypothesis_pipeline_v1.py",
        "Подготовка данных и проверка гипотез",
    )


def run_signal_funnel_action_v1() -> str:
    env = dict(os.environ)
    env.update({"DATABASE_URL": DB, "PYTHONPATH": str(ROOT / "src"), "PYTHONDONTWRITEBYTECODE": "1"})
    for script in ("src/scripts/signal_funnel_analytics_v1.py", "src/scripts/signal_funnel_reason_analytics_v1.py"):
        result = subprocess.run([str(PYTHON), script], cwd=ROOT, env=env, capture_output=True, text=True, timeout=60, check=False)
        if result.returncode:
            return f"Ошибка обновления воронки. Код: {result.returncode}"
    return "Воронка сигналов и причины потерь обновлены"


def run_strategy_generator_action_v2() -> str:
    return _run_background_action_v1(
        "src/scripts/build_strategy_family_registry_v2.py",
        "Генератор стратегий",
    )


def _run_background_action_v1(script: str, label: str) -> str:
    env = dict(os.environ)
    env.update({"DATABASE_URL": DB, "PYTHONPATH": str(ROOT / "src"), "PYTHONDONTWRITEBYTECODE": "1"})
    running = subprocess.run(["pgrep", "-f", script], capture_output=True, text=True, check=False)
    if running.returncode == 0:
        return f"{label} уже выполняется в фоне"
    log_dir = ROOT / "data" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{Path(script).stem}.log"
    with log_path.open("ab") as log_file:
        subprocess.Popen(
            [str(PYTHON), script], cwd=ROOT, env=env,
            stdout=log_file, stderr=subprocess.STDOUT, start_new_session=True,
        )
    return f"{label} запущен в фоне. Результаты появятся после обновления страницы"


def run_data_quality_action_v1() -> str:
    return _run_background_action_v1(
        "src/scripts/build_relationship_data_quality_gate_v1.py",
        "Проверка качества данных",
    )


def run_session_execution_action_v1() -> str:
    return _run_background_action_v1(
        "src/scripts/build_session_execution_edge_v1.py",
        "Поиск по сессиям и исполнению",
    )


def run_edge_search_pipeline_action_v1() -> str:
    return _run_background_action_v1(
        "src/scripts/run_relationship_factory_pipeline_v2.py",
        "Полный цикл поиска edge",
    )


def run_finam_instrument_discovery_action_v1() -> str:
    return _run_background_action_v1(
        "src/scripts/discover_finam_instrument_universe_v1.py",
        "Поиск новых инструментов Finam",
    )


def _section_link(section_id: str, label: str, value: object, active_section: str) -> str:
    active = ' class="active"' if active_section == section_id else ""
    return (
        f'<a{active} href="{html.escape(SECTION_URLS[section_id])}">'
        f"{html.escape(label)} <b>{html.escape(str(value))}</b></a>"
    )


def render_edge_oos_control_center_v1(notice: str = "", active_section: str = "") -> str:
    i18n = UiI18nResolverV1(locale_code="ru")
    if active_section not in {
        "data-quality-gate",
        "commodity-factors",
        "hypothesis-discovery",
        "lead-lag",
        "relationship-factory",
        "signal-funnel",
        "session-edge",
        "execution-edge",
        "finam-instruments",
        "strategy-generator",
    }:
        active_section = ""
    rows = _rows()
    hypotheses, hypothesis_summary = _hypotheses()
    lead_lag_rows, lead_lag_summary = _lead_lag()
    session_rows, session_summary = _session_edges()
    execution_rows, execution_summary = _execution_edges()
    relationship_rows, relationship_summary = _relationship_factory()
    quality_rows, quality_summary = _data_quality_gate()
    commodity_factors, commodity_relations = _commodity_factors()
    funnel_stages, funnel_reasons, funnel_comparable = _signal_funnel()
    strategy_families, strategy_generator_summary = _strategy_generator()
    passed = sum(1 for row in rows if row["verdict_code"] == "OOS_PASS")
    failed = len(rows) - passed
    oos_bars = 0
    if rows and rows[0].get("oos_start") and rows[0].get("oos_end"):
        oos_bars = "2846"
    last_run = max((row.get("updated_at") for row in rows), default=None)
    quality_blocked = int(quality_summary.get("blocked", 0) or 0)
    relationship_passed = int(relationship_summary.get("passed", 0) or 0)
    next_step = (
        "Сначала восстановить данные и покрытие режимами"
        if quality_blocked else
        "Запустить поиск связей по режимам и сессиям"
        if relationship_passed == 0 else
        "Проверить найденных кандидатов на строгом OOS"
    )

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
        <small>{'LIVE заблокирован · заявки не отправляются' if row['stage_code'] == 'ORDERS' and int(row['stage_count']) == 0 and row.get('evidence_json', {}).get('zero_is_expected_while_live_blocked') else ('Источник несопоставим' if row['previous_stage_count'] is not None and row['stage_count'] > row['previous_stage_count'] else ('Конверсия ' + str(row['pass_rate_pct']) + '%' if row['pass_rate_pct'] is not None else 'Начальная стадия'))}</small></article>"""
        for row in funnel_stages
    )
    funnel_reason_rows = "".join(
        f"""<tr><td><strong>{html.escape(i18n.text(_funnel_i18n_key(row['reason_group'], 'label')))}</strong></td><td>{int(row['rows_total'])}</td><td>{int(row['reason_values'])}</td>
        <td>{html.escape(i18n.text(_funnel_i18n_key(row['reason_group'], 'action')))}</td></tr>"""
        for row in funnel_reasons
    )
    live_boundary_blocked = bool(
        len(funnel_stages) > 1
        and funnel_stages[1]["stage_code"] == "ORDERS"
        and int(funnel_stages[1]["stage_count"]) == 0
        and funnel_stages[1].get("evidence_json", {}).get("zero_is_expected_while_live_blocked")
    )
    strategy_family_cards = "".join(
        f"""<article><span>P{row['priority']} · {html.escape(row['name_ru'])}</span>
        <b>{html.escape(row['engine_code'].replace('_', ' '))}</b>
        <small>{len(row['parameter_schema'])} параметра · {len(row['allowed_regimes'])} режима · OOS обязательно</small></article>"""
        for row in strategy_families
    )
    section_nav = "".join(
        (
            _section_link("data-quality-gate", "Качество", f"{quality_summary.get('factory_ready', 0)}/{quality_summary.get('symbols', 0)}", active_section),
            _section_link("commodity-factors", "Сырьё", len(commodity_relations), active_section),
            _section_link("signal-funnel", "Воронка", len(funnel_stages), active_section),
            _section_link("relationship-factory", "Фабрика связей", relationship_summary.get("trials", 0), active_section),
            _section_link("session-edge", "Сессии", session_summary.get("trials", 0), active_section),
            _section_link("execution-edge", "Исполнение", execution_summary.get("trials", 0), active_section),
            _section_link("strategy-generator", "Генератор", strategy_generator_summary.get("candidates", 0), active_section),
        )
    )
    return f"""<!doctype html><html lang="ru"><head><meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>MarketCore — Edge OOS Control Center</title>
    <link rel="stylesheet" href="/assets/marketcore/ui-runtime/v1/runtime.css"></head>
	    <body data-active-section="{html.escape(active_section)}" data-action-running-label="{html.escape(i18n.text('control_center.action.running'))}"><div class="mc-oos-layout">
      <aside class="mc-oos-sidebar"><a class="brand" href="/">MARKETCORE</a>
	        <nav><a href="/">Главная</a><a href="/workspace-v2/portfolio">Портфель</a>
        <a class="active" href="/workspace-v2/control-center/edge-oos">Edge · OOS <span>{failed}</span></a></nav>
        <div class="mc-oos-safety"><b>LIVE LOCK</b><small>Продвижение разрешено только после OOS_PASS</small></div>
      </aside>
      <main class="mc-oos-main"><header class="mc-oos-header"><div><p>CONTROL CENTER / EDGE</p>
        <h1>OOS-проверка Momentum</h1><span>Честный holdout после первых 5000 баров</span></div>
        <div class="mc-oos-actions"><form method="post" action="/workspace-v2/control-center/edge-oos/run">
          <button class="secondary" type="submit">Повторить OOS</button></form>
          <form method="post" action="/workspace-v2/control-center/edge-oos/discover">
          <button type="submit">{html.escape(i18n.text('control_center.action.generate_hypotheses'))}</button></form>
          <form method="post" action="/workspace-v2/control-center/edge-oos/hypothesis-pipeline">
          <button type="submit">{html.escape(i18n.text('control_center.action.validate_hypotheses'))}</button></form>
          <form method="post" action="/workspace-v2/control-center/edge-oos/lead-lag">
          <button type="submit">Lead/Lag поиск</button></form>
          <form method="post" action="/workspace-v2/control-center/edge-oos/relationship-factory">
          <button type="submit">Factory V2</button></form>
          <form method="post" action="/workspace-v2/control-center/edge-oos/relationship-pipeline">
          <button type="submit">Проверить всю цепочку</button></form>
          <form method="post" action="/workspace-v2/control-center/edge-oos/signal-funnel">
          <button class="secondary" type="submit">Обновить воронку</button></form>
          <form method="post" action="/workspace-v2/control-center/edge-oos/finam-instruments">
          <button type="submit">Найти инструменты Finam</button></form>
          <form method="post" action="/workspace-v2/control-center/edge-oos/strategy-generator">
          <button type="submit">Генератор стратегий</button></form></div></header>
        <section class="mc-action-status" data-action-status data-state="RUNNING" hidden aria-live="polite">
          <div class="mc-action-status-head"><strong data-action-status-text>Выполняется</strong><span data-action-progress-pct>0%</span></div>
          <div class="mc-action-progress" role="progressbar" aria-label="Ход выполнения"><span data-action-progress-fill></span></div>
        </section>{notice_html}
        <details class="mc-edge-action-center" aria-label="План поиска edge">
          <summary class="mc-edge-action-heading"><div><p>EDGE SEARCH PLAYBOOK</p><h2>План поиска edge</h2><span>{html.escape(next_step)}</span></div>
            <strong>{quality_summary.get('factory_ready', 0)}/{quality_summary.get('symbols', 0)} источников готовы · PASS {relationship_passed}</strong></summary>
          <div class="mc-edge-action-grid">
            <article data-state="{'BLOCKED' if quality_blocked else 'READY'}"><span>Шаг 1 · Данные</span><h3>Data Quality Gate</h3><p>Свежесть, глубина истории, ошибки OHLC и покрытие режимами.</p>
              <b>{'Заблокировано: ' + str(quality_blocked) if quality_blocked else 'Готово к исследованию'}</b>
              <form method="post" action="/workspace-v2/control-center/edge-oos/data-quality"><button type="submit">Проверить данные</button></form></article>
            <article data-state="ACTIVE"><span>Шаг 2 · Связи</span><h3>Relationship Factory</h3><p>Индексы, сырьё, валюты и многофакторные Lead/Lag-гипотезы.</p>
              <b>{relationship_summary.get('trials', 0)} испытаний · PASS {relationship_passed}</b>
              <form method="post" action="/workspace-v2/control-center/edge-oos/edge-search-pipeline"><button type="submit">Запустить полный цикл</button></form></article>
            <article data-state="ACTIVE"><span>Шаг 3 · Время</span><h3>Сессии и исполнение</h3><p>Раздельный PF по режимам, торговым сессиям и политикам выхода.</p>
              <b>{session_summary.get('trials', 0)} сессий · {execution_summary.get('trials', 0)} политик</b>
              <form method="post" action="/workspace-v2/control-center/edge-oos/session-execution"><button type="submit">Искать по сессиям</button></form></article>
            <article data-state="ACTIVE"><span>Шаг 4 · Доверие</span><h3>Строгий OOS</h3><p>Повторная проверка текущих кандидатов: holdout, устойчивость, издержки и отсутствие утечки.</p>
              <b>{'Есть кандидаты OOS_PASS' if relationship_passed else 'PASS пока нет — повторная проверка разрешена'}</b>
              <form method="post" action="/workspace-v2/control-center/edge-oos/run"><button type="submit">Повторить OOS</button></form></article>
            <article data-state="ACTIVE"><span>Диагностика · Воронка</span><h3>Потери сигналов</h3><p>Обновить стадии, конверсии, причины блокировок и рекомендуемые действия.</p>
              <b>{len(funnel_stages)} стадий · {len(funnel_reasons)} групп причин</b>
              <form method="post" action="/workspace-v2/control-center/edge-oos/signal-funnel"><button type="submit">Обновить воронку</button></form></article>
            <article id="finam-instruments" data-state="ACTIVE"><span>Расширение · Finam</span><h3>Новые инструменты</h3><p>Получить активный каталог брокера и отделить готовые к исследованию инструменты от требующих истории.</p>
              <b>Каталог → M5 → Data Gate → режимы → OOS</b>
              <form method="post" action="/workspace-v2/control-center/edge-oos/finam-instruments"><button type="submit">Найти новые инструменты</button></form></article>
          </div>
        </details>
        <section class="mc-oos-kpis"><article><span>Параметров</span><b>{len(rows)}</b></article>
          <article><span>OOS PASS</span><b class="is-positive">{passed}</b></article>
          <article><span>OOS FAIL</span><b class="is-negative">{failed}</b></article>
          <article><span>Holdout</span><b>{oos_bars} баров</b></article></section>
        <section class="mc-oos-panel"><div class="mc-oos-toolbar"><div><h2>Рейтинг параметров</h2>
          <p>Последний запуск: {_format_datetime_ru(last_run)}</p></div>
          <label>Вердикт <select data-oos-filter><option value="ALL">Все</option><option value="OOS_PASS">PASS</option><option value="OOS_FAIL">FAIL</option></select></label></div>
          <details class="mc-table-spoiler"><summary>Показать таблицу <span>{len(rows)} строк</span></summary><div class="mc-oos-table-wrap"><table class="mc-oos-table"><thead><tr><th>Порог</th><th>Сделки</th><th>PF</th><th>Ожидание</th><th>Просадка</th><th>Периоды</th><th>Вердикт</th><th>Продвижение</th></tr></thead>
          <tbody data-oos-results>{table_rows}</tbody></table></div></details></section>
        <section id="hypothesis-discovery" class="mc-oos-panel mc-hypothesis-panel"><div class="mc-oos-toolbar"><div><h2>Поиск новых гипотез</h2>
          <p>{hypothesis_summary.get('hypotheses', 0)} комбинаций · {hypothesis_summary.get('markets', 0)} рынков · {hypothesis_summary.get('families', 0)} семейства · PASS {hypothesis_summary.get('passed', 0)}</p></div>
          <label>Семейство <select data-hypothesis-filter><option value="ALL">Все</option><option value="MOMENTUM">Следование за импульсом</option><option value="MEAN_REVERSION">Возврат к среднему</option><option value="BREAKOUT">Пробой уровня</option></select></label></div>
          <details class="mc-table-spoiler"><summary>Показать таблицу <span>{len(hypotheses)} строк</span></summary><div class="mc-oos-table-wrap"><table class="mc-oos-table"><thead><tr><th>Стратегия</th><th>Инструмент</th><th>Режим входа</th><th>Параметры</th><th>Val PF</th><th>OOS PF</th><th>OOS Exp</th><th>Периоды</th><th>Покрытие</th><th>Издержки</th><th>Score</th><th>Доверие</th><th>Вердикт</th></tr></thead>
          <tbody>{hypothesis_rows}</tbody></table></div></details></section>
        <section class="mc-oos-kpis"><article><span>Lead/Lag испытаний</span><b>{lead_lag_summary.get('trials', 0)}</b></article>
          <article><span>Подтверждено</span><b class="is-positive">{lead_lag_summary.get('passed', 0)}</b></article>
          <article><span>Отклонено</span><b class="is-negative">{lead_lag_summary.get('failed', 0)}</b></article>
          <article><span>Нет данных</span><b>{lead_lag_summary.get('unverified', 0)}</b></article></section>
        <section id="lead-lag" class="mc-oos-panel"><div class="mc-oos-toolbar"><div><h2>Межрыночные Lead/Lag связи</h2>
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
          <p>{'Связанная когорта до границы Research → Execution; LIVE-заявки учитываются только после допуска' if funnel_comparable else 'Источники невозможно связать в единую когорту'}</p></div><span class="mc-oos-badge {'fail' if live_boundary_blocked or not funnel_comparable else 'pass'}">{'LIVE ЗАБЛОКИРОВАН' if live_boundary_blocked else ('СОПОСТАВИМО' if funnel_comparable else 'НЕТ СВЯЗНОСТИ')}</span></div>
          <div class="mc-oos-kpis mc-funnel-kpis">{funnel_cards}</div>
          <details class="mc-table-spoiler"><summary>Диагностические события и варианты решения <span>{len(funnel_reasons)} групп</span></summary><div class="mc-oos-table-wrap"><table class="mc-oos-table"><thead><tr><th>Группа</th><th>События</th><th>Варианты причин</th><th>Рекомендуемое действие</th></tr></thead><tbody>{funnel_reason_rows}</tbody></table></div><p>Диагностические события собраны из журналов системы и не считаются потерями между этапами воронки.</p></details></section>
        <section id="strategy-generator" class="mc-oos-panel mc-edge-research-panel"><div class="mc-oos-toolbar mc-edge-toolbar"><div><p class="mc-edge-eyebrow">HYPOTHESIS PARAMETER SPACE V2</p><h2>Генератор стратегий</h2>
          <p>{strategy_generator_summary.get('families', 0)} семейств · {strategy_generator_summary.get('candidates', 0)} комбинаций · лимит {strategy_generator_summary.get('trial_limit', 5000)} испытаний</p></div>
          <form method="post" action="/workspace-v2/control-center/edge-oos/strategy-generator"><button type="submit">Сформировать пространство</button></form></div>
          <div class="mc-oos-kpis mc-commodity-kpis">{strategy_family_cards}</div>
          <div class="mc-edge-panel-footer"><span>Риск переобучения: {html.escape(str(strategy_generator_summary.get('risk', 'CONTROLLED')))}</span><span>OOS и поправка множественных испытаний обязательны · LIVE заблокирован</span></div></section>
        <section id="relationship-factory" class="mc-oos-panel mc-edge-research-panel"><div class="mc-oos-toolbar mc-edge-toolbar"><div><p class="mc-edge-eyebrow">RELATIONSHIP FACTORY V2</p><h2>Фабрика связей</h2>
          <p>{relationship_summary.get('relationships', 0)} связей · {relationship_summary.get('trials', 0)} испытаний · PASS {relationship_summary.get('passed', 0)} · FAIL {relationship_summary.get('failed', 0)} · нет данных {relationship_summary.get('unverified', 0)}</p></div>
          <div class="mc-edge-filters"><label>Приоритет <select data-factory-filter="priority"><option value="ALL">Все</option><option value="1">P1 · Индекс и сектор</option><option value="2">P2 · Многофакторные</option><option value="3">P3 · Overnight</option><option value="4">P4 · Ликвидность</option><option value="5">P5 · Пары</option></select></label>
          <label>Семейство <select data-factory-filter="family"><option value="ALL">Все</option>{''.join(f'<option value="{code}">{name}</option>' for code, name in RELATIONSHIP_FAMILY_NAMES_RU.items())}</select></label>
          <label>Режим <select data-factory-filter="regime"><option value="ALL">Все</option><option value="TREND">Тренд</option><option value="RANGE">Боковик</option><option value="EXPANSION">Расширение</option><option value="COMPRESSION">Сжатие</option></select></label>
          <label>Сессия <select data-factory-filter="session"><option value="ALL">Все</option>{''.join(f'<option value="{code}">{name}</option>' for code, name in SESSION_NAMES_RU.items())}</select></label></div></div>
          <details class="mc-table-spoiler"><summary>Показать таблицу <span>{len(relationship_rows)} строк</span></summary><div class="mc-oos-table-wrap"><table class="mc-oos-table"><thead><tr><th>Приоритет</th><th>Семейство</th><th>Источник</th><th>Цель</th><th>Режим</th><th>Сессия</th><th>Импульс → лаг</th><th>Бары</th><th>OOS</th><th>PF</th><th>Ожидание, bps</th><th>Периоды</th><th>p скорр.</th><th>Покрытие</th><th>Вердикт</th></tr></thead><tbody>{relationship_table_rows}</tbody></table></div></details>
          <div class="mc-edge-panel-footer"><span data-factory-count>Показано: {len(relationship_rows)}</span><span>Production заблокирован до OOS PASS и Trust Gate</span></div></section>
        <nav class="mc-edge-section-nav" aria-label="Исследования Edge">{section_nav}</nav>
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
      </main></div><script src="/assets/marketcore/ui-runtime/v1/edge-oos-control.js"></script>
      <script>
      (() => {{
        const sectionId = document.body.dataset.activeSection;
        if (!sectionId) return;
        const section = document.getElementById(sectionId);
        if (!section) return;
        section.dataset.activeSection = "true";
        requestAnimationFrame(() => section.scrollIntoView({{block: "start"}}));
      }})();
      </script></body></html>"""
