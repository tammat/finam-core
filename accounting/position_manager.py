from dataclasses import dataclass
from typing import Dict
from collections import defaultdict
from storage.snapshot_repository import SnapshotRepository
from storage.fill_journal import FillJournal
@dataclass
class Position:
    symbol: str
    qty: float = 0.0
    avg_price: float = 0.0
    realized_pnl: float = 0.0
    mark_price: float = 0.0


class PositionManager:

    def __init__(
            self,
            starting_cash: float = 0.0,
            recover: bool = False,
            enable_wal: bool = False,
    ):
        self.enable_wal = enable_wal
        self.journal = FillJournal() if enable_wal else None
        self.cash = float(starting_cash)
        self._applied_fills = set()
        self.journal = FillJournal()
        self.positions: Dict[str, Position] = defaultdict(
            lambda: Position(symbol="")
        )
        self.starting_cash = starting_cash
        self.realized_pnl = 0.0
        self.unrealized_pnl = 0.0
        self.processed_fills = set()
        self._peak_equity = float(starting_cash)
        self.daily_realized_pnl = 0.0

        # TEMP: recovery disabled
        self.snapshot_repo = SnapshotRepository()
    # --------------------------------------------------
    def apply_fill(self, fill, from_replay: bool = False):
        """
        Apply execution fill to portfolio state.

        from_replay=True:
            - do NOT write to WAL
            - still respect idempotency
        """

        # --------------------------------------------------
        # 1) WAL append (only for live fills)
        # --------------------------------------------------
        if self.enable_wal and not from_replay:
            fill_dict = {
                "symbol": fill.symbol,
                "qty": fill.qty,
                "price": fill.price,
                "side": fill.side,
                "fill_id": getattr(fill, "fill_id", None),
                "event_id": getattr(fill, "event_id", None),
                "commission": getattr(fill, "commission", 0.0),
            }
            self.journal.append(fill_dict)
        # --------------------------------------------------
        # 2) Idempotency protection
        # --------------------------------------------------
        fill_id = getattr(fill, "fill_id", None) or getattr(fill, "event_id", None)

        if fill_id is not None:
            if fill_id in self.processed_fills:
                return
            self.processed_fills.add(fill_id)

        # --------------------------------------------------
        # 3) Position update
        # --------------------------------------------------
        pos = self.positions[fill.symbol]
        pos.symbol = fill.symbol

        signed_qty = fill.qty if fill.side == "BUY" else -fill.qty

        # --- Increase / open ---
        if (
                pos.qty == 0
                or (pos.qty > 0 and signed_qty > 0)
                or (pos.qty < 0 and signed_qty < 0)
        ):
            new_qty = pos.qty + signed_qty

            if new_qty != 0:
                pos.avg_price = (
                                        pos.qty * pos.avg_price + signed_qty * fill.price
                                ) / new_qty

            pos.qty = new_qty

        # --- Reduce / close ---
        else:
            closing = min(abs(pos.qty), abs(signed_qty))
            pnl = closing * (fill.price - pos.avg_price)

            if pos.qty < 0:
                pnl = -pnl

            pos.realized_pnl += pnl
            self.realized_pnl += pnl
            self.daily_realized_pnl += pnl

            pos.qty += signed_qty

            if pos.qty == 0:
                pos.avg_price = 0.0

        # --------------------------------------------------
        # 4) Cash update
        # --------------------------------------------------
        self.cash -= signed_qty * fill.price
        self.cash -= getattr(fill, "commission", 0.0)

        # --------------------------------------------------
        # 5) Recalculate unrealized PnL
        # --------------------------------------------------
        self._recalculate_unrealized()

        # --------------------------------------------------
        # 6) Optional snapshot (safe but can be throttled later)
        # --------------------------------------------------
        if hasattr(self, "snapshot_repo") and not from_replay:
            self.snapshot_repo.save(self.get_snapshot())

            # Idempotency: prefer fill_id if present, otherwise fall back to event_id
            fill_id = getattr(fill, "fill_id", None) or getattr(fill, "event_id", None)

            if fill_id is not None:
                if fill_id in self.processed_fills:
                    return
                self.processed_fills.add(fill_id)
            pos = self.positions[fill.symbol]

            signed_qty = fill.qty if fill.side == "BUY" else -fill.qty

            # Increase / open
            if pos.qty == 0 or (pos.qty > 0 and signed_qty > 0) or (pos.qty < 0 and signed_qty < 0):
                new_qty = pos.qty + signed_qty

                if new_qty != 0:
                    pos.avg_price = (
                                            pos.qty * pos.avg_price + signed_qty * fill.price
                                    ) / new_qty

                pos.qty = new_qty

            # Reduce / close
            else:
                closing = min(abs(pos.qty), abs(signed_qty))
                pnl = closing * (fill.price - pos.avg_price)

                if pos.qty < 0:
                    pnl = -pnl

                pos.realized_pnl += pnl
                pos.qty += signed_qty

                if pos.qty == 0:
                    pos.avg_price = 0.0

            # Cash update
            self.cash -= signed_qty * fill.price
            self.cash -= getattr(fill, "commission", 0.0)

            if hasattr(self, "snapshot_repo"):
                self.snapshot_repo.save(self.get_snapshot())
        # --------------------------------------------------

    def update_market_price(self, symbol: str, price: float):
        pos = self.positions[symbol]
        pos.mark_price = price
        if symbol in self.positions:
            self.positions[symbol].mark_price = price
        self._recalculate_unrealized()

    # --------------------------------------------------

    def total_equity(self):

        market_value = sum(
            p.qty * (p.mark_price if p.mark_price else p.avg_price)
            for p in self.positions.values()
        )

        equity = self.cash + market_value

        if equity > self._peak_equity:
            self._peak_equity = equity

        return equity

    # --------------------------------------------------

    def current_drawdown(self):

        equity = self.total_equity()

        if self._peak_equity == 0:
            return 0.0

        return (equity - self._peak_equity) / self._peak_equity

    # --------------------------------------------------

    def get_context(self):

        class Context:
            pass

        context = Context()

        # -------------------------------
        # Equity
        # -------------------------------
        context.equity = self.total_equity()
        context.realized_pnl = self.realized_pnl
        context.unrealized_pnl = self.unrealized_pnl        # -------------------------------
        # Peak equity (capital protection)
        # -------------------------------
        if not hasattr(self, "peak_equity"):
            self.peak_equity = float(self.starting_cash)

        if context.equity > self.peak_equity:
            self.peak_equity = context.equity

        context.peak_equity = self.peak_equity

        # drawdown (negative value)
        if self.peak_equity != 0:
            context.drawdown = (
                    (context.equity - self.peak_equity)
                    / self.peak_equity
            )
        else:
            context.drawdown = 0.0
        # -------------------------------
        # Daily loss
        # -------------------------------
        daily_pnl = getattr(self, "daily_realized_pnl", 0.0)

        context.daily_realized_pnl = daily_pnl

        if self.starting_cash != 0:
            context.daily_drawdown = daily_pnl / self.starting_cash
        else:
            context.daily_drawdown = 0.0
        # -------------------------------
        # Gross exposure
        # -------------------------------
        context.gross_exposure = sum(
            abs(pos.qty) * pos.avg_price
            for pos in self.positions.values()
        )

        context.positions = self.positions

        # -------------------------------
        # Portfolio Heat
        # -------------------------------
        portfolio_heat = 0.0

        for symbol, pos in self.positions.items():
            if pos.qty == 0:
                continue

            atr = getattr(pos, "atr", None)

            if atr:
                portfolio_heat += abs(pos.qty) * atr
            else:
                portfolio_heat += abs(pos.qty) * pos.avg_price

        context.portfolio_heat = portfolio_heat

        return context
    # --------------------------------------------------

    def on_fill(self, fill):
        self.apply_fill(fill)

    def on_market_data(self, market_data):
        symbol = market_data.symbol
        price = market_data.price
        self.update_market_price(symbol, price)

    def _recalculate_unrealized(self):

        total = 0.0

        for symbol, pos in self.positions.items():
            if pos.qty == 0:
                continue

            market_price = getattr(pos, "mark_price", None)
            if market_price is None:
                continue

            total += (market_price - pos.avg_price) * pos.qty

        self.unrealized_pnl = total

    def get_snapshot(self) -> dict:
        return {
            "applied_fills": list(self.processed_fills),            "cash": self.cash,
            "realized_pnl": self.realized_pnl,
            "positions": {
                symbol: {
                    "qty": pos.qty,
                    "avg_price": pos.avg_price,
                    "mark_price": pos.mark_price,
                }
                for symbol, pos in self.positions.items()
            },
        }

    def load_snapshot(self, snapshot: dict) -> None:
        self.processed_fills = set(snapshot.get("applied_fills", []))
        self.cash = snapshot["cash"]
        self.realized_pnl = snapshot["realized_pnl"]

        self.positions.clear()

        for symbol, data in snapshot["positions"].items():
            pos = self.positions[symbol]
            pos.qty = data["qty"]
            pos.avg_price = data["avg_price"]
            pos.mark_price = data["mark_price"]

    def recover_from_journal(self):
        if not self.enable_wal or self.journal is None:
            return

        for record in self.journal.read_all():

            # WAL format: {"ts": ..., "fill": {...}}
            fill_data = record.get("fill")

            if not fill_data:
                continue

            class DummyFill:
                pass

            fill = DummyFill()

            for k, v in fill_data.items():
                setattr(fill, k, v)

            # CRITICAL: no WAL write during replay
            self.apply_fill(fill, from_replay=True)

    def restore_from_snapshot(self, snapshot: dict):
        if not snapshot:
            return

        self.cash = snapshot.get("cash", self.cash)
        self.realized_pnl = snapshot.get("realized_pnl", 0.0)
        self.daily_realized_pnl = snapshot.get("daily_realized_pnl", 0.0)
        self._peak_equity = snapshot.get("peak_equity", self.cash)

        # Восстановление позиций
        restored_positions = snapshot.get("positions", {})

        self.positions.clear()

        for symbol, data in restored_positions.items():
            pos = Position(
                symbol=symbol,
                qty=data.get("qty", 0.0),
                avg_price=data.get("avg_price", 0.0),
                realized_pnl=data.get("realized_pnl", 0.0),
                mark_price=data.get("mark_price", 0.0),
            )
            self.positions[symbol] = pos