from __future__ import annotations

import os
from pathlib import Path

import psycopg2
import requests

from finam_core.auth.token_manager import FinamTokenManager


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
ROOT = Path(__file__).resolve().parents[2]


def load_env() -> None:
    path = ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def fetch_assets() -> list[dict]:
    load_env()
    token = FinamTokenManager().get_token()
    cursor = 0
    assets: list[dict] = []
    while True:
        response = requests.get(
            "https://api.finam.ru/v1/assets/all",
            headers={"Authorization": token},
            params={"cursor": cursor, "only_active": "true"},
            timeout=30,
        )
        if response.status_code == 401:
            response = requests.get(
                "https://api.finam.ru/v1/assets/all",
                headers={"Authorization": f"Bearer {token}"},
                params={"cursor": cursor, "only_active": "true"},
                timeout=30,
            )
        response.raise_for_status()
        payload = response.json()
        assets.extend(payload.get("assets") or [])
        next_cursor = int(payload.get("nextCursor") or payload.get("next_cursor") or 0)
        if not next_cursor or next_cursor == cursor:
            break
        cursor = next_cursor
    return assets


def main() -> None:
    assets = fetch_assets()
    with psycopg2.connect(DB) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS analytics.finam_instrument_universe_v1 (
                    symbol text PRIMARY KEY, ticker text NOT NULL, mic text NOT NULL,
                    asset_type text NOT NULL, name text NOT NULL, isin text,
                    is_archived boolean NOT NULL DEFAULT false,
                    m5_bars bigint NOT NULL DEFAULT 0,
                    research_status text NOT NULL,
                    discovered_at timestamptz NOT NULL DEFAULT now(),
                    updated_at timestamptz NOT NULL DEFAULT now()
                )
            """)
            stored = ready = needs_history = 0
            for asset in assets:
                symbol = str(asset.get("symbol") or "").strip()
                mic = str(asset.get("mic") or "").strip()
                ticker = str(asset.get("ticker") or symbol.split("@", 1)[0]).strip()
                if not symbol or not mic or bool(asset.get("isArchived") or asset.get("is_archived")):
                    continue
                cur.execute("SELECT count(*) FROM public.market_bars WHERE symbol=%s AND timeframe='M5'", (symbol,))
                bars = int(cur.fetchone()[0])
                status = "READY_FOR_DATA_GATE" if bars >= 6000 else "NEEDS_HISTORY"
                ready += int(status == "READY_FOR_DATA_GATE")
                needs_history += int(status == "NEEDS_HISTORY")
                cur.execute("""
                    INSERT INTO analytics.finam_instrument_universe_v1
                    (symbol,ticker,mic,asset_type,name,isin,is_archived,m5_bars,research_status)
                    VALUES (%s,%s,%s,%s,%s,%s,false,%s,%s)
                    ON CONFLICT(symbol) DO UPDATE SET ticker=excluded.ticker,mic=excluded.mic,
                    asset_type=excluded.asset_type,name=excluded.name,isin=excluded.isin,
                    is_archived=false,m5_bars=excluded.m5_bars,research_status=excluded.research_status,updated_at=now()
                """, (symbol, ticker, mic, str(asset.get("type") or "UNKNOWN"),
                      str(asset.get("name") or ticker), asset.get("isin"), bars, status))
                stored += 1
    print(f"catalog_assets={len(assets)}")
    print(f"stored_active={stored}")
    print(f"ready_for_data_gate={ready}")
    print(f"needs_history={needs_history}")
    print("promotion_allowed=0")
    print("VERDICT=FINAM_INSTRUMENT_UNIVERSE_DISCOVERY_V1_OK")


if __name__ == "__main__":
    main()
