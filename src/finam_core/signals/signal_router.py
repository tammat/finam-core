from __future__ import annotations

import os
import time
from dataclasses import dataclass

from finam_core.signals.signal_intent import SignalIntent
from finam_core.ai.sentiment_signal_enricher import SentimentSignalEnricher


@dataclass
class RoutedSignal:
    allowed: bool
    reason: str
    intent: SignalIntent | None = None


import time

_ROUTER_LOG_DEDUP = {}


def _log_allowed(key: str, ttl_seconds: int = 300) -> bool:
    now = time.time()
    last = _ROUTER_LOG_DEDUP.get(key)
    if last is not None and (now - last) < ttl_seconds:
        return False
    _ROUTER_LOG_DEDUP[key] = now
    return True


class SignalRouter:

    def __init__(self):
        self.min_confidence = float(os.getenv("SIGNAL_MIN_CONFIDENCE", "0.0"))
        self.score_min = float(os.getenv("SIGNAL_SCORE_MIN", "0.0"))
        self.score_max = float(os.getenv("SIGNAL_SCORE_MAX", "1.0"))
        self.signal_ttl_sec = float(os.getenv("SIGNAL_TTL_SEC", "30"))
        self._last_by_symbol = {}
        self._last_ts_by_symbol = {}

        # Русский комментарий:
        # AI-сентимент только добавляется в features.
        # Он не принимает торговых решений и не отправляет заявки.
        self.enable_ai_sentiment_features = os.getenv("ENABLE_AI_SENTIMENT_FEATURES", "0") == "1"
        self.sentiment_enricher = (
            SentimentSignalEnricher()
            if self.enable_ai_sentiment_features
            else None
        )

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

            if self.sentiment_enricher is not None:
                features = self.sentiment_enricher.enrich(
                    symbol=str(intent["symbol"]),
                    features=features,
                )

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

        # --- AI FEATURE ENRICHMENT ---
        if self.sentiment_enricher is not None:
            intent.features = self.sentiment_enricher.enrich(
                symbol=intent.symbol,
                features=intent.features,
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

        # Русский комментарий: router diagnostics выключены по умолчанию, чтобы не засорять journal.
        if os.getenv("ROUTER_DEBUG_LOGS", "0") == "1":
            if _log_allowed(f"ROUTER_VOL:{intent.symbol}:{vol}", ttl_seconds=300):
                print(f"ROUTER_VOL {intent.symbol} atr_pct={atr_pct:.5f} vol={vol}", flush=True)

            ai_label = intent.features.get("ai_sentiment_label", "none")
            ai_source = intent.features.get("ai_sentiment_source", "none")

            if _log_allowed(f"ROUTER_AI_FEATURES:{intent.symbol}:{ai_label}:{ai_source}", ttl_seconds=300):
                print(
                    "ROUTER_AI_FEATURES "
                    f"symbol={intent.symbol} "
                    f"label={ai_label} "
                    f"score={intent.features.get('ai_sentiment_score', 0.0)} "
                    f"source={ai_source} "
                    f"ts={intent.features.get('ai_sentiment_ts', 'none')}",
                    flush=True,
                )

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
