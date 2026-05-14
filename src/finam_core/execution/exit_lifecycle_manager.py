from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExitLifecycleInput:
    symbol: str
    price: float
    atr: float | None = None


class ExitLifecycleManager:
    """
    Русский комментарий:
    Единая точка входа для exit lifecycle.

    Этап 1:
    manager является тонкой обёрткой над текущим методом PaperTradingPipeline.
    Поведение не меняем, только убираем прямой вызов из quote path.
    """

    def __init__(self, pipeline) -> None:
        self.pipeline = pipeline

    def build_exit_intent_if_any(self, symbol: str, price: float, atr: float | None = None) -> dict | None:
        p = self.pipeline
        """Русский комментарий: строит raw_intent для закрытия позиции через общий execution path."""
        p._sync_broker_positions_readonly()
        p._sync_broker_open_orders_if_needed()

        state = p._exit_state_for_symbol(symbol)

        qty = p._position_qty_for_symbol(symbol)
        broker_qty = float(getattr(self, "_broker_position_qty_by_symbol", {}).get(symbol, 0.0) or 0.0)

        # Русский комментарий: broker snapshot не должен автоматически превращаться в paper-позицию.
        if os.getenv("ENABLE_BROKER_POSITION_APPLY_TO_PM", "0") == "1" and abs(broker_qty) > 1e-9:
            prev_broker_qty = float(
                state.get("last_broker_qty_logged", 0.0) or 0.0
            )

            qty = broker_qty

            if abs(prev_broker_qty - broker_qty) > 1e-9:
                print(
                    f"PIPE_BROKER_POSITION_APPLIED symbol={symbol}",
                    flush=True,
                )
                state["last_broker_qty_logged"] = broker_qty

        p._log_position_order_state_if_changed(symbol, qty)
        p._reconcile_position_lifecycle_state(
            symbol=symbol,
            actual_qty=float(qty or 0.0),
            strategy="default",
        )
        p._self_heal_position_lifecycle_state(
            symbol=symbol,
            actual_qty=float(qty or 0.0),
            strategy="default",
        )

        now_ts = time.time()
        has_position = abs(float(qty or 0.0)) > 1e-9
        qty_key = "last_nonzero_qty_log_ts" if has_position else "last_zero_qty_log_ts"
        interval_key = "EXIT_NONZERO_QTY_LOG_INTERVAL_SEC" if has_position else "EXIT_ZERO_QTY_LOG_INTERVAL_SEC"
        default_interval = "15" if has_position else "60"

        last_log_ts = float(state.get(qty_key, 0.0) or 0.0)
        should_log_exit_check = now_ts - last_log_ts >= float(os.getenv(interval_key, default_interval))

        if should_log_exit_check and (
            abs(float(qty or 0.0)) > 1e-9 or os.getenv("EXIT_ENGINE_DEBUG", "0") == "1"
        ):
            state[qty_key] = now_ts
            print(
                f"PIPE_EXIT_ENGINE_CHECK symbol={symbol} qty={qty} "
                f"price={round(float(price), 6)} atr_in={atr}",
                flush=True,
            )

        if qty == 0:
            state["bars_held"] = 0
            state["prev_close"] = float(price)
            state["stop_price"] = None
            state["last_qty"] = 0.0
            try:
                p.exit_state_machine.on_position(symbol, 0.0)
            except Exception:
                pass
            return None

        exit_allowed, exit_reason = p._position_intent_allows_exit_engine(symbol)
        if not exit_allowed:
            now_ts = time.time()
            last_intent_block_ts = float(state.get("last_intent_block_log_ts", 0.0) or 0.0)
            if now_ts - last_intent_block_ts >= float(os.getenv("POSITION_INTENT_BLOCK_LOG_INTERVAL_SEC", "300")):
                state["last_intent_block_log_ts"] = now_ts
                print(
                    f"PIPE_POSITION_INTENT_EXIT_BLOCK symbol={symbol} qty={qty} reason={exit_reason}",
                    flush=True,
                )
            return None

        avg_price = p._position_avg_price_for_symbol(symbol)
        if avg_price is None:
            now_ts = time.time()
            last_no_avg_ts = float(state.get("last_no_avg_log_ts", 0.0) or 0.0)

            if now_ts - last_no_avg_ts >= float(os.getenv("EXIT_NO_AVG_LOG_INTERVAL_SEC", "300")):
                state["last_no_avg_log_ts"] = now_ts
                print(
                    f"PIPE_EXIT_ENGINE_NO_AVG symbol={symbol} qty={qty} "
                    f"price={round(float(price), 6)}",
                    flush=True,
                )

            return None

        if float(state.get("last_qty") or 0.0) == 0.0:
            state["bars_held"] = 0
            state["stop_price"] = None

        state["bars_held"] = int(state.get("bars_held") or 0) + 1
        state["last_qty"] = float(qty)

        side = "BUY" if qty > 0 else "SELL"
        close_side = "SELL" if qty > 0 else "BUY"
        effective_atr = float(atr if atr is not None else 0.0)

        if effective_atr <= 0:
            effective_atr = p._exit_fallback_atr(symbol, price)
            log_key = f"ATR_FALLBACK:{symbol}"

            if p._runtime_log_allowed(log_key, ttl_seconds=300):
                print(
                    f"PIPE_EXIT_ENGINE_ATR_FALLBACK symbol={symbol} "
                    f"atr={round(effective_atr, 6)} price={round(float(price), 6)}",
                    flush=True,
                )

        # Русский комментарий:
        # Lazy fallback: сервис мог не инициализироваться в __init__ после refactoring.
        if not hasattr(self, "position_lifecycle_service"):
            p.position_lifecycle_service = PositionLifecycleService(self)

        # Русский комментарий:
        # lifecycle сопровождения запускаем через отдельный сервис.
        p.position_lifecycle_service.on_position_quote(
            PositionLifecycleInput(
                symbol=symbol,
                qty=float(qty),
                price=float(price),
                avg_price=float(avg_price),
                strategy="default",
            )
        )

        decision = p._exit_engine_for_symbol(symbol).evaluate(
            side=side,
            entry_price=float(avg_price),
            current_price=float(price),
            atr=effective_atr,
            bars_held=int(state["bars_held"]),
            prev_close=state.get("prev_close"),
            current_stop=state.get("stop_price"),
        )

        state["prev_close"] = float(price)
        state["stop_price"] = decision.stop_price

        if not decision.should_exit:
            hold_key = f"EXIT_HOLD:{symbol}:{side}:{decision.reason}"

            if p._runtime_log_allowed(hold_key, ttl_seconds=300):
                print(
                    f"PIPE_EXIT_ENGINE_HOLD symbol={symbol} side={side} qty={abs(qty)} "
                    f"price={round(float(price), 6)} reason={decision.reason} stop={decision.stop_price}",
                    flush=True,
                )

            return None

        try:
            p.exit_state_machine.on_position(symbol, float(qty))
            allowed, sm_reason = p.exit_state_machine.allow_request(
                symbol=symbol,
                side=close_side,
                qty=abs(float(qty)),
                reason=str(decision.reason),
            )
            if not allowed:
                log_key = f"DUPLICATE_BLOCK:{symbol}:{decision.reason}"

                if p._runtime_log_allowed(log_key, ttl_seconds=120):
                    print(
                        f"PIPE_EXIT_ENGINE_DUPLICATE_BLOCK symbol={symbol} "
                        f"side={close_side} "
                        f"qty={abs(float(qty))} "
                        f"reason={decision.reason} "
                        f"sm_reason={sm_reason}",
                        flush=True,
                    )
                return None
        except Exception as exc:
            print(f"PIPE_EXIT_ENGINE_SM_ERROR symbol={symbol} error={exc}", flush=True)

        print(
            f"PIPE_EXIT_ENGINE_SIGNAL symbol={symbol} close_side={close_side} qty={abs(qty)} "
            f"price={round(float(price), 6)} reason={decision.reason}",
            flush=True,
        )

        return {
            "symbol": symbol,
            "side": close_side,
            "qty": abs(float(qty)),
            "price": float(price),
            "source": "exit_engine",
            "confidence": 1.0,
            "reason": decision.reason,
            "features": {
                "entry": float(avg_price),
                "exit_price": float(price),
                "atr": effective_atr,
                "bars_held": int(state["bars_held"]),
                "stop": decision.stop_price,
                "exit_engine": True,
            },
        }

