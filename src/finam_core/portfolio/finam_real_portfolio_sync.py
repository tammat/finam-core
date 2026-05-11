from __future__ import annotations

import os
from typing import Any

import psycopg2
import psycopg2.extras
import requests

from finam_core.auth.token_manager import FinamTokenManager


class FinamRealPortfolioSync:
    """Русский комментарий: прямая синхронизация реального портфеля через Finam REST account endpoint."""

    def __init__(self) -> None:
        self.database_url = os.environ["DATABASE_URL"]
        self.account_id = (os.getenv("FINAM_ACCOUNT_ID") or "").strip()
        if not self.account_id:
            raise RuntimeError("FINAM_ACCOUNT_ID is required")

        self.url = os.getenv(
            "FINAM_ACCOUNT_REST_URL",
            f"https://api.finam.ru/v1/accounts/{self.account_id}",
        ).strip()

        self.jwt = FinamTokenManager().get_token()

    def _request_payload(self) -> dict[str, Any]:
        response = requests.get(
            self.url,
            headers={
                "Accept": "application/json",
                "Authorization": self.jwt,
                "User-Agent": "FinamCore/1.0",
            },
            timeout=30,
        )

        preview = (response.text or "")[:700].replace("\n", " ")
        content_type = response.headers.get("content-type", "")

        if response.status_code >= 400:
            raise RuntimeError(
                "FINAM_ACCOUNT_HTTP_ERROR "
                f"status={response.status_code} content_type={content_type} body={preview!r}"
            )

        try:
            payload = response.json()
        except Exception as exc:
            raise RuntimeError(
                "FINAM_ACCOUNT_NON_JSON_RESPONSE "
                f"status={response.status_code} content_type={content_type} body={preview!r}"
            ) from exc

        if not isinstance(payload, dict):
            raise RuntimeError(f"FINAM_ACCOUNT_UNEXPECTED_JSON type={type(payload).__name__}")

        return payload

    @staticmethod
    def _num(value: Any) -> float:
        """Русский комментарий: Finam API часто возвращает числа как {'value': '10.0'}."""
        if value in (None, ""):
            return 0.0

        if isinstance(value, dict):
            nested = (
                value.get("value")
                or value.get("amount")
                or value.get("units")
                or value.get("nano")
                or 0
            )
            return FinamRealPortfolioSync._num(nested)

        if isinstance(value, (int, float)):
            return float(value)

        return float(str(value).replace(",", ".").strip())

    @staticmethod
    def _extract_positions(payload: dict[str, Any]) -> list[dict[str, Any]]:
        data = (
            payload.get("positions")
            or payload.get("securities")
            or payload.get("assets")
            or payload.get("portfolio")
            or payload.get("items")
            or payload.get("data")
            or []
        )

        if isinstance(data, dict):
            data = (
                data.get("positions")
                or data.get("securities")
                or data.get("assets")
                or data.get("items")
                or []
            )

        if not isinstance(data, list):
            return []

        return [x for x in data if isinstance(x, dict)]

    @staticmethod
    def _symbol(row: dict[str, Any]) -> str:
        code = str(
            row.get("symbol")
            or row.get("ticker")
            or row.get("securityCode")
            or row.get("secCode")
            or row.get("code")
            or ""
        ).strip()

        board = str(
            row.get("board")
            or row.get("boardCode")
            or row.get("market")
            or row.get("exchange")
            or ""
        ).strip()

        if code and "@" not in code and board:
            return f"{code}@{board}"

        return code

    def save_positions(self, positions: list[dict[str, Any]]) -> int:
        saved = 0

        with psycopg2.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute("TRUNCATE real_portfolio_positions")

                for row in positions:
                    symbol = self._symbol(row)
                    if not symbol:
                        continue

                    qty = self._num(row.get("qty") or row.get("quantity") or row.get("balance") or row.get("lots") or 0)
                    avg_price = self._num(row.get("avg_price") or row.get("averagePrice") or row.get("avgPrice") or 0)
                    current_price = self._num(row.get("current_price") or row.get("lastPrice") or row.get("price") or 0)
                    market_value = self._num(row.get("market_value") or row.get("marketValue") or row.get("value") or 0)
                    pnl = self._num(row.get("pnl") or row.get("profit") or row.get("profitLoss") or 0)
                    pnl_day = self._num(row.get("pnl_day") or row.get("dayPnl") or row.get("dailyPnl") or 0)
                    currency = str(row.get("currency") or "RUB")

                    cur.execute(
                        """
                        INSERT INTO real_portfolio_positions (
                            symbol, qty, avg_price, current_price,
                            market_value, pnl, pnl_day, currency,
                            source, raw_json, updated_at
                        )
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'finam_api',%s,now())
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
                            symbol,
                            qty,
                            avg_price,
                            current_price,
                            market_value,
                            pnl,
                            pnl_day,
                            currency,
                            psycopg2.extras.Json(row),
                        ),
                    )
                    saved += 1

        return saved

    def sync(self) -> int:
        payload = self._request_payload()
        positions = self._extract_positions(payload)

        if not positions:
            print(f"FINAM_REAL_PORTFOLIO_EMPTY payload_keys={list(payload.keys())}", flush=True)
            print(f"FINAM_REAL_PORTFOLIO_PAYLOAD_PREVIEW={str(payload)[:1000]}", flush=True)
            return 0

        saved = self.save_positions(positions)
        print(f"FINAM_REAL_PORTFOLIO_SYNC_OK saved={saved}", flush=True)
        return saved


def main() -> None:
    FinamRealPortfolioSync().sync()


if __name__ == "__main__":
    main()
