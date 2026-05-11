# -*- coding: utf-8 -*-

import os
import time

class RegimeDecision:
    """
    Результат оценки режима рынка
    """

    def __init__(self, trend: str, vol: str, tradable: bool, atr: float):
        self.trend = trend            # "up" | "down" | "flat"
        self.vol = vol                # "low" | "normal" | "high"
        self.tradable = tradable      # можно ли торговать
        self.atr = atr                # числовое значение ATR
    @property

    def volatility(self) -> str:
        """
        Совместимость с pipeline (alias для vol)
        """
        return self.vol

    def is_tradeable(self):
        # минимум: либо тренд, либо волатильность

        if self.trend != "flat":
            return True

        if self.volatility in ("normal", "high"):
            return True

        return False

class RegimeEngine:
    """
    Regime Layer (production-ready baseline)

    Определяет:
    - тренд (по окну цен)
    - волатильность (по ATR)
    - торгуемость рынка
    """

    def __init__(self, window: int = 20):
        self.window = window
        self.prices: list[float] = []
        # Русский комментарий: анти-спам для regime logs в systemd journal.
        self._last_regime_engine_log_ts = 0.0
        self._last_regime_engine_log_key = None

    def evaluate(self, price: float, features: dict) -> RegimeDecision:
        """
        Главная точка входа (pipeline вызывает именно её)
        """

        # --- обновляем историю ---
        self.prices.append(price)
        if len(self.prices) > self.window:
            self.prices.pop(0)

        # --- TREND ---
        if len(self.prices) >= 5:
            if self.prices[-1] > self.prices[0]:
                trend = "up"
            elif self.prices[-1] < self.prices[0]:
                trend = "down"
            else:
                trend = "flat"
        else:
            trend = "flat"

        # --- ATR ---
        atr = float(features.get("atr", price * 0.003))

        # --- VOLATILITY ---
        if atr < price * 0.001:
            vol = "low"
        elif atr > price * 0.01:
            vol = "high"
        else:
            vol = "normal"

        # --- TRADEABILITY LOGIC ---
        # --- REGIME TYPE ---
        if trend in ("up", "down"):
            regime_type = "trend"
        elif vol in ("normal", "high"):
            regime_type = "range"
        else:
            regime_type = "dead"
        # ключевая логика: рынок плохой только если flat + low
        # более мягкий режим (для теста)
        # мягкий режим: разрешаем почти всё, кроме совсем мёртвого рынка
        tradable = not (trend == "flat" and vol == "low")
        # Русский комментарий: печатаем regime только при изменении режима или не чаще заданного интервала.
        now_ts = time.time()
        log_every_sec = float(os.getenv("REGIME_ENGINE_LOG_EVERY_SEC", "60"))
        log_key = (regime_type, trend, vol, tradable)
        if log_key != self._last_regime_engine_log_key or (
            now_ts - float(self._last_regime_engine_log_ts or 0.0)
        ) >= log_every_sec:
            self._last_regime_engine_log_ts = now_ts
            self._last_regime_engine_log_key = log_key
            print(
                f"REGIME type={regime_type} trend={trend} vol={vol} atr={atr:.4f} tradable={tradable}",
                flush=True,
            )
        decision = RegimeDecision(
            trend=trend,
            vol=vol,
            tradable=tradable,
            atr=atr,
        )

        decision.regime_type = regime_type  # ← ДОБАВЬ ЭТУ СТРОКУ

        return decision