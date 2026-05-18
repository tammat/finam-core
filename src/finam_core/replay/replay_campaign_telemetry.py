from __future__ import annotations

import json
from datetime import datetime
from typing import Any


class ReplayCampaignTelemetry:
    """
    Русский комментарий:
    institutional telemetry replay campaign runs.
    """

    def __init__(self, pg_logger: Any):
        self.pg_logger = pg_logger

    def log_run(
        self,
        *,
        campaign_id: str,
        replay_id: str,
        symbol: str,
        timeframe: str,
        strategy: str,
        status: str,
        started_at: datetime,
        finished_at: datetime,
        duration_sec: float,
        return_code: int,
        command: str,
        raw_json: dict[str, Any] | None = None,
    ) -> None:
        sql = """
        insert into replay_campaign_runs (
            campaign_id,
            replay_id,
            symbol,
            timeframe,
            strategy,
            status,
            started_at,
            finished_at,
            duration_sec,
            return_code,
            command,
            raw_json
        )
        values (
            %s,%s,%s,%s,%s,
            %s,%s,%s,%s,%s,
            %s,%s::jsonb
        )
        """

        payload = raw_json or {}

        with self.pg_logger._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql,
                    (
                        campaign_id,
                        replay_id,
                        symbol,
                        timeframe,
                        strategy,
                        status,
                        started_at,
                        finished_at,
                        duration_sec,
                        return_code,
                        command,
                        json.dumps(payload, ensure_ascii=False, default=str),
                    ),
                )

            conn.commit()

        print(
            "REPLAY_CAMPAIGN_TELEMETRY_OK "
            f"campaign_id={campaign_id} "
            f"replay_id={replay_id} "
            f"status={status}",
            flush=True,
        )
