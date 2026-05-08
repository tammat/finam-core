# -*- coding: utf-8 -*-
from __future__ import annotations

import requests


class MoexClient:
    """Русский комментарий: MOEX ISS клиент только для spot-данных, без фьючерсов."""

    BASE_URL = "https://iss.moex.com/iss"

    def get_board_marketdata(self, board: str) -> dict:
        """Русский комментарий: получает marketdata по конкретному board."""
        url = (
            f"{self.BASE_URL}/engines/stock/markets/shares/boards/{board}/securities.json"
            "?iss.meta=off"
            "&securities.columns=SECID,SHORTNAME,BOARDID"
            "&marketdata.columns=SECID,LAST,CHANGE,VALTODAY,VOLTODAY,NUMTRADES"
        )

        r = requests.get(url, timeout=20)
        r.raise_for_status()
        return r.json()

    def get_today_spot_universe(self) -> dict[str, dict]:
        """Русский комментарий: акции + фонды/металлы, без срочного рынка."""
        result: dict[str, dict] = {}

        for board in ("TQBR",):
            result[board] = self.get_board_marketdata(board)

        return result

    def get_imoex_change_pct(self) -> float:
        """Русский комментарий: берёт изменение IMOEX через board SNDX."""
        url = (
            f"{self.BASE_URL}/engines/stock/markets/index/boards/SNDX/securities/IMOEX.json"
            "?iss.meta=off"
        )

        r = requests.get(url, timeout=20)
        r.raise_for_status()

        data = r.json()

        cols = data.get("marketdata", {}).get("columns", [])
        rows = data.get("marketdata", {}).get("data", [])

        if not cols or not rows:
            return 0.0

        rec = dict(zip(cols, rows[0]))

        # Русский комментарий: для индекса MOEX поле изменения — LASTCHANGEPRC.
        try:
            return float(rec.get("LASTCHANGEPRC") or 0.0)
        except Exception:
            return 0.0
