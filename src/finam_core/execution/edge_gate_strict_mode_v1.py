from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class EdgeGateStrictDecisionV1:
    allowed: bool
    reason: str
    expectancy_points: float | None
    closed_trades: int | None
    matched_symbol: str | None = None
    hour_msk: int | None = None


class EdgeGateStrictModeV1:
    """
    Русский комментарий:
    Строгий runtime-фильтр поверх session-side gate.
    Пропускает только окна с положительным expectancy и достаточной выборкой.
    """

    def __init__(
        self,
        config_path: str | Path = "runtime/edge_gate_strict_mode_v1.json",
    ) -> None:
        self.config_path = Path(config_path)
        self.config = json.loads(self.config_path.read_text(encoding="utf-8"))

        self.enabled = bool(self.config.get("enabled", False))
        self.threshold = float(self.config.get("strict_expectancy_threshold", 0.0))
        self.min_closed_trades = int(self.config.get("strict_min_closed_trades", 30))

        self.rows: list[dict] = []

        for src in self.config.get("sources", []):
            p = Path(src)
            if not p.exists():
                continue

            data = json.loads(p.read_text(encoding="utf-8"))

            self.rows.extend(data.get("allow", []))
            self.rows.extend(data.get("block", []))
            self.rows.extend(data.get("insufficient_data", []))

    @staticmethod
    def _current_hour_msk() -> int:
        return int(datetime.now(tz=ZoneInfo("Europe/Moscow")).hour)

    @staticmethod
    def _symbol_matches(row_symbol: str, symbol: str) -> bool:
        return (
            row_symbol == symbol
            or (
                row_symbol == "BR_ROLLING@RTSX"
                and symbol.startswith("BR")
                and symbol.endswith("@RTSX")
            )
        )

    def evaluate(
        self,
        *,
        symbol: str,
        side: str,
        hour_msk: int | None = None,
    ) -> EdgeGateStrictDecisionV1:
        if hour_msk is None:
            hour_msk = self._current_hour_msk()

        if not self.enabled:
            return EdgeGateStrictDecisionV1(
                allowed=True,
                reason="strict_mode_disabled",
                expectancy_points=None,
                closed_trades=None,
                hour_msk=hour_msk,
            )

        side_norm = str(side or "").upper().strip()

        matched: dict | None = None

        for row in self.rows:
            row_symbol = str(row.get("symbol") or "")
            row_side = str(row.get("entry_side") or "").upper().strip()
            row_hour = int(row.get("hour_msk") or -1)

            if (
                self._symbol_matches(row_symbol, str(symbol))
                and row_side == side_norm
                and row_hour == int(hour_msk)
            ):
                matched = row
                break

        if matched is None:
            return EdgeGateStrictDecisionV1(
                allowed=False,
                reason="strict_mode_no_match",
                expectancy_points=None,
                closed_trades=None,
                hour_msk=hour_msk,
            )

        expectancy = float(matched.get("expectancy_points") or 0.0)
        closed_trades = int(matched.get("closed_trades") or 0)
        matched_symbol = str(matched.get("symbol") or "")

        if closed_trades < self.min_closed_trades:
            return EdgeGateStrictDecisionV1(
                allowed=False,
                reason="strict_mode_low_sample",
                expectancy_points=expectancy,
                closed_trades=closed_trades,
                matched_symbol=matched_symbol,
                hour_msk=hour_msk,
            )

        if expectancy <= self.threshold:
            return EdgeGateStrictDecisionV1(
                allowed=False,
                reason="strict_mode_non_positive_expectancy",
                expectancy_points=expectancy,
                closed_trades=closed_trades,
                matched_symbol=matched_symbol,
                hour_msk=hour_msk,
            )

        return EdgeGateStrictDecisionV1(
            allowed=True,
            reason="strict_mode_positive_expectancy",
            expectancy_points=expectancy,
            closed_trades=closed_trades,
            matched_symbol=matched_symbol,
            hour_msk=hour_msk,
        )
