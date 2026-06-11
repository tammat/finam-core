#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess

import psycopg2
import psycopg2.extras
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

app = FastAPI(title="Панель Finam_Core")
templates = Jinja2Templates(directory="src/ui/templates")


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

    gold_count = int(gold["signals"] or 0)
    target = 50

    return {
        "system_status": "Работает",
        "mode": "Research / Shadow",
        "execution": "Отключено",
        "gold_signals": gold_count,
        "gold_target": target,
        "gold_remaining": max(0, target - gold_count),
        "gold_last_signal_ts": gold["last_signal_ts"],
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
          AND source='closed_trade_engine_v1_1'
        GROUP BY symbol
    ),
    gold AS (
        SELECT COUNT(*) AS gold_shadow_signals
        FROM runtime_shadow_gold_signals
        WHERE symbol='GDU6@RTSX'
          AND strategy='gold_short_only_shadow_v1'
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
            WHEN src.symbol='GDU6@RTSX' THEN 'SHADOW'
            WHEN src.symbol IN ('BRN6@RTSX','NGN6@RTSX') AND COALESCE(c.expectancy,0) < 0 THEN 'REJECT'
            WHEN src.symbol IN ('USDRUBF@RTSX','LKOH@MISX') THEN 'WATCH'
            WHEN COALESCE(b.bars,0)=0 THEN 'NO_DATA'
            WHEN b.last_bar_ts < now() - interval '7 days' THEN 'STALE'
            ELSE 'WATCH'
        END AS status,
        (SELECT gold_shadow_signals FROM gold) AS gold_shadow_signals
    FROM src
    LEFT JOIN bars b ON b.symbol = src.symbol
    LEFT JOIN closed c ON c.symbol = src.symbol
    ORDER BY src.symbol;
    """

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (symbols, symbols, symbols))
            return cur.fetchall()


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
        "gold.html",
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
