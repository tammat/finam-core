# src/finam_core/pipelines/paper_pipeline.py
# Русский коммент: Pipeline B (event-driven).
# QUOTE -> Strategy -> Risk -> PaperExecution -> publish(FILL) -> Accounting(PM.apply_fill)

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
from finam_core.risk.regime_layer import RegimeLayer
from finam_core.risk.portfolio_heat import PortfolioHeatEngine
from finam_core.risk.kill_switch import KillSwitchEngine
from finam_core.risk.correlation_risk import CorrelationRiskEngine
from finam_core.risk.unified_decision import UnifiedRiskDecision, RiskDecisionRecorder
from finam_core.signals.signal_router import SignalRouter
from finam_core.features.live_feature_buffer import LiveFeatureBuffer

try:
    from finam_core.strategy.filters.regime_filters import FilterContext, FilterEngine
except Exception:
    FilterContext = None
    FilterEngine = None

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
        self.regime_layer = RegimeLayer()
        self.portfolio_heat = PortfolioHeatEngine()
        self.kill_switch = KillSwitchEngine()
        self.correlation_risk = CorrelationRiskEngine()
        self.risk_recorder = RiskDecisionRecorder(self.pg_logger)
        self.signal_router = SignalRouter()
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

        # quote logging throttled
        now = time.time()
        if self._quote_log_every > 0 and (now - self._last_quote_log_ts) >= self._quote_log_every:
            self._last_quote_log_ts = now
            LOG.info("QUOTE %s last=%s", sym, event.get("last"))

        # merge quote state
        st = self._mkt.get(sym, {})
        st.update(event)
        self._mkt[sym] = st

        # optional mark-to-market
        last = st.get("last")
        if last is not None:
            try:
                st["atr"] = self.live_atr.update(last)
            except Exception as e:
                LOG.debug("LIVE ATR UPDATE FAILED: %s", e)

        if last is not None and hasattr(self.portfolio, "mark_price"):
            try:
                self.portfolio.mark_price(sym, float(last))
            except Exception:
                pass

        # === Risk v2: SL/TP exit by quote ===
        try:
            pos = self.pm.positions.get(sym)
            qty_now = float(getattr(pos, "qty", 0.0) or 0.0) if pos is not None else 0.0
            avg_now = float(getattr(pos, "avg_price", 0.0) or 0.0) if pos is not None else 0.0
            last_px = float(last) if last is not None else None
        except Exception:
            qty_now = 0.0
            avg_now = 0.0
            last_px = None

        if qty_now != 0.0 and last_px is not None:
            exit_decision = self.exit_engine.evaluate(sym, qty_now, avg_now, last_px)
            if exit_decision.should_exit:
                exit_intent = {
                    "symbol": sym,
                    "side": exit_decision.side,
                    "qty": exit_decision.qty,
                    "reason": exit_decision.reason,
                }
                print(
                    f"PIPE_EXIT_V2 reason={exit_decision.reason} side={exit_decision.side} qty={exit_decision.qty}",
                    flush=True,
                )
                fill = self.paper.execute(exit_intent, st)

                fill_price = float(getattr(fill, "price", 0.0) or 0.0)
                exit_qty = abs(_safe_float(getattr(fill, "qty", 0.0), default=0.0) or 0.0)
                fee_result = self.fee_tax.trade_fees(exit_qty * fill_price)
                total_commission = (
                    float(getattr(fill, "commission", 0.0) or 0.0)
                    + fee_result.broker_fee
                    + fee_result.exchange_fee
                )

                exec_fill = ExecutionFill(
                    fill_id=getattr(fill, "fill_id", None),
                    symbol=getattr(fill, "symbol", None) or exit_intent.get("symbol"),
                    side=str(exit_decision.side).upper(),
                    qty=exit_qty,
                    price=fill_price,
                    commission=total_commission,
                    origin="paper",
                )

                self.bus.publish({"type": "FILL", "fill": exec_fill, "origin": "paper"})
                self.exit_engine.mark_exit(sym)
                self._cooldown_until[sym] = time.time() + float(os.getenv("ENTRY_COOLDOWN_SEC", "300"))
                return


        # --- FEATURE BUFFER ---
        fb = self.features.get(sym)
        if fb is None:
            fb = LiveFeatureBuffer()
            self.features[sym] = fb

        # --- FEATURE BUFFER ---
        fb = self.features.get(sym)
        if fb is None:
            fb = LiveFeatureBuffer()
            self.features[sym] = fb

        fb.update(st)
        feat = fb.compute()

        # Русский коммент: если включён tradeability-фильтр, не даём Strategy сгенерировать одноразовый intent до прогрева фич.
        if self.filter_engine is not None:
            gate = str(getattr(self.filter_engine, "params", {}).get("tradeability_gate", "") or "").strip().lower()
            if gate not in ("", "off", "none") and feat is None:
                LOG.info("FILTER WARMUP: waiting for live features symbol=%s", sym)
                return

        # trailing exit
        try:
            pos = self.pm.positions.get(sym)
            qty_now = float(getattr(pos, "qty", 0.0) or 0.0) if pos is not None else 0.0
            last_px = float(st.get("last")) if st.get("last") is not None else None
        except Exception:
            qty_now = 0.0
            last_px = None

        if qty_now > 0 and last_px is not None:
            exit_intent = self.trailing_exit.evaluate_long(sym, last_px, qty_now)
            if exit_intent:
                LOG.info("TRAILING EXIT intent=%s", exit_intent)
                fill = self.paper.execute(exit_intent, st)

                fill_price = float(getattr(fill, "price", 0.0) or 0.0)
                exit_qty = abs(_safe_float(getattr(fill, "qty", 0.0), default=0.0) or 0.0)
                fee_result = self.fee_tax.trade_fees(exit_qty * fill_price)
                total_commission = (
                    float(getattr(fill, "commission", 0.0) or 0.0)
                    + fee_result.broker_fee
                    + fee_result.exchange_fee
                )

                exec_fill = ExecutionFill(
                    fill_id=getattr(fill, "fill_id", None),
                    symbol=getattr(fill, "symbol", None) or exit_intent.get("symbol"),
                    side="SELL",
                    qty=exit_qty,
                    price=fill_price,
                    commission=total_commission,
                    origin="paper",
                )

                self.bus.publish({"type": "FILL", "fill": exec_fill, "origin": "paper"})
                self.trailing_exit.reset(sym)
                self._cooldown_until[sym] = time.time() + float(os.getenv("ENTRY_COOLDOWN_SEC", "300"))
                return

        # entry cooldown после выхода по SL/TP
        if time.time() < float(self._cooldown_until.get(sym, 0.0)):
            LOG.info("ENTRY COOLDOWN: skip symbol=%s", sym)
            return

        # Risk v2 cooldown
        if self.exit_engine.is_cooldown(sym):
            print("PIPE_RISK_V2_COOLDOWN", flush=True)
            return

        # === Regime Layer: block bad market regimes before new entry ===
        if os.getenv("REGIME_ENABLE", "0") == "1":
            regime_decision = self.regime_layer.evaluate(
                atr=st.get("atr"),
                price=st.get("last"),
            )

            if not regime_decision.allowed:
                now = time.time()
                interval = float(os.getenv("REGIME_LOG_EVERY_SEC", "30"))

                if now - self._regime_last_log_ts >= interval:
                    print(
                        f"PIPE_REGIME_BLOCK regime={regime_decision.regime} "
                        f"reason={regime_decision.reason} "
                        f"atr={regime_decision.atr} "
                        f"slope={regime_decision.slope}",
                        flush=True,
                    )
                    self._regime_last_log_ts = now
                self.pg_logger.log_risk_event(
                    symbol=sym,
                    event="regime_block",
                    decision=regime_decision.reason,
                    payload={
                        "regime": regime_decision.regime,
                        "atr": regime_decision.atr,
                        "slope": regime_decision.slope,
                    },
                )
                return

            now = time.time()
            interval = float(os.getenv("REGIME_LOG_EVERY_SEC", "30"))

            if now - self._regime_last_log_ts >= interval:
                print(
                    f"PIPE_REGIME_OK regime={regime_decision.regime} "
                    f"atr={regime_decision.atr} "
                    f"slope={regime_decision.slope}",
                    flush=True,
                )
                self._regime_last_log_ts = now

        # strategy -> SignalRouter -> normalized intent
        raw_intent = self.strategy.on_quote(st)
        routed_signal = self.signal_router.route(raw_intent)

        if not routed_signal.allowed:
            reason = str(routed_signal.reason).strip().lower() if routed_signal.reason is not None else "unknown"

            # Русский коммент: полностью подавляем duplicate_signal (никаких логов и print)
            if reason in ("duplicate_signal", "no_signal"):
                return

            print(
                f"PIPE_SIGNAL_REJECT reason={reason} symbol={sym}",
                flush=True,
            )

            self.pg_logger.log_signal(
                symbol=sym,
                strategy=getattr(self.strategy, "__class__", type(self.strategy)).__name__,
                side=None,
                qty=None,
                status="signal_rejected",
                payload={"reason": reason},
            )
            return

        intent = routed_signal.intent.to_dict()

        # Русский коммент: защита от добора позиции до появления отдельной логики scaling/pyramiding.
        current_pos = self.pm.positions.get(intent.get("symbol"))
        current_qty = float(getattr(current_pos, "qty", 0.0) or 0.0) if current_pos is not None else 0.0
        if current_qty != 0.0:
            print(
                f"PIPE_POSITION_BLOCK symbol={intent.get('symbol')} qty={current_qty} reason=position_already_open",
                flush=True,
            )
            self.pg_logger.log_signal(
                symbol=intent.get("symbol"),
                strategy=intent.get("source"),
                side=intent.get("side"),
                qty=intent.get("qty"),
                status="position_blocked",
                payload={"reason": "position_already_open", "current_qty": current_qty, "intent": intent},
            )
            return

        print(
             
            f"side={intent.get('side')} qty={intent.get('qty')} confidence={intent.get('confidence')}",
            flush=True,
        )
        # === Risk v3: volatility-aware sizing ===
        if os.getenv("VOL_RISK_ENABLE", "0") == "1":
            features = st.get("features") or {}
            atr = (
                st.get("range_atr")
                or st.get("atr")
                or features.get("range_atr")
                or features.get("atr")
            )

            confidence = max(0.0, min(1.0, _safe_float(intent.get("confidence"), default=1.0)))
            vol_params = self.vol_risk.compute(atr=atr, confidence=confidence)

            # Русский коммент: confidence теперь влияет на риск-бюджет внутри VolatilityRiskEngine.
            intent["qty"] = vol_params.qty
            intent["confidence_qty_factor"] = confidence

            print(
                f"PIPE_CONFIDENCE_SIZING confidence={confidence} "
                f"final_qty={vol_params.qty} risk_amount={vol_params.risk_amount}",
                flush=True,
            )

            print(
                f"PIPE_SCORE_DIAG source={intent.get('source')} "
                f"score={intent.get('score')} "
                f"confidence={confidence} "
                f"risk_amount={vol_params.risk_amount} "
                f"qty={vol_params.qty}",
                flush=True,
            )

            # Русский коммент: Risk v3 динамически настраивает SL/TP для Risk v2 exit-layer.
            self.exit_engine.stop_loss_abs = vol_params.stop_abs
            self.exit_engine.take_profit_abs = vol_params.take_abs

            print(
                f"PIPE_VOL_RISK atr={vol_params.atr} "
                f"stop_abs={vol_params.stop_abs} "
                f"take_abs={vol_params.take_abs} "
                f"qty={vol_params.qty} "
                f"risk_amount={vol_params.risk_amount}",
                flush=True,
            )

        LOG.info("PIPE intent=%s", intent)
        self.pg_logger.log_signal(
            symbol=intent.get("symbol"),
            strategy=getattr(self.strategy, "__class__", type(self.strategy)).__name__,
            side=intent.get("side"),
            qty=intent.get("qty"),
            status="generated",
            payload={"intent": intent},
        )

        # Русский коммент: Strategy FilterEngine стоит между Strategy и Risk.
        if self.filter_engine is not None:
            if callable(self.filter_context_builder):
                filter_context = self.filter_context_builder(intent, st, self.portfolio)
            elif FilterContext is not None:
                filter_context = FilterContext(
                    range_atr=feat.get("range_atr") if isinstance(feat, dict) else None,
                    ema=feat.get("ema") if isinstance(feat, dict) else None,
                )
            else:
                filter_context = None

            if filter_context is not None and hasattr(self.filter_engine, "allow"):
                filter_i = int(feat.get("i", 0)) if isinstance(feat, dict) else 0
                filter_decision = self.filter_engine.allow(filter_i, filter_context)
                LOG.info("FILTER decision=%s", filter_decision)
                if not getattr(filter_decision, "allowed", False):
                    LOG.warning(
                        "FILTER REJECT reason=%s details=%s",
                        getattr(filter_decision, "reason", None),
                        getattr(filter_decision, "details", None),
                    )
                    self.pg_logger.log_signal(
                        symbol=intent.get("symbol"),
                        strategy=getattr(self.strategy, "__class__", type(self.strategy)).__name__,
                        side=intent.get("side"),
                        qty=intent.get("qty"),
                        status="filter_rejected",
                        payload={
                            "intent": intent,
                            "reason": getattr(filter_decision, "reason", None),
                            "details": getattr(filter_decision, "details", None),
                        },
                    )
                    self.pg_logger.log_risk_event(
                        symbol=intent.get("symbol"),
                        event="filter_reject",
                        decision=str(getattr(filter_decision, "reason", None)),
                        payload={"details": getattr(filter_decision, "details", None), "intent": intent},
                    )
                    return

        # risk
        if os.getenv("RISK_SOFT") == "1":
            LOG.info("RISK SOFT: bypass")
            approved = True
            decision = None
        else:
            ctx = build_risk_context(intent, self.portfolio, st)
            if hasattr(self.risk, "stack") and hasattr(self.risk.stack, "evaluate"):
                decision = self.risk.stack.evaluate(ctx)
            else:
                decision = self.risk.evaluate(ctx)
            LOG.info("RISK decision=%s", decision)
            approved = _decision_allowed(decision)

        if not approved:
            if decision is not None:
                for attr in ("reasons", "reason", "message", "messages", "violations", "rule", "rule_name", "code"):
                    if hasattr(decision, attr):
                        LOG.warning("RISK detail %s=%s", attr, getattr(decision, attr))
                        print(f"PIPE_RISK_DETAIL {attr}={getattr(decision, attr)}", flush=True)
            LOG.warning("RISK REJECT")
            print("PIPE_RISK_REJECT", flush=True)
            try:
                # Русский коммент: Telegram alert по risk reject не должен ломать pipeline.
                risk_reason = getattr(decision, "reason", None) or "unknown"
                self.notifier.send(
                    "⛔ RISK REJECT\n"
                    f"symbol={intent.get('symbol')}\n"
                    f"side={intent.get('side')} qty={intent.get('qty')}\n"
                    f"reason={risk_reason}"
                )
            except Exception as e:
                LOG.warning("TELEGRAM RISK ALERT FAILED: %s", e)
            return

        # === Kill Switch Layer ===
        if os.getenv("KILL_SWITCH_ENABLE", "0") == "1":
            pm_ctx = self.pm.get_context()
            equity = _safe_float(getattr(pm_ctx, "portfolio_value", 0.0), default=0.0)
            start_equity = _safe_float(getattr(pm_ctx, "starting_capital", equity), default=equity)
            daily_pnl = _safe_float(getattr(pm_ctx, "daily_realized_pnl", 0.0), default=0.0)

            kill_decision = self.kill_switch.evaluate(
                daily_realized_pnl=daily_pnl,
                equity=equity,
                start_equity=start_equity,
            )

            if not kill_decision.allowed:
                print(
                    f"PIPE_KILL_SWITCH reason={kill_decision.reason} "
                    f"daily_pnl={kill_decision.daily_realized_pnl} "
                    f"drawdown={kill_decision.drawdown} "
                    f"equity={kill_decision.equity} "
                    f"start_equity={kill_decision.start_equity}",
                    flush=True,
                )
                self.risk_recorder.emit(UnifiedRiskDecision.reject(
                    layer="kill_switch",
                    reason=kill_decision.reason,
                    symbol=intent.get("symbol"),
                    side=intent.get("side"),
                    qty=intent.get("qty"),
                    payload={
                        "daily_realized_pnl": kill_decision.daily_realized_pnl,
                        "drawdown": kill_decision.drawdown,
                        "equity": kill_decision.equity,
                        "start_equity": kill_decision.start_equity,
                    },
                ))
                self.pg_logger.log_risk_event(
                    symbol=intent.get("symbol"),
                    event="kill_switch_reject",
                    decision=kill_decision.reason,
                    payload={
                        "daily_realized_pnl": kill_decision.daily_realized_pnl,
                        "drawdown": kill_decision.drawdown,
                        "equity": kill_decision.equity,
                        "start_equity": kill_decision.start_equity,
                        "intent": intent,
                    },
                )
                return

            print(
                f"PIPE_KILL_OK daily_pnl={kill_decision.daily_realized_pnl} "
                f"drawdown={kill_decision.drawdown}",
                flush=True,
            )
            self.risk_recorder.emit(UnifiedRiskDecision.allow(
                layer="kill_switch_ok",
                symbol=intent.get("symbol"),
                side=intent.get("side"),
                qty=intent.get("qty"),
                payload={
                    "daily_realized_pnl": kill_decision.daily_realized_pnl,
                    "drawdown": kill_decision.drawdown,
                },
            ))

        # === Portfolio Heat Layer ===
        if os.getenv("PORTFOLIO_HEAT_ENABLE", "0") == "1":
            pm_ctx = self.pm.get_context()
            px = _get_price_from_state(st, intent.get("side")) or 0.0
            qty = _safe_float(intent.get("qty"), default=0.0)
            trade_value = abs(qty * px)

            heat_decision = self.portfolio_heat.evaluate(
                portfolio_value=_safe_float(getattr(pm_ctx, "portfolio_value", 0.0), default=0.0),
                current_exposure=_safe_float(getattr(pm_ctx, "total_exposure", 0.0), default=0.0),
                new_trade_value=trade_value,
            )

            if not heat_decision.allowed:
                print(
                    f"PIPE_HEAT_REJECT reason={heat_decision.reason} "
                    f"current_heat={heat_decision.current_heat} "
                    f"projected_heat={heat_decision.projected_heat} "
                    f"limit={heat_decision.limit}",
                    flush=True,
                )
                self.risk_recorder.emit(UnifiedRiskDecision.reject(
                    layer="portfolio_heat",
                    reason=heat_decision.reason,
                    symbol=intent.get("symbol"),
                    side=intent.get("side"),
                    qty=intent.get("qty"),
                    payload={
                        "current_heat": heat_decision.current_heat,
                        "projected_heat": heat_decision.projected_heat,
                        "limit": heat_decision.limit,
                    },
                ))
                self.pg_logger.log_risk_event(
                    symbol=intent.get("symbol"),
                    event="portfolio_heat_reject",
                    decision=heat_decision.reason,
                    payload={
                        "current_heat": heat_decision.current_heat,
                        "projected_heat": heat_decision.projected_heat,
                        "limit": heat_decision.limit,
                        "intent": intent,
                    },
                )
                return

            print(
                f"PIPE_HEAT_OK current_heat={heat_decision.current_heat} "
                f"projected_heat={heat_decision.projected_heat} "
                f"limit={heat_decision.limit}",
                flush=True,
            )

        # === Correlation / Bucket Exposure Layer ===
        if os.getenv("CORR_RISK_ENABLE", "0") == "1":
            pm_ctx = self.pm.get_context()
            px = _get_price_from_state(st, intent.get("side")) or 0.0
            qty = _safe_float(intent.get("qty"), default=0.0)
            trade_value = abs(qty * px)
            target_bucket = self.correlation_risk.bucket_for_symbol(intent.get("symbol"))

            current_bucket_exposure = 0.0
            for pos_symbol, pos in getattr(self.pm, "positions", {}).items():
                if self.correlation_risk.bucket_for_symbol(pos_symbol) != target_bucket:
                    continue
                pos_qty = abs(_safe_float(getattr(pos, "qty", 0.0), default=0.0))
                pos_price = _safe_float(getattr(pos, "avg_price", 0.0), default=0.0)
                current_bucket_exposure += pos_qty * pos_price

            corr_decision = self.correlation_risk.evaluate(
                symbol=intent.get("symbol"),
                portfolio_value=_safe_float(getattr(pm_ctx, "portfolio_value", 0.0), default=0.0),
                current_bucket_exposure=current_bucket_exposure,
                new_trade_value=trade_value,
            )

            if not corr_decision.allowed:
                print(
                    f"PIPE_CORR_REJECT reason={corr_decision.reason} "
                    f"bucket={corr_decision.bucket} "
                    f"current_bucket_exposure={corr_decision.current_bucket_exposure} "
                    f"projected_bucket_exposure={corr_decision.projected_bucket_exposure} "
                    f"limit={corr_decision.bucket_limit}",
                    flush=True,
                )
                self.risk_recorder.emit(UnifiedRiskDecision.reject(
                    layer="correlation_risk",
                    reason=corr_decision.reason,
                    symbol=intent.get("symbol"),
                    side=intent.get("side"),
                    qty=intent.get("qty"),
                    payload={
                        "bucket": corr_decision.bucket,
                        "current_bucket_exposure": corr_decision.current_bucket_exposure,
                        "projected_bucket_exposure": corr_decision.projected_bucket_exposure,
                        "limit": corr_decision.bucket_limit,
                    },
                ))
                return

            print(
                f"PIPE_CORR_OK bucket={corr_decision.bucket} "
                f"current_bucket_exposure={corr_decision.current_bucket_exposure} "
                f"projected_bucket_exposure={corr_decision.projected_bucket_exposure} "
                f"limit={corr_decision.bucket_limit}",
                flush=True,
            )
            self.risk_recorder.emit(UnifiedRiskDecision.allow(
                layer="correlation_risk_ok",
                symbol=intent.get("symbol"),
                side=intent.get("side"),
                qty=intent.get("qty"),
                payload={
                    "bucket": corr_decision.bucket,
                    "current_bucket_exposure": corr_decision.current_bucket_exposure,
                    "projected_bucket_exposure": corr_decision.projected_bucket_exposure,
                    "limit": corr_decision.bucket_limit,
                },
            ))
            self.risk_recorder.emit(UnifiedRiskDecision.allow(
                layer="portfolio_heat_ok",
                symbol=intent.get("symbol"),
                side=intent.get("side"),
                qty=intent.get("qty"),
                payload={
                    "current_heat": heat_decision.current_heat,
                    "projected_heat": heat_decision.projected_heat,
                    "limit": heat_decision.limit,
                },
            ))

        LOG.info("RISK OK")
        print("PIPE_RISK_OK", flush=True)
        self.pg_logger.log_signal(
            symbol=intent.get("symbol"),
            strategy=getattr(self.strategy, "__class__", type(self.strategy)).__name__,
            side=intent.get("side"),
            qty=intent.get("qty"),
            status="risk_approved",
            payload={"intent": intent, "decision": str(decision) if "decision" in locals() else None},
        )
        self.pg_logger.log_risk_event(
            symbol=intent.get("symbol"),
            event="risk_approved",
            decision="approved",
            payload={"intent": intent, "decision": str(decision) if "decision" in locals() else None},
        )

        # Русский коммент: позиционный guard — не наращиваем long по тому же символу.
        try:
            pos = self.pm.positions.get(intent.get("symbol"))
            current_qty = float(getattr(pos, "qty", 0.0) or 0.0) if pos is not None else 0.0
        except Exception:
            current_qty = 0.0

        side = str(intent.get("side", "BUY")).upper()
        if side == "BUY" and current_qty > 0:
            LOG.info("POSITION GUARD: skip BUY, existing qty=%s symbol=%s", current_qty, intent.get("symbol"))
            return

        # paper execute
        LOG.info("PIPE PAPER EXECUTE")
        fill = self.paper.execute(intent, st)

        if hasattr(self.strategy, "mark_submitted"):
            self.strategy.mark_submitted()

        side = str(intent.get("side", "BUY")).upper()
        qty = abs(_safe_float(getattr(fill, "qty", 0.0), default=0.0) or 0.0)

        fill_price = float(getattr(fill, "price", 0.0) or 0.0)
        trade_value = abs(qty) * fill_price
        fee_result = self.fee_tax.trade_fees(trade_value)
        total_commission = (
            float(getattr(fill, "commission", 0.0) or 0.0)
            + fee_result.broker_fee
            + fee_result.exchange_fee
        )

        # Русский коммент: налоговый резерв считаем только при SELL и только с положительной прибыли.
        if side == "SELL":
            try:
                pos = self.pm.positions.get(intent.get("symbol"))
                avg_price = float(getattr(pos, "avg_price", 0.0) or 0.0) if pos is not None else 0.0
                realized_profit = max((fill_price - avg_price) * qty, 0.0)
                tax_result = self.fee_tax.tax_on_realized_profit(realized_profit)
                total_commission += tax_result.tax_reserve
            except Exception:
                pass

        exec_fill = ExecutionFill(
            fill_id=getattr(fill, "fill_id", None),
            symbol=getattr(fill, "symbol", None) or intent.get("symbol"),
            side=side,
            qty=qty,  # Русский коммент: qty положительный, направление в side
            price=fill_price,
            commission=total_commission,
            origin="paper",
        )

        LOG.info("PIPE fill=%s -> ExecutionFill(side=%s, qty=%s, fill_id=%s)",
                 fill, exec_fill.side, exec_fill.qty, exec_fill.fill_id)

        # Русский коммент: Вариант B — публикуем FILL, а применять будем в _on_fill().
        fill_event = {"type": "FILL", "fill": exec_fill, "origin": "paper"}
        self.bus.publish(fill_event)

    def _on_fill(self, event: dict):
        """
        Русский коммент: единая точка применения исполнений.
        Идемпотентность по fill_id держит PositionManager (если включена).
        """
        fill = event.get("fill") if isinstance(event, dict) else event
        if fill is None:
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
