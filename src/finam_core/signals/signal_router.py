# src/finam_core/signals/signal_router.py

from __future__ import annotations

import os
import time
from dataclasses import dataclass

from finam_core.signals.signal_intent import SignalIntent


@dataclass
class RoutedSignal:
    allowed: bool
    reason: str
    intent: SignalIntent | None = None


class SignalRouter:
    """
    Русский коммент: минимальный SignalRouter.
    Нормализует и фильтрует сигналы до risk-stack.
    """

    def __init__(self):
        self.min_confidence = float(os.getenv("SIGNAL_MIN_CONFIDENCE", "0.0"))
        self.score_min = float(os.getenv("SIGNAL_SCORE_MIN", "0.0"))
        self.score_max = float(os.getenv("SIGNAL_SCORE_MAX", "1.0"))
        self.signal_ttl_sec = float(os.getenv("SIGNAL_TTL_SEC", "30"))
        self._last_by_symbol: dict[str, str] = {}
        self._last_ts_by_symbol: dict[str, float] = {}

    def normalize_confidence(self, score) -> float:
        """Русский коммент: нормализуем score стратегии в confidence 0..1."""
        try:
            value = float(score)
        except Exception:
            return 1.0

        if self.score_max <= self.score_min:
            return max(0.0, min(1.0, value))

        normalized = (value - self.score_min) / (self.score_max - self.score_min)
        return max(0.0, min(1.0, normalized))

    def route(self, intent: SignalIntent | dict | None) -> RoutedSignal:
        if intent is None:
            return RoutedSignal(False, "no_signal", None)

        if isinstance(intent, dict):
            # 🔹 цена обязательна
            price = intent.get("price") or intent.get("last") or intent.get("last_price")
            if price is None:
                return RoutedSignal(False, "no_price", None)

            price = float(price)
            side = str(intent["side"]).upper()

            # 🔹 ATR (или fallback)
            atr = float(intent.get("features", {}).get("atr", price * 0.005))

            # 🔹 уровни
            stop = price - atr if side == "BUY" else price + atr
            take = price + atr * 2 if side == "BUY" else price - atr * 2

            # 🔹 RR
            rr = abs(take - price) / max(1e-9, abs(price - stop))

            # 🔹 расширяем features (КЛЮЧЕВО!)
            features = dict(intent.get("features", {}))
            features.update({
                "entry": price,
                "stop": stop,
                "take": take,
                "rr": rr,
            })

            # 🔹 создаём ЧИСТЫЙ SignalIntent
            intent = SignalIntent(
                symbol=intent["symbol"],
                side=side,
                qty=float(intent.get("qty", 1.0)),
                source=str(intent.get("source", "legacy_strategy")),
                confidence=self.normalize_confidence(
                    intent.get("confidence", intent.get("score", 1.0))
                ),
                reason=str(intent.get("reason", "")),
                features=features,
            )

        # 🔹 базовые проверки
        if intent.side.upper() not in ("BUY", "SELL"):
            return RoutedSignal(False, "invalid_side", intent)

        if intent.qty <= 0:
            return RoutedSignal(False, "invalid_qty", intent)

        if intent.confidence < self.min_confidence:
            return RoutedSignal(False, "low_confidence", intent)
        # 🔹 фильтр по Risk/Reward
        rr = intent.features.get("rr", 0)
        if rr < 1.5:
            return RoutedSignal(False, "low_rr", intent)
        # 🔹 фильтр волатильности (убираем шум)
        atr = intent.features.get("atr", 0)
        entry = intent.features.get("entry", 0)

        # защита от деления на ноль и мусора
        if entry > 0 and atr < entry * 0.003:
            return RoutedSignal(False, "low_volatility", intent)
        # 🔹 фильтр тренда (если стратегия передаёт, с fallback)
        trend = intent.features.get("trend")

        # Русский коммент: если тренд не передан или явно flat — не торгуем
        if trend is None or trend == "flat":
            return RoutedSignal(False, "no_trend", intent)
        # 🔹 антидубли
        key = f"{intent.symbol}:{intent.side.upper()}:{intent.reason}"
        now = time.time()
        last_key = self._last_by_symbol.get(intent.symbol)
        last_ts = self._last_ts_by_symbol.get(intent.symbol, 0.0)

        if last_key == key and (now - last_ts) < self.signal_ttl_sec:
            return RoutedSignal(False, "duplicate_signal", intent)

        self._last_by_symbol[intent.symbol] = key
        self._last_ts_by_symbol[intent.symbol] = now

        return RoutedSignal(True, "ok", intent)