from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from typing import Any

import psycopg2
import psycopg2.extras

from finam_core.recovery.portfolio_rebuilder import PortfolioRebuildResult


@dataclass(frozen=True)
class RecoverySnapshot:
    snapshot_id: str
    aggregate_type: str
    aggregate_id: str
    event_offset: int
    cash_delta: float
    positions: dict[str, Any]
    realized_pnl: float
    source: str


class RecoverySnapshotService:
    """Русский комментарий: сохраняет recovery snapshots для быстрого startup rebuild."""

    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if not self.database_url:
            raise RuntimeError("DATABASE_URL is required for RecoverySnapshotService")

    def _connect(self):
        return psycopg2.connect(self.database_url)

    def ensure_schema(self) -> None:
        with open("sql/20260510_recovery_snapshots.sql", "r", encoding="utf-8") as f:
            sql = f.read()

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)

    @staticmethod
    def build_snapshot_id(
        *,
        aggregate_type: str,
        aggregate_id: str,
        event_offset: int,
        positions: dict[str, Any],
    ) -> str:
        body = json.dumps(
            {
                "aggregate_type": aggregate_type,
                "aggregate_id": aggregate_id,
                "event_offset": int(event_offset),
                "positions": positions,
            },
            sort_keys=True,
            ensure_ascii=False,
            default=str,
        )
        digest = hashlib.sha256(body.encode("utf-8")).hexdigest()[:32]
        return f"snap_{digest}"

    @staticmethod
    def positions_from_rebuild(result: PortfolioRebuildResult) -> dict[str, Any]:
        return {
            symbol: {
                "symbol": pos.symbol,
                "qty": pos.qty,
                "avg_price": pos.avg_price,
                "realized_pnl": pos.realized_pnl,
            }
            for symbol, pos in result.positions.items()
        }

    def save_snapshot(
        self,
        *,
        aggregate_type: str,
        aggregate_id: str,
        event_offset: int,
        cash_delta: float,
        positions: dict[str, Any],
        realized_pnl: float = 0.0,
        source: str = "recovery_snapshot_service",
        snapshot_id: str | None = None,
    ) -> tuple[bool, RecoverySnapshot]:
        """Русский комментарий: idempotent insert recovery snapshot."""
        self.ensure_schema()

        snapshot_id = snapshot_id or self.build_snapshot_id(
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            event_offset=event_offset,
            positions=positions,
        )

        with self._connect() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    INSERT INTO recovery_snapshots (
                        snapshot_id,
                        aggregate_type,
                        aggregate_id,
                        event_offset,
                        cash_delta,
                        positions,
                        realized_pnl,
                        source
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (snapshot_id) DO NOTHING
                    RETURNING
                        snapshot_id,
                        aggregate_type,
                        aggregate_id,
                        event_offset,
                        cash_delta,
                        positions,
                        realized_pnl,
                        source
                    """,
                    (
                        snapshot_id,
                        aggregate_type,
                        aggregate_id,
                        int(event_offset),
                        float(cash_delta),
                        psycopg2.extras.Json(positions),
                        float(realized_pnl),
                        source,
                    ),
                )
                row = cur.fetchone()

                if row:
                    return True, RecoverySnapshot(**dict(row))

                cur.execute(
                    """
                    SELECT
                        snapshot_id,
                        aggregate_type,
                        aggregate_id,
                        event_offset,
                        cash_delta,
                        positions,
                        realized_pnl,
                        source
                    FROM recovery_snapshots
                    WHERE snapshot_id = %s
                    """,
                    (snapshot_id,),
                )
                existing = cur.fetchone()
                if not existing:
                    raise RuntimeError(f"Recovery snapshot duplicate not found: {snapshot_id}")

                return False, RecoverySnapshot(**dict(existing))

    def save_from_rebuild(
        self,
        *,
        aggregate_type: str,
        aggregate_id: str,
        event_offset: int,
        rebuild_result: PortfolioRebuildResult,
        source: str = "portfolio_rebuilder",
    ) -> tuple[bool, RecoverySnapshot]:
        positions = self.positions_from_rebuild(rebuild_result)
        realized_pnl = sum(float(x.get("realized_pnl") or 0.0) for x in positions.values())

        return self.save_snapshot(
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            event_offset=event_offset,
            cash_delta=rebuild_result.cash_delta,
            positions=positions,
            realized_pnl=realized_pnl,
            source=source,
        )

    def latest_snapshot(
        self,
        *,
        aggregate_type: str,
        aggregate_id: str,
    ) -> RecoverySnapshot | None:
        self.ensure_schema()

        with self._connect() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT
                        snapshot_id,
                        aggregate_type,
                        aggregate_id,
                        event_offset,
                        cash_delta,
                        positions,
                        realized_pnl,
                        source
                    FROM recovery_snapshots
                    WHERE aggregate_type = %s
                      AND aggregate_id = %s
                    ORDER BY event_offset DESC, id DESC
                    LIMIT 1
                    """,
                    (aggregate_type, aggregate_id),
                )
                row = cur.fetchone()

        if not row:
            return None

        return RecoverySnapshot(**dict(row))
