from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from finam_core.analytics.runtime_guard_config_loader_v1 import (
    RuntimeGuardConfigLoaderV1,
)
from finam_core.runtime.research_contract_key_v1 import (
    normalize_research_contract_key_v1,
)


@dataclass(slots=True)
class RuntimeGuardDecision:
    """
    Русский комментарий:
    Runtime-safe normalized decision object.
    Пока НЕ влияет на execution/risk.
    Только observability/telemetry.
    """

    symbol: str
    strategy: str
    timeframe: str

    regime: str
    volatility_regime: str
    session_type: str

    decision: str
    reason: str

    matched: bool

    closed_total: int | None = None
    winrate: float | None = None
    profit_factor: float | None = None
    expectancy: float | None = None


class RuntimeGuardDecisionAdapterV1:
    """
    Русский комментарий:
    Adapter между runtime strategy flow и analytics snapshot.
    Без доступа к БД.
    Без блокировки исполнения.
    """

    def __init__(
        self,
        loader: RuntimeGuardConfigLoaderV1 | None = None,
    ):
        self.loader = loader or RuntimeGuardConfigLoaderV1()

    @staticmethod
    def _normalize(value: Any, default: str = "UNKNOWN") -> str:
        if value is None:
            return default

        value = str(value).strip()

        if not value:
            return default

        return value.upper()

    def evaluate(
        self,
        *,
        symbol: str,
        strategy: str,
        timeframe: str | None = None,
        regime: str | None = None,
        volatility_regime: str | None = None,
        session_type: str | None = None,
    ) -> RuntimeGuardDecision:
        requested_key = normalize_research_contract_key_v1(
            symbol=symbol,
            strategy=strategy,
            timeframe=timeframe,
            side="UNKNOWN",
            session_name=session_type,
            regime=regime,
        )

        result = self.loader.lookup(
            symbol=symbol,
            strategy=strategy,
            timeframe=timeframe,
            regime=regime,
            volatility_regime=volatility_regime,
            session_type=session_type,
        )

        if not result:
            decision = RuntimeGuardDecision(
                symbol=requested_key.normalized_symbol,
                strategy=requested_key.strategy,
                timeframe=requested_key.timeframe,

                regime=self._normalize(regime),
                volatility_regime=self._normalize(volatility_regime),
                session_type=self._normalize(session_type),

                decision="NO_RULE",
                reason="runtime_guard_rule_not_found",

                matched=False,
            )

            print(
                "GUARD_DECISION_RUNTIME "
                f"symbol={decision.symbol} "
                f"strategy={decision.strategy} "
                f"timeframe={decision.timeframe} "
                f"decision={decision.decision} "
                f"matched={decision.matched} "
                f"reason={decision.reason}",
                flush=True,
            )

            return decision

        decision = RuntimeGuardDecision(
            # Snapshot может содержать истёкший конкретный контракт (BRN6).
            # В telemetry всегда показываем канонический ключ текущего запроса.
            symbol=requested_key.normalized_symbol,
            strategy=requested_key.strategy,
            timeframe=requested_key.timeframe,

            regime=self._normalize(result.get("regime")),
            volatility_regime=self._normalize(result.get("volatility_regime")),
            session_type=self._normalize(result.get("session_type")),

            decision=self._normalize(result.get("guard_decision")),
            reason=str(result.get("guard_reason") or ""),

            matched=True,

            closed_total=result.get("closed_total"),
            winrate=result.get("winrate"),
            profit_factor=result.get("profit_factor"),
            expectancy=result.get("expectancy"),
        )

        print(
            "GUARD_DECISION_RUNTIME "
            f"symbol={decision.symbol} "
            f"strategy={decision.strategy} "
            f"timeframe={decision.timeframe} "
            f"decision={decision.decision} "
            f"matched={decision.matched} "
            f"closed_total={decision.closed_total} "
            f"pf={decision.profit_factor} "
            f"expectancy={decision.expectancy}",
            flush=True,
        )

        return decision


if __name__ == "__main__":
    adapter = RuntimeGuardDecisionAdapterV1()

    result = adapter.evaluate(
        symbol="BR_ROLLING@RTSX",
        strategy="HISTORICAL_BREAKOUT_V1",
        timeframe="M5",
        regime="UNKNOWN",
        volatility_regime="UNKNOWN",
        session_type="UNKNOWN",
    )

    print(result)
