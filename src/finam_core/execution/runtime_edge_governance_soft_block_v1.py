from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from finam_core.execution.session_side_execution_gate_v1 import SessionSideExecutionGateV1
from finam_core.execution.edge_gate_strict_mode_v1 import EdgeGateStrictModeV1


@dataclass(frozen=True)
class RuntimeEdgeGovernanceSoftBlockDecisionV1:
    allowed: bool
    action: str
    reason: str
    symbol: str
    side: str
    hour_msk: int
    session_action: str
    strict_reason: str | None
    decay_state: str | None
    expectancy_points: float | None
    closed_trades: int | None


class RuntimeEdgeGovernanceSoftBlockV1:
    """
    Русский комментарий:
    Phase2 soft runtime blocking.
    Единая точка принятия governance-решения:
    session-side gate → strict mode → decay state.
    """

    def __init__(
        self,
        *,
        session_gate_path: str | Path = "runtime/session_side_execution_gate_v1.json",
        strict_config_path: str | Path = "runtime/edge_gate_strict_mode_v1.json",
        decay_state_path: str | Path = "runtime/edge_gate_decay_state_v1.json",
    ) -> None:
        self.session_gate = SessionSideExecutionGateV1(session_gate_path)
        self.strict_gate = EdgeGateStrictModeV1(strict_config_path)
        self.decay_state_path = Path(decay_state_path)

    @staticmethod
    def _hour_msk(ts: datetime | None = None) -> int:
        if ts is None:
            ts = datetime.now(tz=ZoneInfo("Europe/Moscow"))

        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=ZoneInfo("Europe/Moscow"))

        return int(ts.astimezone(ZoneInfo("Europe/Moscow")).hour)

    @staticmethod
    def _decay_key_candidates(symbol: str, side: str, hour_msk: int) -> list[str]:
        side_norm = str(side or "").upper().strip()
        keys = [f"{symbol}|{side_norm}|{hour_msk}"]

        if symbol.startswith("BR") and symbol.endswith("@RTSX"):
            keys.append(f"BR_ROLLING@RTSX|{side_norm}|{hour_msk}")

        return keys

    def _decay_state_for(
        self,
        *,
        symbol: str,
        side: str,
        hour_msk: int,
    ) -> tuple[str | None, float | None, int | None]:
        if not self.decay_state_path.exists():
            return None, None, None

        data = json.loads(self.decay_state_path.read_text(encoding="utf-8"))
        runtime_state = data.get("runtime_state", {}) or {}

        for key in self._decay_key_candidates(symbol, side, hour_msk):
            row = runtime_state.get(key)
            if not row:
                continue

            expectancy = float(row.get("expectancy_points") or 0.0)
            closed_trades = int(row.get("closed_trades") or 0)
            decay_state = "DECAY" if expectancy <= 0 else "HEALTHY"

            return decay_state, expectancy, closed_trades

        return None, None, None

    def decide(
        self,
        *,
        symbol: str,
        side: str,
        ts: datetime | None = None,
    ) -> RuntimeEdgeGovernanceSoftBlockDecisionV1:
        side_norm = str(side or "").upper().strip()
        hour_msk = self._hour_msk(ts)

        session_decision = self.session_gate.decide(
            symbol=symbol,
            side=side_norm,
            ts=ts,
        )

        if not session_decision.allowed:
            return RuntimeEdgeGovernanceSoftBlockDecisionV1(
                allowed=False,
                action="SOFT_BLOCK",
                reason="session_side_gate_block",
                symbol=symbol,
                side=side_norm,
                hour_msk=hour_msk,
                session_action=session_decision.action,
                strict_reason=None,
                decay_state=None,
                expectancy_points=session_decision.expectancy_points,
                closed_trades=session_decision.closed_trades,
            )

        strict_decision = self.strict_gate.evaluate(
            symbol=symbol,
            side=side_norm,
            hour_msk=hour_msk,
        )

        if not strict_decision.allowed:
            return RuntimeEdgeGovernanceSoftBlockDecisionV1(
                allowed=False,
                action="SOFT_BLOCK",
                reason="strict_gate_block",
                symbol=symbol,
                side=side_norm,
                hour_msk=hour_msk,
                session_action=session_decision.action,
                strict_reason=strict_decision.reason,
                decay_state=None,
                expectancy_points=strict_decision.expectancy_points,
                closed_trades=strict_decision.closed_trades,
            )

        decay_state, decay_expectancy, decay_closed = self._decay_state_for(
            symbol=symbol,
            side=side_norm,
            hour_msk=hour_msk,
        )

        if decay_state == "DECAY":
            return RuntimeEdgeGovernanceSoftBlockDecisionV1(
                allowed=False,
                action="SOFT_BLOCK",
                reason="decay_monitor_block",
                symbol=symbol,
                side=side_norm,
                hour_msk=hour_msk,
                session_action=session_decision.action,
                strict_reason=strict_decision.reason,
                decay_state=decay_state,
                expectancy_points=decay_expectancy,
                closed_trades=decay_closed,
            )

        return RuntimeEdgeGovernanceSoftBlockDecisionV1(
            allowed=True,
            action="ALLOW",
            reason="runtime_edge_governance_allow",
            symbol=symbol,
            side=side_norm,
            hour_msk=hour_msk,
            session_action=session_decision.action,
            strict_reason=strict_decision.reason,
            decay_state=decay_state,
            expectancy_points=strict_decision.expectancy_points,
            closed_trades=strict_decision.closed_trades,
        )
