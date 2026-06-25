import os
from datetime import datetime, timezone

from finam_core.research.event_adapter import ResearchEventAdapter
from finam_core.research.events import MarketFeaturesReadyEvent
from finam_core.research.market_state.repository import MarketStateRepository


class MarketStateDbWriter:
    # Writer принимает market features event, строит MarketStateBuiltEvent и сохраняет его в PostgreSQL.

    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or os.environ.get("DATABASE_URL", "")
        self.adapter = ResearchEventAdapter()
        self.repository = MarketStateRepository(self.database_url)

    def save_features_event(
        self,
        event: MarketFeaturesReadyEvent,
        *,
        snapshot_ts: datetime | None = None,
        asset_class: str | None = None,
    ) -> int:
        built_event = self.adapter.handle_market_features(event)
        return self.repository.save_market_state_event(
            built_event,
            snapshot_ts=snapshot_ts or datetime.now(timezone.utc),
            asset_class=asset_class,
        )
