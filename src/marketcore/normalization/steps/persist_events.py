from __future__ import annotations

import os

import psycopg2

from marketcore.normalization.context import NormalizationContext
from marketcore.normalization.steps import (
    BaseBuilderStep,
    StepResult,
    StepTag,
)

BAR_EVENT_NOT_READY = "BAR_EVENT_NOT_READY"


class PersistEventsStep(BaseBuilderStep):
    name = "persist_events"
    version = 1
    tags = (StepTag.PERSIST,)

    def execute(self, ctx: NormalizationContext) -> StepResult:

        if not hasattr(ctx, "bar_event"):
            ctx.reject(BAR_EVENT_NOT_READY)
            return StepResult(
                success=False,
                rows_processed=1,
                rows_rejected=1,
            )

        conn = getattr(ctx.resolvers, "conn", None)

        if conn is None:
            conn = psycopg2.connect(
                os.getenv("DATABASE_URL", "postgresql:///finam_core")
            )

        sql = """
        INSERT INTO warehouse.normalized_bar_event_v1
        (
            event_uuid,
            event_sequence,
            event_type_id,
            quality_status_id,
            source_system_id,
            symbol_alias_id,
            instrument_id,
            contract_id,
            timeframe_id,
            event_time,
            source_time,
            received_at,
            open_price,
            high_price,
            low_price,
            close_price,
            volume,
            payload
        )
        VALUES
        (
            %(event_uuid)s,
            DEFAULT,
            1,
            %(quality_status_id)s,
            %(source_system_id)s,
            %(symbol_alias_id)s,
            %(instrument_id)s,
            %(contract_id)s,
            %(timeframe_id)s,
            %(event_time)s,
            %(source_time)s,
            %(received_at)s,
            %(open)s,
            %(high)s,
            %(low)s,
            %(close)s,
            %(volume)s,
            %(payload)s
        )
        ON CONFLICT (event_uuid)
        DO NOTHING
        """

        with conn.cursor() as cur:
            cur.execute(sql, ctx.bar_event)


        conn.commit()

        ctx.increment("events_persisted")

        return StepResult(
            success=True,
            rows_processed=1,
        )

