import os
from datetime import datetime, timedelta, timezone

import pytest

from finam_core.ingestion.finam_client import FinamClient
from finam_proto.grpc.tradeapi.v1.marketdata import marketdata_service_pb2 as md_pb2


@pytest.mark.integration
def test_get_bars_real():

    token = os.environ.get("FINAM_TOKEN")
    if not token:
        pytest.skip("FINAM_TOKEN not set")

    client = FinamClient(
        host="api.finam.ru:443",
        personal_token=token,
    )

    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=1)

    response = client.get_bars(
        symbol="GAZP@MISX",
        timeframe=md_pb2.TimeFrame.TIME_FRAME_H1,
        start_time=start_time,
        end_time=end_time,
    )

    assert response.symbol == "GAZP@MISX"
    assert len(response.bars) > 0

    first_bar = response.bars[0]
    assert float(first_bar.open.value) > 0
    assert float(first_bar.close.value) > 0