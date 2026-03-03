#src/scripts/finam_smoke.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Optional, Tuple

import grpc

# finam proto (ваш пакет с сгенерированными файлами)
from finam_proto.grpc.tradeapi.v1.assets import assets_service_pb2 as a_pb2
from finam_proto.grpc.tradeapi.v1.assets import assets_service_pb2_grpc as a_grpc

from finam_proto.grpc.tradeapi.v1.marketdata import marketdata_service_pb2 as md_pb2
from finam_proto.grpc.tradeapi.v1.marketdata import marketdata_service_pb2_grpc as md_grpc

from google.protobuf.timestamp_pb2 import Timestamp
from google.type.interval_pb2 import Interval


# ---------------------------
# .env loader (без dotenv)
# ---------------------------

def _parse_env_line(line: str) -> Optional[Tuple[str, str]]:
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    if "=" not in line:
        return None
    k, v = line.split("=", 1)
    k = k.strip()
    v = v.strip()

    # remove surrounding quotes
    if (v.startswith("'") and v.endswith("'")) or (v.startswith('"') and v.endswith('"')):
        v = v[1:-1]

    return k, v


def load_env_file(env_path: Path, override: bool = False) -> Dict[str, str]:
    if not env_path.exists():
        raise FileNotFoundError(f".env not found: {env_path}")

    loaded: Dict[str, str] = {}
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        parsed = _parse_env_line(raw)
        if not parsed:
            continue
        k, v = parsed
        if override or (k not in os.environ):
            os.environ[k] = v
        loaded[k] = v
    return loaded


# ---------------------------
# helpers
# ---------------------------

def _ts(dt: datetime) -> Timestamp:
    # protobuf Timestamp expects UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt = dt.astimezone(timezone.utc)
    t = Timestamp()
    t.FromDatetime(dt)
    return t


@dataclass(frozen=True)
class FinamEnv:
    host: str
    token: str
    account_id: Optional[str] = None


def read_finam_env(project_root: Path) -> FinamEnv:
    # читаем .env из корня проекта
    load_env_file(project_root / ".env", override=False)

    host = os.getenv("FINAM_API_HOST", "api.finam.ru:443")
    token = os.getenv("FINAM_TOKEN")
    account_id = os.getenv("FINAM_ACCOUNT_ID")

    if not token:
        raise RuntimeError("FINAM_TOKEN is missing in .env / env")

    return FinamEnv(host=host, token=token, account_id=account_id)


def make_channel(host: str) -> grpc.Channel:
    return grpc.secure_channel(host, grpc.ssl_channel_credentials())


def call_get_assets(channel: grpc.Channel, token: str, search: str) -> a_pb2.GetAssetsResponse:
    stub = a_grpc.AssetsServiceStub(channel)
    # Вариант 1 (чаще всего): Bearer
    md = [("authorization", f"Bearer {token}")]
    try:
        return stub.GetAssets(a_pb2.GetAssetsRequest(search=search), metadata=md, timeout=10)
    except grpc.RpcError as e:
        # Вариант 2: без Bearer (если у API так)
        if getattr(e, "code", lambda: None)() == grpc.StatusCode.UNAUTHENTICATED:
            md2 = [("authorization", token)]
            return stub.GetAssets(a_pb2.GetAssetsRequest(search=search), metadata=md2, timeout=10)
        raise


def call_bars(
    channel: grpc.Channel,
    token: str,
    symbol: str,
    timeframe: md_pb2.TimeFrame,
    start_utc: datetime,
    end_utc: datetime,
) -> md_pb2.BarsResponse:
    stub = md_grpc.MarketDataServiceStub(channel)

    req = md_pb2.BarsRequest(
        symbol=symbol,                 # IMPORTANT: обычно должно быть "XXX@MIC"
        timeframe=timeframe,
        interval=Interval(
            start_time=_ts(start_utc),
            end_time=_ts(end_utc),
        ),
    )

    md = [("authorization", f"Bearer {token}")]
    try:
        return stub.Bars(req, metadata=md, timeout=15)
    except grpc.RpcError as e:
        if getattr(e, "code", lambda: None)() == grpc.StatusCode.UNAUTHENTICATED:
            md2 = [("authorization", token)]
            return stub.Bars(req, metadata=md2, timeout=15)
        raise


def main() -> int:
    project_root = Path(__file__).resolve().parents[2]  # src/scripts -> project root
    env = read_finam_env(project_root)

    print(f"HOST: {env.host}")
    print(f"TOKEN: {env.token[:10]}... (len={len(env.token)})")

    channel = make_channel(env.host)

    # 1) GetAssets
    search = os.getenv("FINAM_ASSET_SEARCH", "NG")
    assets_resp = call_get_assets(channel, env.token, search=search)
    print("GetAssets:", len(assets_resp.assets))

    if not assets_resp.assets:
        print("No assets found for search:", search)
        return 2

    first = assets_resp.assets[0]
    symbol = getattr(first, "symbol", None)

    # На практике Finam часто требует symbol вида "XXXX@MIC".
    # Если вдруг symbol без @, попробуем собрать из mic/exchange (если поля есть).
    if symbol and "@" not in symbol:
        mic = getattr(first, "mic", None) or getattr(first, "exchange", None)
        if mic:
            symbol = f"{symbol}@{mic}"

    if not symbol or "@" not in symbol:
        print("ERROR: asset symbol is missing or has no MIC (@).")
        print("First asset:", first)
        return 3

    print("Using symbol:", symbol)

    # 2) Bars (последние N часов/дней)
    tf_str = os.getenv("FINAM_TIMEFRAME", "M15").upper()  # e.g. M1/M5/M15/H1/D
    tf_map = {
        "M1": md_pb2.TIME_FRAME_M1,
        "M5": md_pb2.TIME_FRAME_M5,
        "M15": md_pb2.TIME_FRAME_M15,
        "M30": md_pb2.TIME_FRAME_M30,
        "H1": md_pb2.TIME_FRAME_H1,
        "H2": md_pb2.TIME_FRAME_H2,
        "H4": md_pb2.TIME_FRAME_H4,
        "H8": md_pb2.TIME_FRAME_H8,
        "D": md_pb2.TIME_FRAME_D,
        "W": md_pb2.TIME_FRAME_W,
        "MN": md_pb2.TIME_FRAME_MN,
        "QR": md_pb2.TIME_FRAME_QR,
    }
    timeframe = tf_map.get(tf_str, md_pb2.TIME_FRAME_M15)

    lookback_hours = int(os.getenv("FINAM_LOOKBACK_HOURS", "24"))
    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=lookback_hours)

    bars_resp = call_bars(
        channel=channel,
        token=env.token,
        symbol=symbol,
        timeframe=timeframe,
        start_utc=start,
        end_utc=end,
    )

    print("Bars:", len(bars_resp.bars))
    for b in bars_resp.bars[:5]:
        # поля Bar в вашем proto: timestamp/open/high/low/close/volume (Decimal как string)
        print("bar:", b.timestamp, b.open, b.high, b.low, b.close, b.volume)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())