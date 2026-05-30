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
                    normalized_fill_id = str(fill_id) if fill_id is not None else f"paper-{datetime.utcnow().timestamp()}"
                    normalized_symbol = str(symbol)
                    normalized_side = str(side).upper()
                    normalized_qty = float(qty)
                    normalized_price = float(price)
                    normalized_commission = float(commission or 0.0)
                    normalized_execution_type = str(kwargs.get("execution_type") or getattr(fill, "execution_type", None) or "paper")

                    # Русский комментарий: сохраняем metadata fill для analytics lineage.
                    extra_payload = kwargs.get("payload")
                    if extra_payload is None:
                        extra_payload = getattr(fill, "payload", None)

                    if not isinstance(extra_payload, dict):
                        extra_payload = {}

                    payload = {
                        **extra_payload,
                        "symbol": normalized_symbol,
                        "side": normalized_side,
                        "qty": normalized_qty,
                        "price": normalized_price,
                        "commission": normalized_commission,
                        "commission_rub": normalized_commission,
                        "currency": getattr(fill, "currency", "RUB") if fill is not None else "RUB",
                        "broker_commission_rub": float(getattr(fill, "broker_commission_rub", 0.0) or 0.0) if fill is not None else 0.0,
                        "exchange_commission_rub": float(getattr(fill, "exchange_commission_rub", 0.0) or 0.0) if fill is not None else 0.0,
                        "tax_rub": float(getattr(fill, "tax_rub", 0.0) or 0.0) if fill is not None else 0.0,
                        "net_cost_rub": float(getattr(fill, "net_cost_rub", normalized_commission) or 0.0) if fill is not None else normalized_commission,
                        "trade_id": normalized_fill_id,
                        "paper_only": normalized_execution_type.lower().startswith("paper") or normalized_execution_type == "paper",
                        "execution_type": normalized_execution_type,
                    }

                    cur.execute(
                        """
                        INSERT INTO fills (
                            fill_id, ts, symbol, side, qty, price, commission, order_id
                        )
                        VALUES (%s, now(), %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (fill_id) DO NOTHING
                        """,
                        (
                            normalized_fill_id,
                            normalized_symbol,
                            normalized_side,
                            normalized_qty,
                            normalized_price,
                            normalized_commission,
                            kwargs.get("order_id") or getattr(fill, "order_id", None),
                        ),
                    )

                    cur.execute(
                        """
                        INSERT INTO trades (
                            symbol, side, qty, price, commission,
                            fill_id, origin, payload, created_at, ts, trade_source
                        )
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s::jsonb,now(),now(),%s)
                        ON CONFLICT (fill_id) DO NOTHING
                        """,
                        (
                            normalized_symbol,
                            normalized_side,
                            normalized_qty,
                            normalized_price,
                            normalized_commission,
                            normalized_fill_id,
                            normalized_execution_type,
                            json.dumps(payload, ensure_ascii=False),
                            normalized_execution_type,
                        ),
                    )
        except Exception as e:
            print(f"POSTGRES LOG FILL FAILED: {e}", flush=True)

    def log_market_tick(self, symbol: str, price: float, volume: float = 0.0) -> None:
        """Русский коммент: запись текущих котировок/тиков в PostgreSQL."""
        if not self.enabled:
            return

        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO market_ticks (symbol, price, volume, ts)
                        VALUES (%s, %s, %s, now())
                        """,
                        (str(symbol), float(price), float(volume or 0.0)),
                    )
        except Exception as exc:
            LOG.warning("POSTGRES LOG MARKET TICK FAILED: %s", exc)

    def log_market_bar(self, symbol, timeframe, ts, open_price, high_price, low_price, close_price, volume=0.0) -> None:
        """Русский коммент: запись свечей в PostgreSQL с защитой от дублей."""
        if not self.enabled:
            return

        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO market_data (
                            symbol, timeframe, open, high, low, close_price, volume, ts
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (symbol, timeframe, ts) DO UPDATE SET
                            open = EXCLUDED.open,
                            high = EXCLUDED.high,
                            low = EXCLUDED.low,
                            close_price = EXCLUDED.close_price,
                            volume = EXCLUDED.volume
                        """,
                        (
                            str(symbol),
                            str(timeframe),
                            float(open_price) if open_price is not None else None,
                            float(high_price) if high_price is not None else None,
                            float(low_price) if low_price is not None else None,
                            float(close_price),
                            float(volume or 0.0),
                            ts,
                        ),
                    )
        except Exception as exc:
            LOG.warning("POSTGRES LOG MARKET BAR FAILED: %s", exc)

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


    def log_execution_event(
        self,
        *,
        event_type: str,
        symbol: str | None = None,
        side: str | None = None,
        qty: float | None = None,
        price: float | None = None,
        status: str | None = None,
        reason: str | None = None,
        order_id: str | None = None,
        raw_json: dict | None = None,
    ) -> None:
        """Русский коммент: единый журнал execution-событий для real/dry-run/rejected/repair."""
        if not self.enabled:
            return

        try:
            payload_json = json.dumps(raw_json or {}, ensure_ascii=False, default=str)
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO execution_events
                            (ts, event_type, symbol, side, qty, price, status, reason, order_id, raw_json)
                        VALUES
                            (now(), %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                        """,
                        (
                            str(event_type),
                            symbol,
                            side,
                            float(qty) if qty is not None else None,
                            float(price) if price is not None else None,
                            status,
                            reason,
                            order_id,
                            payload_json,
                        ),
                    )
        except Exception as exc:
            LOG.warning("POSTGRES LOG EXECUTION EVENT FAILED: %s", exc)


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
