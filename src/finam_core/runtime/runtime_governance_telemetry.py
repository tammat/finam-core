from __future__ import annotations

import json
from datetime import date
from typing import Any


class RuntimeGovernanceTelemetry:
    """Русский комментарий: пишет агрегированную телеметрию governance-cycle."""

    def __init__(self, pg_logger: Any) -> None:
        self.pg_logger = pg_logger

    def write_cycle(
        self,
        *,
        trade_date: date,
        scorecards_saved: int,
        rank_decisions_saved: int,
        cooldowns_saved: int,
        allocation_count: int,
        source: str = "runtime_governance_service",
        raw_json: dict[str, Any] | None = None,
    ) -> None:
        stats = self._load_rank_and_cooldown_stats(trade_date)

        sql = """
        INSERT INTO runtime_governance_history (
            trade_date,
            scorecards_saved,
            rank_decisions_saved,
            cooldowns_saved,
            allocation_count,
            strategies_enabled,
            strategies_reduced,
            strategies_disabled,
            strategies_watch,
            active_cooldowns,
            source,
            raw_json
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
        """

        payload = raw_json or {}

        with self.pg_logger._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql,
                    (
                        trade_date,
                        scorecards_saved,
                        rank_decisions_saved,
                        cooldowns_saved,
                        allocation_count,
                        stats["ENABLE"],
                        stats["REDUCE"],
                        stats["DISABLE"],
                        stats["WATCH"],
                        stats["active_cooldowns"],
                        source,
                        json.dumps(payload, ensure_ascii=False, default=str),
                    ),
                )
            conn.commit()

    def _load_rank_and_cooldown_stats(self, trade_date: date) -> dict[str, int]:
        sql = """
        select
            count(*) filter (where decision = 'ENABLE') as enabled,
            count(*) filter (where decision = 'REDUCE') as reduced,
            count(*) filter (where decision = 'DISABLE') as disabled,
            count(*) filter (where decision = 'WATCH') as watch
        from strategy_rank_decisions
        where trade_date = %s
        """

        cooldown_sql = """
        select count(*)
        from strategy_cooldowns
        where cooldown_until > now()
        """

        with self.pg_logger._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (trade_date,))
                row = cur.fetchone() or (0, 0, 0, 0)

                cur.execute(cooldown_sql)
                cooldown_row = cur.fetchone() or (0,)

        return {
            "ENABLE": int(row[0] or 0),
            "REDUCE": int(row[1] or 0),
            "DISABLE": int(row[2] or 0),
            "WATCH": int(row[3] or 0),
            "active_cooldowns": int(cooldown_row[0] or 0),
        }
