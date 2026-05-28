from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class SessionSideGateDecisionV1:
    allowed: bool
    action: str
    reason: str
    symbol: str
    side: str
    hour_msk: int
    session_name: str
    matched_symbol: str | None = None
    expectancy_points: float | None = None
    closed_trades: int | None = None


class SessionSideExecutionGateV1:
    """
    Русский комментарий:
    Runtime gate по найденным session/side/hour edge-окнам.
    Явный BLOCK блокирует вход до RiskRouter.
    NO_MATCH и INSUFFICIENT_DATA пока fail-open, чтобы не сломать поток.
    """

    def __init__(
        self,
        config_path: str | Path = "runtime/session_side_execution_gate_v1.json",
        *,
        fail_open: bool = True,
    ) -> None:
        self.config_path = Path(config_path)
        self.fail_open = bool(fail_open)
        self._loaded = False
        self._allow: list[dict] = []
        self._block: list[dict] = []
        self._insufficient: list[dict] = []

    def _load_once(self) -> None:
        if self._loaded:
            return

        if not self.config_path.exists():
            self._loaded = True
            return

        data = json.loads(self.config_path.read_text(encoding="utf-8"))

        self._allow = list(data.get("allow", []))
        self._block = list(data.get("block", []))
        self._insufficient = list(data.get("insufficient_data", []))
        self._loaded = True

    @staticmethod
    def session_name_for_hour(hour_msk: int) -> str:
        if 0 <= hour_msk <= 5:
            return "азиатская_сессия"
        if 6 <= hour_msk <= 11:
            return "утро_мск"
        if 12 <= hour_msk <= 15:
            return "московская_середина"
        if 16 <= hour_msk <= 20:
            return "вечерняя_сессия"
        return "ночь"

    @staticmethod
    def _hour_msk(ts: datetime | None = None) -> int:
        if ts is None:
            ts = datetime.now(tz=ZoneInfo("Europe/Moscow"))

        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=ZoneInfo("Europe/Moscow"))

        return int(ts.astimezone(ZoneInfo("Europe/Moscow")).hour)

    @staticmethod
    def _side(value: object) -> str:
        return str(value or "").upper().strip()

    @staticmethod
    def _matches(row: dict, *, symbol: str, side: str, hour_msk: int) -> bool:
        row_symbol = str(row.get("symbol") or "")
        row_side = str(row.get("entry_side") or "").upper().strip()
        row_hour = int(row.get("hour_msk"))

        symbol_ok = (
            row_symbol == symbol
            or (
                row_symbol == "BR_ROLLING@RTSX"
                and symbol.startswith("BR")
                and symbol.endswith("@RTSX")
            )
        )

        return symbol_ok and row_side == side and row_hour == hour_msk

    def decide(
        self,
        *,
        symbol: str,
        side: str,
        ts: datetime | None = None,
    ) -> SessionSideGateDecisionV1:
        self._load_once()

        side_norm = self._side(side)
        hour_msk = self._hour_msk(ts)
        session_name = self.session_name_for_hour(hour_msk)

        for row in self._block:
            if self._matches(row, symbol=symbol, side=side_norm, hour_msk=hour_msk):
                return SessionSideGateDecisionV1(
                    allowed=False,
                    action="BLOCK",
                    reason="session_side_negative_edge",
                    symbol=symbol,
                    side=side_norm,
                    hour_msk=hour_msk,
                    session_name=session_name,
                    matched_symbol=str(row.get("symbol")),
                    expectancy_points=float(row.get("expectancy_points") or 0.0),
                    closed_trades=int(row.get("closed_trades") or 0),
                )

        for row in self._allow:
            if self._matches(row, symbol=symbol, side=side_norm, hour_msk=hour_msk):
                return SessionSideGateDecisionV1(
                    allowed=True,
                    action="ALLOW",
                    reason="session_side_positive_edge",
                    symbol=symbol,
                    side=side_norm,
                    hour_msk=hour_msk,
                    session_name=session_name,
                    matched_symbol=str(row.get("symbol")),
                    expectancy_points=float(row.get("expectancy_points") or 0.0),
                    closed_trades=int(row.get("closed_trades") or 0),
                )

        for row in self._insufficient:
            if self._matches(row, symbol=symbol, side=side_norm, hour_msk=hour_msk):
                return SessionSideGateDecisionV1(
                    allowed=self.fail_open,
                    action="INSUFFICIENT_DATA",
                    reason="session_side_insufficient_data_fail_open",
                    symbol=symbol,
                    side=side_norm,
                    hour_msk=hour_msk,
                    session_name=session_name,
                    matched_symbol=str(row.get("symbol")),
                    expectancy_points=float(row.get("expectancy_points") or 0.0),
                    closed_trades=int(row.get("closed_trades") or 0),
                )

        return SessionSideGateDecisionV1(
            allowed=self.fail_open,
            action="NO_MATCH",
            reason="session_side_no_match_fail_open",
            symbol=symbol,
            side=side_norm,
            hour_msk=hour_msk,
            session_name=session_name,
        )
