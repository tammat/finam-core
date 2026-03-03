from datetime import datetime, timezone


def normalize_bars(response, timeframe: str):
    rows = []

    for bar in response.bars:
        ts = datetime.fromtimestamp(
            bar.timestamp.seconds,
            tz=timezone.utc
        )

        rows.append({
            "symbol": response.symbol,
            "timeframe": timeframe,
            "ts": ts,
            "open": float(bar.open.value),
            "high": float(bar.high.value),
            "low": float(bar.low.value),
            "close": float(bar.close.value),
            "volume": float(bar.volume.value),
        })

    return rows