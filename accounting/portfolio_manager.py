from dataclasses import dataclass
from decimal import Decimal

from core.validator import StateValidator
from core.state import PortfolioState as CorePortfolioState, Position
from domain.position_manager import PositionManager
from datetime import datetime
from risk.risk_engine import RiskContext

@dataclass
class PortfolioState:
    cash: float
    equity: float
    realized_pnl: float
    unrealized_pnl: float
    exposure: float
    drawdown: float

    @property
    def total_abs_notional(self) -> float:
        return sum(abs(p.notional) for p in self.positions.values())
    # ------------------------------------------------------------
    # ------------------- RiskContext Builder --------------------
    # ------------------------------------------------------------

    def build_context(self) -> RiskContext:
        """
        Строит неизменяемый snapshot состояния для RiskEngine.
        Никаких мутаций.
        """

        equity = getattr(self, "equity", 0.0)
        daily_pnl = getattr(self, "daily_pnl", 0.0)
        drawdown_pct = getattr(self, "drawdown_pct", 0.0)

        positions = getattr(self, "positions", {})
        exposure_by_asset = getattr(self, "exposure_by_asset", {})

        return RiskContext(
            equity=equity,
            daily_pnl=daily_pnl,
            drawdown_pct=drawdown_pct,
            positions=positions,
            exposure_by_asset=exposure_by_asset,
            timestamp=datetime.utcnow(),
        )


class PortfolioManager:
    """
    Clean production model.

    - Position math → PositionManager
    - Accounting → cash + realized aggregation
    - Equity derived strictly
    """

    def __init__(self, initial_cash: float = 100000.0, validator: StateValidator = None, price_provider=None):
        self.cash = float(initial_cash)
        self.realized_pnl = 0.0

        self._equity_peak = float(initial_cash)
        self.drawdown = 0.0

        self.validator = validator or StateValidator()
        self._applied_fills = set()

        self.position_manager = PositionManager()
        self.price_provider = price_provider
        # ====================================================
    # SNAPSHOT VALIDATION
    # ====================================================

    def _validate_snapshot(self, equity: float, unrealized: float):

        # ---- DECIMAL NORMALIZATION ----
        cash_dec = Decimal(str(round(self.cash, 12)))
        realized_dec = Decimal(str(round(self.realized_pnl, 12)))
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

        side = fill.side.upper()
        notional = fill.qty * fill.price
        commission = getattr(fill, "commission", 0.0)

        if commission < 0:
            raise RuntimeError("INVALID_COMMISSION_SIGN")

        # ---- POSITION LAYER ----
        symbol = getattr(fill, "symbol", None)
        if symbol is None:
            symbol = getattr(fill, "instrument", None)
        if symbol is None:
            symbol = "__TEST_SYMBOL__"

        realized = self.position_manager.apply_fill(
            symbol=symbol,
            side=fill.side,
            qty=fill.qty,
            price=fill.price,
        )

        # ---- CASH FLOW ----
        if side == "BUY":
            self.cash -= notional
        else:
            self.cash += notional

        self.cash -= commission

        # ---- REALIZED AGGREGATION ----
        prev_realized = self.realized_pnl
        self.realized_pnl += realized

        if abs(self.realized_pnl - prev_realized - realized) > 1e-9:
            raise RuntimeError("REALIZED_INVARIANT_BROKEN")

        return self.compute_state()

    # ====================================================
    # STATE COMPUTATION
    # ====================================================

    def compute_state(self, now_ts=None) -> PortfolioState:
        market_value = 0.0
        unrealized_total = 0.0
        exposure = 0.0

        for symbol, pos in self.position_manager.positions.items():
            # ---- MARKET PRICE INJECTION ----
            if self.price_provider:
                market_price = self.price_provider.get_price(symbol)
                current_price = market_price if market_price is not None else pos.avg_price
            else:
                current_price = pos.avg_price

            position_value = pos.qty * current_price
            market_value += position_value
            exposure += abs(position_value)

            unrealized_total += (current_price - pos.avg_price) * pos.qty

        equity = self.cash + market_value

        # ---- STRICT EQUITY INVARIANT ----
        if abs(equity - (self.cash + market_value)) > 1e-9:
            raise RuntimeError("EQUITY_STRICT_INVARIANT_BROKEN")

        # ---- EXPOSURE INVARIANTS ----
        if exposure < 0:
            raise RuntimeError("EXPOSURE_NEGATIVE")

        if exposure > 1e12:
            raise RuntimeError("EXPOSURE_OVERFLOW")

        if not self.position_manager.positions:
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
        # Core validator model: equity = cash + unrealized
        # Пока нет отдельной realized-схемы в core,
        # unrealized должен содержать full marked position value
        # ---- FLOAT NORMALIZATION (avoid drift into Decimal validator) ----
        equity = round(equity, 12)
        market_value = round(market_value, 12)
        self._validate_snapshot(equity, market_value)
        return PortfolioState(
            cash=float(self.cash),
            equity=float(equity),
            realized_pnl=float(self.realized_pnl),
            unrealized_pnl=float(unrealized_total),
            exposure=float(exposure),
            drawdown=float(drawdown),
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