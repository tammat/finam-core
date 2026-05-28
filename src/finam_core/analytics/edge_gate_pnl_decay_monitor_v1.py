from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class EdgeGateDecayDecisionV1:
    enabled: bool
    reason: str
    expectancy_points: float
    pnl_points: float
    closed_trades: int


class EdgeGatePnlDecayMonitorV1:
    """
    Русский комментарий:
    Runtime-монитор деградации edge.
    Автоматически отключает execution gate,
    если rolling expectancy становится отрицательным.
    """

    def __init__(
        self,
        state_path: str | Path = "runtime/edge_gate_decay_state_v1.json",
    ) -> None:
        self.state_path = Path(state_path)

        self.state = json.loads(
            self.state_path.read_text(encoding="utf-8")
        )

        self.enabled = bool(self.state.get("enabled", False))
        self.global_floor = float(
            self.state.get("global_expectancy_floor", 0.0)
        )

        self.window = int(
            self.state.get("rolling_window_trades", 25)
        )

        self.disable_negative_expectancy = bool(
            self.state.get(
                "disable_on_negative_expectancy",
                True,
            )
        )

        self.disable_negative_pnl = bool(
            self.state.get(
                "disable_on_negative_pnl",
                False,
            )
        )

        self.runtime_state = dict(
            self.state.get("runtime_state", {})
        )

    @staticmethod
    def _make_key(
        symbol: str,
        side: str,
        hour_msk: int,
    ) -> str:
        return f"{symbol}|{side}|{hour_msk}"

    def evaluate(
        self,
        *,
        symbol: str,
        side: str,
        hour_msk: int,
        expectancy_points: float,
        pnl_points: float,
        closed_trades: int,
    ) -> EdgeGateDecayDecisionV1:

        if not self.enabled:
            return EdgeGateDecayDecisionV1(
                enabled=True,
                reason="decay_monitor_disabled",
                expectancy_points=expectancy_points,
                pnl_points=pnl_points,
                closed_trades=closed_trades,
            )

        key = self._make_key(
            symbol=symbol,
            side=side,
            hour_msk=hour_msk,
        )

        self.runtime_state[key] = {
            "expectancy_points": expectancy_points,
            "pnl_points": pnl_points,
            "closed_trades": closed_trades,
        }

        self.state["runtime_state"] = self.runtime_state

        self.state_path.write_text(
            json.dumps(
                self.state,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        if (
            self.disable_negative_expectancy
            and expectancy_points <= self.global_floor
        ):
            return EdgeGateDecayDecisionV1(
                enabled=False,
                reason="negative_expectancy_decay",
                expectancy_points=expectancy_points,
                pnl_points=pnl_points,
                closed_trades=closed_trades,
            )

        if (
            self.disable_negative_pnl
            and pnl_points <= 0
        ):
            return EdgeGateDecayDecisionV1(
                enabled=False,
                reason="negative_pnl_decay",
                expectancy_points=expectancy_points,
                pnl_points=pnl_points,
                closed_trades=closed_trades,
            )

        return EdgeGateDecayDecisionV1(
            enabled=True,
            reason="edge_decay_ok",
            expectancy_points=expectancy_points,
            pnl_points=pnl_points,
            closed_trades=closed_trades,
        )
