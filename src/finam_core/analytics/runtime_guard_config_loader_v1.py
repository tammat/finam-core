from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from finam_core.runtime.research_contract_key_v1 import (
    normalize_research_contract_key_v1,
)


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
        self._loaded_mtime_ns: int | None = None
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
        self._loaded_mtime_ns = self.path.stat().st_mtime_ns

        print(
            f"RUNTIME_GUARD_CONFIG_LOADED path={self.path} items={len(self._items)}",
            flush=True,
        )

        return len(self._items)

    def _reload_if_changed(self) -> None:
        """Подхватывает новый безопасный snapshot без перезапуска pipeline."""
        try:
            current_mtime_ns = self.path.stat().st_mtime_ns
        except FileNotFoundError:
            current_mtime_ns = None
        if current_mtime_ns != self._loaded_mtime_ns:
            self.load()

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
        contract_key = normalize_research_contract_key_v1(
            symbol=str(symbol or "UNKNOWN"),
            strategy=str(strategy or "UNKNOWN"),
            timeframe=str(timeframe or "UNKNOWN"),
            side="UNKNOWN",
            session_name=str(session_type or "UNKNOWN"),
            regime=str(regime or "UNKNOWN"),
        )
        return (
            self._normalize(contract_key.normalized_symbol),
            self._normalize(contract_key.strategy),
            self._normalize(contract_key.timeframe),
            self._normalize(contract_key.regime_code),
            self._normalize(volatility_regime),
            self._normalize(contract_key.session_name),
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
        else:
            self._reload_if_changed()

        key = self._build_key(
            symbol=symbol,
            strategy=strategy,
            timeframe=timeframe,
            regime=regime,
            volatility_regime=volatility_regime,
            session_type=session_type,
        )

        result = self._index.get(key)

        # Исторические отчёты часто имеют UNKNOWN для режима/волатильности/сессии.
        # Разрешаем только безопасное обобщённое правило с теми же
        # symbol × strategy. Пустой исторический timeframe также может покрыть
        # конкретный runtime-timeframe. Это не создаёт ALLOW: решение берётся
        # из рассчитанного snapshot, а при нескольких правилах побеждает самое
        # ограничительное.
        if result is None:
            prefix = key[:2]
            candidates = [
                item
                for candidate_key, item in self._index.items()
                if candidate_key[:2] == prefix
                and all(
                    expected == actual or actual == "UNKNOWN"
                    for expected, actual in zip(key[2:], candidate_key[2:])
                )
            ]
            if candidates:
                rank = {
                    "BLOCK": 0,
                    "INSUFFICIENT_DATA": 1,
                    "WATCH": 2,
                    "ALLOW": 3,
                }
                result = min(
                    candidates,
                    key=lambda item: rank.get(
                        str(item.get("guard_decision") or "").upper(),
                        -1,
                    ),
                )

        canonical = normalize_research_contract_key_v1(
            symbol=symbol,
            strategy=strategy,
            timeframe=timeframe,
            side="UNKNOWN",
            session_name=session_type,
            regime=regime,
        )
        print(
            f"RUNTIME_GUARD_LOOKUP "
            f"symbol={canonical.normalized_symbol} "
            f"strategy={canonical.strategy} "
            f"timeframe={canonical.timeframe} "
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
