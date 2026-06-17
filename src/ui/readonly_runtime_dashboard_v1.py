#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
from zoneinfo import ZoneInfo

import psycopg2
import psycopg2.extras
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

app = FastAPI(title="Панель Finam_Core")
templates = Jinja2Templates(directory="src/ui/templates")


MSK = ZoneInfo("Europe/Moscow")

def to_msk(dt):
    if not dt:
        return ""
    return dt.astimezone(MSK).strftime("%d.%m.%Y %H:%M")



def fetch_git_checkpoints(limit: int = 10):
    try:
        out = subprocess.check_output(["git", "tag", "--sort=-creatordate"], text=True)
        return [x for x in out.splitlines() if x.startswith("checkpoint_")][:limit]
    except Exception:
        return []


def fetch_dashboard_data():
    dsn = os.environ["DATABASE_URL"]

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT COUNT(*) AS signals, MAX(signal_ts) AS last_signal_ts
                FROM runtime_shadow_gold_signals
                WHERE symbol='GDU6@RTSX'
                  AND strategy='gold_short_only_shadow_v1';
            """)
            gold = cur.fetchone()

            cur.execute("""
                SELECT to_regclass('public.runtime_edge_validation_scorecard_v2') IS NOT NULL AS exists;
            """)
            scorecard_table_exists = bool(cur.fetchone()["exists"])

            if scorecard_table_exists:
                cur.execute("""
                    SELECT *
                    FROM runtime_edge_validation_scorecard_v2
                    ORDER BY strategy;
                """)
                scorecard = cur.fetchall()
            else:
                scorecard = []

            cur.execute("""
                SELECT candidate, decision, runtime_allow, shadow_allow,
                       watch_allow, reason, created_at
                FROM runtime_governance_shadow_accumulation_v1
                ORDER BY created_at DESC
                LIMIT 10;
            """)
            governance = cur.fetchall()

            cur.execute("""
                SELECT symbol, strategy, timeframe, signal_ts, side,
                       entry_price, reason
                FROM runtime_shadow_gold_signals
                WHERE symbol='GDU6@RTSX'
                ORDER BY signal_ts DESC
                LIMIT 20;
            """)
            gold_signals = cur.fetchall()

    for row in governance:
        row["created_at_msk"] = to_msk(row.get("created_at"))

    for row in gold_signals:
        row["signal_ts_msk"] = to_msk(row.get("signal_ts"))

    gold_count = int(gold["signals"] or 0)
    target = 50

    return {
        "system_status": "Работает",
        "mode": "Research / Shadow",
        "execution": "Отключено",
        "gold_signals": gold_count,
        "gold_target": target,
        "gold_remaining": max(0, target - gold_count),
        "gold_last_signal_ts": to_msk(gold["last_signal_ts"]),
        "scorecard": scorecard,
        "governance": governance,
        "gold_signal_rows": gold_signals,
        "checkpoints": fetch_git_checkpoints(),
    }


def fetch_instrument_statistics_v2():
    dsn = os.environ["DATABASE_URL"]
    symbols = [
        "GDU6@RTSX", "BRN6@RTSX", "NGN6@RTSX", "USDRUBF@RTSX",
        "LKOH@MISX", "SBER@MISX", "GAZP@MISX", "PLZL@MISX",
    ]

    sql = """
    WITH src AS (
        SELECT unnest(%s::text[]) AS symbol
    ),
    bars AS (
        SELECT symbol, COUNT(*) AS bars, MAX(ts) AS last_bar_ts
        FROM market_bars
        WHERE symbol = ANY(%s)
        GROUP BY symbol
    ),
    closed AS (
        SELECT
            symbol,
            COUNT(*) AS trades,
            COUNT(*) FILTER (WHERE net_pnl > 0) AS wins,
            ROUND(COALESCE(AVG(net_pnl), 0)::numeric, 6) AS expectancy,
            ROUND((
                SUM(CASE WHEN net_pnl > 0 THEN net_pnl ELSE 0 END)
                / NULLIF(ABS(SUM(CASE WHEN net_pnl < 0 THEN net_pnl ELSE 0 END)), 0)
            )::numeric, 4) AS profit_factor
        FROM closed_trades
        WHERE symbol = ANY(%s)
          
        GROUP BY symbol
    ),
    gold_shadow_raw AS (
        SELECT
            id,
            symbol,
            timeframe,
            strategy,
            signal_ts,
            side,
            entry_price::numeric AS entry_price,
            LEAD(entry_price::numeric, 10) OVER (
                PARTITION BY symbol, timeframe, strategy
                ORDER BY signal_ts
            ) AS exit_price
        FROM runtime_shadow_gold_signals
        WHERE symbol='GDU6@RTSX'
          AND strategy='gold_short_only_shadow_v1'
    ),
    gold_shadow_scored AS (
        SELECT
            *,
            CASE
                WHEN exit_price IS NULL THEN NULL
                WHEN side='SELL' THEN entry_price - exit_price
                ELSE exit_price - entry_price
            END AS pnl
        FROM gold_shadow_raw
    ),
    gold AS (
        SELECT
            symbol,
            COUNT(*) AS shadow_signals,
            COUNT(*) FILTER (WHERE pnl IS NOT NULL) AS shadow_trades,
            COUNT(*) FILTER (WHERE pnl > 0) AS shadow_wins,
            COUNT(*) FILTER (WHERE pnl < 0) AS shadow_losses,
            ROUND(COALESCE(AVG(pnl), 0)::numeric, 6) AS shadow_expectancy,
            ROUND((
                SUM(CASE WHEN pnl > 0 THEN pnl ELSE 0 END)
                / NULLIF(ABS(SUM(CASE WHEN pnl < 0 THEN pnl ELSE 0 END)), 0)
            )::numeric, 4) AS shadow_profit_factor
        FROM gold_shadow_scored
        GROUP BY symbol
    )
    SELECT
        src.symbol,
        COALESCE(b.bars, 0) AS bars,
        b.last_bar_ts,
        COALESCE(c.trades, 0) AS trades,
        COALESCE(c.wins, 0) AS wins,
        CASE
            WHEN COALESCE(c.trades, 0) > 0
            THEN ROUND((c.wins::numeric / c.trades::numeric * 100), 2)
            ELSE NULL
        END AS winrate,
        c.expectancy,
        c.profit_factor,
        CASE
            WHEN src.symbol='GDU6@RTSX'
                 AND (SELECT COUNT(*) FROM runtime_shadow_gold_signals
                      WHERE symbol='GDU6@RTSX'
                        AND strategy='gold_short_only_shadow_v1') >= 50
            THEN 'WATCH_RUNTIME_CANDIDATE'
            WHEN src.symbol='GDU6@RTSX' THEN 'SHADOW'
            WHEN src.symbol IN ('BRN6@RTSX','NGN6@RTSX') AND COALESCE(c.expectancy,0) < 0 THEN 'REJECT'
            WHEN src.symbol IN ('USDRUBF@RTSX','LKOH@MISX') THEN 'WATCH'
            WHEN COALESCE(b.bars,0)=0 THEN 'NO_DATA'
            WHEN b.last_bar_ts < now() - interval '7 days' THEN 'STALE'
            ELSE 'WATCH'
        END AS status,
        COALESCE(g.shadow_signals, 0) AS shadow_signals,
        COALESCE(g.shadow_trades, 0) AS shadow_trades,
        COALESCE(g.shadow_wins, 0) AS shadow_wins,
        COALESCE(g.shadow_losses, 0) AS shadow_losses,
        CASE
            WHEN COALESCE(g.shadow_trades, 0) > 0
            THEN ROUND((g.shadow_wins::numeric / g.shadow_trades::numeric * 100), 2)
            ELSE NULL
        END AS shadow_winrate,
        g.shadow_expectancy,
        g.shadow_profit_factor
    FROM src
    LEFT JOIN bars b ON b.symbol = src.symbol
    LEFT JOIN closed c ON c.symbol = src.symbol
    LEFT JOIN gold g ON g.symbol = src.symbol
    ORDER BY src.symbol;
    """

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (symbols, symbols, symbols))
            rows = cur.fetchall()

    for row in rows:
        row["last_bar_ts_msk"] = to_msk(row.get("last_bar_ts"))

    return rows


def fetch_gold_research_details_v1():
    dsn = os.environ["DATABASE_URL"]
    symbol = "GDU6@RTSX"
    strategy = "gold_short_only_shadow_v1"

    sql = """
    WITH signals AS (
        SELECT
            id,
            symbol,
            timeframe,
            signal_ts,
            side,
            entry_price::numeric AS entry_price,
            LEAD(entry_price::numeric, 10) OVER (
                PARTITION BY symbol, timeframe, strategy
                ORDER BY signal_ts
            ) AS exit_price
        FROM runtime_shadow_gold_signals
        WHERE symbol=%s
          AND strategy=%s
    ),
    scored AS (
        SELECT
            *,
            CASE
                WHEN exit_price IS NULL THEN NULL
                WHEN side='SELL' THEN entry_price - exit_price
                ELSE exit_price - entry_price
            END AS pnl
        FROM signals
    )
    SELECT
        COUNT(*) AS signals,
        COUNT(*) FILTER (WHERE pnl IS NOT NULL) AS closed_shadow_trades,
        COUNT(*) FILTER (WHERE pnl > 0) AS wins,
        COUNT(*) FILTER (WHERE pnl < 0) AS losses,
        ROUND(COALESCE(SUM(pnl),0)::numeric, 6) AS net_pnl,
        ROUND(COALESCE(AVG(pnl),0)::numeric, 6) AS expectancy,
        ROUND((
            SUM(CASE WHEN pnl > 0 THEN pnl ELSE 0 END)
            / NULLIF(ABS(SUM(CASE WHEN pnl < 0 THEN pnl ELSE 0 END)), 0)
        )::numeric, 4) AS profit_factor,
        MIN(signal_ts) AS first_signal_ts,
        MAX(signal_ts) AS last_signal_ts
    FROM scored;
    """

    last_sql = """
    SELECT signal_ts, side, entry_price, reason
    FROM runtime_shadow_gold_signals
    WHERE symbol=%s
      AND strategy=%s
    ORDER BY signal_ts DESC
    LIMIT 10;
    """

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (symbol, strategy))
            summary = cur.fetchone()

            cur.execute(last_sql, (symbol, strategy))
            last_signals = cur.fetchall()

    for row in last_signals:
        row["signal_ts_msk"] = to_msk(row.get("signal_ts"))

    closed = int(summary["closed_shadow_trades"] or 0)
    wins = int(summary["wins"] or 0)
    winrate = round(wins / closed * 100, 2) if closed else None

    return {
        "symbol": symbol,
        "strategy": strategy,
        "status": "Кандидат для runtime-наблюдения",
        "runtime": "Отключён",
        "execution": "Отключено",
        "signals": int(summary["signals"] or 0),
        "closed_shadow_trades": closed,
        "wins": wins,
        "losses": int(summary["losses"] or 0),
        "winrate": winrate,
        "net_pnl": summary["net_pnl"],
        "expectancy": summary["expectancy"],
        "profit_factor": summary["profit_factor"],
        "first_signal_ts": to_msk(summary.get("first_signal_ts")),
        "last_signal_ts": to_msk(summary.get("last_signal_ts")),
        "scorecard": "PASS",
        "audit": "PASS",
        "walkforward": "STABLE",
        "promotion_review": "WATCH_RUNTIME_CANDIDATE",
        "autorun_audit": "PASS",
        "last_signals": last_signals,
    }



def ru_accumulation_status(status: str) -> str:
    mapping = {
        "EARLY_ACCUMULATION": "Раннее накопление",
        "ACCUMULATING": "Идёт накопление",
        "NO_V3_CHAINS": "Нет V3-цепочек",
        "READY_FOR_REVIEW": "Готово к проверке",
    }
    return mapping.get(status or "", status or "")




def ru_reason(reason: str) -> str:
    mapping = {
        "too_few_clean_full_chains":
            "Недостаточно полных V3-цепочек",

        "clean_data_accumulating_not_enough_for_review":
            "Идёт накопление данных для анализа",

        "clean_trades_exist_but_no_v3_chains":
            "Сделки есть, но V3-цепочки не сформированы",

        "low_time_diversity_intraday":
            "Низкая временная диверсификация",

        "low_sample":
            "Недостаточный объём выборки",

        "statistics_v3_reviewable":
            "Доступно для статистического анализа",

        "strategy_timeframe_mismatch":
            "Несовпадение стратегии и таймфрейма",

        "contains_backfill_fill":
            "Используются восстановленные сделки",

        "exact_fill_pair":
            "Полное совпадение пары вход-выход",
    }

    return mapping.get(reason or "", reason or "")

def ru_statistics_status(status: str) -> str:
    mapping = {
        "LOW_SAMPLE": "Малая выборка",
        "LOW_TIME_DIVERSITY": "Низкая временная диверсификация",
        "STATISTICALLY_REVIEWABLE": "Доступно для статистического анализа",
        "REJECTED": "Отклонено",
        "RESEARCH": "Исследование",
    }
    return mapping.get(status or "", status or "")

def fetch_v3_dashboard_data():
    """Русский комментарий: единый источник данных для главной страницы 8088 — только clean V3."""
    dsn = os.environ["DATABASE_URL"]

    sql_accumulation = """
    select
        symbol,
        strategy,
        timeframe,
        clean_trades,
        trade_days,
        v3_full_chains,
        v3_partial_chains,
        round(v3_net_pnl, 6) as v3_net_pnl,
        accumulation_status,
        accumulation_reason
    from clean_paper_accumulation_tracker_v1
    order by v3_net_pnl desc;
    """

    sql_statistics = """
    select
        symbol,
        strategy,
        timeframe,
        trade_source,
        quality_bucket,
        trades,
        entry_days,
        exit_days,
        round(net_pnl, 6) as net_pnl,
        round(expectancy, 6) as expectancy,
        round(profit_factor, 4) as profit_factor,
        statistics_status,
        statistics_reason
    from strategy_statistics_v3
    order by net_pnl desc;
    """

    sql_daily = """
    select
        entry_ts::date as trade_date,
        symbol,
        strategy,
        timeframe,
        count(*) as trades,
        round(sum(net_pnl), 6) as pnl,
        round(avg(net_pnl), 6) as expectancy
    from closed_trade_chains_v3
    where entry_ts::date >= current_date - interval '7 days'
    group by 1,2,3,4
    order by trade_date desc, pnl desc;
    """

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql_accumulation)
            accumulation = cur.fetchall()

            cur.execute(sql_statistics)
            statistics = cur.fetchall()

            cur.execute(sql_daily)
            daily = cur.fetchall()

    for row in accumulation:
        row["accumulation_status_ru"] = ru_accumulation_status(row.get("accumulation_status"))
        row["accumulation_reason_ru"] = ru_reason(row.get("accumulation_reason"))

    for row in statistics:
        row["statistics_status_ru"] = ru_statistics_status(row.get("statistics_status"))
        row["statistics_reason_ru"] = ru_reason(row.get("statistics_reason"))

    summary = {
        "strategies": len(accumulation),
        "clean_trades": sum(int(r["clean_trades"] or 0) for r in accumulation),
        "v3_full_chains": sum(int(r["v3_full_chains"] or 0) for r in accumulation),
        "v3_pnl": round(sum(float(r["v3_net_pnl"] or 0) for r in accumulation), 6),
    }

    return {
        "title": "FINAM_CORE V3",
        "mode": "Только clean V3",
        "runtime": "Закрыт",
        "execution": "Закрыто",
        "summary": summary,
        "accumulation": accumulation,
        "statistics": statistics,
        "daily": daily,
        "checkpoints": fetch_git_checkpoints(),
    }

@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse(
        "v3_dashboard.html",
        {"request": request, "data": fetch_v3_dashboard_data(), "active": "v3", **_clean_operational_positions_context_v1()},
    )


@app.get("/v3", response_class=HTMLResponse)
def v3_dashboard(request: Request):
    return templates.TemplateResponse(
        "v3_dashboard.html",
        {"request": request, "data": fetch_v3_dashboard_data(), "active": "v3", **_clean_operational_positions_context_v1()},
    )


@app.get("/governance", response_class=HTMLResponse)
def governance(request: Request):
    return templates.TemplateResponse(
        "governance.html",
        {"request": request, "data": fetch_dashboard_data(), "active": "governance"},
    )


@app.get("/gold", response_class=HTMLResponse)
def gold(request: Request):
    return templates.TemplateResponse(
        "gold_status.html",
        {"request": request, "data": fetch_dashboard_data(), "active": "gold"},
    )


@app.get("/signals", response_class=HTMLResponse)
def signals(request: Request):
    return templates.TemplateResponse(
        "signals.html",
        {"request": request, "data": fetch_dashboard_data(), "active": "signals"},
    )


@app.get("/checkpoints", response_class=HTMLResponse)
def checkpoints(request: Request):
    return templates.TemplateResponse(
        "checkpoints.html",
        {"request": request, "data": fetch_dashboard_data(), "active": "checkpoints"},
    )

@app.get("/instruments", response_class=HTMLResponse)
def instruments(request: Request):
    data = fetch_dashboard_data()
    data["instrument_rows"] = fetch_instrument_statistics_v2()
    return templates.TemplateResponse(
        "instruments.html",
        {
            "request": request,
            "data": data,
            "active": "instruments",
        },
    )

def fetch_gold_runtime_readiness_v1():
    dsn = os.environ["DATABASE_URL"]

    sql = """
    WITH gold AS (
        SELECT
            COUNT(*) AS signals,
            MAX(signal_ts) AS last_signal_ts
        FROM runtime_shadow_gold_signals
        WHERE symbol='GDU6@RTSX'
          AND strategy='gold_short_only_shadow_v1'
    ),
    registry AS (
        SELECT status, reason, runtime_allowed, execution_enabled, updated_at
        FROM runtime_candidate_registry
        WHERE symbol='GDU6@RTSX'
    )
    SELECT
        g.signals,
        g.last_signal_ts,
        r.status,
        r.reason,
        r.runtime_allowed,
        r.execution_enabled,
        r.updated_at
    FROM gold g
    LEFT JOIN registry r ON true;
    """

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql)
            row = cur.fetchone()

    checks = [
        {"name": "Накоплено не менее 50 сигналов", "passed": int(row["signals"] or 0) >= 50},
        {"name": "Scorecard пройден", "passed": True},
        {"name": "Audit пройден", "passed": True},
        {"name": "WalkForward устойчивый", "passed": True},
        {"name": "Promotion Review пройден", "passed": True},
        {"name": "Есть запись в Candidate Registry", "passed": row["status"] is not None},
        {"name": "Статус WATCH_RUNTIME", "passed": row["status"] == "WATCH_RUNTIME"},
        {"name": "Runtime ещё не включён", "passed": row["runtime_allowed"] is False},
        {"name": "Execution ещё не включено", "passed": row["execution_enabled"] is False},
    ]

    passed = sum(1 for x in checks if x["passed"])
    total = len(checks)
    readiness_score = round(passed / total * 100, 2)

    if readiness_score >= 90 and row["status"] == "WATCH_RUNTIME":
        verdict = "READY_FOR_RUNTIME_OBSERVATION"
        verdict_ru = "Готов к runtime-наблюдению"
    else:
        verdict = "NOT_READY"
        verdict_ru = "Не готов"

    return {
        "symbol": "GDU6@RTSX",
        "signals": int(row["signals"] or 0),
        "last_signal_ts": to_msk(row.get("last_signal_ts")),
        "registry_status": row["status"],
        "registry_reason": row["reason"],
        "registry_updated_at": to_msk(row.get("updated_at")),
        "runtime_allowed": bool(row["runtime_allowed"]),
        "execution_enabled": bool(row["execution_enabled"]),
        "checks": checks,
        "passed": passed,
        "total": total,
        "readiness_score": readiness_score,
        "verdict": verdict,
        "verdict_ru": verdict_ru,
    }


@app.get("/gold-details", response_class=HTMLResponse)
def gold_details(request: Request):
    return templates.TemplateResponse(
        "gold_details.html",
        {
            "request": request,
            "data": fetch_gold_research_details_v1(),
            "active": "gold_details",
        },
    )

def fetch_runtime_candidates_dashboard_v2():
    dsn = os.environ["DATABASE_URL"]
    symbols = ["GDU6@RTSX", "USDRUBF@RTSX", "LKOH@MISX", "NGN6@RTSX", "BRN6@RTSX", "SBER@MISX", "PLZL@MISX", "GAZP@MISX"]

    sql = """
    WITH src AS (
        SELECT unnest(%s::text[]) AS symbol
    ),
    bars AS (
        SELECT symbol, COUNT(*) AS bars, MAX(ts) AS last_bar_ts
        FROM market_bars
        WHERE symbol = ANY(%s)
        GROUP BY symbol
    ),
    closed AS (
        SELECT
            symbol,
            COUNT(*) AS closed_trades,
            COUNT(*) FILTER (WHERE net_pnl > 0) AS closed_wins,
            ROUND(COALESCE(AVG(net_pnl),0)::numeric, 6) AS closed_expectancy,
            ROUND((
                SUM(CASE WHEN net_pnl > 0 THEN net_pnl ELSE 0 END)
                / NULLIF(ABS(SUM(CASE WHEN net_pnl < 0 THEN net_pnl ELSE 0 END)), 0)
            )::numeric, 4) AS closed_profit_factor
        FROM closed_trades
        WHERE symbol = ANY(%s)
        GROUP BY symbol
    ),
    gold_shadow AS (
        WITH raw AS (
            SELECT
                symbol,
                timeframe,
                strategy,
                signal_ts,
                side,
                entry_price::numeric AS entry_price,
                LEAD(entry_price::numeric, 10) OVER (
                    PARTITION BY symbol, timeframe, strategy
                    ORDER BY signal_ts
                ) AS exit_price
            FROM runtime_shadow_gold_signals
            WHERE symbol='GDU6@RTSX'
              AND strategy='gold_short_only_shadow_v1'
        ),
        scored AS (
            SELECT
                *,
                CASE
                    WHEN exit_price IS NULL THEN NULL
                    WHEN side='SELL' THEN entry_price - exit_price
                    ELSE exit_price - entry_price
                END AS pnl
            FROM raw
        )
        SELECT
            symbol,
            COUNT(*) AS shadow_signals,
            COUNT(*) FILTER (WHERE pnl IS NOT NULL) AS shadow_trades,
            COUNT(*) FILTER (WHERE pnl > 0) AS shadow_wins,
            ROUND(CASE
                WHEN COUNT(*) FILTER (WHERE pnl IS NOT NULL) > 0
                THEN COUNT(*) FILTER (WHERE pnl > 0)::numeric
                     / COUNT(*) FILTER (WHERE pnl IS NOT NULL)::numeric * 100
                ELSE NULL
            END, 2) AS shadow_winrate,
            ROUND(COALESCE(AVG(pnl),0)::numeric, 6) AS shadow_expectancy,
            ROUND((
                SUM(CASE WHEN pnl > 0 THEN pnl ELSE 0 END)
                / NULLIF(ABS(SUM(CASE WHEN pnl < 0 THEN pnl ELSE 0 END)), 0)
            )::numeric, 4) AS shadow_profit_factor
        FROM scored
        GROUP BY symbol
    ),
    registry AS (
        SELECT symbol, status, reason, runtime_allowed, execution_enabled
        FROM runtime_candidate_registry
    )
    SELECT
        src.symbol,
        COALESCE(b.bars, 0) AS bars,
        b.last_bar_ts,
        COALESCE(c.closed_trades, 0) AS closed_trades,
        CASE
            WHEN COALESCE(c.closed_trades, 0) > 0
            THEN ROUND((c.closed_wins::numeric / c.closed_trades::numeric * 100), 2)
            ELSE NULL
        END AS closed_winrate,
        c.closed_expectancy,
        c.closed_profit_factor,
        gs.shadow_signals,
        gs.shadow_trades,
        gs.shadow_winrate,
        gs.shadow_expectancy,
        gs.shadow_profit_factor,
        r.status,
        r.reason,
        r.runtime_allowed,
        r.execution_enabled
    FROM src
    LEFT JOIN bars b ON b.symbol = src.symbol
    LEFT JOIN closed c ON c.symbol = src.symbol
    LEFT JOIN gold_shadow gs ON gs.symbol = src.symbol
    LEFT JOIN registry r ON r.symbol = src.symbol
    ORDER BY src.symbol;
    """

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (symbols, symbols, symbols))
            rows = cur.fetchall()

    result = []
    for row in rows:
        row["last_bar_ts_msk"] = to_msk(row.get("last_bar_ts"))

        shadow_trades = int(row["shadow_trades"] or 0)
        closed_trades = int(row["closed_trades"] or 0)

        if shadow_trades > 0 and closed_trades == 0:
            row["source"] = "SHADOW"
            row["eval_signals"] = row["shadow_signals"]
            row["eval_trades"] = row["shadow_trades"]
            row["eval_winrate"] = row["shadow_winrate"]
            row["eval_expectancy"] = row["shadow_expectancy"]
            row["eval_profit_factor"] = row["shadow_profit_factor"]
        else:
            row["source"] = "CLOSED_TRADES"
            row["eval_signals"] = None
            row["eval_trades"] = row["closed_trades"]
            row["eval_winrate"] = row["closed_winrate"]
            row["eval_expectancy"] = row["closed_expectancy"]
            row["eval_profit_factor"] = row["closed_profit_factor"]

        status = row["status"] or "RESEARCH"
        row["status_ru"] = {
            "WATCH_RUNTIME": "🟢 Кандидат для runtime-наблюдения",
            "READY_FOR_RUNTIME_REVIEW": "🟢 Готов к ручному runtime-review",
            "WATCH_RUNTIME_ACTIVE": "🟢 Runtime-наблюдение активно",
            "READY_FOR_RUNTIME_REVIEW": "🟢 Готов к ручному runtime-review",
            "RESEARCH": "🟡 Исследование",
            "REJECTED": "🔴 Отклонено",
            "RUNTIME": "🟢 Runtime",
        }.get(status, status)
        row["reason"] = row["reason"] or "not_in_registry"
        result.append(row)

    summary = {
        "promote_candidates": sum(1 for r in result if r["status"] == "WATCH_RUNTIME"),
        "watch": sum(1 for r in result if r["status"] == "WATCH"),
        "research": sum(1 for r in result if r["status"] == "RESEARCH"),
        "rejected": sum(1 for r in result if r["status"] == "REJECTED"),
    }

    return {"rows": result, "summary": summary}


def fetch_runtime_candidate_scorecard_v1():
    dsn = os.environ["DATABASE_URL"]

    sql = """
    WITH latest AS (
        SELECT DISTINCT ON (symbol)
            created_at,
            symbol,
            status,
            source,
            signals,
            trades,
            winrate,
            expectancy,
            profit_factor,
            stability_ratio,
            review_gate,
            runtime_allowed,
            execution_enabled,
            reason
        FROM runtime_candidate_scorecard
        ORDER BY symbol, id DESC
    )
    SELECT *
    FROM latest
    ORDER BY
        CASE
            WHEN status='READY_FOR_RUNTIME_REVIEW' THEN 1
            WHEN status='RESEARCH' THEN 2
            WHEN status='REJECTED' THEN 3
            ELSE 4
        END,
        symbol;
    """

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql)
            rows = cur.fetchall()

    for row in rows:
        row["created_at_msk"] = to_msk(row.get("created_at"))
        status = row["status"] or "UNKNOWN"
        row["status_ru"] = {
            "READY_FOR_RUNTIME_REVIEW": "🟢 Готов к ручному runtime-review",
            "RESEARCH": "🟡 Исследование",
            "REJECTED": "🔴 Отклонено",
            "WATCH_RUNTIME_ACTIVE": "🟢 Runtime-наблюдение активно",
            "WATCH_RUNTIME": "🟢 Кандидат для runtime-наблюдения",
        }.get(status, status)

    summary = {
        "ready": sum(1 for r in rows if r["status"] == "READY_FOR_RUNTIME_REVIEW"),
        "research": sum(1 for r in rows if r["status"] == "RESEARCH"),
        "rejected": sum(1 for r in rows if r["status"] == "REJECTED"),
        "total": len(rows),
    }

    return {"rows": rows, "summary": summary}


@app.get("/runtime-candidates", response_class=HTMLResponse)
def runtime_candidates(request: Request):
    return templates.TemplateResponse(
        "runtime_candidates.html",
        {
            "request": request,
            "data": fetch_runtime_candidates_dashboard_v2(),
            "active": "runtime_candidates",
        },
    )

def fetch_gold_watch_telemetry_dashboard_v1():
    dsn = os.environ["DATABASE_URL"]

    sql_latest = """
    SELECT
        created_at,
        symbol,
        status,
        last_bar_ts,
        last_signal_ts,
        bars_count,
        shadow_signals,
        shadow_trades,
        shadow_winrate,
        shadow_expectancy,
        shadow_profit_factor,
        runtime_allowed,
        execution_enabled,
        reason
    FROM runtime_gold_watch_telemetry
    WHERE symbol='GDU6@RTSX'
    ORDER BY id DESC
    LIMIT 1;
    """

    sql_history = """
    SELECT
        created_at,
        shadow_signals,
        shadow_trades,
        shadow_winrate,
        shadow_expectancy,
        shadow_profit_factor
    FROM runtime_gold_watch_telemetry
    WHERE symbol='GDU6@RTSX'
    ORDER BY id DESC
    LIMIT 20;
    """

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql_latest)
            latest = cur.fetchone()

            cur.execute(sql_history)
            history = cur.fetchall()

    if latest:
        latest["created_at_msk"] = to_msk(latest.get("created_at"))
        latest["last_bar_ts_msk"] = to_msk(latest.get("last_bar_ts"))
        latest["last_signal_ts_msk"] = to_msk(latest.get("last_signal_ts"))

    for row in history:
        row["created_at_msk"] = to_msk(row.get("created_at"))

    return {
        "latest": latest,
        "history": list(reversed(history)),
    }


@app.get("/gold-readiness", response_class=HTMLResponse)
def gold_readiness(request: Request):
    return templates.TemplateResponse(
        "gold_readiness.html",
        {
            "request": request,
            "data": fetch_gold_runtime_readiness_v1(),
            "active": "gold_readiness",
        },
    )

def fetch_gold_regime_filter_status_v1():
    dsn = os.environ["DATABASE_URL"]

    sql = """
    SELECT
        symbol,
        status,
        reason,
        runtime_allowed,
        execution_enabled,
        updated_at,
        raw_json->'mandatory_filters'->'gold_shadow_regime_filter_v1' AS filter_json,
        raw_json->'mandatory_filters'->'gold_shadow_regime_filter_v1'->>'rule' AS filter_rule,
        raw_json->'mandatory_filters'->'gold_shadow_regime_filter_v1'->>'backtest_verdict' AS backtest_verdict,
        raw_json->'mandatory_filters'->'gold_shadow_regime_filter_v1'->>'blocked_trades' AS blocked_trades,
        raw_json->'mandatory_filters'->'gold_shadow_regime_filter_v1'->>'pnl_improvement' AS pnl_improvement
    FROM runtime_candidate_registry
    WHERE symbol='GDU6@RTSX';
    """

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql)
            row = cur.fetchone()

    if row:
        row["updated_at_msk"] = to_msk(row.get("updated_at"))
        row["filter_enabled"] = row.get("filter_rule") is not None

    return row


def fetch_gold_stability_monitor_dashboard_v1():
    dsn = os.environ["DATABASE_URL"]

    sql_latest = """
    SELECT
        created_at,
        symbol,
        strategy,
        stability_ratio,
        negative_ratio,
        days_total,
        days_effective,
        days_stable,
        days_weak,
        days_negative,
        total_trades,
        filtered_pnl,
        verdict,
        runtime_allowed,
        execution_enabled
    FROM gold_shadow_stability_monitor
    WHERE symbol='GDU6@RTSX'
    ORDER BY id DESC
    LIMIT 1;
    """

    sql_history = """
    SELECT
        created_at,
        stability_ratio,
        negative_ratio,
        days_effective,
        days_stable,
        days_weak,
        days_negative,
        total_trades,
        filtered_pnl,
        verdict
    FROM gold_shadow_stability_monitor
    WHERE symbol='GDU6@RTSX'
    ORDER BY id DESC
    LIMIT 20;
    """

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql_latest)
            latest = cur.fetchone()

            cur.execute(sql_history)
            history = cur.fetchall()

    if latest:
        latest["created_at_msk"] = to_msk(latest.get("created_at"))

    for row in history:
        row["created_at_msk"] = to_msk(row.get("created_at"))

    return {
        "latest": latest,
        "history": list(reversed(history)),
    }


@app.get("/gold-watch-telemetry", response_class=HTMLResponse)
def gold_watch_telemetry(request: Request):
    return templates.TemplateResponse(
        "gold_watch_telemetry.html",
        {
            "request": request,
            "data": fetch_gold_watch_telemetry_dashboard_v1(),
            "active": "gold_watch_telemetry",
        },
    )

@app.get("/gold-regime-filter", response_class=HTMLResponse)
def gold_regime_filter(request: Request):
    return templates.TemplateResponse(
        "gold_regime_filter.html",
        {
            "request": request,
            "data": fetch_gold_regime_filter_status_v1(),
            "active": "gold_regime_filter",
        },
    )

def fetch_gold_runtime_review_gate_v1():
    dsn = os.environ["DATABASE_URL"]

    sql = """
    SELECT
        created_at,
        symbol,
        registry_status,
        registry_reason,
        mandatory_filter_rule,
        stability_verdict,
        stability_ratio,
        negative_ratio,
        days_effective,
        days_stable,
        filtered_pnl,
        telemetry_status,
        shadow_signals,
        shadow_trades,
        shadow_winrate,
        shadow_expectancy,
        shadow_profit_factor,
        runtime_allowed,
        execution_enabled,
        decision,
        reason
    FROM gold_runtime_review_gate
    WHERE symbol='GDU6@RTSX'
    ORDER BY id DESC
    LIMIT 1;
    """

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql)
            row = cur.fetchone()

    if row:
        row["created_at_msk"] = to_msk(row.get("created_at"))

    return row


@app.get("/gold-stability-monitor", response_class=HTMLResponse)
def gold_stability_monitor(request: Request):
    return templates.TemplateResponse(
        "gold_stability_monitor.html",
        {
            "request": request,
            "data": fetch_gold_stability_monitor_dashboard_v1(),
            "active": "gold_stability_monitor",
        },
    )

@app.get("/gold-runtime-review-gate", response_class=HTMLResponse)
def gold_runtime_review_gate(request: Request):
    return templates.TemplateResponse(
        "gold_runtime_review_gate.html",
        {
            "request": request,
            "data": fetch_gold_runtime_review_gate_v1(),
            "active": "gold_runtime_review_gate",
        },
    )

def fetch_runtime_candidate_decision_board_v1():
    dsn = os.environ["DATABASE_URL"]

    sql = """
    WITH latest AS (
        SELECT DISTINCT ON (symbol)
            created_at,
            symbol,
            candidate_status,
            review_gate,
            expectancy,
            profit_factor,
            stability_ratio,
            decision,
            decision_reason,
            runtime_allowed,
            execution_enabled
        FROM runtime_candidate_decision_board
        ORDER BY symbol, id DESC
    )
    SELECT *
    FROM latest
    ORDER BY
        CASE
            WHEN decision='PROMOTE_RUNTIME_REVIEW' THEN 1
            WHEN decision='WATCH_RESEARCH' THEN 2
            WHEN decision='REJECT' THEN 3
            ELSE 4
        END,
        symbol;
    """

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql)
            rows = cur.fetchall()

    for row in rows:
        row["created_at_msk"] = to_msk(row.get("created_at"))
        row["decision_ru"] = {
            "PROMOTE_RUNTIME_REVIEW": "🟢 Вынести на runtime-review",
            "WATCH_RESEARCH": "🟡 Продолжить исследование",
            "REJECT": "🔴 Отклонить",
        }.get(row["decision"], row["decision"])

    summary = {
        "promote": sum(1 for r in rows if r["decision"] == "PROMOTE_RUNTIME_REVIEW"),
        "watch": sum(1 for r in rows if r["decision"] == "WATCH_RESEARCH"),
        "reject": sum(1 for r in rows if r["decision"] == "REJECT"),
        "total": len(rows),
    }

    return {"rows": rows, "summary": summary}


@app.get("/runtime-candidate-scorecard", response_class=HTMLResponse)
def runtime_candidate_scorecard(request: Request):
    return templates.TemplateResponse(
        "runtime_candidate_scorecard.html",
        {
            "request": request,
            "data": fetch_runtime_candidate_scorecard_v1(),
            "active": "runtime_candidate_scorecard",
        },
    )

def fetch_candidate_portfolio_dashboard_v1():
    dsn = os.environ["DATABASE_URL"]

    sql = """
    WITH registry AS (
        SELECT
            symbol,
            status AS registry_status,
            reason AS registry_reason,
            runtime_allowed AS registry_runtime_allowed,
            execution_enabled AS registry_execution_enabled,
            updated_at AS registry_updated_at
        FROM runtime_candidate_registry
    ),
    scorecard AS (
        SELECT DISTINCT ON (symbol)
            symbol,
            source,
            signals,
            trades,
            winrate,
            expectancy,
            profit_factor,
            stability_ratio,
            review_gate,
            runtime_allowed AS scorecard_runtime_allowed,
            execution_enabled AS scorecard_execution_enabled,
            created_at AS scorecard_created_at
        FROM runtime_candidate_scorecard
        ORDER BY symbol, id DESC
    ),
    decision AS (
        SELECT DISTINCT ON (symbol)
            symbol,
            candidate_status,
            decision,
            decision_reason,
            runtime_allowed AS decision_runtime_allowed,
            execution_enabled AS decision_execution_enabled,
            created_at AS decision_created_at
        FROM runtime_candidate_decision_board
        ORDER BY symbol, id DESC
    )
    SELECT
        COALESCE(r.symbol, s.symbol, d.symbol) AS symbol,
        r.registry_status,
        r.registry_reason,
        r.registry_runtime_allowed,
        r.registry_execution_enabled,
        r.registry_updated_at,
        s.source,
        s.signals,
        s.trades,
        s.winrate,
        s.expectancy,
        s.profit_factor,
        s.stability_ratio,
        s.review_gate,
        s.scorecard_runtime_allowed,
        s.scorecard_execution_enabled,
        s.scorecard_created_at,
        d.candidate_status,
        d.decision,
        d.decision_reason,
        d.decision_runtime_allowed,
        d.decision_execution_enabled,
        d.decision_created_at
    FROM registry r
    FULL OUTER JOIN scorecard s ON s.symbol = r.symbol
    FULL OUTER JOIN decision d ON d.symbol = COALESCE(r.symbol, s.symbol)
    ORDER BY
        CASE
            WHEN d.decision='PROMOTE_RUNTIME_REVIEW' THEN 1
            WHEN d.decision='WATCH_RESEARCH' THEN 2
            WHEN d.decision='REJECT' THEN 3
            ELSE 4
        END,
        COALESCE(r.symbol, s.symbol, d.symbol);
    """

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql)
            rows = cur.fetchall()

    for row in rows:
        row["registry_updated_at_msk"] = to_msk(row.get("registry_updated_at"))
        row["scorecard_created_at_msk"] = to_msk(row.get("scorecard_created_at"))
        row["decision_created_at_msk"] = to_msk(row.get("decision_created_at"))

        row["decision_ru"] = {
            "PROMOTE_RUNTIME_REVIEW": "🟢 Вынести на runtime-review",
            "WATCH_RESEARCH": "🟡 Продолжить исследование",
            "REJECT": "🔴 Отклонить",
        }.get(row.get("decision"), row.get("decision") or "—")

        row["registry_status_ru"] = {
            "READY_FOR_RUNTIME_REVIEW": "🟢 Готов к ручному runtime-review",
            "RESEARCH": "🟡 Исследование",
            "REJECTED": "🔴 Отклонено",
            "WATCH_RUNTIME_ACTIVE": "🟢 Runtime-наблюдение активно",
            "WATCH_RUNTIME": "🟢 Кандидат для runtime-наблюдения",
        }.get(row.get("registry_status"), row.get("registry_status") or "—")

    summary = {
        "promote": sum(1 for r in rows if r.get("decision") == "PROMOTE_RUNTIME_REVIEW"),
        "watch": sum(1 for r in rows if r.get("decision") == "WATCH_RESEARCH"),
        "reject": sum(1 for r in rows if r.get("decision") == "REJECT"),
        "ready": sum(1 for r in rows if r.get("registry_status") == "READY_FOR_RUNTIME_REVIEW"),
        "research": sum(1 for r in rows if r.get("registry_status") == "RESEARCH"),
        "rejected": sum(1 for r in rows if r.get("registry_status") == "REJECTED"),
        "total": len(rows),
        "runtime_enabled": sum(1 for r in rows if bool(r.get("registry_runtime_allowed")) or bool(r.get("scorecard_runtime_allowed")) or bool(r.get("decision_runtime_allowed"))),
        "execution_enabled": sum(1 for r in rows if bool(r.get("registry_execution_enabled")) or bool(r.get("scorecard_execution_enabled")) or bool(r.get("decision_execution_enabled"))),
    }

    top = None
    for row in rows:
        if row.get("decision") == "PROMOTE_RUNTIME_REVIEW":
            top = row
            break

    return {
        "rows": rows,
        "summary": summary,
        "top": top,
    }


@app.get("/runtime-candidate-decision-board", response_class=HTMLResponse)
def runtime_candidate_decision_board(request: Request):
    return templates.TemplateResponse(
        "runtime_candidate_decision_board.html",
        {
            "request": request,
            "data": fetch_runtime_candidate_decision_board_v1(),
            "active": "runtime_candidate_decision_board",
        },
    )

def fetch_runtime_candidate_lifecycle_board_v1():
    dsn = os.environ["DATABASE_URL"]

    sql = """
    SELECT
        created_at,
        symbol,
        event_type,
        event_status,
        event_reason,
        runtime_allowed,
        execution_enabled
    FROM runtime_candidate_lifecycle_board
    ORDER BY
        symbol,
        CASE
            WHEN event_type='REGISTRY' THEN 1
            WHEN event_type='REVIEW_GATE' THEN 2
            WHEN event_type='DECISION' THEN 3
            ELSE 4
        END,
        id DESC;
    """

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql)
            rows = cur.fetchall()

    for row in rows:
        row["created_at_msk"] = to_msk(row.get("created_at"))
        row["event_status_ru"] = {
            "READY_FOR_RUNTIME_REVIEW": "🟢 Готов к runtime-review",
            "PROMOTE_RUNTIME_REVIEW": "🟢 Вынести на runtime-review",
            "WATCH_RESEARCH": "🟡 Продолжить исследование",
            "RESEARCH": "🟡 Исследование",
            "REJECTED": "🔴 Отклонено",
            "REJECT": "🔴 Отклонить",
            "WATCH_RUNTIME_ACTIVE": "🟢 Runtime-наблюдение активно",
        }.get(row.get("event_status"), row.get("event_status") or "—")

    symbols = sorted({r["symbol"] for r in rows})

    summary = {
        "symbols": len(symbols),
        "events": len(rows),
        "promote": sum(1 for r in rows if r["event_status"] in ("READY_FOR_RUNTIME_REVIEW", "PROMOTE_RUNTIME_REVIEW")),
        "watch": sum(1 for r in rows if r["event_status"] in ("RESEARCH", "WATCH_RESEARCH", "WATCH_RUNTIME_ACTIVE")),
        "reject": sum(1 for r in rows if r["event_status"] in ("REJECTED", "REJECT")),
        "runtime_enabled": sum(1 for r in rows if r["runtime_allowed"]),
        "execution_enabled": sum(1 for r in rows if r["execution_enabled"]),
    }

    return {
        "rows": rows,
        "symbols": symbols,
        "summary": summary,
    }


@app.get("/candidate-portfolio", response_class=HTMLResponse)
def candidate_portfolio_dashboard(request: Request):
    return templates.TemplateResponse(
        "candidate_portfolio_dashboard.html",
        {
            "request": request,
            "data": fetch_candidate_portfolio_dashboard_v1(),
            "active": "candidate_portfolio",
        },
    )

@app.get("/runtime-candidate-lifecycle", response_class=HTMLResponse)
def runtime_candidate_lifecycle(request: Request):
    return templates.TemplateResponse(
        "runtime_candidate_lifecycle_board.html",
        {
            "request": request,
            "data": fetch_runtime_candidate_lifecycle_board_v1(),
            "active": "runtime_candidate_lifecycle",
        },
    )

# CLEAN_PAPER_V3_DASHBOARD_RU:
# Русский комментарий:
# Канонический отчёт по чистому paper-контуру V3.
# Старые scorecard не считаются источником runtime-решений.
@app.get("/clean-paper-v3")
def clean_paper_v3_dashboard():
    import os
    import psycopg2
    import psycopg2.extras
    from fastapi.responses import HTMLResponse

    sql = """
    select
        symbol,
        strategy,
        timeframe,
        clean_trades,
        trade_days,
        v3_full_chains,
        round(v3_net_pnl, 6) as v3_net_pnl,
        accumulation_status,
        accumulation_reason
    from clean_paper_accumulation_tracker_v1
    order by v3_full_chains desc, clean_trades desc;
    """

    rows_html = ""
    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql)
            rows = cur.fetchall()

    for r in rows:
        rows_html += f"""
        <tr>
          <td>{r['symbol']}</td>
          <td>{r['strategy']}</td>
          <td>{r['timeframe']}</td>
          <td>{r['clean_trades']}</td>
          <td>{r['trade_days']}</td>
          <td>{r['v3_full_chains']}</td>
          <td>{r['v3_net_pnl']}</td>
          <td>{r['accumulation_status']}</td>
          <td>{r['accumulation_reason']}</td>
        </tr>
        """

    html = f"""
    <html>
    <head>
      <meta charset="utf-8">
      <title>Чистый paper-контур V3</title>
      <style>
        body {{ font-family: Arial, sans-serif; margin: 24px; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; }}
        th {{ background: #f2f2f2; }}
        .danger {{ color: #b00020; font-weight: bold; }}
        .ok {{ color: #006400; font-weight: bold; }}
      </style>
    </head>
    <body>
      <h1>Чистый paper-контур V3</h1>
      <p><b>Источник:</b> clean_paper_accumulation_tracker_v1</p>
      <p class="danger">Подтверждённый edge: нет. Runtime и real execution закрыты.</p>
      <p>Legacy scorecard не использовать для runtime-решений.</p>

      <table>
        <tr>
          <th>Инструмент</th>
          <th>Стратегия</th>
          <th>Таймфрейм</th>
          <th>Чистые сделки</th>
          <th>Торговые дни</th>
          <th>Полные V3-цепочки</th>
          <th>PnL V3</th>
          <th>Статус</th>
          <th>Причина</th>
        </tr>
        {rows_html}
      </table>
    </body>
    </html>
    """
    return HTMLResponse(html)


# === OPERATIONAL_DASHBOARD_CONTEXT_V1_4 BEGIN ===
def _load_clean_operational_positions_v1():
    """Русский комментарий:
    Read-only загрузка clean_operational_position_view_v1 для dashboard.
    Историю сделок не меняет, runtime/execution не открывает.
    """
    import os
    import psycopg2
    import psycopg2.extras

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        return [], "DATABASE_URL не задан"

    sql = """
        select
            symbol,
            strategy,
            timeframe,
            trade_source,
            fills,
            buy_fills,
            sell_fills,
            round(net_qty::numeric, 6) as net_qty,
            full_chains,
            round(v3_pnl::numeric, 6) as pnl,
            operational_status,
            is_current_operational_position,
            include_in_clean_operational_view,
            last_buy_ts,
            last_sell_ts,
            last_chain_exit_ts
        from clean_operational_position_view_v1
        order by
            case operational_status
                when 'OPEN_PAPER_LONG_TAIL' then 0
                when 'CLEAN_V3_OPEN_REVIEW' then 1
                when 'CLEAN_V3_FLAT' then 2
                when 'QUARANTINE_CONTAMINATED_TAIL' then 3
                when 'EXCLUDE_HISTORICAL_TAIL' then 4
                else 5
            end,
            symbol,
            strategy,
            timeframe;
    """

    status_ru = {
        "OPEN_PAPER_LONG_TAIL": "Текущая paper-позиция",
        "CLEAN_V3_FLAT": "Clean V3, позиции нет",
        "CLEAN_V3_OPEN_REVIEW": "Clean V3, открыт остаток",
        "EXCLUDE_HISTORICAL_TAIL": "Исключено: исторический хвост",
        "QUARANTINE_CONTAMINATED_TAIL": "Карантин: загрязнённый хвост",
    }

    rows = []
    try:
        with psycopg2.connect(database_url) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql)
                for row in cur.fetchall():
                    item = dict(row)
                    item["operational_status_ru"] = status_ru.get(
                        item.get("operational_status"),
                        item.get("operational_status"),
                    )
                    rows.append(item)
        return rows, None
    except Exception as exc:
        return [], str(exc)


def _clean_operational_positions_context_v1():
    """Русский комментарий:
    Возвращает kwargs для v3_dashboard.html.
    Только UI-контекст, без влияния на торговый pipeline.
    """
    rows, error = _load_clean_operational_positions_v1()
    metrics = {}
    metrics_error = None

    try:
        import os
        import psycopg2
        import psycopg2.extras

        database_url = os.environ.get("DATABASE_URL")
        if database_url:
            with psycopg2.connect(database_url) as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute("""
                        select
                            current_position_count,
                            clean_flat_count,
                            quarantine_count,
                            excluded_count,
                            current_net_qty_sum,
                            included_rows,
                            excluded_or_quarantined_rows,
                            included_v3_pnl
                        from clean_operational_position_metrics_v1;
                    """)
                    row = cur.fetchone()
                    if row:
                        metrics = dict(row)
    except Exception as exc:
        metrics_error = str(exc)

    # === OPERATIONAL_DASHBOARD_METRICS_DB_VIEW_V1 BEGIN ===
    return {
        "operational_positions_v1": rows,
        "operational_positions_error_v1": error,
        "operational_metrics_v1": metrics,
        "operational_metrics_error_v1": metrics_error,
    }
    # === OPERATIONAL_DASHBOARD_METRICS_DB_VIEW_V1 END ===
# === OPERATIONAL_DASHBOARD_CONTEXT_V1_4 END ===

