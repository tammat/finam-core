from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Callable, Mapping, Protocol, Sequence


STAGE_ORDER: tuple[str, ...] = (
    "MARKET_DATA",
    "STRATEGY",
    "REGIME",
    "EDGE",
    "RISK",
    "PORTFOLIO",
    "RUNTIME",
    "EXECUTION",
    "BROKER",
    "FILL",
)

OUTCOMES: tuple[str, ...] = (
    "PASS",
    "REJECT",
    "ERROR",
    "SKIP",
)


class CursorProtocol(Protocol):
    def execute(
        self,
        query: str,
        params: Sequence[Any] | None = None,
    ) -> None:
        ...

    def fetchone(self) -> Mapping[str, Any] | None:
        ...

    def fetchall(self) -> list[Mapping[str, Any]]:
        ...


class ConnectionProtocol(Protocol):
    def cursor(self) -> CursorProtocol:
        ...

    def close(self) -> None:
        ...


ConnectionFactory = Callable[[], ConnectionProtocol]


@dataclass(frozen=True, slots=True)
class DecisionFunnelReadModelFilter:
    since: datetime
    until: datetime
    symbol: str | None = None
    strategy: str | None = None
    timeframe: str | None = None
    recent_limit: int = 50
    reason_limit: int = 20
    dimension_limit: int = 100

    def __post_init__(self) -> None:
        if self.since.tzinfo is None:
            raise ValueError("since must be timezone-aware")

        if self.until.tzinfo is None:
            raise ValueError("until must be timezone-aware")

        if self.since >= self.until:
            raise ValueError("since must be earlier than until")

        if not 1 <= self.recent_limit <= 500:
            raise ValueError(
                "recent_limit must be between 1 and 500"
            )

        if not 1 <= self.reason_limit <= 100:
            raise ValueError(
                "reason_limit must be between 1 and 100"
            )

        if not 1 <= self.dimension_limit <= 500:
            raise ValueError(
                "dimension_limit must be between 1 and 500"
            )

    @classmethod
    def last_hours(
        cls,
        hours: int = 24,
        *,
        now: datetime | None = None,
        symbol: str | None = None,
        strategy: str | None = None,
        timeframe: str | None = None,
        recent_limit: int = 50,
        reason_limit: int = 20,
        dimension_limit: int = 100,
    ) -> DecisionFunnelReadModelFilter:
        if hours < 1 or hours > 24 * 365:
            raise ValueError(
                "hours must be between 1 and 8760"
            )

        current = now or datetime.now(timezone.utc)

        if current.tzinfo is None:
            raise ValueError("now must be timezone-aware")

        return cls(
            since=current - timedelta(hours=hours),
            until=current,
            symbol=symbol,
            strategy=strategy,
            timeframe=timeframe,
            recent_limit=recent_limit,
            reason_limit=reason_limit,
            dimension_limit=dimension_limit,
        )


class DecisionFunnelReadModelBuilder:
    """
    Read-only агрегатор Decision Funnel.

    Не выполняет INSERT, UPDATE, DELETE, DDL, COMMIT
    и не изменяет runtime/execution.
    """

    SUMMARY_SQL = """
        SELECT
            COUNT(*)::bigint AS event_count,
            COUNT(DISTINCT signal_id)::bigint AS signal_count,
            COUNT(DISTINCT symbol)::bigint AS symbol_count,
            COUNT(DISTINCT strategy)::bigint AS strategy_count,
            MIN(occurred_at) AS first_event_at,
            MAX(occurred_at) AS last_event_at,
            COUNT(*) FILTER (
                WHERE outcome = 'PASS'
            )::bigint AS pass_events,
            COUNT(*) FILTER (
                WHERE outcome = 'REJECT'
            )::bigint AS reject_events,
            COUNT(*) FILTER (
                WHERE outcome = 'ERROR'
            )::bigint AS error_events,
            COUNT(*) FILTER (
                WHERE outcome = 'SKIP'
            )::bigint AS skip_events
        FROM analytics.signal_decision_funnel_v1
        WHERE occurred_at >= %s
          AND occurred_at < %s
          AND (%s IS NULL OR symbol = %s)
          AND (%s IS NULL OR strategy = %s)
          AND (%s IS NULL OR timeframe = %s)
    """

    STAGE_SQL = """
        SELECT
            stage,
            COUNT(*)::bigint AS event_count,
            COUNT(DISTINCT signal_id)::bigint AS signal_count,
            COUNT(DISTINCT signal_id) FILTER (
                WHERE outcome = 'PASS'
            )::bigint AS passed_signals,
            COUNT(DISTINCT signal_id) FILTER (
                WHERE outcome = 'REJECT'
            )::bigint AS rejected_signals,
            COUNT(DISTINCT signal_id) FILTER (
                WHERE outcome = 'ERROR'
            )::bigint AS error_signals,
            COUNT(DISTINCT signal_id) FILTER (
                WHERE outcome = 'SKIP'
            )::bigint AS skipped_signals
        FROM analytics.signal_decision_funnel_v1
        WHERE occurred_at >= %s
          AND occurred_at < %s
          AND (%s IS NULL OR symbol = %s)
          AND (%s IS NULL OR strategy = %s)
          AND (%s IS NULL OR timeframe = %s)
        GROUP BY stage
    """

    REASONS_SQL = """
        SELECT
            stage,
            reason_code,
            COUNT(*)::bigint AS event_count,
            COUNT(DISTINCT signal_id)::bigint AS signal_count,
            MAX(occurred_at) AS last_seen_at
        FROM analytics.signal_decision_funnel_v1
        WHERE occurred_at >= %s
          AND occurred_at < %s
          AND outcome = 'REJECT'
          AND (%s IS NULL OR symbol = %s)
          AND (%s IS NULL OR strategy = %s)
          AND (%s IS NULL OR timeframe = %s)
        GROUP BY stage, reason_code
        ORDER BY signal_count DESC, event_count DESC, stage, reason_code
        LIMIT %s
    """

    DIMENSIONS_SQL = """
        SELECT
            symbol,
            strategy,
            timeframe,
            COUNT(*)::bigint AS event_count,
            COUNT(DISTINCT signal_id)::bigint AS signal_count,
            COUNT(DISTINCT signal_id) FILTER (
                WHERE outcome = 'REJECT'
            )::bigint AS rejected_signals,
            COUNT(DISTINCT signal_id) FILTER (
                WHERE stage = 'FILL'
                  AND outcome = 'PASS'
            )::bigint AS filled_signals,
            MAX(occurred_at) AS last_event_at
        FROM analytics.signal_decision_funnel_v1
        WHERE occurred_at >= %s
          AND occurred_at < %s
          AND (%s IS NULL OR symbol = %s)
          AND (%s IS NULL OR strategy = %s)
          AND (%s IS NULL OR timeframe = %s)
        GROUP BY symbol, strategy, timeframe
        ORDER BY signal_count DESC, event_count DESC
        LIMIT %s
    """

    RECENT_SQL = """
        SELECT
            event_id::text AS event_id,
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
        FROM analytics.signal_decision_funnel_v1
        WHERE occurred_at >= %s
          AND occurred_at < %s
          AND (%s IS NULL OR symbol = %s)
          AND (%s IS NULL OR strategy = %s)
          AND (%s IS NULL OR timeframe = %s)
        ORDER BY occurred_at DESC, event_id DESC
        LIMIT %s
    """

    def __init__(
        self,
        connection_factory: ConnectionFactory,
    ) -> None:
        self._connection_factory = connection_factory

    @staticmethod
    def _base_params(
        filters: DecisionFunnelReadModelFilter,
    ) -> tuple[Any, ...]:
        return (
            filters.since,
            filters.until,
            filters.symbol,
            filters.symbol,
            filters.strategy,
            filters.strategy,
            filters.timeframe,
            filters.timeframe,
        )

    @staticmethod
    def _integer(
        row: Mapping[str, Any],
        key: str,
    ) -> int:
        return int(row.get(key) or 0)

    @staticmethod
    def _iso(value: Any) -> str | None:
        if value is None:
            return None

        if isinstance(value, datetime):
            return value.isoformat()

        return str(value)

    @staticmethod
    def _ratio(
        numerator: int,
        denominator: int,
    ) -> str | None:
        if denominator <= 0:
            return None

        value = (
            Decimal(numerator)
            / Decimal(denominator)
        ).quantize(Decimal("0.0001"))

        return format(value, "f")

    def build(
        self,
        filters: DecisionFunnelReadModelFilter,
    ) -> dict[str, Any]:
        connection = self._connection_factory()

        try:
            cursor = connection.cursor()
            params = self._base_params(filters)

            cursor.execute(self.SUMMARY_SQL, params)
            summary_raw = cursor.fetchone() or {}

            cursor.execute(self.STAGE_SQL, params)
            stage_rows = cursor.fetchall()

            cursor.execute(
                self.REASONS_SQL,
                (*params, filters.reason_limit),
            )
            reason_rows = cursor.fetchall()

            cursor.execute(
                self.DIMENSIONS_SQL,
                (*params, filters.dimension_limit),
            )
            dimension_rows = cursor.fetchall()

            cursor.execute(
                self.RECENT_SQL,
                (*params, filters.recent_limit),
            )
            recent_rows = cursor.fetchall()
        finally:
            connection.close()

        event_count = self._integer(
            summary_raw,
            "event_count",
        )
        signal_count = self._integer(
            summary_raw,
            "signal_count",
        )

        stage_by_name = {
            str(row.get("stage")): row
            for row in stage_rows
            if row.get("stage") is not None
        }

        stage_funnel: list[dict[str, Any]] = []
        previous_signal_count: int | None = None
        previous_observed_stage: str | None = None

        for position, stage in enumerate(
            STAGE_ORDER,
            start=1,
        ):
            raw = stage_by_name.get(stage, {})

            current_signal_count = self._integer(
                raw,
                "signal_count",
            )
            passed_signals = self._integer(
                raw,
                "passed_signals",
            )
            rejected_signals = self._integer(
                raw,
                "rejected_signals",
            )
            error_signals = self._integer(
                raw,
                "error_signals",
            )
            skipped_signals = self._integer(
                raw,
                "skipped_signals",
            )

            stage_funnel.append(
                {
                    "position": position,
                    "stage": stage,
                    "event_count": self._integer(
                        raw,
                        "event_count",
                    ),
                    "signal_count": current_signal_count,
                    "passed_signals": passed_signals,
                    "rejected_signals": rejected_signals,
                    "error_signals": error_signals,
                    "skipped_signals": skipped_signals,
                    "pass_rate": self._ratio(
                        passed_signals,
                        current_signal_count,
                    ),
                    "rejection_rate": self._ratio(
                        rejected_signals,
                        current_signal_count,
                    ),
                    "previous_observed_stage": (
                        previous_observed_stage
                    ),
                    "conversion_from_previous_stage": (
                        None
                        if (
                            previous_signal_count is None
                            or current_signal_count == 0
                        )
                        else self._ratio(
                            current_signal_count,
                            previous_signal_count,
                        )
                    ),
                }
            )

            # До подключения всех runtime-стадий таблица будет разреженной.
            # Пустая стадия не должна обнулять базу для следующей
            # наблюдаемой конверсии.
            if current_signal_count > 0:
                previous_signal_count = current_signal_count
                previous_observed_stage = stage

        summary = {
            "event_count": event_count,
            "signal_count": signal_count,
            "symbol_count": self._integer(
                summary_raw,
                "symbol_count",
            ),
            "strategy_count": self._integer(
                summary_raw,
                "strategy_count",
            ),
            "pass_events": self._integer(
                summary_raw,
                "pass_events",
            ),
            "reject_events": self._integer(
                summary_raw,
                "reject_events",
            ),
            "error_events": self._integer(
                summary_raw,
                "error_events",
            ),
            "skip_events": self._integer(
                summary_raw,
                "skip_events",
            ),
            "first_event_at": self._iso(
                summary_raw.get("first_event_at")
            ),
            "last_event_at": self._iso(
                summary_raw.get("last_event_at")
            ),
            "rejection_rate": self._ratio(
                self._integer(
                    summary_raw,
                    "reject_events",
                ),
                event_count,
            ),
        }

        return {
            "status": (
                "EMPTY"
                if event_count == 0
                else "READY"
            ),
            "read_only": True,
            "window": {
                "since": filters.since.isoformat(),
                "until": filters.until.isoformat(),
            },
            "filters": {
                "symbol": filters.symbol,
                "strategy": filters.strategy,
                "timeframe": filters.timeframe,
            },
            "summary": summary,
            "stage_funnel": stage_funnel,
            "top_rejection_reasons": [
                {
                    "stage": str(row.get("stage")),
                    "reason_code": str(
                        row.get("reason_code")
                    ),
                    "event_count": self._integer(
                        row,
                        "event_count",
                    ),
                    "signal_count": self._integer(
                        row,
                        "signal_count",
                    ),
                    "last_seen_at": self._iso(
                        row.get("last_seen_at")
                    ),
                }
                for row in reason_rows
            ],
            "dimensions": [
                {
                    "symbol": str(row.get("symbol")),
                    "strategy": str(row.get("strategy")),
                    "timeframe": str(row.get("timeframe")),
                    "event_count": self._integer(
                        row,
                        "event_count",
                    ),
                    "signal_count": self._integer(
                        row,
                        "signal_count",
                    ),
                    "rejected_signals": self._integer(
                        row,
                        "rejected_signals",
                    ),
                    "filled_signals": self._integer(
                        row,
                        "filled_signals",
                    ),
                    "last_event_at": self._iso(
                        row.get("last_event_at")
                    ),
                }
                for row in dimension_rows
            ],
            "recent_events": [
                {
                    "event_id": str(row.get("event_id")),
                    "signal_id": str(row.get("signal_id")),
                    "symbol": str(row.get("symbol")),
                    "strategy": str(row.get("strategy")),
                    "timeframe": str(row.get("timeframe")),
                    "direction": row.get("direction"),
                    "stage": str(row.get("stage")),
                    "outcome": str(row.get("outcome")),
                    "reason_code": str(
                        row.get("reason_code")
                    ),
                    "attempt_no": self._integer(
                        row,
                        "attempt_no",
                    ),
                    "source": str(row.get("source")),
                    "context": (
                        dict(row.get("context"))
                        if isinstance(
                            row.get("context"),
                            Mapping,
                        )
                        else {}
                    ),
                    "occurred_at": self._iso(
                        row.get("occurred_at")
                    ),
                }
                for row in recent_rows
            ],
            "metadata": {
                "source": (
                    "analytics."
                    "signal_decision_funnel_v1"
                ),
                "logic": (
                    "DECISION_FUNNEL_READ_MODEL_V1"
                ),
                "stage_order": list(STAGE_ORDER),
                "outcomes": list(OUTCOMES),
                "ui_direct_sql": 0,
                "write_actions_allowed": 0,
                "runtime_instrumentation": 0,
                "execution_actions_allowed": 0,
            },
        }


def build_decision_funnel_read_model(
    connection_factory: ConnectionFactory,
    *,
    hours: int = 24,
    now: datetime | None = None,
    symbol: str | None = None,
    strategy: str | None = None,
    timeframe: str | None = None,
    recent_limit: int = 50,
    reason_limit: int = 20,
    dimension_limit: int = 100,
) -> dict[str, Any]:
    filters = DecisionFunnelReadModelFilter.last_hours(
        hours,
        now=now,
        symbol=symbol,
        strategy=strategy,
        timeframe=timeframe,
        recent_limit=recent_limit,
        reason_limit=reason_limit,
        dimension_limit=dimension_limit,
    )

    return DecisionFunnelReadModelBuilder(
        connection_factory
    ).build(filters)
