from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable, Mapping, Protocol

from core.decision_funnel import SignalDecisionEvent


class CursorProtocol(Protocol):
    def execute(
        self,
        query: str,
        params: tuple[Any, ...] | None = None,
    ) -> None:
        ...

    def executemany(
        self,
        query: str,
        params: Iterable[tuple[Any, ...]],
    ) -> None:
        ...

    def fetchall(self) -> list[Mapping[str, Any]]:
        ...


class ConnectionProtocol(Protocol):
    def cursor(self) -> CursorProtocol:
        ...

    def commit(self) -> None:
        ...

    def rollback(self) -> None:
        ...


@dataclass(frozen=True, slots=True)
class FunnelSummaryRow:
    stage: str
    outcome: str
    reason_code: str
    event_count: int
    signal_count: int


class DecisionFunnelRepository:
    """PostgreSQL repository для событий Decision Funnel."""

    INSERT_SQL = """
        INSERT INTO analytics.signal_decision_funnel_v1 (
            event_id,
            signal_id,
            symbol,
            strategy,
            timeframe,
            direction,
            stage,
            outcome,
            reason_code,
            attempt_no,
            source,
            context,
            occurred_at
        )
        VALUES (
            %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s::jsonb, %s
        )
        ON CONFLICT (signal_id, stage, attempt_no)
        DO UPDATE SET
            outcome = EXCLUDED.outcome,
            reason_code = EXCLUDED.reason_code,
            source = EXCLUDED.source,
            context = EXCLUDED.context,
            occurred_at = EXCLUDED.occurred_at,
            updated_at = now()
    """

    SUMMARY_SQL = """
        SELECT
            stage,
            outcome,
            reason_code,
            COUNT(*)::bigint AS event_count,
            COUNT(DISTINCT signal_id)::bigint AS signal_count
        FROM analytics.signal_decision_funnel_v1
        WHERE occurred_at >= %s
          AND (%s IS NULL OR symbol = %s)
          AND (%s IS NULL OR strategy = %s)
        GROUP BY stage, outcome, reason_code
        ORDER BY stage, outcome, event_count DESC
    """

    def __init__(self, connection: ConnectionProtocol) -> None:
        self._connection = connection

    @staticmethod
    def _params(event: SignalDecisionEvent) -> tuple[Any, ...]:
        return (
            str(event.event_id),
            event.signal_id,
            event.symbol,
            event.strategy,
            event.timeframe,
            event.direction,
            event.stage.value,
            event.outcome.value,
            event.reason.value,
            event.attempt_no,
            event.source,
            json.dumps(
                dict(event.context),
                ensure_ascii=False,
                separators=(",", ":"),
                default=str,
            ),
            event.occurred_at,
        )

    def record(self, event: SignalDecisionEvent) -> None:
        cursor = self._connection.cursor()

        try:
            cursor.execute(
                self.INSERT_SQL,
                self._params(event),
            )
            self._connection.commit()
        except Exception:
            self._connection.rollback()
            raise

    def record_many(
        self,
        events: Iterable[SignalDecisionEvent],
    ) -> int:
        params = [self._params(event) for event in events]

        if not params:
            return 0

        cursor = self._connection.cursor()

        try:
            cursor.executemany(self.INSERT_SQL, params)
            self._connection.commit()
        except Exception:
            self._connection.rollback()
            raise

        return len(params)

    def summary(
        self,
        *,
        since: datetime,
        symbol: str | None = None,
        strategy: str | None = None,
    ) -> tuple[FunnelSummaryRow, ...]:
        cursor = self._connection.cursor()
        cursor.execute(
            self.SUMMARY_SQL,
            (
                since,
                symbol,
                symbol,
                strategy,
                strategy,
            ),
        )

        rows = cursor.fetchall()

        return tuple(
            FunnelSummaryRow(
                stage=str(row["stage"]),
                outcome=str(row["outcome"]),
                reason_code=str(row["reason_code"]),
                event_count=int(row["event_count"]),
                signal_count=int(row["signal_count"]),
            )
            for row in rows
        )
