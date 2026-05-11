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
        # Русский комментарий: гистерезис режима — новый режим должен подтвердиться несколько тиков подряд.
        self.confirm_ticks = int(os.getenv("REGIME_CONFIRM_TICKS", "3"))
        self._confirmed_regime_key = None
        self._candidate_regime_key = None
        self._candidate_regime_count = 0
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

        raw_regime_key = (regime_type, trend, vol, tradable)
        if self._confirmed_regime_key is None:
            self._confirmed_regime_key = raw_regime_key
        elif raw_regime_key != self._confirmed_regime_key:
            if raw_regime_key == self._candidate_regime_key:
                self._candidate_regime_count += 1
            else:
                self._candidate_regime_key = raw_regime_key
                self._candidate_regime_count = 1

            if self._candidate_regime_count >= self.confirm_ticks:
                self._confirmed_regime_key = raw_regime_key
                self._candidate_regime_key = None
                self._candidate_regime_count = 0
        else:
            self._candidate_regime_key = None
            self._candidate_regime_count = 0

        regime_type, trend, vol, tradable = self._confirmed_regime_key
        # Русский комментарий: жёсткий rate-limit regime logs — без печати на каждое изменение режима.
        now_ts = time.time()
        log_every_sec = float(os.getenv("REGIME_ENGINE_LOG_EVERY_SEC", "60"))
        if (now_ts - float(self._last_regime_engine_log_ts or 0.0)) >= log_every_sec:
            self._last_regime_engine_log_ts = now_ts
            self._last_regime_engine_log_key = (regime_type, trend, vol, tradable)
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