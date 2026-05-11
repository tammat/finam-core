from __future__ import annotations

import os
from typing import Any

import psycopg2
import requests


MOEX_SECURITIES_URL = "https://iss.moex.com/iss/securities.json"


class FinamInstrumentSyncService:
    """Русский комментарий: синхронизация instrument_reference через MOEX ISS."""

    def __init__(self) -> None:
        self.database_url = os.environ["DATABASE_URL"]

    @staticmethod
    def _rows(block: dict[str, Any]) -> list[dict[str, Any]]:
        columns = block.get("columns") or []
        data = block.get("data") or []
        return [dict(zip(columns, row)) for row in data]

    def sync(self) -> int:
        response = requests.get(
            MOEX_SECURITIES_URL,
            params={
                "iss.meta": "off",
                "securities.columns": "SECID,SHORTNAME,SECNAME,BOARDID,PRIMARY_BOARDID,TYPE,ISIN,LATNAME",
                "limit": "10000",
            },
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()

        rows = self._rows(payload.get("securities") or {})

        synced = 0

        with psycopg2.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                for row in rows:
                    secid = str(row.get("SECID") or "").strip()
                    if not secid:
                        continue

                    board = str(row.get("PRIMARY_BOARDID") or row.get("BOARDID") or "").strip()
                    symbol = f"{secid}@{board}" if board else secid

                    short_name = str(row.get("SHORTNAME") or secid)
                    display_name = str(row.get("SECNAME") or short_name)
                    asset_class = str(row.get("TYPE") or "unknown")

                    cur.execute(
                        """
                        INSERT INTO instrument_reference (
                            symbol, short_name, display_name, board, market,
                            asset_class, source, updated_at
                        )
                        VALUES (%s,%s,%s,%s,%s,%s,'moex',now())
                        ON CONFLICT(symbol)
                        DO UPDATE SET
                            short_name = EXCLUDED.short_name,
                            display_name = EXCLUDED.display_name,
                            board = EXCLUDED.board,
                            market = EXCLUDED.market,
                            asset_class = EXCLUDED.asset_class,
                            source = 'moex',
                            updated_at = now()
                        """,
                        (symbol, short_name, display_name, board, board, asset_class),
                    )
                    synced += 1

        print(f"MOEX_INSTRUMENT_SYNC_OK synced={synced}", flush=True)
        return synced


def main() -> None:
    FinamInstrumentSyncService().sync()


if __name__ == "__main__":
    main()
