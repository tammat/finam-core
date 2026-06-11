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
                SELECT *
                FROM runtime_edge_validation_scorecard_v2
                ORDER BY strategy;
            """)
            scorecard = cur.fetchall()

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
