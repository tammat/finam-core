import os
from datetime import datetime, timezone

import pytest

from storage.postgres_storage import PostgresStorage
from domain.fill_event import FillEvent


@pytest.mark.integration
def test_postgres_append_and_load():
    dsn = os.getenv("POSTGRES_DSN")
    assert dsn, "Set POSTGRES_DSN env var, e.g. postgresql://user:pass@localhost:5432/finam"

    storage = PostgresStorage(dsn=dsn)

    fill = FillEvent(
        fill_id=f"test-{int(datetime.now(tz=timezone.utc).timestamp() * 1_000_000)}",
        timestamp=datetime.now(tz=timezone.utc),
        symbol="SI",
        side="BUY",
        quantity=1.0,
        price=100.0,
        commission=0.0,
        order_id="test-order",
    )

    storage.append_fill(fill)
    loaded = list(storage.load_fills("SI"))

    assert any(x.fill_id == fill.fill_id for x in loaded)