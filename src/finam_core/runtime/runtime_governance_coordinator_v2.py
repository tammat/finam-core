from __future__ import annotations

from dataclasses import dataclass

import psycopg


@dataclass(frozen=True)
class RuntimeGovernanceDecisionV2:
    symbol: str
    strategy: str
    timeframe: str
    mode: str
    heat_status: str
    risk_multiplier: float
    allow_new_entries: bool
    allow_execution: bool
    watch_only: bool
    reason: str


class RuntimeGovernanceCoordinatorV2:
    """
    Русский комментарий:
    Runtime Governance Coordinator v2.

    Назначение:
    - читает последнее portfolio_governance_events;
    - формирует runtime advisory decision;
    - не отправляет заявки;
    - не меняет RiskStack напрямую;
    - не меняет execution route.
    """

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def decide(
        self,
        *,
        symbol: str,
        strategy: str,
        timeframe: str,
    ) -> RuntimeGovernanceDecisionV2:
        row = self._load_latest_event(
            symbol=symbol,
            strategy=strategy,
            timeframe=timeframe,
        )

        if row is None:
            return RuntimeGovernanceDecisionV2(
                symbol=symbol,
                strategy=strategy,
                timeframe=timeframe,
                mode="ADVISORY_ONLY",
                heat_status="UNKNOWN",
                risk_multiplier=1.0,
                allow_new_entries=True,
                allow_execution=True,
                watch_only=False,
                reason="governance_event_not_found",
            )

        heat_status = str(row["portfolio_heat_status"])
        risk_multiplier = float(row["portfolio_risk_multiplier"])
        allow_new_entries = bool(row["allow_new_entries"])
        governance_mode = str(row["governance_mode"])

        allow_execution = True
        watch_only = False
        reason = "governance_advisory_normal"

        if heat_status in {"CRITICAL", "EXTREME"}:
            allow_new_entries = False
            allow_execution = True
            watch_only = True
            risk_multiplier = 0.0
            reason = "portfolio_heat_critical_watch_only"

        elif heat_status == "HIGH":
            allow_execution = True
            watch_only = False
            reason = "portfolio_heat_high_reduce_risk"

        elif heat_status == "ELEVATED":
            allow_execution = True
            watch_only = False
            reason = "portfolio_heat_elevated_soft_reduce"

        return RuntimeGovernanceDecisionV2(
            symbol=symbol,
            strategy=strategy,
            timeframe=timeframe,
            mode=governance_mode,
            heat_status=heat_status,
            risk_multiplier=risk_multiplier,
            allow_new_entries=allow_new_entries,
            allow_execution=allow_execution,
            watch_only=watch_only,
            reason=reason,
        )

    def _load_latest_event(
        self,
        *,
        symbol: str,
        strategy: str,
        timeframe: str,
    ) -> dict | None:
        sql = """
        SELECT
            symbol,
            strategy,
            timeframe,
            portfolio_heat_status,
            portfolio_risk_multiplier,
            allow_new_entries,
            governance_mode
        FROM portfolio_governance_events
        WHERE symbol = %s
          AND strategy = %s
          AND timeframe = %s
        ORDER BY created_at DESC
        LIMIT 1
        """

        try:
            with psycopg.connect(self.database_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (symbol, strategy, timeframe))
                    row = cur.fetchone()
        except Exception:
            return None

        if row is None:
            return None

        return {
            "symbol": row[0],
            "strategy": row[1],
            "timeframe": row[2],
            "portfolio_heat_status": row[3],
            "portfolio_risk_multiplier": row[4],
            "allow_new_entries": row[5],
            "governance_mode": row[6],
        }
