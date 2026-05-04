# src/finam_core/pipelines/paper_pipeline.py
# Русский коммент: Pipeline B (event-driven).
# QUOTE -> Strategy -> Risдавайk -> PaperExecution -> publish(FILL) -> Accounting(PM.apply_fill)

from __future__ import annotations
from finam_core.storage.postgres_logger import PostgresLogger
import os
import logging
import os
import time
from types import SimpleNamespace

from finam_core.execution.execution_fill import ExecutionFill
from finam_core.accounting.fees import FeeTaxModel
from finam_core.risk.trailing_exit import TrailingExitEngine
from finam_core.notifications.telegram_notifier import TelegramNotifier
from finam_core.storage.postgres_logger import PostgresLogger
from finam_core.risk.sl_tp_cooldown import SlTpCooldownEngine
from finam_core.risk.volatility_risk import VolatilityRiskEngine
from finam_core.risk.live_atr import LiveAtrEstimator
from finam_core.risk.portfolio_heat import PortfolioHeatEngine
from finam_core.risk.kill_switch import KillSwitchEngine
from finam_core.risk.correlation_risk import CorrelationRiskEngine
from finam_core.risk.unified_decision import UnifiedRiskDecision, RiskDecisionRecorder
from finam_core.signals.signal_router import SignalRouter
from finam_core.features.live_feature_buffer import LiveFeatureBuffer
from finam_core.regime.regime_engine import RegimeEngine
from finam_core.data.mtf_aggregator import MTFBarAggregator
from core.instrument_resolver import InstrumentResolver
from finam_core.strategy.br_conservative_breakout import BrConservativeBreakout
from finam_core.risk.finam_limits_adapter import FinamLimitsAdapter
from finam_core.risk.regime_policy import RegimePolicy
# === RISK CLUSTERS (упрощённая корреляция) ===
CLUSTERS = {
    "energy": ["NG", "BR"],
    "metals": ["GC", "SI"],
    "fx": ["SR"],
}
LOG = logging.getLogger(__name__)


def _safe_float(x, default=0.0) -> float:
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default


def _get_price_from_state(st: dict, side: str) -> float | None:
    """Русский коммент: берём last, иначе ask/bid по направлению."""
    last = st.get("last")
    bid = st.get("bid")
    ask = st.get("ask")

    px = last
    if px is None:
        px = ask if side.upper() == "BUY" else bid
    try:
        return float(px) if px is not None else None
    except Exception:
        return None


def build_risk_context(intent: dict, portfolio, market_state: dict):
    """
    Русский коммент: минимальный контекст для risk-правил.
    Важно: starting_capital/equity/total_exposure/current_symbol_exposure/trade_value.
    """
    sym = intent.get("symbol")
    side = str(intent.get("side", "BUY")).upper()
    qty = _safe_float(intent.get("qty", intent.get("quantity", 0)) or 0.0, default=0.0)

    px = _get_price_from_state(market_state, side) or 0.0
    trade_value = abs(qty) * px

    # equity / starting_capital
    equity = getattr(portfolio, "equity", None)
    equity = equity() if callable(equity) else equity
    if equity is None:
        equity = getattr(portfolio, "total_equity", None)
        equity = equity() if callable(equity) else equity
    equity = float(equity or 0.0)

    starting_capital = getattr(portfolio, "starting_cash", None)
    if starting_capital is None:
        starting_capital = getattr(portfolio, "initial_cash", None)
    if starting_capital is None:
        starting_capital = getattr(portfolio, "starting_capital", None)
    starting_capital = starting_capital() if callable(starting_capital) else starting_capital
    starting_capital = float(starting_capital or equity or 0.0)

    # exposures (best effort)
    total_exposure = getattr(portfolio, "total_exposure", None)
    if total_exposure is None:
        total_exposure = getattr(portfolio, "gross_exposure", None)
    total_exposure = float(total_exposure or 0.0)

    pm = getattr(portfolio, "position_manager", None)
    pos_qty = 0.0
    if pm is not None:
        try:
            pos = pm.positions.get(sym)
            pos_qty = float(getattr(pos, "qty", 0.0) or 0.0) if pos is not None else 0.0
        except Exception:
            pos_qty = 0.0

    current_symbol_exposure = abs(pos_qty) * px

    daily_realized_pnl = getattr(portfolio, "daily_realized_pnl", None)
    if daily_realized_pnl is None:
        daily_realized_pnl = getattr(pm, "daily_realized_pnl", 0.0) if pm is not None else 0.0

    portfolio_heat = getattr(portfolio, "portfolio_heat", 0.0) or 0.0

    return SimpleNamespace(
        symbol=sym,
        side=side,
        qty=float(qty),
        price=float(px),
        trade_value=float(trade_value),

        # === CORE RISK FIELDS ===
        portfolio_value=float(equity),
        realized_pnl=float(getattr(portfolio, "realized_pnl", 0.0) or 0.0),
        daily_realized_pnl=float(daily_realized_pnl or 0.0),
        max_drawdown=0.0,

        # === EXPOSURE ===
        total_exposure=float(total_exposure),
        current_symbol_exposure=float(current_symbol_exposure),
        portfolio_heat=float(portfolio_heat or 0.0),

        # === CAPITAL ===
        equity=float(equity),
        starting_capital=float(starting_capital),
        starting_cash=float(starting_capital),

        # === CONTEXT ===
        intent=intent,
        market_state=market_state,
        portfolio=portfolio,
    )


def _decision_allowed(decision) -> bool:
    """Русский коммент: нормализуем разные типы RiskDecision."""
    if isinstance(decision, bool):
        return decision
    if decision is None:
        # === FIX: если risk ничего не вернул — считаем OK (no blocking)
        return True
    for flag in ("allowed", "is_allowed", "ok", "approved", "pass_"):
        if hasattr(decision, flag):
            return bool(getattr(decision, flag))
    return bool(decision)


class PaperTradingPipeline:
    """MarketData → Strategy → Risk → PaperExecution → publish(FILL) → PM.apply_fill"""

    def __init__(self, bus, portfolio, position_manager, risk, paper, strategy, done=None, filter_engine=None, filter_context_builder=None):
        from finam_core.strategy.mean_reversion import MeanReversionStrategy
        from finam_core.session.session_manager import SessionManager

        self.session = SessionManager()
        self.mean_reversion = MeanReversionStrategy()

        self.bus = bus
        self.portfolio = portfolio
        self.pm = position_manager
        self.risk = risk
        self.paper = paper
        self.fee_tax = FeeTaxModel()
        self.strategy = strategy
        # Русский коммент: единый pre-risk фильтр сигналов. По умолчанию отключён.
        self.filter_engine = filter_engine
        self.filter_context_builder = filter_context_builder
        self._done = done

        self._mkt: dict[str, dict] = {}
        # === MTF buffers ===
        self._mtf = {}  # symbol -> buffers
        self.features = {}  # live feature buffers
        self._filled_once = False

        # Русский коммент: троттлинг логов котировок
        self._last_quote_log_ts = 0.0
        self._quote_log_every = float(os.getenv("QUOTE_LOG_EVERY", "0"))  # 0 = выключено
        self.trailing_exit = TrailingExitEngine()
        self._cooldown_until = {}
        self.notifier = TelegramNotifier()
        self.pg_logger = PostgresLogger()
        # Русский коммент: агрегатор закрытых M1/M5/M15 свечей из live quote потока.
        self.mtf_aggregator = MTFBarAggregator(("M1", "M5", "M15"))
        self.exit_engine = SlTpCooldownEngine()
        self.vol_risk = VolatilityRiskEngine()
        self.live_atr = LiveAtrEstimator()
        self.portfolio_heat = PortfolioHeatEngine()
        self.kill_switch = KillSwitchEngine()
        self.correlation_risk = CorrelationRiskEngine()
        self.risk_recorder = RiskDecisionRecorder(self.pg_logger)
        self.signal_router = SignalRouter()
        self.regime_engine = RegimeEngine()
        # Русский комментарий: BR_CONSERVATIVE_BREAKOUT_M5 работает только в PAPER и только как генератор сигналов.
        self.br_breakout_enabled = (
            os.getenv("EXECUTION_MODE", "paper").lower() == "paper"
            and os.getenv("ENABLE_BR_CONSERVATIVE_BREAKOUT", "0") == "1"
        )
        self.br_breakout_symbol = os.getenv("BR_BREAKOUT_SYMBOL", "BRM6@RTSX")
        self.br_breakout = BrConservativeBreakout(symbol=self.br_breakout_symbol) if self.br_breakout_enabled else None
        self.finam_limits_adapter = FinamLimitsAdapter()
        self.regime_policy = RegimePolicy()
        # === REGIME CONFIG (единая точка управления) ===
        self.regime_enabled = os.getenv("REGIME_ENABLE", "1") == "1"

        # параметры (можно потом вынести в config.py)
        self.regime_min_atr_pct = float(os.getenv("REGIME_MIN_ATR_PCT", "0.001"))
        self.regime_trend_mode = os.getenv("REGIME_TREND_MODE", "ema")  # ema / simple

        # debug
        LOG.info(
            "REGIME INIT enabled=%s min_atr_pct=%.5f trend_mode=%s",
            self.regime_enabled,
            self.regime_min_atr_pct,
            self.regime_trend_mode,
        )
        self._regime_last_log_ts = 0.0

    def _record_live_quote_to_storage(self, symbol: str, price: float, volume: float, ts) -> None:
        """Русский коммент: сохраняет live tick и закрытые MTF-свечи в PostgreSQL."""
        try:
            self.pg_logger.log_market_tick(
                symbol=symbol,
                price=float(price),
                volume=float(volume or 0.0),
            )
        except Exception as exc:
            LOG.warning("PIPE_MARKET_TICK_LOG_FAILED symbol=%s error=%s", symbol, exc)

        try:
            closed_bars = self.mtf_aggregator.update(
                symbol=symbol,
                price=float(price),
                volume=float(volume or 0.0),
                ts=ts,
            )

            for bar in closed_bars:
                self.pg_logger.log_market_bar(
                    symbol=bar.symbol,
                    timeframe=bar.timeframe,
                    ts=bar.ts,
                    open_price=bar.open,
                    high_price=bar.high,
                    low_price=bar.low,
                    close_price=bar.close_price,
                    volume=bar.volume,
                )
                self._process_br_closed_bar_for_paper_signal(bar)
                LOG.info(
                    "PIPE_MTF_BAR_CLOSED symbol=%s tf=%s ts=%s close=%s volume=%s",
                    bar.symbol,
                    bar.timeframe,
                    bar.ts,
                    bar.close_price,
                    bar.volume,
                )
        except Exception as exc:
            LOG.warning("PIPE_MTF_AGG_FAILED symbol=%s error=%s", symbol, exc)

    def attach(self):
        # Русский коммент: Pipeline B — подписываемся на QUOTE, а FILL применяем централизованно.
        self.bus.subscribe("QUOTE", self._on_quote)
        self.bus.subscribe("FILL", self._on_fill)
        LOG.debug("PIPE attach(): subscribed QUOTE/FILL")

    def _on_quote(self, event: dict):
        self._resolver = getattr(self, "_resolver", InstrumentResolver())

        raw_sym = event.get("symbol")
        sym = self._resolver.resolve(raw_sym)
        if not sym:
            return

        # === STATE UPDATE ===
        st = self._mkt.get(sym, {})
        prev_price = st.get("last")

        st.update(event)

        # prev_price НЕ обновляем здесь (используется в fallback)
        if "prev_price" not in st:
            st["prev_price"] = prev_price
        self._mkt[sym] = st

        last = st.get("last") or st.get("price") or st.get("bid") or st.get("ask")
        if last is None:
            return

        price = float(last)

        volume = _safe_float(event.get("volume", event.get("qty", 0.0)) or 0.0, default=0.0)
        ts = event.get("ts") or event.get("timestamp")
        if ts is None:
            from datetime import datetime, timezone
            ts = datetime.now(timezone.utc)

        # Русский коммент: рыночные данные сохраняем до session/risk/strategy фильтров.
        self._record_live_quote_to_storage(
            symbol=sym,
            price=price,
            volume=volume,
            ts=ts,
        )

        # =========================================================
        # === SESSION LAYER (ЕДИНЫЙ ИСТОЧНИК)
        # =========================================================
        session = self.session.get_regime()
        # === FORCE OVERRIDE (DEV MODE) ===
        if os.getenv("SESSION_OVERRIDE", "0") == "1":
            print("PIPE_SESSION_OVERRIDE_ACTIVE", flush=True)
            session = {
                "phase": "override",
                "allow_entries": True,
            }

        # =========================================================
        # === REGIME V2: STRATEGY ROUTER (АДАПТИВНЫЙ)
        # =========================================================
        regime_type = session.get("phase")

        # временная логика (дальше улучшим)
        if regime_type == "core":
            strategy_mode = "mr"   # mean reversion
        elif regime_type == "override":
            strategy_mode = "mr"
        else:
            strategy_mode = None

        # === SESSION FILTER (FIX: do not block in SIM/OVERRIDE) ===
        if not session.get("allow_entries", False):
            if os.getenv("SESSION_OVERRIDE", "0") == "1" or os.getenv("SIMULATE_MARKET", "0") == "1":
                print("PIPE_SESSION_BYPASS (override/sim)", flush=True)
            else:
                print(f"PIPE_SESSION_BLOCK phase={session.get('phase')}", flush=True)
                return
        # === FIX CRITICAL (GLOBAL PRICE) ===

        curr_price = price
        # === SIMULATION MOVE (CRITICAL) ===
        if os.getenv("SIMULATE_MARKET", "0") == "1":
            import random
            price = price * (1 + random.uniform(-0.002, 0.002))
            st["last"] = price
        # =========================================================
        # === MTF AGGREGATION (M1/M5/M15)
        # =========================================================
        mtf = self._mtf.setdefault(sym, {"m1": [], "m5": None, "m15": None})

        mtf["m1"].append(price)

        # ограничим буфер
        if len(mtf["m1"]) > 20:
            mtf["m1"] = mtf["m1"][-20:]

        if len(mtf["m1"]) >= 5:
            mtf["m5"] = sum(mtf["m1"][-5:]) / 5

        if len(mtf["m1"]) >= 15:
            mtf["m15"] = sum(mtf["m1"][-15:]) / 15

        st["m5"] = mtf["m5"]
        st["m15"] = mtf["m15"]

        # === LIVE ATR ===
        try:
            st["atr"] = self.live_atr.update(price)
        except Exception:
            pass

        # === MARK TO MARKET ===
        try:
            if hasattr(self.portfolio, "mark_price"):
                self.portfolio.mark_price(sym, price)
        except Exception:
            pass

        # =========================================================
        # === EXIT BLOCK (SL/TP / TRAILING)
        # =========================================================
        try:
            pos = self.pm.positions.get(sym)
            qty_now = float(getattr(pos, "qty", 0.0) or 0.0) if pos else 0.0
            avg_now = float(getattr(pos, "avg_price", 0.0) or 0.0) if pos else 0.0
        except Exception:
            qty_now = 0.0
            avg_now = 0.0

        if qty_now != 0.0:
            exit_decision = self.exit_engine.evaluate(sym, qty_now, avg_now, price)
            if exit_decision.should_exit:
                exit_intent = {
                    "symbol": sym,
                    "side": exit_decision.side,
                    "qty": exit_decision.qty,
                    "reason": exit_decision.reason,
                }

                print(f"PIPE_EXIT reason={exit_decision.reason}", flush=True)

                raw_fill = self.paper.execute(exit_intent, st)

                # === CONVERT TO ExecutionFill (NO RAW PaperFill IN BUS) ===
                raw_qty = float(getattr(raw_fill, "qty", exit_intent.get("qty", 0.0)) or 0.0)
                side = "SELL" if raw_qty < 0 else "BUY"
                exec_price = float(getattr(raw_fill, "price", st.get("last") or 0.0))

                commission = 0.0
                if hasattr(self.fee_tax, "commission"):
                    commission = self.fee_tax.commission(
                        symbol=exit_intent.get("symbol"),
                        qty=abs(raw_qty),
                        price=exec_price
                    )

                fill = ExecutionFill(
                    symbol=exit_intent.get("symbol"),
                    side=side,
                    qty=abs(raw_qty),
                    price=exec_price,
                    commission=commission,
                    fill_id=getattr(raw_fill, "fill_id", None),
                )

                self.bus.publish({"type": "FILL", "fill": fill})
                self.exit_engine.mark_exit(sym)
                # === LOSS COOLDOWN (LEVEL 2) ===
                try:
                    if "stop_loss" in exit_decision.reason:
                        self._cooldown_until[sym] = time.time() + 180  # 1 мин пауза
                except Exception:
                    pass
                return
        # === PROFIT PROTECTION (BREAK-EVEN + TRAILING) ===
        try:
            if avg_now > 0:
                if qty_now > 0:
                    pnl_pct = (price - avg_now) / avg_now
                else:
                    pnl_pct = (avg_now - price) / avg_now

                # === BREAK-EVEN ===
                if pnl_pct > 0.003:  # +0.3%
                    if qty_now > 0:
                        be_price = avg_now * 1.0005
                        if price > be_price:
                            self.exit_engine._dynamic_stops[sym] = be_price
                            print(f"PIPE_BE_LONG {be_price}", flush=True)
                    else:
                        be_price = avg_now * 0.9995
                        if price < be_price:
                            self.exit_engine._dynamic_stops[sym] = be_price
                            print(f"PIPE_BE_SHORT {be_price}", flush=True)

                # === TRAILING ===
                if pnl_pct > 0.006:  # +0.6%
                    trail_distance = max(st.get("atr", 0.0), price * 0.003)

                    if qty_now > 0:
                        trail_price = price - trail_distance
                        self.exit_engine._dynamic_stops[sym] = trail_price
                        print(f"PIPE_TRAIL_LONG {trail_price}", flush=True)
                    else:
                        trail_price = price + trail_distance
                        self.exit_engine._dynamic_stops[sym] = trail_price
                        print(f"PIPE_TRAIL_SHORT {trail_price}", flush=True)

        except Exception as e:
            print(f"PIPE_PROFIT_PROTECT_ERROR {e}", flush=True)
        # =========================================================
        # === FEATURES + REGIME (ОДИН РАЗ)
        # =========================================================

        prev_price = st.get("prev_price", price)

        # === ATR FIX (ограничение и нормализация) ===
        raw_atr = st.get("atr") or abs(price - prev_price) or price * 0.003
        atr = min(raw_atr, price * 0.02)  # максимум 2% от цены
        st["atr"] = atr

        # EMA trend
        alpha_fast = 2 / (5 + 1)
        alpha_slow = 2 / (20 + 1)

        ema_fast = alpha_fast * price + (1 - alpha_fast) * st.get("ema_fast", price)
        ema_slow = alpha_slow * price + (1 - alpha_slow) * st.get("ema_slow", price)

        st["ema_fast"] = ema_fast
        st["ema_slow"] = ema_slow

        if ema_fast > ema_slow:
            trend = "up"
        elif ema_fast < ema_slow:
            trend = "down"
        else:
            trend = "flat"

        features = {
            "atr": atr,
            "trend": trend,
            "m5": st.get("m5"),
            "m15": st.get("m15"),
        }

        # === REGIME ===
        if not self.regime_enabled:
            regime = SimpleNamespace(
                trend="any",
                volatility="any",
                atr=atr,
                is_tradeable=lambda: True,
            )
        else:
            regime = self.regime_engine.evaluate(price, features)

        # === SAVE REGIME STATE (robust, deterministic) ===
        trend_val = getattr(regime, "trend", "unknown")
        vol_val = getattr(regime, "volatility", "unknown")
        atr_val = _safe_float(getattr(regime, "atr", 0.0), 0.0)

        st["regime_trend"] = trend_val
        st["regime_vol"] = vol_val
        st["regime_atr"] = atr_val

        # === CONTROLLED LOG (ONLY ON CHANGE, WITH TIME GUARD) ===
        prev_trend = st.get("_last_logged_trend")
        prev_vol = st.get("_last_logged_vol")
        now_ts = time.time()

        # логируем либо при изменении режима, либо раз в 10 сек (антишум)
        if (
            (prev_trend != trend_val)
            or (prev_vol != vol_val)
            or (now_ts - self._regime_last_log_ts > 10)
        ):
            print(
                f"REGIME trend={trend_val} vol={vol_val} atr={round(atr_val, 5)}",
                flush=True,
            )

            st["_last_logged_trend"] = trend_val
            st["_last_logged_vol"] = vol_val
            self._regime_last_log_ts = now_ts

        # === TREND + VOL FILTER (LEVEL 2 STABLE) ===
        try:
            atr_pct = abs(regime.atr / price) if price else 0

            # === 1. Слабая волатильность → нет сделки
            if atr_pct < float(os.getenv("ATR_MIN_PCT","0.002")):
                print("PIPE_VOL_LOW_BLOCK", flush=True)
                return

            # === 2. Слишком высокая вола → шум
            if atr_pct > 0.03:
                print("PIPE_VOL_HIGH_BLOCK", flush=True)
                return

            # === 3. СЛАБЫЙ ТРЕНД (главный фикс)
            if regime.trend in ("up", "down"):
                trend_strength = abs(st.get("ema_fast", price) - st.get("ema_slow", price)) / price

                if trend_strength < float(os.getenv("TREND_STRENGTH_MIN","0.0003")) and regime.volatility != "high":  # ключевой параметр
                    print("PIPE_TREND_WEAK_BLOCK", flush=True)
                    return

        except Exception:
            pass


        # === NOISE FILTER (ATR sanity) ===
        try:
            if atr is not None and price is not None:
                atr_pct = abs(atr / price)
                if atr_pct > 0.1:  # >10% — мусорный сигнал
                    print("PIPE_NOISE_BLOCK high_atr", flush=True)
                    return
        except Exception:
            pass

        # =========================================================
        # === STRATEGY SELECTION (FIXED REGIME V2)
        # =========================================================
        raw_intent = None

        # ВАЖНО: используем РЕАЛЬНЫЙ regime (из regime_engine), а не session
        print(f"DEBUG REGIME_ROUTER trend={regime.trend} vol={regime.volatility}", flush=True)

        try:
            # === MTF FILTER (WEAK VERSION, no blocking) ===
            m5 = st.get("m5")
            if m5:
                trend = regime.trend

                if trend == "up" and not (price > m5):
                    print("PIPE_MTF_WEAK_LONG", flush=True)

                if trend == "down" and not (price < m5):
                    print("PIPE_MTF_WEAK_SHORT", flush=True)

            # === TREND MODE (BREAKOUT ONLY, STRATEGY DISABLED) ===
            if regime.trend in ("up", "down"):
                print("DEBUG breakout mode (strategy disabled)", flush=True)
                raw_intent = None  # force fallback breakout logic

            # === MEAN REVERSION ===
            elif regime.trend == "flat":
                print("DEBUG using mean_reversion", flush=True)

                raw_intent = self.mean_reversion.on_quote(st)
                print("DEBUG MR result:", raw_intent, flush=True)

                # fallback to breakout if no MR signal
                if raw_intent is None:
                    print("DEBUG fallback to breakout", flush=True)

        except Exception as e:
            print(f"STRATEGY_ERROR {e}", flush=True)
            return

        # === GLOBAL SAFETY (ensure variables always defined) ===
        curr_price = st.get("last")
        if curr_price is None:
            return

        atr = st.get("atr") or 0.0

        history = st.setdefault("price_history", [])
        if len(history) < 2:
            history.append(curr_price)
            return

        local_high = max(history[-10:])
        local_low = min(history[-10:])

        history.append(curr_price)
        if len(history) > 20:
            st["price_history"] = history[-20:]

        # === GLOBAL FALLBACK (BREAKOUT LEVELS + ATR) ===
        # PATCH: SMART ENTRY (RETEST MODE)
        # вставить в fallback breakout блок

        # === SMART ENTRY STATE ===
        st.setdefault("pending_breakout", None)

        # === DETECT BREAKOUT (не входим сразу) ===
        if curr_price > local_high - atr * 0.5:
            st["pending_breakout"] = {
                "side": "BUY",
                "level": local_high,
                "ts": time.time()
            }
            print(f"PIPE_BREAKOUT_DETECTED BUY level={local_high}", flush=True)

        elif curr_price < local_low + atr * 0.5:
            st["pending_breakout"] = {
                "side": "SELL",
                "level": local_low,
                "ts": time.time()
            }
            print(f"PIPE_BREAKOUT_DETECTED SELL level={local_low}", flush=True)

        # === RETEST ENTRY ===
        pb = st.get("pending_breakout")

        if pb:
            side = pb["side"]
            level = pb["level"]

            # TTL (устаревание сигнала)
            if time.time() - pb["ts"] > 60:
                st["pending_breakout"] = None
                return

            # BUY RETEST
            if side == "BUY":
                if curr_price <= level + atr * 0.2:
                    print("PIPE_SMART_ENTRY BUY", flush=True)
                    entry_side = "BUY"
                else:
                    return

            # SELL RETEST
            elif side == "SELL":
                if curr_price >= level - atr * 0.2:
                    print("PIPE_SMART_ENTRY SELL", flush=True)
                    entry_side = "SELL"
                else:
                    return

            # === EXECUTE ENTRY ===
            risk_per_trade = 0.01
            capital = getattr(self.portfolio, "starting_cash", 100000)
            risk_amount = capital * risk_per_trade

            atr_safe = max(atr, curr_price * 0.002)
            stop_distance = max(atr_safe * 2.0, curr_price * 0.01, 0.15)
            stop_distance = max(stop_distance, 0.05)

            qty = round(risk_amount / stop_distance, 3)
            qty = max(min(qty, 1.0), 0.1)

            rr = 2.0
            take_distance = stop_distance * rr

            raw_intent = {
                "symbol": sym,
                "side": entry_side,
                "qty": qty,
                "price": curr_price,
                "features": {
                    "stop": curr_price - stop_distance if entry_side == "BUY" else curr_price + stop_distance,
                    "take": curr_price + take_distance if entry_side == "BUY" else curr_price - take_distance,
                    "rr": rr,
                }
            }

            # сброс состояния
            st["pending_breakout"] = None

        else:
            return

        # === ROLLBACK PROTECTION (анти-плохой вход) ===
        try:
            last_price = st.get("last")
            prev_price = st.get("prev_price")

            if last_price and prev_price and raw_intent:
                move = abs(last_price - prev_price)

                # 1. слишком маленькое движение → шум
                if move < (st.get("atr", 0.0) or 0.0) * 0.1:
                    print("PIPE_ROLLBACK_BLOCK small_move", flush=True)
                    return

                # 2. вход против импульса
                side = raw_intent.get("side")
                if side == "BUY" and last_price < prev_price:
                    print("PIPE_ROLLBACK_BLOCK wrong_direction", flush=True)
                    return

                if side == "SELL" and last_price > prev_price:
                    print("PIPE_ROLLBACK_BLOCK wrong_direction", flush=True)
                    return

        except Exception as e:
            print(f"PIPE_ROLLBACK_ERROR {e}", flush=True)

        print("DEBUG raw_intent:", raw_intent, flush=True)
        print(f"DEBUG price_in_state last={st.get('last')} bid={st.get('bid')} ask={st.get('ask')}", flush=True)
        # === ENSURE PRICE IN INTENT (FIX no_price) ===
        try:
            if isinstance(raw_intent, dict):
                if "price" not in raw_intent or raw_intent.get("price") is None:
                    px = st.get("last") or st.get("price") or st.get("bid") or st.get("ask")
                    if px is not None:
                        raw_intent["price"] = float(px)
            else:
                if hasattr(raw_intent, "price"):
                    if getattr(raw_intent, "price", None) is None:
                        px = st.get("last") or st.get("price") or st.get("bid") or st.get("ask")
                        if px is not None:
                            raw_intent.price = float(px)
        except Exception as e:
            print(f"PRICE_INJECT_ERROR {e}", flush=True)
        # === INJECT FEATURES ===
        if isinstance(raw_intent, dict):
            raw_intent.setdefault("features", {})
            raw_intent["features"].update({
                "atr": regime.atr,
                "trend": regime.trend,
                "volatility": regime.volatility,
            })
        else:
            if hasattr(raw_intent, "features"):
                raw_intent.features.update({
                    "atr": regime.atr,
                    "trend": regime.trend,
                    "volatility": regime.volatility,
                })

        # =========================================================
        # === REGIME FILTER
        # =========================================================
        if not regime.is_tradeable():
            print(
                f"PIPE_REGIME_BLOCK trend={regime.trend} vol={regime.volatility}",
                flush=True,
            )
            return
        # =========================================================
        # === ROUTER
        # =========================================================
        routed = self.signal_router.route(raw_intent)

        print("DEBUG routed:", routed)

        # =========================================================
        # === SESSION FILTER (ЕДИНЫЙ ИСТОЧНИК, POST-ROUTER)
        # =========================================================
        try:
            session = self.session.get_regime()

            if not session.get("allow_entries", False):
                if os.getenv("SESSION_OVERRIDE", "0") == "1" or os.getenv("SIMULATE_MARKET", "0") == "1":
                    print("PIPE_SESSION_BYPASS_AFTER_ROUTER", flush=True)
                else:
                    print(f"PIPE_SESSION_BLOCK_AFTER_ROUTER phase={session.get('phase')}", flush=True)
                    return

        except Exception as e:
            print(f"PIPE_SESSION_ERROR {e}", flush=True)
            return

        # =========================================================
        # === OVERRIDE LAYER
        # =========================================================
        override = os.getenv("OVERRIDE_MODE", "0") == "1"

        if override:
            print("PIPE_OVERRIDE_ACTIVE", flush=True)
            try:
                routed.allowed = True
            except Exception:
                pass


        # =========================================================
        # === SIGNAL VALIDATION (FIRST!)
        # =========================================================
        if not routed.allowed:
            # suppress noisy duplicate logs
            if routed.reason != "duplicate_signal":
                print(f"PIPE_SIGNAL_REJECT reason={routed.reason}", flush=True)
            return

        intent = routed.intent.to_dict()
        # === CONTRACT RESOLVE BEFORE EXECUTION ===
        try:
            intent["symbol"] = self._resolver.resolve(intent["symbol"])
        except Exception:
            pass
        # === HARD PRICE INJECTION (FIX missing_price) ===
        try:
            if intent.get("price") is None:
                px = st.get("last") or st.get("price") or st.get("bid") or st.get("ask")
                if px is not None:
                    intent["price"] = float(px)
                    print(f"DEBUG PRICE INJECTED {intent['price']}", flush=True)
                else:
                    print("PIPE_PRICE_INJECT_FAIL", flush=True)
        except Exception as e:
            print(f"PRICE_INJECT_ERROR {e}", flush=True)

        # =========================================================
        # === TREND FLIP GUARD (prevents rapid direction changes) ===
        try:
            prev_trend = st.get("prev_trend")
            if prev_trend and prev_trend != regime.trend:
                if abs(regime.atr / price) < 0.01:
                    print("PIPE_TREND_FLIP_BLOCK", flush=True)
                    return
            st["prev_trend"] = regime.trend
        except Exception:
            pass

        # =========================================================
        # === STRICT TREND ALIGNMENT (breakout only in trend direction) ===
        # =========================================================
        try:
            trend = regime.trend
            side = intent.get("side")

            # === PRIMARY TREND ALIGNMENT ===
            if trend == "up" and side != "BUY":
                print(f"PIPE_TREND_BLOCK expected=BUY actual={side}", flush=True)
                return
            # === EXTRA IMPULSE FILTER ===
            if abs(st.get("ema_fast", price) - price) / price < float(os.getenv("IMPULSE_MIN","0.0003")) and regime.volatility != "high":
                print("PIPE_NO_IMPULSE_BLOCK", flush=True)
                return
            if trend == "down" and side != "SELL":
                print(f"PIPE_TREND_BLOCK expected=SELL actual={side}", flush=True)
                return

            # === REMOVE DUPLICATE HARD FILTER (it caused over-blocking & loops) ===
            # (intentionally removed redundant conditions)

        except Exception as e:
            print(f"TREND_FILTER_ERROR {e}", flush=True)

        # =========================================================
        # === SIGNAL DEDUP (ANTI-DUPLICATE CORE FIX, WITH TTL)
        # =========================================================
        try:
            symbol = intent.get("symbol")
            side = intent.get("side")
            price = round(float(intent.get("price", 0.0)), 3)

            signal_key = f"{symbol}:{side}:{price}"
            now_ts = time.time()

            last_key = getattr(self, "_last_signal_key", None)
            last_ts = getattr(self, "_last_signal_ts", 0.0)

            dedup_ttl = float(os.getenv("SIGNAL_DEDUP_TTL", "2"))

            if last_key == signal_key and (now_ts - last_ts) < dedup_ttl:
                # duplicate suppressed silently (cooldown will handle)
                return

            self._last_signal_key = signal_key
            self._last_signal_ts = now_ts

        except Exception as e:
            print(f"PIPE_SIGNAL_KEY_ERROR {e}", flush=True)

        # =========================================================
        # === POSITION GUARD (STRICT, NO STACKING)
        # =========================================================
        pos = self.pm.positions.get(sym)
        current_qty = float(getattr(pos, "qty", 0.0) or 0.0) if pos else 0.0
        avg_price = float(getattr(pos, "avg_price", 0.0) or 0.0) if pos else 0.0

        # === PYRAMIDING (LEVEL 2: add to winners only) ===
        if current_qty != 0.0:
            side = intent.get("side")

            # позиция должна совпадать по направлению
            if (current_qty > 0 and side == "BUY") or (current_qty < 0 and side == "SELL"):

                # считаем текущую прибыль по реальной рыночной цене
                market_price = st.get("last") or price
                if current_qty > 0:
                    pnl_pct = (market_price - avg_price) / avg_price if avg_price else 0.0
                else:
                    pnl_pct = (avg_price - market_price) / avg_price if avg_price else 0.0

                # более гибкий порог для пирамидинга (более агрессивный для MOEX low-vol)
                threshold = float(os.getenv("PYRAMIDING_THRESHOLD", "0.0003"))  # 0.03% (ускорение)
                print(f"DEBUG_PYRAMID pnl={round(pnl_pct,6)} threshold={threshold} avg={avg_price} mkt={market_price}", flush=True)
                # добавляем только если уже есть прибыль
                if pnl_pct > threshold:
                    print(f"PIPE_PYRAMID_ADD pnl={round(pnl_pct,4)}", flush=True)

                    # уменьшаем размер добавки (без увеличения риска)
                    intent["qty"] = round(intent.get("qty", 0.0) * 0.5, 3)

                else:
                    print("PIPE_PYRAMID_WAIT not_ready", flush=True)
                    return
            else:
                print("PIPE_POSITION_BLOCK opposite_direction", flush=True)
                return

        # === REMOVE position exists guard (handled by pyramiding logic) ===
        # if pos and float(getattr(pos, "qty", 0.0)) != 0.0:
        #     print(f"PIPE_POSITION_BLOCK symbol={sym} qty={getattr(pos, 'qty', 0.0)}", flush=True)
        #     return

        # =========================================================
        # === COOLDOWN (LAST FILTER BEFORE EXECUTION)
        # =========================================================
        now_ts = time.time()
        last_ts = getattr(self, "_last_trade_ts", 0.0)
        # Русский коммент: базовый кулдаун + адаптация под волатильность (Level 2)
        base_cooldown = float(os.getenv("TRADE_COOLDOWN_SEC", "45"))

        try:
            atr_pct = abs(st.get("atr", 0.0) / price) if price else 0.0

            # высокая волатильность → быстрее торгуем
            if atr_pct > 0.015:
                cooldown_sec = base_cooldown * 0.6
            # низкая волатильность → замедляемся
            elif atr_pct < 0.005:
                cooldown_sec = base_cooldown * 1.5
            else:
                cooldown_sec = base_cooldown

        except Exception:
            cooldown_sec = base_cooldown

        if now_ts - last_ts < cooldown_sec:
            print("PIPE_COOLDOWN_BLOCK", flush=True)
            return

        # === LOSS COOLDOWN CHECK ===
        if sym in self._cooldown_until:
            if time.time() < self._cooldown_until[sym]:
                print("PIPE_LOSS_COOLDOWN_BLOCK", flush=True)
                return


        self._last_trade_ts = now_ts

        # === TRADE LIMIT (LEVEL 2: анти-овер-трейдинг) ===
        try:
            max_trades_per_hour = int(os.getenv("MAX_TRADES_PER_HOUR", "5"))
            max_trades_per_symbol = int(os.getenv("MAX_TRADES_PER_SYMBOL", "2"))

            now_ts = time.time()

            # === GLOBAL TRADES ===
            trades = getattr(self, "_trade_timestamps", [])
            trades = [t for t in trades if now_ts - t < 3600]

            if len(trades) >= max_trades_per_hour:
                print("PIPE_TRADE_LIMIT_BLOCK_GLOBAL", flush=True)
                self._trade_timestamps = trades
                return

            # === SYMBOL TRADES ===
            sym_trades_map = getattr(self, "_symbol_trade_timestamps", {})
            sym_trades = sym_trades_map.get(sym, [])
            sym_trades = [t for t in sym_trades if now_ts - t < 3600]

            if len(sym_trades) >= max_trades_per_symbol:
                print(f"PIPE_TRADE_LIMIT_BLOCK_SYMBOL {sym}", flush=True)
                sym_trades_map[sym] = sym_trades
                self._symbol_trade_timestamps = sym_trades_map
                return

            # === UPDATE STATE ===
            trades.append(now_ts)
            sym_trades.append(now_ts)

            sym_trades_map[sym] = sym_trades

            self._trade_timestamps = trades
            self._symbol_trade_timestamps = sym_trades_map

            print(f"PIPE_TRADE_EXEC global={len(trades)} symbol={len(sym_trades)}", flush=True)

        except Exception as e:
            print(f"PIPE_TRADE_LIMIT_ERROR {e}", flush=True)
        # =========================================================
        # === RISK (PRODUCTION MODE)
        # =========================================================
        try:
            ctx = build_risk_context(intent, self.portfolio, st)

            print(
                f"PIPE_RISK_CTX symbol={ctx.symbol} qty={ctx.qty} price={ctx.price} "
                f"value={ctx.trade_value} exposure={ctx.total_exposure}",
                flush=True,
            )

            decision = self.risk.evaluate(signal=intent, context=ctx)

            # === DEBUG RISK DECISION (CRITICAL VISIBILITY) ===
            try:
                print(f"PIPE_RISK_DECISION raw={decision}", flush=True)
                if hasattr(decision, "__dict__"):
                    print(f"PIPE_RISK_FIELDS {decision.__dict__}", flush=True)
            except Exception:
                pass

            approved = _decision_allowed(decision)

            # soft override for dev/sim
            if os.getenv("RISK_SOFT", "0") == "1":
                print("PIPE_RISK_FORCE_PASS", flush=True)
                approved = True

            if not approved:
                print(
                    f"PIPE_RISK_REJECT reason={getattr(decision, 'reason', 'unknown')} "
                    f"value={ctx.trade_value} exposure={ctx.total_exposure}",
                    flush=True,
                )
                return


            print("PIPE_RISK_OK", flush=True)

            # =========================================================
            # === PORTFOLIO RISK (LEVEL 2: portfolio heat limit)
            # =========================================================
            try:
                pm_ctx = self.pm.get_context()

                total_exposure = float(getattr(pm_ctx, "total_exposure", 0.0) or 0.0)
                equity = float(getattr(pm_ctx, "portfolio_value", 0.0) or 0.0)

                if equity > 0:
                    heat = total_exposure / equity
                else:
                    heat = 0.0

                max_heat = float(os.getenv("MAX_PORTFOLIO_HEAT", "0.3"))  # 30% default

                if heat > max_heat:
                    print(f"PIPE_PORTFOLIO_HEAT_BLOCK heat={round(heat,3)}", flush=True)
                    return

                print(f"PIPE_PORTFOLIO_HEAT_OK heat={round(heat,3)}", flush=True)

            except Exception as e:
                print(f"PIPE_PORTFOLIO_HEAT_ERROR {e}", flush=True)

            # =========================================================
            # === SYMBOL RISK (LEVEL 2: ограничение на инструмент)
            # =========================================================
            try:
                symbol_exposure = float(getattr(pm_ctx, "current_symbol_exposure", 0.0) or 0.0)

                if equity > 0:
                    symbol_heat = symbol_exposure / equity
                else:
                    symbol_heat = 0.0

                max_symbol_heat = float(os.getenv("MAX_SYMBOL_HEAT", "0.1"))  # 10% default

                if symbol_heat > max_symbol_heat:
                    print(f"PIPE_SYMBOL_HEAT_BLOCK heat={round(symbol_heat,3)}", flush=True)
                    return

                print(f"PIPE_SYMBOL_HEAT_OK heat={round(symbol_heat,3)}", flush=True)

            except Exception as e:
                print(f"PIPE_SYMBOL_HEAT_ERROR {e}", flush=True)

            # =========================================================
            # === KILL SWITCH (LEVEL 2: защита капитала)
            # =========================================================
            try:
                pm_ctx = self.pm.get_context()

                equity = float(getattr(pm_ctx, "portfolio_value", 0.0) or 0.0)
                realized = float(getattr(pm_ctx, "daily_realized_pnl", 0.0) or 0.0)

                # === INIT PEAK EQUITY ===
                peak = getattr(self, "_equity_peak", None)
                if peak is None:
                    self._equity_peak = equity
                    peak = equity

                # === UPDATE PEAK ===
                if equity > peak:
                    self._equity_peak = equity
                    peak = equity

                # === DRAWDOWN ===
                dd = (equity - peak) / peak if peak > 0 else 0.0

                max_dd = float(os.getenv("MAX_DRAWDOWN", "-0.03"))  # -3%
                max_daily_loss = float(os.getenv("MAX_DAILY_LOSS", "-0.02"))  # -2%

                # === HARD LOCK (ONCE TRIGGERED) ===
                if getattr(self, "_kill_switch_active", False):
                    print("PIPE_KILL_SWITCH_ACTIVE", flush=True)
                    return

                if dd < max_dd:
                    print(f"PIPE_KILL_SWITCH_DD dd={round(dd, 4)}", flush=True)
                    self._kill_switch_active = True
                    return

                if realized < max_daily_loss * peak:
                    print(f"PIPE_KILL_SWITCH_DAILY pnl={round(realized, 2)}", flush=True)
                    self._kill_switch_active = True
                    return
                if realized < max_daily_loss * peak:
                    print(f"PIPE_KILL_SWITCH_DAILY pnl={round(realized,2)}", flush=True)
                    return

            except Exception as e:
                print(f"PIPE_KILL_SWITCH_ERROR {e}", flush=True)

            # === TEMP FIX: MIN TRADE SIZE FLOOR ===
            try:
                if ctx.trade_value < 10:  # слишком маленькие сделки режем/расширяем
                    print("PIPE_RISK_ADJUST small_trade -> force min size", flush=True)
                    intent["qty"] = max(1.0, float(intent.get("qty", 0)))
            except Exception:
                pass

        except Exception as e:
            print(f"PIPE_RISK_ERROR {e}", flush=True)
            return
        # =========================================================
        # === EXECUTION
        # =========================================================
        # === VALIDATION BEFORE EXECUTION (CRITICAL FIX) ===
        # === CORRELATION FILTER ===
        try:
            current_positions = getattr(self.pm, "positions", {}) or {}

            active_symbols = list(current_positions.keys())

            def get_cluster(sym):
                base = sym.split("@")[0][:2]
                for k, v in CLUSTERS.items():
                    if base in v:
                        return k
                return None

            new_cluster = get_cluster(intent.get("symbol"))

            for s in active_symbols:
                existing_cluster = get_cluster(s)

                if existing_cluster and existing_cluster == new_cluster:
                    print(f"PIPE_CLUSTER_BLOCK {new_cluster}", flush=True)
                    return

        except Exception:
            pass
        if intent.get("price") is None:
            px = st.get("last") or st.get("price") or st.get("bid") or st.get("ask")
            if px is not None:
                intent["price"] = float(px)
                print(f"DEBUG PRICE FIX BEFORE EXEC {intent['price']}", flush=True)
            else:
                print("PIPE_EXEC_BLOCK missing_price", flush=True)
                return
        if intent.get("qty") is None or float(intent.get("qty", 0)) <= 0:
            print("PIPE_EXEC_BLOCK invalid_qty", flush=True)
            return
        raw_fill = self.paper.execute(intent, st)

        # === NORMALIZE FILL (define raw_qty and side ONCE) ===
        raw_qty = float(getattr(raw_fill, "qty", intent.get("qty", 0.0)) or 0.0)

        if raw_qty < 0:
            side = "SELL"
        else:
            side = "BUY"

        exec_price = float(
            getattr(raw_fill, "price", None)
            or st.get("last")
            or st.get("price")
            or 0.0
        )

        print("DEBUG COMMISSION CALL OK", flush=True)

        if hasattr(self.fee_tax, "commission"):
            commission = self.fee_tax.commission(
                symbol=intent.get("symbol"),
                qty=abs(raw_qty),
                price=exec_price
            )
        elif hasattr(self.fee_tax, "calc_commission"):
            commission = self.fee_tax.calc_commission(
                symbol=intent.get("symbol"),
                qty=abs(raw_qty),
                price=exec_price
            )
        else:
            commission = 0.0

        fill = ExecutionFill(
            symbol=intent.get("symbol"),
            side=side,
            qty=abs(raw_qty),
            price=exec_price,
            commission=commission,
            fill_id=getattr(raw_fill, "fill_id", None),
        )

        # SAFETY: гарантируем корректный fill (также qty > 0)
        if not hasattr(fill, "side") or fill.side is None or fill.qty <= 0:
            LOG.error("FILL BUILD ERROR: invalid fill, intent=%s raw_fill=%s", intent, raw_fill)
            return

        print(
            f"PIPE_EXEC side={intent.get('side')} qty={intent.get('qty')}",
            flush=True,
        )
        print(f"PIPE_TRADE_EXEC symbol={intent.get('symbol')} side={intent.get('side')}", flush=True)

        self.bus.publish({"type": "FILL", "fill": fill})

    def generate(self, state, regime=None):

        if regime is None:
            return None

        # ✔ Правильная логика: используем только regime.tradable
        if not regime.tradable:
            print(
                f"PIPE_SIGNAL_REJECT reason=regime_filter trend={regime.trend} vol={regime.volatility}",
                flush=True,
            )
            return

        # 🚫 не торгуем низкую волу
        if regime.volatility == "low":
            return None

        # ✔ breakout только в тренде
        if regime.trend in ("up", "down"):
            return self._breakout_logic(state)

    def _on_fill(self, event: dict):
        """
        Русский коммент: единая точка применения исполнений.
        Идемпотентность по fill_id держит PositionManager (если включена).
        """
        fill = event.get("fill") if isinstance(event, dict) else event
        # === TYPE GUARD: пропускаем не ExecutionFill ===
        if not isinstance(fill, ExecutionFill):
            # RAW PaperFill игнорируем молча (уже обработан на этапе execution)
            return
        if fill is None:
            return

        # === FIX: safe validation (NO MUTATION, NO NORMALIZATION) ===
        try:
            # === SAFE VALIDATION (NO MUTATION) ===
            raw_qty = float(getattr(fill, "qty", 0.0) or 0.0)
            price = float(getattr(fill, "price", 0.0) or 0.0)

            # просто проверяем корректность, НИЧЕГО НЕ МЕНЯЕМ
            if raw_qty == 0.0 or price == 0.0:
                LOG.warning("INVALID FILL (zero qty/price): %s (skipped)", fill)
                return

            if not hasattr(fill, "side") or fill.side not in ("BUY", "SELL"):
                LOG.warning("INVALID FILL SIDE: %s (skipped)", fill)
                return

        except Exception as e:
            LOG.error("FILL NORMALIZATION ERROR (SAFE SKIP): %s fill=%s", e, fill)
            return

        # SAFETY: проверка обязательных полей ПОСЛЕ валидации
        if fill.qty <= 0:
            LOG.warning("INVALID FILL AFTER VALIDATION: %s (skipped)", fill)
            return

        # === APPLY FILL WITH COMMISSION ===
        self.pm.apply_fill(fill)

        # === PnL CALC (REALIZED) ===
        try:
            pos = self.pm.positions.get(getattr(fill, "symbol", None))
            if pos:
                realized = getattr(pos, "realized_pnl", 0.0)
                tax = self.fee_tax.tax(realized)

                net_pnl = realized - tax

                # списываем налог из cash (если доступно)
                try:
                    if hasattr(self.pm, "cash"):
                        self.pm.cash -= tax
                except Exception:
                    pass

                print(
                    f"PIPE_NET_PNL net={net_pnl}",
                    flush=True,
                )

                print(
                    f"PIPE_TAX realized={realized} tax={tax}",
                    flush=True,
                )
                unrealized = getattr(pos, "unrealized_pnl", 0.0)

                print(
                    f"PIPE_PNL realized={realized} unrealized={unrealized} commission={getattr(fill, 'commission', 0.0)}",
                    flush=True,
                )

                # === EQUITY TRACKING ===
                try:
                    cash = float(getattr(self.pm, "cash", 0.0) or 0.0)
                    unrealized = float(getattr(pos, "unrealized_pnl", 0.0) or 0.0)

                    equity = cash + unrealized

                    # сохраняем историю equity
                    hist = getattr(self, "_equity_curve", None)
                    if hist is None:
                        self._equity_curve = []
                        hist = self._equity_curve

                    hist.append(equity)

                    # === DRAWDOWN ===
                    peak = max(hist)
                    drawdown = (equity - peak) / peak if peak > 0 else 0.0

                    print(
                        f"PIPE_EQUITY equity={round(equity,2)} dd={round(drawdown*100,2)}%",
                        flush=True,
                    )

                except Exception as e:
                    LOG.debug("EQUITY ERROR: %s", e)
        except Exception as e:
            LOG.debug("PNL CALC ERROR: %s", e)

        if str(getattr(fill, "side", "")).upper() == "BUY":
            self.trailing_exit.on_position_opened(
                getattr(fill, "symbol", None),
                float(getattr(fill, "price", 0.0) or 0.0),
            )
        elif str(getattr(fill, "side", "")).upper() == "SELL":
            self.trailing_exit.reset(getattr(fill, "symbol", None))

        # --- DIAG (safe) ---
        try:
            pm_ctx = self.pm.get_context()

            pos = self.pm.positions.get(getattr(fill, "symbol", None))
            qty_now = float(getattr(pos, "qty", 0.0) or 0.0) if pos is not None else 0.0
            avg_now = float(getattr(pos, "avg_price", 0.0) or 0.0) if pos is not None else 0.0
            cash_now = float(getattr(self.pm, "cash", 0.0) or 0.0)

            sym_exposure = abs(qty_now) * float(getattr(fill, "price", 0.0) or 0.0)

            print(
                f"PIPE_PM_CTX portfolio_value={getattr(pm_ctx, 'portfolio_value', None)} "
                f"total_exposure={getattr(pm_ctx, 'total_exposure', None)} "
                f"sym_exposure={sym_exposure} daily_realized_pnl={getattr(pm_ctx, 'daily_realized_pnl', None)} "
                f"qty={qty_now} avg={avg_now} cash={cash_now}",
                flush=True,
            )
            LOG.info(
                "PM_CTX portfolio_value=%s total_exposure=%s sym_exposure=%s daily_realized_pnl=%s qty=%s avg=%s cash=%s",
                getattr(pm_ctx, "portfolio_value", None),
                getattr(pm_ctx, "total_exposure", None),
                sym_exposure,
                getattr(pm_ctx, "daily_realized_pnl", None),
                qty_now,
                avg_now,
                cash_now,
            )
        except Exception as e:
            LOG.debug("PM_CTX DIAG ERROR: %s", e)

        print(
            f"PIPE_FILLED paper {getattr(fill, 'symbol', None)} "
            f"side={getattr(fill, 'side', None)} qty={getattr(fill, 'qty', None)} "
            f"price={getattr(fill, 'price', None)} id={getattr(fill, 'fill_id', None)}",
            flush=True,
        )
        # === TELEGRAM: единый сигнал входа ===
        try:
            trend = self._mkt.get(getattr(fill, "symbol", None), {}).get("regime_trend")
            vol = self._mkt.get(getattr(fill, "symbol", None), {}).get("regime_vol")

            self.notifier.send(
                f"📊 СИГНАЛ\n"
                f"{getattr(fill, 'symbol', None)} | {getattr(fill, 'side', None)}\n"
                f"Цена: {round(getattr(fill, 'price', 0), 4)}\n"
                f"Объём: {getattr(fill, 'qty', None)}\n"
                f"Тренд: {trend} | Волатильность: {vol}"
            )
        except Exception:
            pass
        LOG.info("FILLED paper %s qty=%s price=%s id=%s",
                 getattr(fill, "symbol", None),
                 getattr(fill, "qty", None),
                 getattr(fill, "price", None),
                 getattr(fill, "fill_id", None))

        self.pg_logger.log_fill(
            symbol=getattr(fill, "symbol", None),
            side=getattr(fill, "side", None),
            qty=float(getattr(fill, "qty", 0.0) or 0.0),
            price=float(getattr(fill, "price", 0.0) or 0.0),
            trade_id=getattr(fill, "fill_id", None),
            execution_type="paper",
            commission=float(getattr(fill, "commission", 0.0) or 0.0),
        )

        # === TELEGRAM: исполнение ===
        try:
            self.notifier.send(
                f"✅ ИСПОЛНЕНИЕ\n"
                f"{getattr(fill, 'symbol', None)} | {getattr(fill, 'side', None)}\n"
                f"Цена: {round(getattr(fill, 'price', 0), 4)}\n"
                f"Объём: {getattr(fill, 'qty', None)}"
            )
        except Exception:
            pass

        # exit-on-fill
        if not self._filled_once and os.getenv("EXIT_ON_FILL", "1") == "1":
            self._filled_once = True
            LOG.info("DONE: filled once, exiting")
            if self._done is not None:
                try:
                    self._done.set()
                except Exception:
                    pass

    def _risk_check_br_signal(self, br_signal, qty: float) -> tuple[bool, str]:
        """Русский комментарий: BR PAPER-сигнал проходит RiskEngine, но real orders не создаются."""
        if not hasattr(self, "risk") or self.risk is None:
            return True, "NO_RISK_ENGINE_ATTACHED_PAPER_ONLY"

        try:
            if hasattr(self.risk, "check_order"):
                decision = self.risk.check_order(
                    symbol=br_signal.symbol,
                    side=br_signal.side,
                    qty=qty,
                    price=br_signal.price,
                )
                accepted = bool(getattr(decision, "accepted", decision))
                reason = str(getattr(decision, "reason", "RISK_CHECK_ORDER"))
                return accepted, reason

            if hasattr(self.risk, "evaluate"):
                candidate = {
                    "symbol": br_signal.symbol,
                    "side": br_signal.side,
                    "qty": qty,
                    "price": br_signal.price,
                    "stop": br_signal.stop,
                    "take": br_signal.take,
                    "strategy": "BR_CONSERVATIVE_BREAKOUT_M5",
                    "source": "paper_pipeline_closed_bar",
                }
                decision = self.risk.evaluate(candidate)
                accepted = bool(getattr(decision, "accepted", decision))
                reason = str(getattr(decision, "reason", "RISK_EVALUATE"))
                return accepted, reason

            return True, "RISK_ENGINE_NO_COMPATIBLE_METHOD_PAPER_ONLY"

        except Exception as exc:
            return False, f"RISK_EXCEPTION:{type(exc).__name__}:{exc}"

    def _log_br_risk_event(self, br_signal, qty: float, accepted: bool, reason: str) -> None:
        """Русский комментарий: логируем результат risk gate без отправки реальных заявок."""
        if not hasattr(self, "pg_logger") or self.pg_logger is None:
            return

        payload = {
            "symbol": br_signal.symbol,
            "side": br_signal.side,
            "qty": qty,
            "price": br_signal.price,
            "stop": br_signal.stop,
            "take": br_signal.take,
            "strategy": "BR_CONSERVATIVE_BREAKOUT_M5",
            "accepted": accepted,
            "reason": reason,
            "paper_only": True,
            "execution_mode": os.getenv("EXECUTION_MODE", "paper"),
        }

        try:
            if hasattr(self.pg_logger, "log_risk_event"):
                self.pg_logger.log_risk_event(
                    symbol=br_signal.symbol,
                    event_type="BR_PAPER_SIGNAL_RISK_ACCEPTED" if accepted else "BR_PAPER_SIGNAL_RISK_REJECTED",
                    severity="info" if accepted else "warning",
                    payload=payload,
                )
        except Exception:
            pass

    def _log_br_paper_fill(self, br_signal, qty: float, fill, paper_reason: str) -> None:
        """Русский комментарий: PaperExecutionEngine возвращает PaperFill; здесь явно пишем его в trades."""
        if not hasattr(self, "pg_logger") or self.pg_logger is None:
            return
        if not hasattr(self.pg_logger, "log_trade"):
            return

        fill_qty = float(getattr(fill, "qty", qty) or qty)
        fill_price = float(getattr(fill, "price", br_signal.price) or br_signal.price)
        run_id = str(getattr(self, "run_id", "unknown"))
        fill_id_raw = str(getattr(fill, "fill_id", f"paper_br_{int(br_signal.ts.timestamp())}"))
        fill_id = f"{run_id}_{fill_id_raw}"

        try:
            self.pg_logger.log_trade(
                symbol=br_signal.symbol,
                side=br_signal.side,
                qty=abs(fill_qty),
                price=fill_price,
                trade_id=fill_id,
                execution_type=paper_reason,
                run_id=run_id,
            )
        except TypeError:
            trade = {
                "symbol": br_signal.symbol,
                "side": br_signal.side,
                "qty": abs(fill_qty),
                "quantity": abs(fill_qty),
                "price": fill_price,
                "trade_id": fill_id,
                "execution_type": paper_reason,
                "run_id": run_id,
                "ts": br_signal.ts,
            }
            self.pg_logger.log_trade(trade)

    def _current_br_regime(self) -> str:
        """Русский комментарий: текущий режим из M15-состояния BR-стратегии."""
        br = getattr(self, "br_breakout", None)
        if br is None:
            return "unknown"

        direction = int(getattr(br, "regime_direction", 0) or 0)
        atr_pct = float(getattr(br, "regime_atr_pct", 0.0) or 0.0)

        if direction > 0:
            trend = "up"
        elif direction < 0:
            trend = "down"
        else:
            trend = "flat"

        if atr_pct < 0.0005:
            vol = "low_vol"
        elif atr_pct > 0.003:
            vol = "high_vol"
        else:
            vol = "normal_vol"

        return f"{trend}_{vol}"

    def _regime_policy_allows_br(self, br_signal) -> tuple[bool, str]:
        """Русский комментарий: блокируем не бары, а уже сформированный сигнал перед PaperExecution."""
        policy = getattr(self, "regime_policy", None)
        if policy is None:
            policy = RegimePolicy()
            self.regime_policy = policy

        regime = self._current_br_regime()
        allowed, reason = policy.is_allowed(br_signal.symbol, regime)
        return allowed, f"{reason};regime={regime}"

    def _max_abs_position_for_br(self, symbol: str) -> float:
        """Русский комментарий: лимит позиции берём через adapter; при недоступности Финама работает .env fallback."""
        adapter = getattr(self, "finam_limits_adapter", None)
        if adapter is None:
            adapter = FinamLimitsAdapter()
            self.finam_limits_adapter = adapter
        return float(adapter.get_symbol_limit(symbol).max_abs_position)

    def _current_replay_position_for_br(self, symbol: str) -> float:
        """Русский комментарий: текущая PAPER/replay позиция внутри pipeline."""
        positions = getattr(self, "_br_replay_positions", None)
        if positions is None:
            positions = {}
            self._br_replay_positions = positions
        return float(positions.get(symbol, 0.0))

    def _apply_replay_position_for_br(self, symbol: str, side: str, qty: float) -> None:
        """Русский комментарий: обновляем PAPER/replay позицию после успешного paper-fill."""
        positions = getattr(self, "_br_replay_positions", None)
        if positions is None:
            positions = {}
            self._br_replay_positions = positions
        signed = qty if side.upper() == "BUY" else -qty
        positions[symbol] = float(positions.get(symbol, 0.0)) + signed

    def _position_limit_allows_br(self, br_signal, qty: float) -> tuple[bool, str]:
        """Русский комментарий: не разрешаем наращивать позицию сверх лимита; сокращение разрешаем."""
        symbol = br_signal.symbol
        side = br_signal.side.upper()
        current_pos = self._current_replay_position_for_br(symbol)
        limit = self._max_abs_position_for_br(symbol)
        signed = qty if side == "BUY" else -qty
        new_pos = current_pos + signed

        if abs(new_pos) <= limit:
            return True, f"POSITION_LIMIT_OK current={current_pos} new={new_pos} limit={limit}"

        if abs(new_pos) < abs(current_pos):
            return True, f"POSITION_REDUCE_ALLOWED current={current_pos} new={new_pos} limit={limit}"

        return False, f"MAX_POSITION_LIMIT current={current_pos} requested={signed} new={new_pos} limit={limit}"

    def _execute_br_signal_in_paper(self, br_signal, qty: float) -> tuple[bool, str]:
        """Русский комментарий: исполняем risk_accepted BR-сигнал только через PAPER-движок, без real orders."""
        if os.getenv("EXECUTION_MODE", "paper").lower() != "paper":
            return False, "SKIPPED_NOT_PAPER_MODE"

        if not hasattr(self, "paper") or self.paper is None:
            return False, "NO_PAPER_EXECUTION_ENGINE_ATTACHED"

        regime_allowed, regime_reason = self._regime_policy_allows_br(br_signal)
        if not regime_allowed:
            return False, regime_reason

        allowed, limit_reason = self._position_limit_allows_br(br_signal, qty)
        if not allowed:
            return False, limit_reason

        order = {
            "symbol": br_signal.symbol,
            "side": br_signal.side,
            "qty": qty,
            "price": br_signal.price,
            "stop": br_signal.stop,
            "take": br_signal.take,
            "strategy": "BR_CONSERVATIVE_BREAKOUT_M5",
            "source": "paper_pipeline_closed_bar",
            "paper_only": True,
        }

        try:
            fill = None
            paper_reason = "PAPER_ENGINE_NO_COMPATIBLE_METHOD"

            if hasattr(self.paper, "execute"):
                fill = self.paper.execute(
                    order,
                    market_state={
                        "price": br_signal.price,
                        "last": br_signal.price,
                        "timestamp": br_signal.ts.timestamp(),
                    },
                )
                paper_reason = "PAPER_EXECUTE_ORDER_DICT"

            elif hasattr(self.paper, "execute_order"):
                fill = self.paper.execute_order(order)
                paper_reason = "PAPER_EXECUTE_ORDER_DICT"

            elif hasattr(self.paper, "submit_order"):
                fill = self.paper.submit_order(order)
                paper_reason = "PAPER_SUBMIT_ORDER_DICT"

            elif hasattr(self.paper, "fill_market_order"):
                fill = self.paper.fill_market_order(
                    symbol=br_signal.symbol,
                    side=br_signal.side,
                    qty=qty,
                    price=br_signal.price,
                )
                paper_reason = "PAPER_FILL_MARKET_ORDER"

            if fill is not None:
                self._log_br_paper_fill(
                    br_signal=br_signal,
                    qty=qty,
                    fill=fill,
                    paper_reason=paper_reason,
                )
                self._apply_replay_position_for_br(br_signal.symbol, br_signal.side, qty)
                return True, paper_reason

            if hasattr(self.pg_logger, "log_trade"):
                self.pg_logger.log_trade(
                    symbol=br_signal.symbol,
                    side=br_signal.side,
                    qty=qty,
                    price=br_signal.price,
                    trade_id=f"paper_br_{int(br_signal.ts.timestamp())}",
                    execution_type="paper_replay_fallback",
                )
                return True, "PAPER_TRADE_LOG_FALLBACK"

            return False, "PAPER_ENGINE_NO_COMPATIBLE_METHOD"

        except Exception as exc:
            return False, f"PAPER_EXCEPTION:{type(exc).__name__}:{exc}"

    def _process_br_closed_bar_for_paper_signal(self, bar) -> None:
        """Русский комментарий: единая обработка закрытых M5/M15 баров BR для live и historical replay."""
        if not (self.br_breakout_enabled and self.br_breakout is not None):
            return
        if bar.symbol != self.br_breakout_symbol:
            return

        timeframe = str(bar.timeframe).upper()

        if timeframe == "M15":
            self.br_breakout.on_regime_bar(
                ts=bar.ts,
                open_=float(bar.open),
                high=float(bar.high),
                low=float(bar.low),
                close=float(bar.close_price),
                volume=float(bar.volume or 0.0),
            )
            return

        if timeframe != "M5":
            return

        br_signal = self.br_breakout.on_signal_bar(
            ts=bar.ts,
            open_=float(bar.open),
            high=float(bar.high),
            low=float(bar.low),
            close=float(bar.close_price),
            volume=float(bar.volume or 0.0),
        )

        if br_signal is None:
            return

        current_params = getattr(self.br_breakout, "current_params", None)
        qty = float(os.getenv("BR_BREAKOUT_QTY", "1"))
        risk_accepted, risk_reason = self._risk_check_br_signal(br_signal, qty)
        signal_status = "risk_accepted" if risk_accepted else "risk_rejected"

        payload = {
            "price": br_signal.price,
            "stop": br_signal.stop,
            "take": br_signal.take,
            "reason": br_signal.reason,
            "ts": br_signal.ts.isoformat(),
            "execution_mode": os.getenv("EXECUTION_MODE", "paper"),
            "paper_only": True,
            "source": "paper_pipeline_closed_bar",
            "risk_accepted": risk_accepted,
            "risk_reason": risk_reason,
            "online_mode": getattr(current_params, "mode", None),
            "online_allow_trade": getattr(current_params, "allow_trade", None),
            "online_reason": getattr(current_params, "reason", None),
            "selected_window": getattr(current_params, "breakout_window", None),
            "selected_stop_atr": getattr(current_params, "stop_atr", None),
            "selected_take_atr": getattr(current_params, "take_atr", None),
            "regime_direction": getattr(self.br_breakout, "regime_direction", None),
            "regime_atr_pct": getattr(self.br_breakout, "regime_atr_pct", None),
            "regime_strength": getattr(self.br_breakout, "regime_strength", None),
            "regime_rsi": getattr(self.br_breakout, "regime_rsi", None),
            "regime_rsi_state": getattr(self.br_breakout, "regime_rsi_state", None),
            "rsi_filter_passed": getattr(self.br_breakout, "rsi_filter_passed", None),
            "rsi_filter_reason": getattr(self.br_breakout, "rsi_filter_reason", None),
        }


        self._log_br_risk_event(br_signal=br_signal, qty=qty, accepted=risk_accepted, reason=risk_reason)

        if not risk_accepted:
            return

        paper_executed, paper_reason = self._execute_br_signal_in_paper(br_signal=br_signal, qty=qty)
        payload["paper_executed"] = paper_executed
        payload["paper_reason"] = paper_reason
        payload["run_id"] = getattr(self, "run_id", "unknown")

        # Русский комментарий: разделяем причины отказа execution-gate для replay-аналитики.
        if not paper_executed:
            reason_text = str(paper_reason or "")
            if reason_text.startswith("MAX_POSITION_LIMIT"):
                self._br_position_limit_rejected = int(getattr(self, "_br_position_limit_rejected", 0)) + 1
            elif "REGIME_" in reason_text:
                self._br_regime_policy_rejected = int(getattr(self, "_br_regime_policy_rejected", 0)) + 1
            else:
                self._br_other_execution_rejected = int(getattr(self, "_br_other_execution_rejected", 0)) + 1

        self.pg_logger.log_signal(
            symbol=br_signal.symbol,
            strategy="BR_CONSERVATIVE_BREAKOUT_M5",
            side=br_signal.side,
            qty=qty,
            status=signal_status,
            payload=payload,
        )

        try:
            self.notifier.send(
                f"🛢 BR PAPER SIGNAL\n"
                f"{br_signal.symbol} | {br_signal.side}\n"
                f"Цена: {round(br_signal.price, 4)}\n"
                f"Стоп: {round(br_signal.stop, 4)}\n"
                f"Цель: {round(br_signal.take, 4)}\n"
                f"Причина: {br_signal.reason}\n"
                f"Risk: {risk_reason}\n"
                f"Paper: {paper_reason}"
            )
        except Exception:
            pass