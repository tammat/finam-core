# -*- coding: utf-8 -*-
"""
PostgresLogger — запись торговых событий в PostgreSQL.
Русский коммент: ошибки логирования не должны ломать торговый pipeline.
"""

from __future__ import annotations

import os
import json
import logging
from dataclasses import asdict, is_dataclass
from datetime import datetime

import psycopg2

LOG = logging.getLogger(__name__)


class PostgresLogger:
    def __init__(self) -> None:
        # Русский коммент: logger использует DATABASE_URL либо собирает DSN из DB_* переменных.
        self.database_url = os.getenv("DATABASE_URL", "").strip()
        if not self.database_url:
            db_host = os.getenv("DB_HOST", "127.0.0.1")
            db_port = os.getenv("DB_PORT", "5432")
            db_name = os.getenv("DB_NAME", "finam")
            db_user = os.getenv("DB_USER", "finam")
            db_password = os.getenv("DB_PASSWORD", "finam")
            self.database_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        self.enabled = bool(self.database_url)

    def _connect(self):
        return psycopg2.connect(self.database_url)

    def _payload(self, obj):
        try:
            if is_dataclass(obj):
                data = asdict(obj)
            elif isinstance(obj, dict):
                data = dict(obj)
            else:
                data = dict(getattr(obj, "__dict__", {}))

            for k, v in list(data.items()):
                if isinstance(v, datetime):
                    data[k] = v.isoformat()

            return json.dumps(data, ensure_ascii=False)
        except Exception:
            return json.dumps({"raw": str(obj)}, ensure_ascii=False)

    def log_fill(self, *args, **kwargs) -> None:
        """
        Русский коммент: логирование fill в PostgreSQL.
        Поддерживает:
        1) log_fill(fill_object)
        2) log_fill(symbol=..., side=..., qty=..., price=..., trade_id=..., execution_type=...)
        """
        if not self.enabled:
            return

        fill = args[0] if args else None

        symbol = kwargs.get("symbol") or getattr(fill, "symbol", None)
        side = kwargs.get("side") or getattr(fill, "side", None)

        qty = kwargs.get("qty")
        if qty is None:
            qty = getattr(fill, "qty", None)

        price = kwargs.get("price")
        if price is None:
            price = getattr(fill, "price", None)

        commission = kwargs.get("commission")
        if commission is None:
            commission = getattr(fill, "commission", 0.0)

        fill_id = (
            kwargs.get("fill_id")
            or kwargs.get("trade_id")
            or getattr(fill, "fill_id", None)
            or getattr(fill, "trade_id", None)
        )

        if symbol is None or side is None or qty is None or price is None:
            return

        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO fills (
                            fill_id, ts, symbol, side, qty, price, commission, order_id
                        )
                        VALUES (%s, now(), %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (fill_id) DO NOTHING
                        """,
                        (
                            str(fill_id) if fill_id is not None else f"paper-{datetime.utcnow().timestamp()}",
                            str(symbol),
                            str(side).upper(),
                            float(qty),
                            float(price),
                            float(commission or 0.0),
                            kwargs.get("order_id") or getattr(fill, "order_id", None),
                        ),
                    )
        except Exception as e:
            print(f"POSTGRES LOG FILL FAILED: {e}", flush=True)

    def log_signal(self, symbol=None, strategy=None, side=None, qty=None, status="generated", payload=None) -> None:
        """Русский коммент: логирование всех сигналов стратегии/фильтра/риска, включая отклонённые."""
        if not self.enabled:
            return

        try:
            payload_json = json.dumps(payload or {}, ensure_ascii=False, default=str)
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO signals
                            (symbol, strategy, side, qty, status, payload)
                        VALUES
                            (%s, %s, %s, %s, %s, %s::jsonb)
                        """,
                        (
                            symbol,
                            strategy,
                            side,
                            float(qty) if qty is not None else None,
                            status,
                            payload_json,
                        ),
                    )
        except Exception as exc:
            LOG.warning("POSTGRES LOG SIGNAL FAILED: %s", exc)

    def log_risk_event(self, symbol=None, event="risk_event", decision=None, payload=None) -> None:
        """Русский коммент: логирование решений RiskEngine/FilterEngine без остановки pipeline."""
        if not self.enabled:
            return

        try:
            payload_json = json.dumps(payload or {}, ensure_ascii=False, default=str)
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO risk_events
                            (symbol, event, decision, payload)
                        VALUES
                            (%s, %s, %s, %s::jsonb)
                        """,
                        (
                            symbol,
                            event,
                            decision,
                            payload_json,
                        ),
                    )
        except Exception as exc:
            LOG.warning("POSTGRES LOG RISK EVENT FAILED: %s", exc)
