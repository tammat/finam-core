from __future__ import annotations

import os
import time
from typing import Any

import psycopg2
import requests


MOEX_SECURITIES_URL = "https://iss.moex.com/iss/securities.json"


class FinamInstrumentSyncService:
    """Русский комментарий: синхронизация instrument_reference через MOEX ISS с ограничением страниц."""

    def __init__(self) -> None:
        self.database_url = os.environ["DATABASE_URL"]
        self.page_limit = int(os.getenv("MOEX_INSTRUMENT_PAGE_LIMIT", "100"))
        self.max_pages = int(os.getenv("MOEX_INSTRUMENT_MAX_PAGES", "80"))
        self.request_timeout_sec = float(os.getenv("MOEX_INSTRUMENT_TIMEOUT_SEC", "10"))
        self.sleep_sec = float(os.getenv("MOEX_INSTRUMENT_SLEEP_SEC", "0.05"))

    @staticmethod
    def _rows(block: dict[str, Any]) -> list[dict[str, Any]]:
        columns = [str(c).lower() for c in (block.get("columns") or [])]
        data = block.get("data") or []
        return [dict(zip(columns, row)) for row in data]

    @staticmethod
    def _finam_alias_board(*, board: str, instrument_type: str, group: str) -> str:
        if group.startswith("stock") or board in {"TQBR", "TQTF", "TQTD", "TQOB", "TQCB"}:
            return "MISX"
        # Русский комментарий: @RTSX alias делаем только для фьючерсов.
        # Опционы на фьючерсы не должны попадать как BR*@RTSX/NG*@RTSX в основной список фьючерсов.
        if instrument_type == "futures":
            return "RTSX"
        return board

    def _upsert(self, cur, *, symbol, short_name, display_name, board, market, asset_class, source) -> None:
        cur.execute(
            """
            INSERT INTO instrument_reference (
                symbol, short_name, display_name, board, market,
                asset_class, source, updated_at
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,now())
            ON CONFLICT(symbol)
            DO UPDATE SET
                short_name = EXCLUDED.short_name,
                display_name = EXCLUDED.display_name,
                board = EXCLUDED.board,
                market = EXCLUDED.market,
                asset_class = EXCLUDED.asset_class,
                source = EXCLUDED.source,
                updated_at = now()
            """,
            (symbol, short_name, display_name, board, market, asset_class, source),
        )

    def _sync_row(self, cur, row: dict[str, Any]) -> int:
        secid = str(row.get("secid") or "").strip()
        if not secid:
            return 0

        board = str(row.get("primary_boardid") or row.get("marketprice_boardid") or "").strip()
        short_name = str(row.get("shortname") or secid).strip()
        display_name = str(row.get("name") or short_name).strip()
        instrument_type = str(row.get("type") or "unknown").strip()
        group = str(row.get("group") or "").strip()

        inserted = 0

        self._upsert(
            cur,
            symbol=f"{secid}@{board}" if board else secid,
            short_name=short_name,
            display_name=display_name,
            board=board,
            market=board,
            asset_class=instrument_type,
            source="moex",
        )
        inserted += 1

        alias_board = self._finam_alias_board(
            board=board,
            instrument_type=instrument_type,
            group=group,
        )

        if alias_board and alias_board != board:
            self._upsert(
                cur,
                symbol=f"{secid}@{alias_board}",
                short_name=short_name,
                display_name=display_name,
                board=alias_board,
                market=alias_board,
                asset_class=instrument_type,
                source="moex_alias",
            )
            inserted += 1

        return inserted

    def _load_page(self, *, start: int) -> list[dict[str, Any]]:
        response = requests.get(
            MOEX_SECURITIES_URL,
            params={
                "iss.meta": "off",
                "limit": str(self.page_limit),
                "start": str(start),
            },
            timeout=self.request_timeout_sec,
        )
        response.raise_for_status()
        payload = response.json()
        return self._rows(payload.get("securities") or {})

    def sync(self) -> int:
        synced = 0
        start = 0
        pages = 0

        with psycopg2.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                while pages < self.max_pages:
                    rows = self._load_page(start=start)

                    if not rows:
                        break

                    for row in rows:
                        synced += self._sync_row(cur, row)

                    pages += 1
                    start += len(rows)

                    print(
                        f"MOEX_INSTRUMENT_SYNC_PAGE page={pages} start={start} rows={len(rows)} synced={synced}",
                        flush=True,
                    )

                    time.sleep(self.sleep_sec)

        print(f"MOEX_INSTRUMENT_SYNC_OK synced={synced} pages={pages}", flush=True)
        return synced


def main() -> None:
    FinamInstrumentSyncService().sync()


if __name__ == "__main__":
    main()
