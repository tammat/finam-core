from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_PATH = Path("config/generated/guard_decisions_v1.json")


class RuntimeGuardConfigLoaderV1:
    """
    Русский комментарий:
    Runtime-only loader.
    Никаких запросов в БД.
    Только чтение экспортированного analytics snapshot.
    """

    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else DEFAULT_PATH

        self._loaded = False
        self._items: list[dict[str, Any]] = []
        self._index: dict[tuple, dict[str, Any]] = {}

    def load(self) -> int:
        if not self.path.exists():
            print(
                f"RUNTIME_GUARD_CONFIG_NOT_FOUND path={self.path}",
                flush=True,
            )
            self._loaded = True
            self._items = []
            self._index = {}
            return 0

        payload = json.loads(self.path.read_text(encoding="utf-8"))

        self._items = payload.get("items") or []
        self._index = {}

        for item in self._items:
            key = self._build_key(
                symbol=item.get("symbol"),
                strategy=item.get("strategy"),
                timeframe=item.get("timeframe"),
                regime=item.get("regime"),
                volatility_regime=item.get("volatility_regime"),
                session_type=item.get("session_type"),
            )

            self._index[key] = item

        self._loaded = True

        print(
            f"RUNTIME_GUARD_CONFIG_LOADED path={self.path} items={len(self._items)}",
            flush=True,
        )

        return len(self._items)

    @staticmethod
    def _normalize(value: Any) -> str:
        if value is None:
            return "UNKNOWN"

        value = str(value).strip()

        if not value:
            return "UNKNOWN"

        return value.upper()

    def _build_key(
        self,
        *,
        symbol: Any,
        strategy: Any,
        timeframe: Any,
        regime: Any,
        volatility_regime: Any,
        session_type: Any,
    ) -> tuple:
        return (
            self._normalize(symbol),
            self._normalize(strategy),
            self._normalize(timeframe),
            self._normalize(regime),
            self._normalize(volatility_regime),
            self._normalize(session_type),
        )

    def lookup(
        self,
        *,
        symbol: str,
        strategy: str,
        timeframe: str | None = None,
        regime: str | None = None,
        volatility_regime: str | None = None,
        session_type: str | None = None,
    ) -> dict[str, Any] | None:
        if not self._loaded:
            self.load()

        key = self._build_key(
            symbol=symbol,
            strategy=strategy,
            timeframe=timeframe,
            regime=regime,
            volatility_regime=volatility_regime,
            session_type=session_type,
        )

        result = self._index.get(key)

        print(
            f"RUNTIME_GUARD_LOOKUP "
            f"symbol={symbol} "
            f"strategy={strategy} "
            f"timeframe={timeframe} "
            f"decision={result.get('guard_decision') if result else 'NONE'}",
            flush=True,
        )

        return result

    def decision(
        self,
        *,
        symbol: str,
        strategy: str,
        timeframe: str | None = None,
        regime: str | None = None,
        volatility_regime: str | None = None,
        session_type: str | None = None,
    ) -> str:
        result = self.lookup(
            symbol=symbol,
            strategy=strategy,
            timeframe=timeframe,
            regime=regime,
            volatility_regime=volatility_regime,
            session_type=session_type,
        )

        if not result:
            return "NO_RULE"

        return str(result.get("guard_decision") or "NO_RULE").upper()


if __name__ == "__main__":
    loader = RuntimeGuardConfigLoaderV1()

    loader.load()

    print(
        loader.decision(
            symbol="BR_ROLLING@RTSX",
            strategy="HISTORICAL_BREAKOUT_V1",
            timeframe="M5",
            regime="UNKNOWN",
            volatility_regime="UNKNOWN",
            session_type="UNKNOWN",
        )
    )
