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

    def __init__(self):
        self.min_confidence = float(os.getenv("SIGNAL_MIN_CONFIDENCE", "0.0"))
        self.score_min = float(os.getenv("SIGNAL_SCORE_MIN", "0.0"))
        self.score_max = float(os.getenv("SIGNAL_SCORE_MAX", "1.0"))
        self.signal_ttl_sec = float(os.getenv("SIGNAL_TTL_SEC", "30"))
        self._last_by_symbol = {}
        self._last_ts_by_symbol = {}

    def normalize_confidence(self, score) -> float:
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

        # --- NORMALIZE INPUT ---
        if isinstance(intent, dict):
            price = intent.get("price") or intent.get("last") or intent.get("last_price")
            if price is None:
                return RoutedSignal(False, "no_price", None)

            price = float(price)
            side = str(intent.get("side", "")).upper()

            features = dict(intent.get("features", {}))
            atr = float(features.get("atr", abs(price * 0.003)))

            stop = price - atr if side == "BUY" else price + atr
            take = price + atr * 2 if side == "BUY" else price - atr * 2

            rr = abs(take - price) / max(1e-9, abs(price - stop))

            features.update({
                "entry": price,
                "stop": stop,
                "take": take,
                "rr": rr,
                "atr": atr,
            })

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

        # --- VALIDATION ---
        if intent.side.upper() not in ("BUY", "SELL"):
            return RoutedSignal(False, "invalid_side", intent)

        if intent.qty <= 0:
            return RoutedSignal(False, "invalid_qty", intent)

        if intent.confidence < self.min_confidence:
            return RoutedSignal(False, "low_confidence", intent)

        rr = float(intent.features.get("rr", 0))
        if rr < 1.5:
            return RoutedSignal(False, "low_rr", intent)

        # --- VOL ---
        atr = float(intent.features.get("atr", 0.0))
        entry = float(intent.features.get("entry", 0.0))

        atr_pct = (atr / entry) if entry > 0 else 0.0
        intent.features["atr_pct"] = atr_pct

        if atr_pct < 0.0005:
            vol = "dead"
        elif atr_pct < 0.0015:
            vol = "low"
        elif atr_pct < 0.005:
            vol = "normal"
        else:
            vol = "high"

        intent.features["volatility"] = vol

        if vol == "dead":
            intent.confidence *= 0.5
            intent.qty *= 0.5

        elif vol == "low":
            intent.confidence *= 0.8
            intent.qty *= 0.8

        print(f"ROUTER_VOL {intent.symbol} atr_pct={atr_pct:.5f} vol={vol}", flush=True)

        # --- DEDUP ---
        key = f"{intent.symbol}:{intent.side}:{intent.reason}"
        now = time.time()

        if (
            self._last_by_symbol.get(intent.symbol) == key
            and now - self._last_ts_by_symbol.get(intent.symbol, 0) < self.signal_ttl_sec
        ):
            return RoutedSignal(False, "duplicate_signal", intent)

        self._last_by_symbol[intent.symbol] = key
        self._last_ts_by_symbol[intent.symbol] = now

        return RoutedSignal(True, "ok", intent)
