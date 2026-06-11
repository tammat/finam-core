#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

app = FastAPI(title="Панель Finam_Core")
templates = Jinja2Templates(directory="src/ui/templates")

def fetch_dashboard():
    dsn = os.environ["DATABASE_URL"]
    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    COUNT(*) AS signals,
                    MAX(signal_ts) AS last_signal_ts
                FROM runtime_shadow_gold_signals
                WHERE symbol='GDU6@RTSX'
                  AND strategy='gold_short_only_shadow_v1';
            """)
            gold = cur.fetchone()

            cur.execute("""
                SELECT
                    candidate,
                    decision,
                    runtime_allow,
                    shadow_allow,
                    watch_allow,
                    reason,
                    created_at
                FROM runtime_governance_shadow_accumulation_v1
                ORDER BY created_at DESC
                LIMIT 5;
            """)
            governance = cur.fetchall()

    gold_signals = int(gold["signals"] or 0)
    target = 50

    return {
        "system_status": "Работает",
        "mode": "Research / Shadow",
        "execution": "Отключено",
        "gold_signals": gold_signals,
        "gold_target": target,
        "gold_remaining": max(0, target - gold_signals),
        "gold_last_signal_ts": gold["last_signal_ts"],
        "governance": governance,
        "instruments": [
            {"name": "GOLD", "status": "Накопление статистики"},
            {"name": "BR", "status": "Только наблюдение"},
            {"name": "NG", "status": "Отклонён"},
            {"name": "USD", "status": "Наблюдение"},
            {"name": "LKOH", "status": "Наблюдение"},
        ],
    }

@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse(
        "readonly_runtime_dashboard_v1.html",
        {"request": request, "data": fetch_dashboard()},
    )
