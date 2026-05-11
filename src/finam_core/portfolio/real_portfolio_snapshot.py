from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import psycopg2
import psycopg2.extras


class RealPortfolioSnapshotService:
    """Русский комментарий: сохраняет реальный портфель в PostgreSQL snapshot table."""

    def __init__(self) -> None:
        self.database_url = os.environ["DATABASE_URL"]

    def load_json_file(self, path: str) -> list[dict[str, Any]]:
        data = json.loads(Path(path).read_text(encoding="utf-8"))

        if isinstance(data, dict):
            data = data.get("positions") or data.get("items") or data.get("data") or []

        if not isinstance(data, list):
            raise RuntimeError("REAL_PORTFOLIO_JSON_MUST_BE_LIST_OR_OBJECT_WITH_POSITIONS")

        return [x for x in data if isinstance(x, dict)]

    @staticmethod
    def _get(row: dict[str, Any], *names: str, default: Any = None) -> Any:
        for name in names:
            if name in row and row[name] is not None:
                return row[name]
        return default

    @staticmethod
    def _num(value: Any) -> float:
        if value in (None, ""):
            return 0.0
        return float(str(value).replace(",", "."))

    def save_positions(self, positions: list[dict[str, Any]], *, source: str) -> int:
        saved = 0

        with psycopg2.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                for row in positions:
                    symbol = str(
                        self._get(row, "symbol", "ticker", "sec_code", "securityCode", "code", default="")
                    ).strip()

                    if not symbol:
                        continue

                    qty = self._num(self._get(row, "qty", "quantity", "balance", "lots", default=0))
                    avg_price = self._num(self._get(row, "avg_price", "averagePrice", "avgPrice", default=0))
                    current_price = self._num(self._get(row, "current_price", "lastPrice", "price", default=0))
                    market_value = self._num(self._get(row, "market_value", "value", "amount", default=0))
                    pnl = self._num(self._get(row, "pnl", "profit", "profitLoss", default=0))
                    pnl_day = self._num(self._get(row, "pnl_day", "dayPnl", "dailyPnl", default=0))
                    currency = str(self._get(row, "currency", default="RUB"))

                    cur.execute(
                        """
                        INSERT INTO real_portfolio_positions (
                            symbol, qty, avg_price, current_price,
                            market_value, pnl, pnl_day, currency,
                            source, raw_json, updated_at
                        )
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,now())
                        ON CONFLICT(symbol)
                        DO UPDATE SET
                            qty = EXCLUDED.qty,
                            avg_price = EXCLUDED.avg_price,
                            current_price = EXCLUDED.current_price,
                            market_value = EXCLUDED.market_value,
                            pnl = EXCLUDED.pnl,
                            pnl_day = EXCLUDED.pnl_day,
                            currency = EXCLUDED.currency,
                            source = EXCLUDED.source,
                            raw_json = EXCLUDED.raw_json,
                            updated_at = now()
                        """,
                        (
                            symbol, qty, avg_price, current_price,
                            market_value, pnl, pnl_day,
                            currency, source, psycopg2.extras.Json(row),
                        ),
                    )
                    saved += 1

        return saved


def main() -> None:
    path = os.getenv("REAL_PORTFOLIO_JSON", "").strip()
    if not path:
        raise RuntimeError("REAL_PORTFOLIO_JSON is required")

    service = RealPortfolioSnapshotService()
    positions = service.load_json_file(path)
    saved = service.save_positions(positions, source="json_snapshot")

    print(f"REAL_PORTFOLIO_SNAPSHOT_OK saved={saved}", flush=True)


if __name__ == "__main__":
    main()
