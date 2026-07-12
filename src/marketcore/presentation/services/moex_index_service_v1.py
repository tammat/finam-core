from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from urllib.request import urlopen
from zoneinfo import ZoneInfo

import psycopg2


@dataclass(frozen=True, slots=True)
class MoexIndexSnapshotV1:
    value: float | None
    change_pct: float | None
    updated_at: datetime | None
    freshness: str
    source: str


class MoexIndexServiceV1:
    URL = (
        "https://iss.moex.com/iss/engines/stock/markets/index/"
        "securities/IMOEX.json?iss.meta=off&iss.only=marketdata&"
        "marketdata.columns=SECID,CURRENTVALUE,LASTVALUE,LASTCHANGEPRC,SYSTIME"
    )

    def load(self) -> MoexIndexSnapshotV1:
        try:
            with urlopen(self.URL, timeout=3) as response:
                payload = json.load(response)
            block = payload["marketdata"]
            row = dict(zip(block["columns"], block["data"][0]))
            updated_at = datetime.strptime(row["SYSTIME"], "%Y-%m-%d %H:%M:%S").replace(
                tzinfo=ZoneInfo("Europe/Moscow")
            )
            return MoexIndexSnapshotV1(
                value=float(row["CURRENTVALUE"]),
                change_pct=float(row["LASTCHANGEPRC"]),
                updated_at=updated_at,
                freshness="LIVE",
                source="MOEX_ISS",
            )
        except Exception:
            return self._fallback()

    @staticmethod
    def _fallback() -> MoexIndexSnapshotV1:
        with psycopg2.connect("postgresql:///finam_core") as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT close, ts
                    FROM public.market_bars
                    WHERE symbol='IMOEX' AND timeframe='M1'
                    ORDER BY ts DESC LIMIT 1
                """)
                row = cur.fetchone()
        if not row:
            return MoexIndexSnapshotV1(None, None, None, "NO_DATA", "NONE")
        return MoexIndexSnapshotV1(float(row[0]), None, row[1], "STALE", "market_bars")
