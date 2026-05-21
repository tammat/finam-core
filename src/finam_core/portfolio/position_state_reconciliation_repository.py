from __future__ import annotations

import psycopg

from finam_core.portfolio.position_symbol_normalizer import normalize_position_symbol
from finam_core.portfolio.position_display_name import resolve_position_display_name
from finam_core.portfolio.position_state_reconciliation import (
    PositionStateInput,
    PositionStateReconciliationDecision,
    reconcile_position_state,
)


class PositionStateReconciliationRepository:
    """
    Русский комментарий:
    Read-only repository для сверки broker/local/lifecycle/managed positions.
    """

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def migrate(self) -> None:
        sql = """
        CREATE TABLE IF NOT EXISTS position_state_reconciliation_events (
            id BIGSERIAL PRIMARY KEY,
            symbol TEXT NOT NULL,
            display_name TEXT NOT NULL DEFAULT '',
            broker_qty NUMERIC NOT NULL,
            local_qty NUMERIC NOT NULL,
            lifecycle_qty NUMERIC NOT NULL,
            managed_qty NUMERIC NOT NULL,
            status TEXT NOT NULL,
            severity TEXT NOT NULL,
            reason TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE INDEX IF NOT EXISTS idx_position_state_reconciliation_created_at
        ON position_state_reconciliation_events(created_at DESC);

        CREATE INDEX IF NOT EXISTS idx_position_state_reconciliation_symbol
        ON position_state_reconciliation_events(symbol, created_at DESC);

        CREATE INDEX IF NOT EXISTS idx_position_state_reconciliation_status
        ON position_state_reconciliation_events(status, severity);
        """

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()

    def build_inputs(self) -> list[PositionStateInput]:
        broker = self._broker_positions()
        local = self._local_positions()
        lifecycle = self._lifecycle_positions()
        managed = self._managed_positions()

        local_available = bool(local)

        symbols = sorted(
            set(broker)
            | set(local)
            | set(lifecycle)
            | set(managed)
        )

        return [
            PositionStateInput(
                symbol=symbol,
                broker_qty=broker.get(symbol, 0.0),
                # Русский комментарий:
                # Если таблица positions пустая, не считаем local state источником истины.
                # В этом случае local_qty нейтрализуем broker_qty, чтобы не получать ложный CRITICAL.
                local_qty=local.get(symbol, broker.get(symbol, 0.0)) if not local_available else local.get(symbol, 0.0),
                lifecycle_qty=lifecycle.get(symbol, 0.0),
                managed_qty=managed.get(symbol, 0.0),
            )
            for symbol in symbols
        ]

    def build_decisions(self) -> list[PositionStateReconciliationDecision]:
        decisions = []
        for item in self.build_inputs():
            decision = reconcile_position_state(item)
            decisions.append(
                PositionStateReconciliationDecision(
                    symbol=decision.symbol,
                    display_name=resolve_position_display_name(decision.symbol),
                    broker_qty=decision.broker_qty,
                    local_qty=decision.local_qty,
                    lifecycle_qty=decision.lifecycle_qty,
                    managed_qty=decision.managed_qty,
                    status=decision.status,
                    severity=decision.severity,
                    reason=decision.reason,
                )
            )
        return decisions

    def save(self, decisions: list[PositionStateReconciliationDecision]) -> None:
        sql = """
        INSERT INTO position_state_reconciliation_events (
            symbol,
            display_name,
            broker_qty,
            local_qty,
            lifecycle_qty,
            managed_qty,
            status,
            severity,
            reason
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                for item in decisions:
                    cur.execute(
                        sql,
                        (
                            item.symbol,
                            item.display_name,
                            item.broker_qty,
                            item.local_qty,
                            item.lifecycle_qty,
                            item.managed_qty,
                            item.status,
                            item.severity,
                            item.reason,
                        ),
                    )
            conn.commit()

    def _broker_positions(self) -> dict[str, float]:
        sql = """
        SELECT DISTINCT ON (symbol)
            symbol,
            COALESCE(qty, 0)
        FROM real_position_snapshots
        WHERE symbol IS NOT NULL
          AND symbol <> ''
        ORDER BY symbol, ts DESC, id DESC
        """
        return self._load_symbol_qty(sql)

    def _local_positions(self) -> dict[str, float]:
        sql = """
        SELECT symbol, COALESCE(qty, 0)
        FROM positions
        WHERE symbol IS NOT NULL
          AND symbol <> ''
        """
        return self._load_symbol_qty(sql)

    def _lifecycle_positions(self) -> dict[str, float]:
        sql = """
        SELECT symbol, COALESCE(remaining_qty, 0)
        FROM position_lifecycle_state
        WHERE symbol IS NOT NULL
          AND symbol <> ''
        """
        return self._load_symbol_qty(sql)

    def _managed_positions(self) -> dict[str, float]:
        sql = """
        SELECT
            symbol,
            CASE
                WHEN UPPER(COALESCE(side, '')) IN ('SELL', 'SHORT')
                THEN -ABS(COALESCE(qty, 0))
                ELSE ABS(COALESCE(qty, 0))
            END AS qty
        FROM managed_positions
        WHERE symbol IS NOT NULL
          AND symbol <> ''
        """
        return self._load_symbol_qty(sql)

    def _load_symbol_qty(self, sql: str) -> dict[str, float]:
        result: dict[str, float] = {}

        try:
            with psycopg.connect(self.database_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(sql)
                    for symbol, qty in cur.fetchall():
                        normalized = normalize_position_symbol(str(symbol))
                        result[normalized] = result.get(normalized, 0.0) + float(qty or 0.0)
        except Exception:
            return {}

        return result
