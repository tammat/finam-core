
from __future__ import annotations

import time
from datetime import datetime, timezone
import inspect
from dataclasses import asdict
from typing import Any, Dict, Optional

from finam_core.execution.paper_engine import PaperExecutionEngine, PaperFill


def _build_fill_event(pf: "PaperFill", *, side: str, account_id: str | None = None) -> Any:
    """Convert PaperFill -> core FillEvent without hard-coding FillEvent signature."""
    try:
        # ВАЖНО: локальный импорт, чтобы класс совпадал с тем, что импортирован в тесте
        from finam_core.core.events.fill_event import FillEvent as FillEventCls  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError(f"FillEvent import failed: {e}")

    now_dt = datetime.now(timezone.utc)
    now_ts = time.time()

    # Candidate fields (FillEvent implementations differ across versions).
    candidates: Dict[str, Any] = {
        # common identifiers
        "fill_id": getattr(pf, "fill_id", None),
        "id": getattr(pf, "fill_id", None),
        "event_id": getattr(pf, "fill_id", None),

        # trade fields
        "symbol": getattr(pf, "symbol", None),
        "instrument": getattr(pf, "symbol", None),
        "side": str(side).upper(),
        "qty": float(getattr(pf, "qty", 0.0)),
        "quantity": float(getattr(pf, "qty", 0.0)),
        "price": float(getattr(pf, "price", 0.0)),
        "commission": float(getattr(pf, "commission", 0.0)),

        # optional context
        "account_id": account_id,
        "account": account_id,

        # timestamps (разные версии могут ожидать разные поля/типы)
        "timestamp": now_dt,
        "created_at": now_dt,
        "ts": now_ts,
    }

    # Filter by FillEvent __init__ parameters
    sig = inspect.signature(FillEventCls.__init__)
    kwargs: Dict[str, Any] = {}
    for name in sig.parameters.keys():
        if name == "self":
            continue
        if name in candidates and candidates[name] is not None:
            kwargs[name] = candidates[name]

    try:
        return FillEventCls(**kwargs)
    except TypeError:
        # Fallback: минимальный набор (часто достаточно)
        minimal: Dict[str, Any] = {}
        for k in ("symbol", "side", "qty", "price", "commission", "fill_id", "timestamp", "account_id"):
            if k in kwargs:
                minimal[k] = kwargs[k]
            elif k in candidates and candidates[k] is not None:
                minimal[k] = candidates[k]
        return FillEventCls(**minimal)


class ExecutionEngine(PaperExecutionEngine):
    """ExecutionEngine wrapper used by sim-pipeline tests.

    Contract:
      - execute_signal(account_id=..., signal=..., market_state=...) -> FillEvent
    """

    def __init__(self, broker=None, **kwargs):
        # PaperExecutionEngine takes slippage_coef/commission; tolerate extra kwargs for tests.
        slippage_coef = kwargs.pop("slippage_coef", 0.0)
        commission = kwargs.pop("commission", 0.0)
        super().__init__(slippage_coef=slippage_coef, commission=commission)
        self.broker = broker

    def execute_signal(
        self,
        *,
        account_id: str,
        signal: Dict[str, Any],
        market_state: Optional[Dict[str, Any]] = None,
        **_: Any,
    ):
        side = str(signal.get("side", "BUY")).upper()
        qty = float(signal.get("qty", signal.get("quantity", 0)) or 0.0)
        symbol = signal.get("symbol") or signal.get("ticker") or signal.get("instrument") or ""

        # If a broker adapter is provided and has an execution method, prefer it (sim broker).
        if self.broker is not None:
            for m in ("execute_signal", "place", "submit", "send_order"):
                if hasattr(self.broker, m):
                    fn = getattr(self.broker, m)
                    try:
                        fill_like = fn(account_id=account_id, signal=signal, market_state=market_state)
                    except TypeError:
                        fill_like = fn(signal=signal, market_state=market_state, account_id=account_id)

                    # If broker already returns FillEvent, pass through.
                    try:
               #         from finam_core.core.events.fill_event import FillEvent  # type: ignore
                        if isinstance(fill_like, FillEvent):
                            return fill_like
                    except Exception:
                        pass

                    # If broker returns PaperFill-compatible object, normalize.
                    if isinstance(fill_like, PaperFill):
                        pf = fill_like
                    else:
                        # best-effort mapping
                        pf = PaperFill(
                            symbol=getattr(fill_like, "symbol", symbol),
                            qty=float(getattr(fill_like, "qty", qty) or 0.0),
                            price=float(getattr(fill_like, "price", 0.0) or 0.0),
                            commission=float(getattr(fill_like, "commission", 0.0) or 0.0),
                            fill_id=getattr(fill_like, "fill_id", None) or f"paper_{symbol}_{int(time.time()*1000)}",
                        )
                    return _build_fill_event(pf, side=side, account_id=account_id)

        # Fallback: paper execution (requires market_state for price; PaperEngine now tolerates missing).
        pf = self.execute({"symbol": symbol, "side": side, "qty": qty}, market_state or {})
        return _build_fill_event(pf, side=side, account_id=account_id)

# Backward-compatible alias for legacy imports
try:
    BaseExecutionEngine
except NameError:
    BaseExecutionEngine = ExecutionEngine
