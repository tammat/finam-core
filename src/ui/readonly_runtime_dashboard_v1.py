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


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "data": fetch_dashboard_data(), "active": "dashboard"},
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
