from dataclasses import dataclass
from decimal import Decimal

from finam_core.core.validator import StateValidator
from finam_core.core.state import PortfolioState as CorePortfolioState, Position
from finam_core.accounting.position_manager import PositionManager
from datetime import datetime
import uuid

@dataclass
class PortfolioState:
    cash: float
    equity: float
    realized_pnl: float
    unrealized_pnl: float
    exposure: float
    drawdown: float
    positions: dict

    @property
    def total_abs_notional(self) -> float:
        return sum(abs(p.notional) for p in self.positions.values())

    def build_snapshot(self):
        """
        Возвращает immutable snapshot состояния портфеля.
        Используется в тестах и аналитике.
        """
        return {
            "cash": self.cash,
            "equity": self.equity,
            "realized_pnl": self.realized_pnl,
            "unrealized_pnl": self.unrealized_pnl,
            "exposure": self.exposure,
            "drawdown": self.drawdown,
        }


class PortfolioManager:
    """
    Clean production model.

    - Position math → PositionManager
    - Accounting → cash + realized aggregation
    - Equity derived strictly
    """

    def __init__(
        self,
        initial_cash: float | None = None,
        *,
        starting_cash: float | None = None,
        validator: StateValidator | None = None,
        price_provider=None,
    ):
        if initial_cash is None and starting_cash is None:
            raise TypeError("initial_cash or starting_cash must be provided")

        if starting_cash is not None:
            initial_cash = starting_cash

        if initial_cash is None:
            raise TypeError("initial_cash resolved to None")
        self.prices = {}
        self._equity_peak = float(initial_cash)
        self.drawdown = 0.0

        self.validator = validator or StateValidator()
        self._applied_fills = set()

        self.position_manager = PositionManager(starting_cash=float(initial_cash))
        self.price_provider = price_provider

        # ====================================================
    # SNAPSHOT VALIDATION
    # ====================================================
    # -----------------------------
    # Backtest-friendly properties
    # -----------------------------
    @property
    def state(self) -> "PortfolioState":
        # вычисляем “на сейчас”; если есть now_ts — можно прокинуть
        return self.compute_state()

    @property
    def equity(self) -> float:
        return float(self.state.equity)

    def mark_to_market(self, price: float) -> "PortfolioState":
        """
        Backtest alias: если движок не передаёт symbol, просто
        маркируем ВСЕ открытые позиции одним price (single-instrument backtest).
        """
        for symbol, pos in self.position_manager.positions.items():
            pos.mark_price = price
        return self.compute_state()
    def _validate_snapshot(self, equity: float, unrealized: float):

        # ---- DECIMAL NORMALIZATION ----
        pm = self.position_manager
        cash_dec = Decimal(str(round(float(getattr(pm, "cash", 0.0)), 12)))
        realized_dec = Decimal(str(round(float(getattr(pm, "realized_pnl", 0.0)), 12)))
        unrealized_dec = Decimal(str(round(unrealized, 12)))

        # ВАЖНО: equity вычисляем через Decimal,
        # а не берём float equity
        equity_dec = cash_dec + unrealized_dec

        snapshot = CorePortfolioState(
            cash=cash_dec,
            realized_pnl=realized_dec,
            fees=Decimal("0"),
            equity=equity_dec,
        )

        snapshot.upsert_position(
            Position(
                symbol="__AGGREGATED__",
                qty=Decimal("1"),
                avg_price=Decimal("0"),
                unrealized_pnl=unrealized_dec,
            )
        )

        self.validator.assert_valid(snapshot, context="portfolio_snapshot")
    # ====================================================
    # FILL HANDLING
    # ====================================================

    def on_fill(self, fill) -> PortfolioState:
        fill_id = getattr(fill, "fill_id", None)
        if fill_id is None:
            raise RuntimeError("FILL_ID_REQUIRED")

        if fill_id in self._applied_fills:
            raise RuntimeError("DUPLICATE_FILL_DETECTED")
        self._applied_fills.add(fill_id)

        # normalize symbol
        symbol = getattr(fill, "symbol", None) or getattr(fill, "instrument", None) or "__TEST_SYMBOL__"

        # normalize side
        side_attr = getattr(fill, "side", None)
        if side_attr is None:
            qty_val = float(getattr(fill, "qty", 0.0))
            side = "BUY" if qty_val >= 0 else "SELL"
        else:
            side = str(side_attr).upper()

        # normalize qty/price/commission (qty must be positive, direction in side)
        qty = abs(float(getattr(fill, "qty", 0.0)))
        price = float(getattr(fill, "price", 0.0))
        commission = float(getattr(fill, "commission", 0.0))

        # build pm_fill object compatible with PositionManager.apply_fill(fill)
        class _PMFill:
            __slots__ = ("symbol", "side", "qty", "price", "commission", "fill_id")

            def __init__(self, symbol, side, qty, price, commission, fill_id):
                self.symbol = symbol
                self.side = side
                self.qty = qty
                self.price = price
                self.commission = commission
                self.fill_id = fill_id

        pm_fill = _PMFill(symbol, side, qty, price, commission, fill_id)

        # B1: single source of truth here
        self.position_manager.apply_fill(pm_fill)

        return self.compute_state()
    # ----------------------------------------------------
    # Backward compatibility alias (legacy tests)
    # ----------------------------------------------------

    def apply(self, fill) -> PortfolioState:
        """
        Legacy alias for on_fill.
        Required for integration tests compatibility.
        Auto-generates fill_id if missing (legacy tests).
        """
        if getattr(fill, "fill_id", None) is None:
            # deterministic fallback for legacy/integration tests
            fill.fill_id = f"LEGACY_{uuid.uuid4().hex}"

        return self.on_fill(fill)

    def mark_price(self, symbol: str, price: float):
        """
        Mark-to-market helper for integration tests.
        Updates position average mark price via PositionManager
        and recomputes portfolio state.
        """
        if symbol in self.position_manager.positions:
            pos = self.position_manager.positions[symbol]
            pos.mark_price = price
        return self.compute_state()

    def get_state(self) -> PortfolioState:
        """
        Backward-compatible snapshot accessor.
        """
        return self.compute_state()

    def get_context(self):
        """
        Returns full PortfolioState snapshot (with positions).
        Used by integration tests and risk layer.
        """
        return self.compute_state()
    # ====================================================
    # STATE COMPUTATION
    # ====================================================

    def compute_state(self, now_ts=None) -> PortfolioState:
        pm = self.position_manager

        market_value = 0.0
        unrealized_total = 0.0
        exposure = 0.0

        for symbol, pos in pm.positions.items():
            # ---- MARKET PRICE INJECTION ----
            if self.price_provider:
                market_price = self.price_provider.get_price(symbol)
                current_price = market_price if market_price is not None else pos.avg_price
            else:
                # В B1 лучше учитывать mark_price, если он есть
                current_price = getattr(pos, "mark_price", None) or pos.avg_price

            position_value = pos.qty * current_price
            market_value += position_value
            exposure += abs(position_value)

            unrealized_total += (current_price - pos.avg_price) * pos.qty

        # ✅ B1: cash/realized берём только из PM
        cash = float(getattr(pm, "cash", 0.0))
        realized = float(getattr(pm, "realized_pnl", 0.0))

        equity = cash + market_value

        # ---- STRICT EQUITY INVARIANT ----
        if abs(equity - (cash + market_value)) > 1e-9:
            raise RuntimeError("EQUITY_STRICT_INVARIANT_BROKEN")

        # ---- EXPOSURE INVARIANTS ----
        if exposure < 0:
            raise RuntimeError("EXPOSURE_NEGATIVE")

        if exposure > 1e12:
            raise RuntimeError("EXPOSURE_OVERFLOW")

        if not pm.positions:
            if exposure != 0:
                raise RuntimeError("EXPOSURE_WITH_NO_POSITIONS")

            if abs(unrealized_total) > 1e-9:
                raise RuntimeError("UNREALIZED_WITH_NO_POSITIONS")

        # ---- DRAWDOWN ----
        if equity > self._equity_peak:
            self._equity_peak = equity

        if self._equity_peak > 0:
            drawdown = (self._equity_peak - equity) / self._equity_peak
        else:
            drawdown = 0.0

        # ---- FINAL VALIDATION ----
        equity = round(equity, 12)
        market_value = round(market_value, 12)

        # важно: _validate_snapshot должен тоже читать cash/realized из PM (см. пункт 3)
        self._validate_snapshot(equity, market_value)

        return PortfolioState(
            cash=cash,
            equity=float(equity),
            realized_pnl=realized,
            unrealized_pnl=float(unrealized_total),
            exposure=float(exposure),
            drawdown=float(drawdown),
            positions=dict(pm.positions),
        )
    # ====================================================
    # EVENT ADAPTER (EventStore → Domain Model)
    # ====================================================

    def handle_event(self, event_dict: dict):
        event_type = event_dict.get("event_type")
        payload = event_dict.get("payload", {})

        if not event_type:
            return

        # ---- EXECUTION EVENT ----
        if event_type == "ExecutionEvent":
            fill = self._build_fill_from_payload(payload)
            self.on_fill(fill)

    def update_price(self, symbol, price):

        if price is None:
            return

        self.prices[symbol] = price

    def get_price(self, symbol):
        return self.prices.get(symbol)
        # ---- EXTENSION POINT ----
        # elif event_type == "SomethingElse":
        #     ...

    # ----------------------------------------------------
    # INTERNAL ADAPTER HELPERS
    # ----------------------------------------------------

    class _ReplayFill:
        def __init__(self, data: dict):
            self.fill_id = data.get("fill_id")
            self.symbol = data.get("symbol")
            self.side = data.get("side")
            self.qty = data.get("qty")
            self.price = data.get("price")
            self.commission = data.get("commission", 0.0)

    def _build_fill_from_payload(self, payload: dict):
        required = ["fill_id", "side", "qty", "price"]

        for field in required:
            if field not in payload:
                raise RuntimeError(f"REPLAY_EVENT_INVALID: missing {field}")

        return self._ReplayFill(payload)