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
        total_exposure=float(total_exposure),
        current_symbol_exposure=float(current_symbol_exposure),
        equity=float(equity),
        starting_capital=float(starting_capital),
        starting_cash=float(starting_capital),
        daily_realized_pnl=float(daily_realized_pnl or 0.0),
        portfolio_heat=float(portfolio_heat or 0.0),
        intent=intent,
        market_state=market_state,
        portfolio=portfolio,
    )


def _decision_allowed(decision) -> bool:
    """Русский коммент: нормализуем разные типы RiskDecision."""
    if isinstance(decision, bool):
        return decision
    if decision is None:
        return False
    for flag in ("allowed", "is_allowed", "ok", "approved", "pass_"):
        if hasattr(decision, flag):
            return bool(getattr(decision, flag))
    return bool(decision)


class PaperTradingPipeline:
    """MarketData → Strategy → Risk → PaperExecution → publish(FILL) → PM.apply_fill"""

    def __init__(self, bus, portfolio, position_manager, risk, paper, strategy, done=None, filter_engine=None, filter_context_builder=None):
        from finam_core.strategy.mean_reversion import MeanReversionStrategy
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

    def attach(self):
        # Русский коммент: Pipeline B — подписываемся на QUOTE, а FILL применяем централизованно.
        self.bus.subscribe("QUOTE", self._on_quote)
        self.bus.subscribe("FILL", self._on_fill)
        LOG.debug("PIPE attach(): subscribed QUOTE/FILL")
        # 🔥 ПОДПИСКА НА КОТИРОВКИ
        self.bus.subscribe("QUOTE", self._on_quote)

    def _on_quote(self, event: dict):
        sym = event.get("symbol")
        if not sym:
            return

        # === STATE UPDATE ===
        st = self._mkt.get(sym, {})
        st.update(event)
        self._mkt[sym] = st

        last = st.get("last")
        if last is None:
            return

        price = float(last)

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

                fill = self.paper.execute(exit_intent, st)
                self.bus.publish({"type": "FILL", "fill": fill})
                self.exit_engine.mark_exit(sym)
                return

        # =========================================================
        # === FEATURES + REGIME (ОДИН РАЗ)
        # =========================================================

        prev_price = st.get("prev_price", price)

        atr = st.get("atr") or abs(price - prev_price) or price * 0.003

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

        st["prev_price"] = price
        st["regime_trend"] = regime.trend
        st["regime_vol"] = regime.volatility

        print(
            f"REGIME trend={regime.trend} vol={regime.volatility} atr={regime.atr}",
            flush=True,
        )

        # =========================================================
        # === STRATEGY SELECTION (FIXED SAFE VERSION)
        # =========================================================

        raw_intent = None

        try:
            # 🔹 трендовый режим
            if regime.trend in ("up", "down"):
                if hasattr(self.strategy, "generate"):
                    raw_intent = self.strategy.generate(st, policy="first")
                elif hasattr(self.strategy, "on_quote"):
                    raw_intent = self.strategy.on_quote(st)

            # 🔹 флэт
            elif regime.trend == "flat":
                if hasattr(self.mean_reversion, "on_quote"):
                    raw_intent = self.mean_reversion.on_quote(st)

        except Exception as e:
            print(f"STRATEGY_ERROR {e}", flush=True)
            return

        if raw_intent is None:
            return

        print("DEBUG raw_intent:", raw_intent, flush=True)
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
                f"PIPE_REGIME_WARN trend={regime.trend} vol={regime.volatility}",
                flush=True,
            )
            # НЕ БЛОКИРУЕМ
        # =========================================================
        # === ROUTER
        # =========================================================
        routed = self.signal_router.route(raw_intent)

        print("DEBUG routed:", routed)

        if not routed.allowed:
            print(f"PIPE_SIGNAL_REJECT reason={routed.reason}", flush=True)
            return

        intent = routed.intent.to_dict()

        # =========================================================
        # === POSITION GUARD
        # =========================================================
        pos = self.pm.positions.get(sym)
        if pos and float(getattr(pos, "qty", 0.0)) != 0.0:
            print("PIPE_POSITION_BLOCK", flush=True)
            return
        # НЕ блокируем — даём риск-движку решать

        # =========================================================
        # === RISK
        # =========================================================
        if os.getenv("RISK_SOFT") == "1":
            approved = True
        else:
            ctx = build_risk_context(intent, self.portfolio, st)
            decision = self.risk.evaluate(ctx)
            approved = _decision_allowed(decision)

        if not approved:
            print("PIPE_RISK_REJECT", flush=True)
            return

        print("PIPE_RISK_OK", flush=True)

        # =========================================================
        # === EXECUTION
        # =========================================================
        raw_fill = self.paper.execute(intent, st)

        # FIX: нормализуем fill → всегда создаём ExecutionFill без лишних полей
        fill = ExecutionFill(
            symbol=intent.get("symbol"),
            side=str(intent.get("side", "BUY")).upper(),
            qty=float(intent.get("qty", 0.0) or 0.0),
            price=float(
                getattr(raw_fill, "price", None)
                or st.get("last")
                or st.get("price")
                or 0.0
            ),
            fill_id=getattr(raw_fill, "fill_id", None),
        )

        # SAFETY: гарантируем корректный fill
        if not hasattr(fill, "side") or fill.side is None:
            LOG.error("FILL BUILD ERROR: missing side, intent=%s raw_fill=%s", intent, raw_fill)
            return

        print(
            f"PIPE_EXEC side={intent.get('side')} qty={intent.get('qty')}",
            flush=True,
        )

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
        if fill is None:
            return

        # SAFETY: проверка обязательных полей
        if not hasattr(fill, "side") or not hasattr(fill, "qty") or fill.side is None:
            LOG.error("INVALID FILL: missing fields %s", fill)
            return

        self.pm.apply_fill(fill)

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
        # FIX: intent здесь не определён — используем fill
        try:
            self.notifier.send(
                f"📈 ENTRY\n"
                f"{getattr(fill, 'symbol', None)}\n"
                f"{getattr(fill, 'side', None)} qty={getattr(fill, 'qty', None)}\n"
                f"price={getattr(fill, 'price', None)}"
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
            execution_type="paper"
        )

        self.notifier.send(
            "✅ PAPER FILL\n"
            f"symbol={getattr(fill, 'symbol', None)}\n"
            f"side={getattr(fill, 'side', None)}\n"
            f"qty={getattr(fill, 'qty', None)}\n"
            f"price={getattr(fill, 'price', None)}\n"
            f"id={getattr(fill, 'fill_id', None)}"
        )

        # exit-on-fill
        if not self._filled_once and os.getenv("EXIT_ON_FILL", "1") == "1":
            self._filled_once = True
            LOG.info("DONE: filled once, exiting")
            if self._done is not None:
                try:
                    self._done.set()
                except Exception:
                    pass
