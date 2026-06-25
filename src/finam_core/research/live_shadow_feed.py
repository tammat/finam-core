from datetime import datetime, timezone
from typing import Any

from finam_core.research.runtime_shadow_db_pipeline import RuntimeShadowDbPipeline


class LiveShadowFeedProcessor:
    # Получает копию live market event и пишет Market State только в research.*.
    # Runtime, Execution и заявки не затрагиваются.

    def __init__(self, database_url: str) -> None:
        self.pipeline = RuntimeShadowDbPipeline(database_url=database_url)

    def process_live_event(self, event: dict[str, Any]) -> dict[str, Any]:
        event_ts = event.get("event_ts")
        snapshot_ts = self._parse_ts(event_ts)

        result = self.pipeline.process_market_event(
            event,
            snapshot_ts=snapshot_ts,
            asset_class=event.get("asset_class"),
        )

        return {
            **result,
            "feed_mode": "live_shadow_copy_only",
            "db_update": 1,
            "orders_sent": 0,
            "runtime_changed": 0,
            "execution_changed": 0,
            "real_trading_enabled": 0,
        }

    def _parse_ts(self, value: Any) -> datetime:
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        if isinstance(value, str) and value:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc)
