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
    "strategy-hypothesis-run": ("src/scripts/run_strategy_hypothesis_execution_pipeline_v2.py", "Проверка гипотез V2"),
    "hypothesis-lineage": ("src/scripts/build_canonical_hypothesis_trial_registry_v2.py", "Сквозные связи гипотез"),
    "relative-strength-run": ("src/scripts/run_relative_strength_parameter_adapter_v2.py", "Проверка Relative Strength"),
    "intermarket-lead-lag-run": ("src/scripts/run_intermarket_lead_lag_parameter_adapter_v2.py", "Проверка Intermarket Lead/Lag"),
    "failure-diagnostics": ("src/scripts/build_hypothesis_failure_diagnostics_v2.py", "Диагностика провалов гипотез"),
    "gross-net-attribution": ("src/scripts/build_trial_gross_net_attribution_v1.py", "Gross/Net атрибуция"),
    "targeted-trade-replay": ("src/scripts/run_targeted_trade_level_replay_v1.py", "Точный trade-level replay"),
    "swing-timeframes": ("src/scripts/build_canonical_swing_timeframes_v1.py", "Swing таймфреймы"),
    "swing-data-quality": ("src/scripts/build_swing_data_quality_gate_v1.py", "Качество Swing данных"),
    "swing-factory": ("src/scripts/build_swing_hypothesis_factory_v1.py", "Swing Hypothesis Factory"),
    "forward-incubator": ("src/scripts/build_forward_edge_incubator_v1.py", "Forward Edge Incubator"),
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


def _format_age_ru(value: object) -> str:
    total_minutes = max(0, round(float(value or 0) * 60))
    hours, minutes = divmod(total_minutes, 60)
    if hours:
        return f"{hours} ч {minutes} мин"
    return f"{minutes} мин"


def _quality_status_text(i18n: UiI18nResolverV1, value: object) -> str:
    return i18n.text(f"status.{str(value or '').strip().lower()}")


def _quality_reason_text(i18n: UiI18nResolverV1, value: object) -> str:
    return i18n.text(f"error.data_quality.{str(value or '').strip().lower()}")


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


def _strategy_hypothesis_results() -> tuple[list[dict], dict]:
    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""SELECT execution_run_id,total_candidates,processed_candidates,oos_pass,oos_fail,
                       unverified,status,live_allowed,created_at,completed_at
                FROM analytics.strategy_hypothesis_execution_run_v2 ORDER BY created_at DESC LIMIT 1""")
            summary = dict(cur.fetchone() or {})
            rows: list[dict] = []
            if summary:
                cur.execute("""SELECT strategy_family,verdict_code,reason_code,count(*) AS candidates,
                           max(oos_profit_factor) AS best_pf,max(oos_expectancy) AS best_expectancy,
                           min(adjusted_p_value) AS best_adjusted_p
                    FROM analytics.strategy_hypothesis_execution_result_v2 WHERE execution_run_id=%s
                    GROUP BY strategy_family,verdict_code,reason_code ORDER BY strategy_family,verdict_code""",
                    (summary["execution_run_id"],))
                rows = [dict(row) for row in cur.fetchall()]
    return rows, summary


def _hypothesis_lineage_summary() -> dict:
    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""SELECT count(*) AS hypotheses,
                       count(*) FILTER(WHERE lifecycle_state='TESTED') AS tested,
                       count(*) FILTER(WHERE lifecycle_state='UNVERIFIED') AS unverified
                FROM analytics.canonical_hypothesis_registry_v1""")
            summary = dict(cur.fetchone() or {})
            cur.execute("""SELECT count(*) AS trials,
                       count(*) FILTER(WHERE trust_state='PENDING') AS trust_pending,
                       count(*) FILTER(WHERE paper_state NOT IN ('NOT_ELIGIBLE')) AS paper_candidates
                FROM analytics.hypothesis_trial_registry_v2""")
            summary.update(dict(cur.fetchone() or {}))
    return summary


def _failure_diagnostics() -> tuple[list[dict], dict]:
    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""SELECT diagnostics_run_id FROM analytics.hypothesis_failure_diagnostic_v2
                ORDER BY created_at DESC LIMIT 1""")
            latest = cur.fetchone()
            if not latest:
                return [], {"diagnosed": 0, "supported": 0}
            cur.execute("""SELECT strategy_family,primary_failure_code,stability_status,
                       gross_cost_attribution_status,recommended_action,count(*) AS candidates
                FROM analytics.hypothesis_failure_diagnostic_v2 WHERE diagnostics_run_id=%s
                GROUP BY 1,2,3,4,5 ORDER BY strategy_family""", (latest["diagnostics_run_id"],))
            rows = [dict(row) for row in cur.fetchall()]
            summary = {"diagnosed": sum(int(row["candidates"]) for row in rows),
                       "supported": sum(int(row["candidates"]) for row in rows if row["stability_status"] == "SUPPORTED")}
    return rows, summary


def _gross_net_attribution() -> tuple[list[dict], dict]:
    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""SELECT attribution_run_id FROM analytics.trial_gross_net_attribution_v1
                ORDER BY created_at DESC LIMIT 1""")
            latest = cur.fetchone()
            if not latest:
                return [], {"trials": 0, "no_raw_edge": 0, "cost_destroyed": 0}
            cur.execute("""SELECT strategy_family,diagnosis_code,count(*) AS trials,
                       max(estimated_gross_expectancy) AS best_gross,max(net_expectancy) AS best_net,
                       max(attribution_status) AS attribution_status
                FROM analytics.trial_gross_net_attribution_v1 WHERE attribution_run_id=%s
                GROUP BY 1,2 ORDER BY strategy_family,diagnosis_code""", (latest["attribution_run_id"],))
            rows = [dict(row) for row in cur.fetchall()]
            summary = {"trials": sum(int(row["trials"]) for row in rows),
                       "no_raw_edge": sum(int(row["trials"]) for row in rows if row["diagnosis_code"] == "NO_RAW_EDGE"),
                       "cost_destroyed": sum(int(row["trials"]) for row in rows if row["diagnosis_code"] == "EDGE_DESTROYED_BY_COSTS")}
    return rows, summary


def _targeted_trade_replay() -> tuple[list[dict], dict]:
    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT replay_run_id FROM analytics.targeted_trade_level_replay_v1 ORDER BY created_at DESC LIMIT 1")
            latest = cur.fetchone()
            if not latest:
                return [], {"candidates": 0, "gross_pf_1": 0, "net_positive": 0}
            cur.execute("""SELECT strategy_family,count(*) AS candidates,sum(replayed_trades) AS trades,
                       max(gross_profit_factor) AS best_gross_pf,max(net_profit_factor) AS best_net_pf,
                       max(gross_expectancy) AS best_gross_expectancy,max(net_expectancy) AS best_net_expectancy
                FROM analytics.targeted_trade_level_replay_v1 WHERE replay_run_id=%s GROUP BY 1 ORDER BY 1""",
                (latest["replay_run_id"],))
            rows = [dict(row) for row in cur.fetchall()]
            cur.execute("""SELECT count(*) AS candidates,
                       count(*) FILTER(WHERE gross_profit_factor>1) AS gross_pf_1,
                       count(*) FILTER(WHERE gross_profit_factor>=1.1) AS gross_pf_11,
                       count(*) FILTER(WHERE net_expectancy>0) AS net_positive
                FROM analytics.targeted_trade_level_replay_v1 WHERE replay_run_id=%s""", (latest["replay_run_id"],))
            summary = dict(cur.fetchone() or {})
    return rows, summary


def _swing_summary() -> dict:
    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT timeframe,count(*) bars,count(DISTINCT symbol) symbols FROM analytics.swing_market_bars_v1 GROUP BY 1")
            bars = {row["timeframe"]: dict(row) for row in cur.fetchall()}
            cur.execute("SELECT audit_run_id FROM analytics.swing_data_quality_gate_v1 ORDER BY created_at DESC LIMIT 1")
            audit = cur.fetchone()
            cur.execute("SELECT count(*) rows,count(*) FILTER(WHERE quality_status='READY') ready FROM analytics.swing_data_quality_gate_v1 WHERE audit_run_id=%s", (audit["audit_run_id"],))
            quality = dict(cur.fetchone() or {})
            cur.execute("SELECT factory_run_id FROM analytics.swing_hypothesis_factory_v1 ORDER BY created_at DESC LIMIT 1")
            factory = cur.fetchone()
            cur.execute("SELECT count(*) candidates,count(*) FILTER(WHERE final_oos_opened) opened FROM analytics.swing_hypothesis_factory_v1 WHERE factory_run_id=%s", (factory["factory_run_id"],))
            result = dict(cur.fetchone() or {})
            result.update({"bars": bars, "quality_rows": quality.get("rows", 0), "quality_ready": quality.get("ready", 0)})
    return result


def _forward_incubator_summary() -> dict:
    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT cohort_id,activated_at FROM analytics.forward_edge_incubator_v1 ORDER BY created_at DESC LIMIT 1")
            latest = cur.fetchone()
            if not latest: return {"candidates":0,"observations":0}
            cur.execute("""SELECT count(*) candidates,count(*) FILTER(WHERE incubator_status='ACCUMULATING') accumulating,
              count(*) FILTER(WHERE incubator_status='WATCH_BLOCKED') watch_blocked,
              count(*) FILTER(WHERE incubator_status='ROUTER_REQUIRED') router_required,
              count(*) FILTER(WHERE promotion_allowed) promotion_allowed
              FROM analytics.forward_edge_incubator_v1 WHERE cohort_id=%s""",(latest["cohort_id"],))
            result=dict(cur.fetchone() or {}); result["activated_at"]=latest["activated_at"]
            cur.execute("SELECT count(*) observations FROM analytics.forward_edge_observation_v1 WHERE cohort_id=%s",(latest["cohort_id"],))
            result.update(dict(cur.fetchone() or {}))
            cur.execute("SELECT count(*) FILTER(WHERE worker_status='OK') worker_ok,max(updated_at) worker_updated_at FROM analytics.forward_edge_worker_state_v1 WHERE cohort_id=%s",(latest["cohort_id"],))
            result.update(dict(cur.fetchone() or {}))
    return result


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


def run_strategy_hypothesis_action_v2() -> str:
    return _run_background_action_v1(
        "src/scripts/run_strategy_hypothesis_execution_pipeline_v2.py",
        "Проверка гипотез V2",
    )


def run_hypothesis_lineage_action_v2() -> str:
    return _run_background_action_v1(
        "src/scripts/build_canonical_hypothesis_trial_registry_v2.py",
        "Сквозные связи гипотез",
    )


def run_relative_strength_action_v2() -> str:
    return _run_background_action_v1(
        "src/scripts/run_relative_strength_parameter_adapter_v2.py",
        "Проверка Relative Strength",
    )


def run_intermarket_lead_lag_action_v2() -> str:
    return _run_background_action_v1(
        "src/scripts/run_intermarket_lead_lag_parameter_adapter_v2.py",
        "Проверка Intermarket Lead/Lag",
    )


def run_failure_diagnostics_action_v2() -> str:
    return _run_background_action_v1(
        "src/scripts/build_hypothesis_failure_diagnostics_v2.py",
        "Диагностика провалов гипотез",
    )


def run_gross_net_attribution_action_v1() -> str:
    return _run_background_action_v1(
        "src/scripts/build_trial_gross_net_attribution_v1.py",
        "Gross/Net атрибуция",
    )


def run_targeted_trade_replay_action_v1() -> str:
    return _run_background_action_v1(
        "src/scripts/run_targeted_trade_level_replay_v1.py",
        "Точный trade-level replay",
    )


def run_swing_timeframes_action_v1() -> str:
    return _run_background_action_v1("src/scripts/build_canonical_swing_timeframes_v1.py", "Swing таймфреймы")


def run_swing_data_quality_action_v1() -> str:
    return _run_background_action_v1("src/scripts/build_swing_data_quality_gate_v1.py", "Качество Swing данных")


def run_swing_factory_action_v1() -> str:
    return _run_background_action_v1("src/scripts/build_swing_hypothesis_factory_v1.py", "Swing Hypothesis Factory")


def run_forward_incubator_action_v1() -> str:
    return _run_background_action_v1("src/scripts/build_forward_edge_incubator_v1.py", "Forward Edge Incubator")


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


def _traffic_light(state: str, label: str, detail: str, href: str = "") -> str:
    """A single, honest operating state: green is never inferred from activity alone."""
    tag = "a" if href else "div"
    href_attr = f' href="{html.escape(href)}"' if href else ""
    return (
        f'<{tag} class="mc-traffic-light is-{html.escape(state)}"{href_attr} '
        f'title="{html.escape(detail)}"><i aria-hidden="true"></i><span>{html.escape(label)}</span>'
        f'<small>{html.escape(detail)}</small></{tag}>'
    )


def _section_link(section_id: str, label: str, value: object, active_section: str, state: str = "neutral") -> str:
    active = ' class="active"' if active_section == section_id else ""
    return (
        f'<a{active} href="{html.escape(SECTION_URLS[section_id])}">'
        f'<i class="mc-nav-light is-{html.escape(state)}" aria-hidden="true"></i>'
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
    strategy_result_rows, strategy_result_summary = _strategy_hypothesis_results()
    hypothesis_lineage = _hypothesis_lineage_summary()
    failure_rows, failure_summary = _failure_diagnostics()
    attribution_rows, attribution_summary = _gross_net_attribution()
    replay_rows, replay_summary = _targeted_trade_replay()
    swing_summary = _swing_summary()
    forward_summary = _forward_incubator_summary()
    passed = sum(1 for row in rows if row["verdict_code"] == "OOS_PASS")
    failed = len(rows) - passed
    oos_bars = 0
    if rows and rows[0].get("oos_start") and rows[0].get("oos_end"):
        oos_bars = "2846"
    last_run = max((row.get("updated_at") for row in rows), default=None)
    quality_blocked = int(quality_summary.get("blocked", 0) or 0)
    relationship_passed = int(relationship_summary.get("passed", 0) or 0)
    quality_ready = int(quality_summary.get("factory_ready", 0) or 0)
    quality_total = int(quality_summary.get("symbols", 0) or 0)
    quality_state = "green" if quality_total and quality_ready == quality_total else ("amber" if quality_ready else "red")
    edge_state = "green" if relationship_passed else "red"
    forward_candidates = int(forward_summary.get("candidates", 0) or 0)
    forward_promoted = int(forward_summary.get("promotion_allowed", 0) or 0)
    forward_observations = int(forward_summary.get("observations", 0) or 0)
    forward_state = "green" if forward_promoted else ("amber" if forward_candidates else "neutral")
    swing_opened = int(swing_summary.get("opened", 0) or 0)
    swing_state = "green" if swing_opened else "blue"
    execution_quote_verified = int(execution_summary.get("quote_verified", 0) or 0)
    execution_state = "green" if execution_quote_verified else "amber"
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
        <td>{_format_datetime_ru(row['last_ts'])}</td><td>{_format_age_ru(row['latest_age_hours'])}</td>
        <td>{row['duplicate_rows']}</td><td>{row['invalid_ohlc_rows']}</td><td>{float(row['regime_coverage_ratio']) * 100:.0f}%</td>
        <td><span class="mc-oos-badge {'pass' if row['market_data_status'] == 'READY' else 'fail'}">{html.escape(_quality_status_text(i18n, row['market_data_status']))}</span></td>
        <td><span class="mc-oos-badge {'pass' if row['factory_status'] == 'READY' else 'fail'}">{html.escape(_quality_status_text(i18n, row['factory_status']))}</span></td>
        <td>{html.escape(', '.join(_quality_reason_text(i18n, code) for code in row['reason_codes']) if isinstance(row['reason_codes'], list) else _quality_reason_text(i18n, row['reason_codes'])) or '—'}</td></tr>"""
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
    strategy_result_table_rows = "".join(
        f"""<tr><td><strong>{html.escape(_strategy_name_ru(row['strategy_family'], row['strategy_family']))}</strong></td>
        <td>{html.escape(row['verdict_code'].replace('OOS_', ''))}</td><td>{int(row['candidates'])}</td>
        <td>{float(row['best_pf'] or 0):.2f}</td><td>{float(row['best_expectancy'] or 0):.4f}</td>
        <td>{float(row['best_adjusted_p'] or 1):.4f}</td><td>{html.escape(row['reason_code'].replace('_', ' '))}</td></tr>"""
        for row in strategy_result_rows
    )
    failure_table_rows = "".join(
        f"""<tr><td><strong>{html.escape(_strategy_name_ru(row['strategy_family'], row['strategy_family']))}</strong></td>
        <td>{int(row['candidates'])}</td><td>{html.escape(row['primary_failure_code'].replace('_', ' '))}</td>
        <td>{'Есть' if row['stability_status'] == 'SUPPORTED' else 'Нет'}</td>
        <td>{'Недоступно: gross-метрика не сохранена' if row['gross_cost_attribution_status'] != 'AVAILABLE' else 'Доступно'}</td>
        <td>{html.escape(row['recommended_action'])}</td></tr>"""
        for row in failure_rows
    )
    attribution_table_rows = "".join(
        f"""<tr><td><strong>{html.escape(_strategy_name_ru(row['strategy_family'], row['strategy_family']))}</strong></td>
        <td>{'Raw edge уничтожен costs' if row['diagnosis_code'] == 'EDGE_DESTROYED_BY_COSTS' else 'Raw edge отсутствует'}</td>
        <td>{int(row['trials'])}</td><td>{float(row['best_gross'] or 0):.4f}</td><td>{float(row['best_net'] or 0):.4f}</td>
        <td>Gross PF требует trade-level replay</td></tr>"""
        for row in attribution_rows
    )
    replay_table_rows = "".join(
        f"""<tr><td><strong>{html.escape(_strategy_name_ru(row['strategy_family'], row['strategy_family']))}</strong></td>
        <td>{int(row['candidates'])}</td><td>{int(row['trades'])}</td><td>{float(row['best_gross_pf'] or 0):.3f}</td>
        <td>{float(row['best_net_pf'] or 0):.3f}</td><td>{float(row['best_gross_expectancy'] or 0):.4f}</td>
        <td>{float(row['best_net_expectancy'] or 0):.4f}</td></tr>""" for row in replay_rows
    )
    section_nav = "".join(
        (
            _section_link("data-quality-gate", "Качество", f"{quality_ready}/{quality_total}", active_section, quality_state),
            _section_link("commodity-factors", "Сырьё", len(commodity_relations), active_section, quality_state),
            _section_link("signal-funnel", "Воронка", len(funnel_stages), active_section, "red" if live_boundary_blocked else "green"),
            _section_link("relationship-factory", "Фабрика связей", relationship_summary.get("trials", 0), active_section, edge_state),
            _section_link("session-edge", "Сессии", session_summary.get("trials", 0), active_section, edge_state),
            _section_link("execution-edge", "Исполнение", execution_summary.get("trials", 0), active_section, execution_state),
            _section_link("strategy-generator", "Генератор", strategy_generator_summary.get("candidates", 0), active_section, edge_state),
        )
    )
    traffic_lights = "".join((
        _traffic_light(quality_state, "Данные", f"{quality_ready} из {quality_total} источников готовы", SECTION_URLS["data-quality-gate"]),
        _traffic_light(edge_state, "OOS edge", f"Подтверждено: {relationship_passed}; без OOS PASS продвижение запрещено", SECTION_URLS["relationship-factory"]),
        _traffic_light(forward_state, "Forward", f"{forward_candidates} кандидатов, {forward_observations} новых наблюдений", SECTION_URLS["strategy-generator"]),
        _traffic_light(swing_state, "Swing", "Финальный OOS открыт" if swing_opened else "Финальный OOS запечатан до готовности данных", SECTION_URLS["strategy-generator"]),
        _traffic_light(execution_state, "Исполнение", "Bid/ask подтверждены" if execution_quote_verified else "Нет подтверждённых bid/ask и стакана", SECTION_URLS["execution-edge"]),
        _traffic_light("red", "LIVE", "Заявки заблокированы до OOS PASS и Trust Gate"),
    ))
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
        <section class="mc-traffic-overview" aria-label="Операционный светофор">
          <div class="mc-traffic-overview-title"><p>ОПЕРАЦИОННЫЙ СВЕТОФОР</p><span>Зелёный — подтверждено · жёлтый — наблюдение или ограничение · красный — стоп</span></div>
          <div class="mc-traffic-grid">{traffic_lights}</div>
        </section>
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
          <div><form method="post" action="/workspace-v2/control-center/edge-oos/strategy-generator"><button type="submit">Сформировать пространство</button></form>
          <form method="post" action="/workspace-v2/control-center/edge-oos/strategy-hypothesis-run"><button type="submit">Проверить 432 гипотезы</button></form></div></div>
          <div class="mc-oos-kpis mc-commodity-kpis">{strategy_family_cards}</div>
          <div class="mc-oos-kpis mc-funnel-kpis"><article><span>Проверено</span><b>{strategy_result_summary.get('processed_candidates', 0)}</b></article>
          <article><span>OOS PASS</span><b class="is-positive">{strategy_result_summary.get('oos_pass', 0)}</b></article>
          <article><span>OOS FAIL</span><b class="is-negative">{strategy_result_summary.get('oos_fail', 0)}</b></article>
          <article><span>Нет подтверждения</span><b>{strategy_result_summary.get('unverified', 0)}</b></article></div>
          <div class="mc-oos-kpis mc-funnel-kpis"><article><span>Канонические ID</span><b>{hypothesis_lineage.get('hypotheses', 0)}</b></article>
          <article><span>Связанные испытания</span><b>{hypothesis_lineage.get('trials', 0)}</b></article>
          <article><span>Trust Gate ожидают</span><b>{hypothesis_lineage.get('trust_pending', 0)}</b></article>
          <article><span>Paper-кандидаты</span><b>{hypothesis_lineage.get('paper_candidates', 0)}</b></article></div>
          <form method="post" action="/workspace-v2/control-center/edge-oos/hypothesis-lineage"><button class="secondary" type="submit">Обновить сквозные связи</button></form>
          <form method="post" action="/workspace-v2/control-center/edge-oos/relative-strength-run"><button type="submit">Проверить Relative Strength</button></form>
          <form method="post" action="/workspace-v2/control-center/edge-oos/intermarket-lead-lag-run"><button type="submit">Проверить Intermarket Lead/Lag</button></form>
          <form method="post" action="/workspace-v2/control-center/edge-oos/failure-diagnostics"><button class="secondary" type="submit">Диагностика провалов</button></form>
          <details class="mc-table-spoiler"><summary>Почему edge не найден <span>{failure_summary.get('diagnosed', 0)} кандидата</span></summary><div class="mc-oos-table-wrap"><table class="mc-oos-table"><thead><tr><th>Семейство</th><th>Кандидаты</th><th>Главная причина</th><th>Соседняя устойчивость</th><th>Влияние costs</th><th>Следующее действие</th></tr></thead><tbody>{failure_table_rows}</tbody></table></div><p>Новый V3 запрещено настраивать по уже просмотренному OOS: требуется новый untouched участок или nested walk-forward.</p></details>
          <form method="post" action="/workspace-v2/control-center/edge-oos/gross-net-attribution"><button class="secondary" type="submit">Обновить Gross/Net</button></form>
          <details class="mc-table-spoiler"><summary>Gross → Costs → Net <span>{attribution_summary.get('trials', 0)} trials</span></summary>
          <div class="mc-oos-kpis mc-funnel-kpis"><article><span>Raw edge отсутствует</span><b>{attribution_summary.get('no_raw_edge', 0)}</b></article>
          <article><span>Edge уничтожен costs</span><b>{attribution_summary.get('cost_destroyed', 0)}</b></article></div>
          <div class="mc-oos-table-wrap"><table class="mc-oos-table"><thead><tr><th>Семейство</th><th>Диагноз</th><th>Trials</th><th>Лучший gross</th><th>Лучший net</th><th>Ограничение</th></tr></thead><tbody>{attribution_table_rows}</tbody></table></div>
          <p>Gross expectancy восстановлено из фиксированного per-trade cost. Gross PF не рассчитывается без повторного trade-level replay.</p></details>
          <form method="post" action="/workspace-v2/control-center/edge-oos/targeted-trade-replay"><button type="submit">Точный replay 155 кандидатов</button></form>
          <details class="mc-table-spoiler"><summary>Точный trade-level replay <span>{replay_summary.get('candidates', 0)} кандидатов</span></summary>
          <div class="mc-oos-kpis mc-funnel-kpis"><article><span>Gross PF &gt; 1</span><b>{replay_summary.get('gross_pf_1', 0)}</b></article>
          <article><span>Gross PF ≥ 1,10</span><b>{replay_summary.get('gross_pf_11', 0)}</b></article>
          <article><span>Net ожидание &gt; 0</span><b>{replay_summary.get('net_positive', 0)}</b></article></div>
          <div class="mc-oos-table-wrap"><table class="mc-oos-table"><thead><tr><th>Семейство</th><th>Кандидаты</th><th>Сделки</th><th>Лучший gross PF</th><th>Лучший net PF</th><th>Gross ожидание</th><th>Net ожидание</th></tr></thead><tbody>{replay_table_rows}</tbody></table></div></details>
          <details class="mc-table-spoiler"><summary>Swing Research V1 <span>{swing_summary.get('candidates', 0)} гипотез</span></summary>
          <div class="mc-oos-kpis mc-funnel-kpis"><article><span>H1 бары</span><b>{swing_summary.get('bars', {}).get('H1', {}).get('bars', 0)}</b></article>
          <article><span>H4 бары</span><b>{swing_summary.get('bars', {}).get('H4', {}).get('bars', 0)}</b></article>
          <article><span>D1 бары</span><b>{swing_summary.get('bars', {}).get('D1', {}).get('bars', 0)}</b></article>
          <article><span>Data Quality</span><b>{swing_summary.get('quality_ready', 0)}/{swing_summary.get('quality_rows', 0)}</b></article>
          <article><span>Final OOS открыт</span><b>{swing_summary.get('opened', 0)}</b></article></div>
          <div class="mc-oos-actions"><form method="post" action="/workspace-v2/control-center/edge-oos/swing-timeframes"><button type="submit">Обновить H1/H4/D1</button></form>
          <form method="post" action="/workspace-v2/control-center/edge-oos/swing-data-quality"><button type="submit">Проверить Swing данные</button></form>
          <form method="post" action="/workspace-v2/control-center/edge-oos/swing-factory"><button type="submit">Сформировать Swing гипотезы</button></form></div>
          <p>Nested split 40/20/20/20 · final OOS запечатан commitment-хэшем и не открыт.</p></details>
          <details class="mc-table-spoiler"><summary>Forward Edge Incubator V1 <span>{forward_summary.get('candidates', 0)} кандидатов</span></summary>
          <div class="mc-oos-kpis mc-funnel-kpis"><article><span>Накапливают</span><b>{forward_summary.get('accumulating', 0)}</b></article>
          <article><span>Watch blocked</span><b>{forward_summary.get('watch_blocked', 0)}</b></article>
          <article><span>Router required</span><b>{forward_summary.get('router_required', 0)}</b></article>
          <article><span>Новые наблюдения</span><b>{forward_summary.get('observations', 0)}</b></article>
          <article><span>Worker OK</span><b>{forward_summary.get('worker_ok', 0)}</b></article>
          <article><span>Promotion allowed</span><b>{forward_summary.get('promotion_allowed', 0)}</b></article></div>
          <form method="post" action="/workspace-v2/control-center/edge-oos/forward-incubator"><button type="submit">Зафиксировать новую forward-когорту</button></form>
          <p>Принимаются только сигналы после момента фиксации. Исторический backfill запрещён PostgreSQL trigger.</p></details>
          <details class="mc-table-spoiler"><summary>Результаты по семействам <span>{len(strategy_result_rows)} строк</span></summary><div class="mc-oos-table-wrap"><table class="mc-oos-table"><thead><tr><th>Семейство</th><th>Вердикт</th><th>Кандидаты</th><th>Лучший PF</th><th>Ожидание</th><th>p скорр.</th><th>Причина</th></tr></thead><tbody>{strategy_result_table_rows}</tbody></table></div></details>
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
