from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class PositionLifecycleInput:
    symbol: str
    qty: float
    price: float
    avg_price: float
    strategy: str = "default"


class PositionLifecycleService:
    """
    Русский комментарий:
    Единая точка входа для lifecycle сопровождения позиции.

    Этап 1:
    TakeProfitEngine перенесён внутрь сервиса.
    Остальные блоки пока вызываются через pipeline как fallback.
    """

    def __init__(self, pipeline) -> None:
        self.pipeline = pipeline

    def _evaluate_take_profit_engine(
        self,
        *,
        symbol: str,
        qty: float,
        price: float,
        avg_price: float | None = None,
        stop_price: float | None = None,
    ) -> None:
        """Русский комментарий: dry-run take-profit расчёт без отправки заявок брокеру."""
        if os.getenv("ENABLE_TAKE_PROFIT_ENGINE", "0") != "1":
            return

        p = self.pipeline

        try:
            if qty <= 0 or price <= 0:
                return

            entry_price = float(avg_price or price)
            base_stop = float(
                stop_price
                or (
                    entry_price
                    * (1.0 - float(os.getenv("TAKE_PROFIT_DEFAULT_STOP_PCT", "0.01")))
                )
            )

            decision = p.take_profit_engine.evaluate_long(
                qty=float(qty),
                entry_price=entry_price,
                current_price=float(price),
                stop_price=base_stop,
            )

            lifecycle_state = p._load_position_lifecycle_state_for_symbol(symbol) or {}
            last_action_key = (
                f"{decision.action}:{decision.reason}:"
                f"{round(float(decision.take_price or 0.0), 8)}"
            )
            raw_state = lifecycle_state.get("raw") or {}
            if (
                decision.action != "HOLD"
                and raw_state.get("source") == f"take_profit_engine:{last_action_key}"
            ):
                return

            # Материализуем рассчитанные уровни сразу. Раньше открытая Paper-
            # позиция выглядела как позиция без STOP/TAKE до первого срабатывания.
            p._save_position_lifecycle_state(
                symbol=symbol,
                entry_price=entry_price,
                initial_qty=qty,
                remaining_qty=qty,
                current_stop=base_stop,
                current_take_profit=decision.take_price,
                source="take_profit_levels",
            )

            if decision.action == "HOLD":
                return

            # Это наблюдатель, а фактический Paper-fill создаёт единый exit engine.
            # Не обнуляем позицию и не пишем одинаковое решение на каждом тике.
            p._log_dedup(
                f"PIPE_TAKE_PROFIT_DECISION:{symbol}:{decision.action}:{decision.reason}",
                f"PIPE_TAKE_PROFIT_DECISION symbol={symbol} action={decision.action} "
                f"qty={qty} qty_to_close={decision.qty_to_close} "
                f"price={price} entry={entry_price} base_stop={base_stop} "
                f"take_price={decision.take_price} reason={decision.reason} dry_run=1",
                heartbeat_sec=300,
            )

            p.take_profit_event_repository.log_event(
                symbol=symbol,
                action=decision.action,
                qty=qty,
                qty_to_close=decision.qty_to_close,
                price=price,
                entry_price=entry_price,
                base_stop=base_stop,
                take_price=decision.take_price,
                reason=decision.reason,
                dry_run=True,
                raw={"source": "position_lifecycle_service", "engine": "TakeProfitEngine"},
            )

            p._save_position_lifecycle_state(
                symbol=symbol,
                entry_price=entry_price,
                initial_qty=qty,
                remaining_qty=qty,
                current_stop=base_stop,
                current_take_profit=decision.take_price,
                source=f"take_profit_engine:{last_action_key}",
            )

        except Exception as exc:
            print(f"PIPE_TAKE_PROFIT_ERROR symbol={symbol} error={exc}", flush=True)
    def _evaluate_trailing_order_manager(self, symbol: str, qty: float, price: float) -> None:
        """Русский комментарий: trailing stop lifecycle перенесён из PaperTradingPipeline."""
        p = self.pipeline
        if os.getenv("ENABLE_TRAILING_ORDER_MANAGER", "0") != "1":
            return

        if os.getenv("ENABLE_POSITION_INTENT_GATE", "0") == "1":
            policy = self.position_intent_repo.get(symbol)
            if not policy.enabled or not policy.allow_trailing:
                state = self._exit_state_for_symbol(symbol)
                now_ts = time.time()
                last_ts = float(state.get("last_trailing_intent_block_log_ts", 0.0) or 0.0)
                if now_ts - last_ts >= float(os.getenv("POSITION_INTENT_TRAILING_BLOCK_LOG_INTERVAL_SEC", "300")):
                    state["last_trailing_intent_block_log_ts"] = now_ts
                    print(
                        f"PIPE_POSITION_INTENT_TRAILING_BLOCK symbol={symbol} "
                        f"horizon={policy.horizon} enabled={policy.enabled} allow_trailing={policy.allow_trailing}",
                        flush=True,
                    )
                return

        dry_run = os.getenv("TRAILING_ORDER_DRY_RUN", "1") == "1"
        if not dry_run:
            # Русский комментарий:
            # Реальный режим: trailing decision может быть отправлен брокеру только через
            # RealProtectiveLifecycleEngine, который имеет собственные hard-gates.
            pass

        qty = float(qty or 0.0)
        price = float(price)

        if qty <= 0:
            p._trailing_order_stop_by_symbol.pop(symbol, None)
            return

        lifecycle_state = p._load_position_lifecycle_state_for_symbol(symbol) or {}
        current_stop = p._trailing_order_stop_by_symbol.get(symbol)

        if current_stop is None and lifecycle_state.get("current_stop") is not None:
            current_stop = float(lifecycle_state["current_stop"])

        decision = p.trailing_order_manager.evaluate_long(
            symbol=symbol,
            qty=qty,
            last_price=price,
            current_stop=current_stop,
        )

        min_replace_step = max(0.0, float(os.getenv("TRAILING_ORDER_MIN_REPLACE_STEP", "0.10")))
        if (
            decision.action in ("PLACE_STOP", "REPLACE_STOP")
            and current_stop is not None
            and float(decision.stop_price or 0.0) < float(current_stop) + min_replace_step
        ):
            return

        if decision.action in ("PLACE_STOP", "REPLACE_STOP"):
            p._trailing_order_stop_by_symbol[symbol] = decision.stop_price

        if decision.action != "HOLD":
            print(
                f"PIPE_TRAILING_ORDER_DECISION action={decision.action} "
                f"symbol={decision.symbol} side={decision.side} qty={decision.qty} "
                f"stop={decision.stop_price} reason={decision.reason} dry_run=1",
                flush=True,
            )

            p.trailing_order_event_repository.log_event(
                symbol=decision.symbol,
                action=decision.action,
                side=decision.side,
                qty=decision.qty,
                stop_price=decision.stop_price,
                reason=decision.reason,
                dry_run=True,
                raw={
                    "source": "paper_pipeline",
                    "manager": "TrailingOrderManager",
                },
            )

            p._save_position_lifecycle_state(
                symbol=decision.symbol,
                remaining_qty=decision.qty,
                trailing_active=True,
                current_stop=decision.stop_price,
                source="trailing_order_manager",
            )

            if not dry_run:
                result = p.real_protective_lifecycle.place_or_replace_stop(
                    symbol=decision.symbol,
                    side=decision.side,
                    qty=decision.qty,
                    stop_price=decision.stop_price,
                    entry_order_id=None,
                    old_order_id=None,
                    reason=decision.reason,
                )
                print(
                    f"PIPE_REAL_PROTECTIVE_LIFECYCLE_RESULT symbol={decision.symbol} "
                    f"action={result.action} executed={int(result.executed)} "
                    f"status={result.status} order_id={result.order_id} reason={result.reason}",
                    flush=True,
                )
            else:
                exit_state = p._exit_state_for_symbol(decision.symbol)
                exit_state["stop_price"] = decision.stop_price
                print(
                    f"PIPE_PAPER_TRAILING_STOP_APPLIED symbol={decision.symbol} "
                    f"stop={decision.stop_price} reason={decision.reason}",
                    flush=True,
                )


    def _evaluate_partial_close_engine(self, **kwargs) -> None:
        """Русский комментарий: fallback на pipeline до полного переноса partial-close."""
        return self.pipeline._evaluate_partial_close_engine(**kwargs)

    def _evaluate_profit_lock_engine(self, **kwargs) -> None:
        """Русский комментарий: fallback на pipeline до полного переноса profit-lock."""
        return self.pipeline._evaluate_profit_lock_engine(**kwargs)

    def on_position_quote(self, data: PositionLifecycleInput) -> None:
        p = self.pipeline

        self._evaluate_take_profit_engine(
            symbol=data.symbol,
            qty=abs(float(data.qty)),
            price=float(data.price),
            avg_price=float(data.avg_price),
            stop_price=None,
        )

        # Русский комментарий: partial close уже перенесён в сервис.
        self._evaluate_partial_close_engine(
            symbol=data.symbol,
            qty=abs(float(data.qty)),
            price=float(data.price),
            avg_price=float(data.avg_price),
            stop_price=None,
        )

        # Русский комментарий: profit-lock уже перенесён в сервис.
        self._evaluate_profit_lock_engine(
            symbol=data.symbol,
            qty=abs(float(data.qty)),
            price=float(data.price),
            avg_price=float(data.avg_price),
            stop_price=None,
        )

        # Русский комментарий: trailing lifecycle теперь вызывается через сервис.
        self._evaluate_trailing_order_manager(
            data.symbol,
            abs(float(data.qty)),
            float(data.price),
        )
