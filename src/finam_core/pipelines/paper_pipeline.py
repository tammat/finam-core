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
from core.instrument_resolver import InstrumentResolver

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
        self.exit_engine = SlTpCooldownEngine()
        # === FIX: dynamic stops storage ===
        self.vol_risk = VolatilityRiskEngine()
        self.live_atr = LiveAtrEstimator()
        self.portfolio_heat = PortfolioHeatEngine()
        self.kill_switch = KillSwitchEngine()
        self.correlation_risk = CorrelationRiskEngine()
        self.risk_recorder = RiskDecisionRecorder(self.pg_logger)
        self.signal_router = SignalRouter()
        self.regime_engine = RegimeEngine()
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

    def _cluster_risk_check(self, sym: str, st: dict) -> bool:
        try:
            cluster_name = None

            for cname, symbols in CLUSTERS.items():
                for base in symbols:
                    if base in sym:
                        cluster_name = cname
                        break
                if cluster_name:
                    break

            if not cluster_name:
                return True

            cluster_symbols = CLUSTERS.get(cluster_name, [])
            cluster_exposure = 0.0

            for psym, pos in self.pm.positions.items():
                for base in cluster_symbols:
                    if base in psym:
                        qty = float(getattr(pos, "qty", 0.0) or 0.0)
                        avg = float(getattr(pos, "avg_price", 0.0) or 0.0)
                        last_px = float(st.get("last") or avg or 0.0)
                        cluster_exposure += abs(qty) * last_px
                        break

            # безопасно берём equity
            try:
                pm_ctx = self.pm.get_context()
                equity = float(getattr(pm_ctx, "portfolio_value", 0.0) or 0.0)
            except Exception:
                equity = 0.0

            cluster_heat = cluster_exposure / equity if equity > 0 else 0.0
            max_cluster_heat = float(os.getenv("MAX_CLUSTER_HEAT", "0.2"))

            if cluster_heat > max_cluster_heat:
                print(
                    f"PIPE_CLUSTER_BLOCK cluster={cluster_name} "
                    f"heat={round(cluster_heat,3)} exposure={round(cluster_exposure,2)} "
                    f"equity={round(equity,2)}",
                    flush=True
                )
                return False

            print(
                f"PIPE_CLUSTER_OK cluster={cluster_name} "
                f"heat={round(cluster_heat,3)} exposure={round(cluster_exposure,2)} "
                f"equity={round(equity,2)}",
                flush=True
            )
            return True

        except Exception as e:
            print(f"PIPE_CLUSTER_ERROR {e}", flush=True)
            return True

    def attach(self):
        # Русский коммент: Pipeline B — подписываемся на QUOTE, а FILL применяем централизованно.
        self.bus.subscribe("QUOTE", self._on_quote)
        self.bus.subscribe("FILL", self._on_fill)
        LOG.debug("PIPE attach(): subscribed QUOTE/FILL")
        # 🔥 ПОДПИСКА НА КОТИРОВКИ
        self.bus.subscribe("QUOTE", self._on_quote)

    def _on_quote(self, event: dict):
        # =========================================================
        # === SESSION LAYER (ЕДИНЫЙ ИСТОЧНИК)
        # =========================================================
        session = self.session.get_regime()
        # === FORCE OVERRIDE (DEV MODE) ===
        if os.getenv("SESSION_OVERRIDE", "0") == "1":
            print("PIPE_SESSION_OVERRIDE_ACTIVE", flush=True)
            session = {
                "phase": "override",
                "allow_entries": True
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

        # === HOUSEKEEPING: reset SMART ENTRY flag by TTL ===
        try:
            if st.get("_smart_entry_fired") and time.time() > float(st.get("_smart_entry_reset_ts", 0.0)):
                st["_smart_entry_fired"] = False
        except Exception:
            pass

        last = st.get("last")
        if last is None:
            return

        price = float(last)
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

        # === GLOBAL PNL SAFE INIT (single source of truth) ===
        pnl_pct = 0.0
        try:
            if qty_now != 0.0 and avg_now > 0:
                if qty_now > 0:
                    pnl_pct = (price - avg_now) / avg_now
                else:
                    pnl_pct = (avg_now - price) / avg_now
        except Exception:
            pnl_pct = 0.0

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
                # === PARTIAL TAKE-PROFIT (scale-out) ===
                try:
                    pos = self.pm.positions.get(sym)
                    qty_now = float(getattr(pos, "qty", 0.0) or 0.0) if pos else 0.0
                    avg_now = float(getattr(pos, "avg_price", 0.0) or 0.0) if pos else 0.0
                    price_now = st.get("last") or 0.0

                    if qty_now != 0.0 and avg_now > 0:
                        local_pnl_pct = 0.0
                        if avg_now > 0:
                            local_pnl_pct = (price_now - avg_now) / avg_now if qty_now > 0 else (avg_now - price_now) / avg_now

                        # первый частичный выход
                        if local_pnl_pct > 0.006 and abs(qty_now) > 0.3:
                            part_qty = round(abs(qty_now) * 0.5, 3)
                            part_side = "SELL" if qty_now > 0 else "BUY"

                            print(f"PIPE_PARTIAL_EXIT_1 qty={part_qty}", flush=True)

                            part_intent = {
                                "symbol": sym,
                                "side": part_side,
                                "qty": part_qty,
                                "reason": "partial_tp_1"
                            }

                            raw_fill = self.paper.execute(part_intent, st)

                            fill = ExecutionFill(
                                symbol=sym,
                                side=part_side,
                                qty=part_qty,
                                price=float(getattr(raw_fill, "price", price_now)),
                                commission=0.0,
                                fill_id=getattr(raw_fill, "fill_id", None),
                            )

                            self.bus.publish({"type": "FILL", "fill": fill})

                except Exception as e:
                    print(f"PIPE_PARTIAL_EXIT_ERROR {e}", flush=True)
                # === LOSS COOLDOWN (LEVEL 2) ===
                try:
                    if "stop_loss" in exit_decision.reason:
                        now_ts = time.time()
                        self._cooldown_until[sym] = now_ts + 180
                        st["last_loss_ts"] = now_ts
                        print(f"PIPE_LOSS_COOLDOWN_SET until={round(self._cooldown_until[sym], 2)}", flush=True)
                except Exception:
                    pass
                return
        # === PROFIT PROTECTION (BREAK-EVEN + TRAILING) ===
        try:
            if avg_now > 0:
                # use global pnl_pct (do not recompute here)

                # === BREAK-EVEN ===
                if pnl_pct > 0.003:  # +0.3%
                    if qty_now > 0:
                        be_price = avg_now * 1.0005
                        if price > be_price:
                            self.exit_engine.set_dynamic_stop(sym, be_price)
                            print(f"PIPE_BE_LONG {be_price}", flush=True)
                    else:
                        be_price = avg_now * 0.9995
                        if price < be_price:
                            self.exit_engine.set_dynamic_stop(sym, be_price)
                            print(f"PIPE_BE_SHORT {be_price}", flush=True)

                # === ADAPTIVE TRAILING (VOL + PROFIT STAGE) ===
                if pnl_pct > 0.004:  # раньше включаем трейлинг
                    atr_val = st.get("atr", 0.0) or 0.0
                    atr_pct = abs(atr_val / price) if price else 0.0

                    # базовая дистанция
                    base_k = 1.0

                    # при высокой волатильности — расширяем (чтобы не выбивало)
                    if atr_pct > 0.02:
                        base_k = 1.5
                    # при низкой — сужаем (быстрее фиксируем)
                    elif atr_pct < 0.005:
                        base_k = 0.7

                    # стадия прибыли — чем больше прибыль, тем агрессивнее подтягиваем
                    if pnl_pct > 0.01:
                        base_k *= 0.7   # сжимаем трейлинг
                    elif pnl_pct > 0.02:
                        base_k *= 0.5

                    trail_distance = max(atr_val * base_k, price * 0.002)

                    if qty_now > 0:
                        trail_price = price - trail_distance
                        self.exit_engine.set_dynamic_stop(sym, trail_price)
                        print(f"PIPE_TRAIL_LONG {round(trail_price, 4)} k={round(base_k,2)}", flush=True)
                    else:
                        trail_price = price + trail_distance
                        self.exit_engine.set_dynamic_stop(sym, trail_price)
                        print(f"PIPE_TRAIL_SHORT {round(trail_price, 4)} k={round(base_k,2)}", flush=True)
        except Exception as e:
            print(f"PIPE_PROFIT_PROTECT_ERROR {e}", flush=True)

        # === EXIT ALPHA V2: PARTIAL TAKE PROFIT ===
        try:
            pos = self.pm.positions.get(sym)
            if pos:
                qty_now = float(getattr(pos, "qty", 0.0) or 0.0)
                avg_price = float(getattr(pos, "avg_price", 0.0) or 0.0)

                if qty_now != 0 and avg_price:
                    local_pnl_pct = 0.0
                    if avg_price:
                        local_pnl_pct = ((price - avg_price) / avg_price) if qty_now > 0 else ((avg_price - price) / avg_price)

                    partial_tp = float(os.getenv("PARTIAL_TP_PCT", "0.004"))  # 0.4%

                    if local_pnl_pct > partial_tp and not st.get("_partial_tp_done"):
                        close_qty = round(abs(qty_now) * 0.5, 3)

                        exit_side = "SELL" if qty_now > 0 else "BUY"

                        print(f"PIPE_PARTIAL_EXIT qty={close_qty}", flush=True)

                        exit_intent = {
                            "symbol": sym,
                            "side": exit_side,
                            "qty": close_qty,
                            "reason": "partial_tp"
                        }

                        raw_fill = self.paper.execute(exit_intent, st)

                        fill = ExecutionFill(
                            symbol=sym,
                            side=exit_side,
                            qty=close_qty,
                            price=float(getattr(raw_fill, "price", price)),
                            commission=0.0,
                            fill_id=getattr(raw_fill, "fill_id", None),
                        )

                        self.bus.publish({"type": "FILL", "fill": fill})

                        st["_partial_tp_done"] = True

        except Exception as e:
            print(f"PIPE_PARTIAL_EXIT_ERROR {e}", flush=True)

        # === EXIT ALPHA V2: MOMENTUM EXIT (slowdown detection) ===
        try:
            pos = self.pm.positions.get(sym)
            if pos:
                qty_now = float(getattr(pos, "qty", 0.0) or 0.0)

                if qty_now != 0:
                    prev_price = st.get("prev_price")
                    move = abs(price - prev_price) if prev_price else 0.0
                    atr_val = st.get("atr", 0.0) or 0.0

                    # замедление импульса
                    if atr_val > 0 and move < atr_val * 0.05:
                        if st.get("_last_momentum_warn") != True:
                            print("PIPE_MOMENTUM_SLOW", flush=True)
                            st["_last_momentum_warn"] = True

                        # если уже был профит — выходим
                        avg_price = float(getattr(pos, "avg_price", 0.0) or 0.0)

                        local_pnl_pct = 0.0
                        if avg_price:
                            local_pnl_pct = ((price - avg_price) / avg_price) if qty_now > 0 else ((avg_price - price) / avg_price)

                        if local_pnl_pct > 0.002:  # +0.2% достаточно
                            exit_side = "SELL" if qty_now > 0 else "BUY"

                            print("PIPE_MOMENTUM_EXIT", flush=True)

                            exit_intent = {
                                "symbol": sym,
                                "side": exit_side,
                                "qty": abs(qty_now),
                                "reason": "momentum_exit"
                            }

                            raw_fill = self.paper.execute(exit_intent, st)

                            fill = ExecutionFill(
                                symbol=sym,
                                side=exit_side,
                                qty=abs(qty_now),
                                price=float(getattr(raw_fill, "price", price)),
                                commission=0.0,
                                fill_id=getattr(raw_fill, "fill_id", None),
                            )

                            self.bus.publish({"type": "FILL", "fill": fill})
                            return

        except Exception as e:
            print(f"PIPE_MOMENTUM_EXIT_ERROR {e}", flush=True)

        # (removed ensure pnl_pct always defined - now always defined above)
        # === HARD PROFIT LOCK (late stage) ===
        if pnl_pct is not None and pnl_pct > 0.015:
            try:
                lock_dist = (st.get("atr", 0.0) or 0.0) * 0.5

                if qty_now > 0:
                    lock_price = price - lock_dist
                else:
                    lock_price = price + lock_dist

                self.exit_engine.set_dynamic_stop(sym, lock_price)
                print("PIPE_PROFIT_LOCK", flush=True)
            except Exception:
                pass

        # =========================================================
        # === FEATURES + REGIME (ОДИН РАЗ)
        # =========================================================

        prev_price = st.get("prev_price", price)

        # === ATR FIX (ограничение и нормализация) ===
        raw_atr = st.get("atr") or abs(price - prev_price) or price * 0.003
        atr = min(raw_atr, price * 0.02)  # максимум 2% от цены
        st["atr"] = atr

        # EMA trend (throttled to once per second)
        if "_last_ema_ts" not in st or time.time() - st["_last_ema_ts"] > 1:
            alpha_fast = 2 / (5 + 1)
            alpha_slow = 2 / (20 + 1)

            ema_fast = alpha_fast * price + (1 - alpha_fast) * st.get("ema_fast", price)
            ema_slow = alpha_slow * price + (1 - alpha_slow) * st.get("ema_slow", price)

            st["ema_fast"] = ema_fast
            st["ema_slow"] = ema_slow
            st["_last_ema_ts"] = time.time()

        ema_fast = st.get("ema_fast", price)
        ema_slow = st.get("ema_slow", price)
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
                    print("PIPE_TREND_WEAK_ALLOW", flush=True)

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
        # REMOVE DEBUG REGIME_ROUTER print

        try:
            # === MTF FILTER (WEAK VERSION, no blocking) ===
            m5 = st.get("m5")
            if m5:
                trend = regime.trend

                if trend == "up" and not (price > m5):
                    if st.get("_last_mtf") != "long":
                        print("PIPE_MTF_WEAK_LONG", flush=True)
                        st["_last_mtf"] = "long"

                if trend == "down" and not (price < m5):
                    if st.get("_last_mtf") != "short":
                        print("PIPE_MTF_WEAK_SHORT", flush=True)
                        st["_last_mtf"] = "short"

            # === TREND MODE (BREAKOUT ONLY, STRATEGY DISABLED) ===
            if regime.trend in ("up", "down"):
                raw_intent = None  # force fallback breakout logic

            # === MEAN REVERSION ===
            elif regime.trend == "flat":
                raw_intent = self.mean_reversion.on_quote(st)
                # fallback to breakout if no MR signal
                if raw_intent is None:
                    pass

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

        hist = st.get("price_history", [])
        if len(hist) >= 2:
            local_high = max(hist[:-1])
            local_low = min(hist[:-1])
        else:
            local_high = curr_price
            local_low = curr_price

        st["local_high"] = local_high
        st["local_low"] = local_low

        history.append(curr_price)
        if len(history) > 20:
            st["price_history"] = history[-20:]
        # === FIX: синхронизация тренда ===
        st["regime_trend"] = regime.trend
        # === GLOBAL FALLBACK (BREAKOUT LEVELS + ATR) ===
        # PATCH: SMART ENTRY (RETEST MODE)
        # вставить в fallback breakout блок

        # === SMART ENTRY STATE ===
        st.setdefault("pending_breakout", None)

        # === SOFT TREND FILTER (NO HARD BLOCK) ===
        trend_dir = st.get("regime_trend")
        trend_penalty = 1.0

        # === BREAKOUT DEDUP (LEVEL TTL) ===
        try:
            last_bo = st.get("_last_breakout")
            now_ts = time.time()
            dedup_ttl = float(os.getenv("BREAKOUT_DEDUP_TTL", "10"))

            # determine candidate side/level (pre-check)
            cand_side = None
            cand_level = None
            if curr_price > local_high - atr * 1.2 and trend_dir == "up":
                cand_side, cand_level = "BUY", local_high
            elif curr_price < local_low + atr * 1.2 and trend_dir == "down":
                cand_side, cand_level = "SELL", local_low

            if last_bo and cand_side and cand_level:
                same = (last_bo.get("side") == cand_side and abs(last_bo.get("level", 0.0) - cand_level) < (atr or 1e-9))
                if same and (now_ts - last_bo.get("ts", 0.0)) < dedup_ttl:
                    print("PIPE_BREAKOUT_DEDUP", flush=True)
                    return
        except Exception:
            pass

        # === HARD BLOCKS REMOVED, SOFT LOGIC ONLY ===
        if trend_dir == "down" and curr_price > local_high - atr * 1.2:
            trend_penalty = 0.6
            if st.get("_last_bo_soft") != "down":
                print("PIPE_BREAKOUT_SOFT trend_down_penalty", flush=True)
                st["_last_bo_soft"] = "down"
            # HARD BLOCK REMOVED — ALWAYS ALLOW FLOW
            pass

        elif trend_dir == "up" and curr_price < local_low + atr * 1.2:
            trend_penalty = 0.6
            if st.get("_last_bo_soft") != "up":
                print("PIPE_BREAKOUT_SOFT trend_up_penalty", flush=True)
                st["_last_bo_soft"] = "up"
            # HARD BLOCK REMOVED — ALWAYS ALLOW FLOW
            pass

        # === ALLOWED BREAKOUTS ONLY ===
        # === EARLY BREAKOUT (ANTICIPATION ENTRY) ===
        if curr_price > local_high - atr * 0.5 and trend_dir == "up":
            # HARD BLOCK REMOVED — ALWAYS ALLOW FLOW
            pass
            st["pending_breakout"] = {
                "side": "BUY",
                "level": local_high,
                "ts": time.time()
            }
            st["_last_breakout"] = {"side": "BUY", "level": local_high, "ts": time.time()}
            print(f"PIPE_BREAKOUT_DETECTED BUY level={local_high}", flush=True)

        elif curr_price < local_low + atr * 0.5 and trend_dir == "down":
            # HARD BLOCK REMOVED — ALWAYS ALLOW FLOW
            pass
            st["pending_breakout"] = {
                "side": "SELL",
                "level": local_low,
                "ts": time.time()
            }
            st["_last_breakout"] = {"side": "SELL", "level": local_low, "ts": time.time()}
            print(f"PIPE_BREAKOUT_DETECTED SELL level={local_low}", flush=True)

        else:
            # === MICRO BREAKOUT (PROP DESK FAST ENTRY) ===
            try:
                micro_k = float(os.getenv("MICRO_BREAKOUT_K", "0.15"))

                if curr_price > local_high - atr * micro_k and trend_dir == "up":
                    print("PIPE_MICRO_BREAKOUT BUY", flush=True)
                    st["pending_breakout"] = {"side": "BUY", "level": local_high, "ts": time.time()}

                elif curr_price < local_low + atr * micro_k and trend_dir == "down":
                    print("PIPE_MICRO_BREAKOUT SELL", flush=True)
                    st["pending_breakout"] = {"side": "SELL", "level": local_low, "ts": time.time()}
            except Exception:
                pass
            # === SAFE IMPULSE ENTRY (LEVEL 3, PROP-DESK STYLE) ===
            try:
                prev_price = st.get("prev_price")

                # защита от None (критический фикс)
                if prev_price is None:
                    st["prev_price"] = curr_price
                    return

                # === ENTRY ALPHA V2: MULTI-TRIGGER SCORE ===
                score = 0

                # breakout proximity
                if abs(curr_price - local_high) < atr * 0.3 or abs(curr_price - local_low) < atr * 0.3:
                    score += 1

                # momentum
                if prev_price and abs(curr_price - prev_price) > atr * 0.15:
                    score += 1

                # volatility support
                if atr_pct > 0.01:
                    score += 1

                # trend alignment
                if (trend_dir == "up" and curr_price > prev_price) or (trend_dir == "down" and curr_price < prev_price):
                    score += 1

                # DEBUG
                if score >= 2:
                    print(f"PIPE_ENTRY_SCORE {score}", flush=True)

                move = abs(curr_price - prev_price)

                atr_val = st.get("atr") or 0.0
                atr_pct = abs(atr_val / curr_price) if curr_price else 0.0

                impulse_k = float(os.getenv("IMPULSE_K", "0.2"))
                # impulse = move > atr_val * impulse_k
                impulse = (move > atr_val * impulse_k) or score >= 2

                trend_dir = st.get("regime_trend")

                # усиливаем только при нормальной волатильности
                if impulse and atr_pct > 0.003:
                    if trend_dir == "up" and curr_price > prev_price:
                        print("PIPE_IMPULSE_ENTRY BUY", flush=True)
                        entry_side = "BUY"

                    elif trend_dir == "down" and curr_price < prev_price:
                        print("PIPE_IMPULSE_ENTRY SELL", flush=True)
                        entry_side = "SELL"

                    else:
                        entry_side = None

                    if entry_side:
                        risk_per_trade = 0.008
                        capital = getattr(self.portfolio, "starting_cash", 100000)
                        risk_amount = capital * risk_per_trade

                        atr_safe = max(atr_val, curr_price * 0.002)
                        stop_distance = max(atr_safe * 1.3, curr_price * 0.006, 0.08)

                        alpha_boost = 1.0
                        if score >= 3:
                            alpha_boost = 1.3
                        elif score == 2:
                            alpha_boost = 1.15

                        qty = round((risk_amount / stop_distance) * trend_penalty * alpha_boost, 3)
                        qty = max(min(qty, 1.0), 0.1)

                        # === ADAPTIVE TP FOR IMPULSE ===
                        atr_pct = abs(atr_val / curr_price) if curr_price else 0.0

                        base_rr = 1.6
                        if atr_pct > 0.02:
                            base_rr += 0.5
                        if score >= 3:
                            base_rr += 0.5

                        rr = max(1.3, min(base_rr, 3.2))

                        take_distance = stop_distance * rr

                        print(f"PIPE_ADAPTIVE_TP_IMPULSE rr={round(rr, 2)} atr_pct={round(atr_pct, 4)}", flush=True)
                        print(f"PIPE_ENTRY_ALPHA_V2 side={entry_side} score={score}", flush=True)
                        raw_intent = {
                            "symbol": sym,
                            "side": entry_side,
                            "qty": qty,
                            "price": curr_price,
                            "features": {
                                "stop": curr_price - stop_distance if entry_side == "BUY" else curr_price + stop_distance,
                                "take": curr_price + take_distance if entry_side == "BUY" else curr_price - take_distance,
                                "rr": rr,
                                "impulse": True
                            }
                        }

                        st["_smart_entry_fired"] = True
                    else:
                        return
                else:
                    return

            except Exception as e:
                print(f"PIPE_IMPULSE_ERROR {e}", flush=True)
                return

        # === SMART ENTRY DEDUP (PER PENDING) ===
        if st.get("_smart_entry_fired"):
            st["_smart_entry_fired"] = False

        # === RETEST ENTRY ===
        pb = st.get("pending_breakout")

        if pb:
            side = pb["side"]
            level = pb["level"]

            # === HARD TREND ALIGNMENT (FINAL GUARD) ===
            trend_dir = st.get("regime_trend")
            if (trend_dir == "down" and side == "BUY") or (trend_dir == "up" and side == "SELL"):
                print("PIPE_SMART_ENTRY_BLOCK trend_mismatch", flush=True)
                st["pending_breakout"] = None
                return

            # TTL (устаревание сигнала)
            if time.time() - pb["ts"] > 60:
                st["pending_breakout"] = None
                return

            # BUY RETEST
            if side == "BUY":
                if curr_price <= level + atr * 0.9:
                    print("PIPE_SMART_ENTRY BUY", flush=True)
                    entry_side = "BUY"
                else:
                    return

            # SELL RETEST
            elif side == "SELL":
                if curr_price >= level - atr * 0.9:
                    print("PIPE_SMART_ENTRY SELL", flush=True)
                    entry_side = "SELL"
                else:
                    return

            # === EXECUTE ENTRY ===
            risk_per_trade = 0.01
            capital = getattr(self.portfolio, "starting_cash", 100000)
            risk_amount = capital * risk_per_trade

            atr_safe = max(atr, curr_price * 0.002)
            stop_distance = max(atr_safe * 1.5, curr_price * 0.008, 0.1)
            stop_distance = max(stop_distance, 0.05)

            qty = round((risk_amount / stop_distance) * trend_penalty, 3)
            qty = max(min(qty, 1.0), 0.1)

            # === ADAPTIVE TAKE PROFIT (VOL + TREND BASED) ===
            atr_pct = abs(atr / curr_price) if curr_price else 0.0
            trend = st.get("regime_trend")

            # базовый RR
            base_rr = 1.8

            # тренд усиливает цель
            if trend in ("up", "down"):
                base_rr += 0.4

            # волатильность усиливает TP
            if atr_pct > 0.02:
                base_rr += 0.6
            elif atr_pct < 0.005:
                base_rr -= 0.3

            # ограничение
            rr = max(1.2, min(base_rr, 3.0))

            take_distance = stop_distance * rr

            print(f"PIPE_ADAPTIVE_TP rr={round(rr, 2)} atr_pct={round(atr_pct, 4)} trend={trend}", flush=True)

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

            st["_smart_entry_fired"] = True

            # сброс состояния
            st["pending_breakout"] = None
            # reset smart-entry flag after short cooldown
            try:
                st["_smart_entry_reset_ts"] = time.time() + float(os.getenv("SMART_ENTRY_RESET_SEC", "15"))
            except Exception:
                pass

        else:
            return

    # === ROLLBACK PROTECTION (анти-плохой вход) ===
        try:
            last_price = st.get("last")
            prev_price = st.get("prev_price")

            if last_price and prev_price and raw_intent:
                move = abs(last_price - prev_price)

                atr_val = (st.get("atr", 0.0) or 0.0)
                atr_pct = abs(atr_val / curr_price) if curr_price else 0.0

                min_move_k = float(os.getenv("ROLLBACK_MIN_MOVE_K", "0.04"))  # чуть мягче

                # === SMALL MOVE (только ультра шум блокируем) ===
                if move < atr_val * min_move_k:
                    if atr_pct < 0.008:  # 🔥 было 0.015 → теперь только мёртвый рынок
                        print("PIPE_ROLLBACK_BLOCK tiny_move", flush=True)
                        st["prev_price"] = curr_price
                        return
                    else:
                        print("PIPE_ROLLBACK_SOFT_ALLOW small_move", flush=True)

                # === DIRECTION CHECK (почти всегда allow) ===
                side = raw_intent.get("side")

                if side == "BUY" and last_price < prev_price:
                    if atr_pct < 0.008:  # 🔥 было 0.02 → сильно ослабили
                        print("PIPE_ROLLBACK_BLOCK wrong_direction_tiny", flush=True)
                        st["prev_price"] = curr_price
                        return
                    else:
                        print("PIPE_ROLLBACK_SOFT_ALLOW direction", flush=True)

                if side == "SELL" and last_price > prev_price:
                    if atr_pct < 0.008:
                        print("PIPE_ROLLBACK_BLOCK wrong_direction_tiny", flush=True)
                        st["prev_price"] = curr_price
                        return
                    else:
                        print("PIPE_ROLLBACK_SOFT_ALLOW direction", flush=True)

        except Exception as e:
            print(f"PIPE_ROLLBACK_ERROR {e}", flush=True)

        # REMOVE DEBUG raw_intent print
        # === FINAL TREND FILTER (SOFT, ADAPTIVE) ===
        try:
            if raw_intent:
                side = raw_intent.get("side")
                trend = st.get("regime_trend")
                # informational only, no blocking
                if trend == "up" and side != "BUY":
                    print("PIPE_TREND_SOFT_MISMATCH up", flush=True)
                if trend == "down" and side != "SELL":
                    print("PIPE_TREND_SOFT_MISMATCH down", flush=True)
        except Exception:
            pass
        # REMOVE DEBUG price_in_state print
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

        # === ENSURE prev_price is updated every tick ===
        st["prev_price"] = curr_price

        # === TIME STOP (exit stale trades) ===
        try:
            pos_open_ts = st.get("pos_open_ts")
            now_ts = time.time()

            if pos_open_ts and (now_ts - pos_open_ts) > float(os.getenv("MAX_HOLD_SEC", "300")):
                print("PIPE_TIME_EXIT", flush=True)

                pos = self.pm.positions.get(sym)
                if pos:
                    qty_now = float(getattr(pos, "qty", 0.0) or 0.0)
                    if qty_now != 0:
                        side = "SELL" if qty_now > 0 else "BUY"

                        exit_intent = {
                            "symbol": sym,
                            "side": side,
                            "qty": abs(qty_now),
                            "reason": "time_exit"
                        }

                        raw_fill = self.paper.execute(exit_intent, st)

                        fill = ExecutionFill(
                            symbol=sym,
                            side=side,
                            qty=abs(qty_now),
                            price=float(getattr(raw_fill, "price", st.get("last") or 0.0)),
                            commission=0.0,
                            fill_id=getattr(raw_fill, "fill_id", None),
                        )

                        self.bus.publish({"type": "FILL", "fill": fill})
                        return
        except Exception:
            pass

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

        # REMOVE DEBUG routed print

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
                    # REMOVE DEBUG PRICE INJECTED print
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

            # === ADAPTIVE TREND FILTER (PROP-DESK STYLE) ===
            ema_fast = st.get("ema_fast", price)
            ema_slow = st.get("ema_slow", price)

            trend_strength = abs(ema_fast - ema_slow) / price if price else 0.0
            atr_pct = abs(st.get("atr", 0.0) / price) if price else 0.0

            # динамический порог силы тренда
            base_trend_min = float(os.getenv("TREND_STRENGTH_MIN", "0.0003"))

            # сильная вола → снижаем требования (ловим импульс)
            if atr_pct > 0.02:
                trend_min = base_trend_min * 0.5
            # низкая вола → ужесточаем (фильтруем шум)
            elif atr_pct < 0.005:
                trend_min = base_trend_min * 2.0
            else:
                trend_min = base_trend_min

            # === SOFT ALIGNMENT ONLY (NO HARD BLOCK) ===
            if trend in ("up", "down") and trend_strength > trend_min:
                last_block = st.get("_last_trend_block")

                if trend == "up" and side != "BUY":
                    if last_block != ("up", side):
                        print(f"PIPE_TREND_MISMATCH expected=BUY actual={side}", flush=True)
                        st["_last_trend_block"] = ("up", side)
                    print("PIPE_TREND_SOFT_MISMATCH up", flush=True)

                if trend == "down" and side != "SELL":
                    if last_block != ("down", side):
                        print(f"PIPE_TREND_MISMATCH expected=SELL actual={side}", flush=True)
                        st["_last_trend_block"] = ("down", side)
                    print("PIPE_TREND_SOFT_MISMATCH down", flush=True)

                st["_last_trend_block"] = None

            # === SOFT MODE (trend weak → allow but warn)
            elif trend in ("up", "down"):
                print(f"PIPE_TREND_WEAK_ALLOW trend={trend} strength={round(trend_strength,6)}", flush=True)

            # === IMPULSE FILTER (adaptive)
            impulse = abs(st.get("ema_fast", price) - price) / price if price else 0.0
            impulse_min = float(os.getenv("IMPULSE_MIN", "0.0003"))

            # при высокой воле даём больше свободы
            if atr_pct > 0.02:
                impulse_min *= 0.5

            if impulse < impulse_min and regime.volatility != "high":
                print("PIPE_NO_IMPULSE_SOFT", flush=True)

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

            dedup_ttl = float(os.getenv("SIGNAL_DEDUP_TTL", "3"))
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

        # === RESET PARTIAL TP FLAG ON POSITION CLOSE ===
        if pos and float(getattr(pos, "qty", 0.0) or 0.0) == 0.0:
            st["_partial_tp_done"] = False

        # === PYRAMIDING (LEVEL 2: add to winners only) ===
        if current_qty != 0.0:
            # === CLUSTER CHECK FOR PYRAMIDING ===
            try:
                if not self._cluster_risk_check(sym, st):
                    print("PIPE_PYRAMID_CLUSTER_BLOCK", flush=True)
                    return
            except Exception:
                pass
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
                # REMOVE DEBUG_PYRAMID print
                # добавляем только если уже есть прибыль
                if pnl_pct > threshold:
                    print(f"PIPE_PYRAMID_ADD pnl={round(pnl_pct,4)}", flush=True)

                    # Русский коммент: адаптивный размер пирамиды (уменьшается с ростом позиции)
                    scale = min(0.5, max(0.2, 1.0 / (1.0 + abs(current_qty))))
                    intent["qty"] = round(intent.get("qty", 0.0) * scale, 3)

                else:
                    print("PIPE_PYRAMID_WAIT not_ready", flush=True)
                    return
            else:
                # === FLIP PROTECTION (ANTI-CHURN) ===
                try:
                    flip_cooldown = float(os.getenv("FLIP_COOLDOWN_SEC", "30"))
                    last_flip_ts = getattr(self, "_last_flip_ts", 0.0)
                    now_ts = time.time()

                    # блокируем частые flip
                    if now_ts - last_flip_ts < flip_cooldown:
                        print("PIPE_FLIP_BLOCK cooldown", flush=True)
                        return

                    # разрешаем flip только при импульсе или высокой воле
                    atr_pct = abs(st.get("atr", 0.0) / (st.get("last") or 1.0))
                    is_impulse = intent.get("features", {}).get("impulse")

                    if not is_impulse and atr_pct < 0.015:
                        print("PIPE_FLIP_BLOCK weak_signal", flush=True)
                        return

                except Exception:
                    pass
                # === POSITION FLIP (REVERSE INSTEAD OF BLOCK) ===
                try:
                    print("PIPE_POSITION_FLIP", flush=True)

                    # сначала закрываем текущую позицию
                    close_side = "SELL" if current_qty > 0 else "BUY"

                    close_intent = {
                        "symbol": sym,
                        "side": close_side,
                        "qty": abs(current_qty),
                        "reason": "flip_close"
                    }

                    raw_fill = self.paper.execute(close_intent, st)

                    raw_qty = float(getattr(raw_fill, "qty", 0.0) or 0.0)
                    exec_price = float(getattr(raw_fill, "price", st.get("last") or 0.0))

                    commission = 0.0
                    if hasattr(self.fee_tax, "commission"):
                        commission = self.fee_tax.commission(
                            symbol=close_intent.get("symbol"),
                            qty=abs(raw_qty),
                            price=exec_price
                        )

                    fill = ExecutionFill(
                        symbol=close_intent.get("symbol"),
                        side=close_side,
                        qty=abs(raw_qty),
                        price=exec_price,
                        commission=commission,
                        fill_id=getattr(raw_fill, "fill_id", None),
                    )

                    self.bus.publish({"type": "FILL", "fill": fill})

                    # после закрытия разрешаем вход в новую сторону
                    print("PIPE_POSITION_FLIP_CLOSED", flush=True)
                    # фиксируем время flip
                    try:
                        self._last_flip_ts = time.time()
                    except Exception:
                        pass

                except Exception as e:
                    print(f"PIPE_POSITION_FLIP_ERROR {e}", flush=True)
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
        base_cooldown = float(os.getenv("TRADE_COOLDOWN_SEC", "20"))

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

        # === ADAPTIVE COOLDOWN (FAST ENTRY MODE) ===
        allow_fast_reentry = False

        try:
            # разрешаем быстрый повторный вход по тренду или импульсу
            last_side = getattr(self, "_last_trade_side", None)
            curr_side = intent.get("side")

            is_same_direction = last_side == curr_side
            is_impulse = intent.get("features", {}).get("impulse")

            if is_same_direction or is_impulse:
                allow_fast_reentry = True

        except Exception:
            pass

        if not allow_fast_reentry and (now_ts - last_ts < cooldown_sec):
            if st.get("_last_cd") != True:
                print("PIPE_COOLDOWN_BLOCK", flush=True)
                st["_last_cd"] = True
            return
        else:
            if allow_fast_reentry:
                print("PIPE_COOLDOWN_SOFT_ALLOW", flush=True)

        # === LOSS COOLDOWN CHECK ===
        if sym in self._cooldown_until:
            if time.time() < self._cooldown_until[sym]:
                # === LOSS COOLDOWN (adaptive) ===
                last_loss_ts = st.get("last_loss_ts", 0.0)
                cooldown_sec = float(os.getenv("LOSS_COOLDOWN_SEC", "60"))

                time_since_loss = time.time() - last_loss_ts

                if time_since_loss < cooldown_sec:
                    history = st.get("price_history", [])

                    if len(history) >= 2:
                        impulse = abs(curr_price - history[-2])

                        # разрешаем вход если есть сильный импульс
                        if impulse > atr * 0.5:
                            print("PIPE_LOSS_COOLDOWN_SOFT_ALLOW impulse", flush=True)
                        else:
                            print("PIPE_LOSS_COOLDOWN_BLOCK", flush=True)
                            return
                    else:
                        print("PIPE_LOSS_COOLDOWN_BLOCK", flush=True)
                        return
            # Русский коммент: если cooldown активен, но условие не выполнено — просто блокируем вход
            pass


        self._last_trade_ts = now_ts
        st["_last_cd"] = False
        # сохраняем направление последней сделки
        try:
            self._last_trade_side = intent.get("side")
        except Exception:
            pass
        # фиксируем время открытия позиции
        try:
            st["pos_open_ts"] = time.time()
        except Exception:
            pass

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
        # === CLUSTER RISK PRE-CHECK (LEVEL 2)
        # =========================================================
        try:
            if not self._cluster_risk_check(sym, st):
                return
        except Exception as e:
            print(f"PIPE_CLUSTER_FATAL {e}", flush=True)
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
        if intent.get("price") is None:
            px = st.get("last") or st.get("price") or st.get("bid") or st.get("ask")
            if px is not None:
                intent["price"] = float(px)
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
