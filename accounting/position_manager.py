from dataclasses import dataclass
from typing import Dict
from collections import defaultdict
from storage.snapshot_repository import SnapshotRepository
from storage.fill_journal import FillJournal
from domain.risk.risk_factory import build_risk_stack
from domain.risk.risk_context import RiskContext
@dataclass
class Position:
    symbol: str
    qty: float = 0.0
    avg_price: float = 0.0
    realized_pnl: float = 0.0
    mark_price: float = 0.0


class PositionManager:
    from domain.risk.risk_factory import build_risk_stack

    def __init__(
            self,
            starting_cash: float = 0.0,
            recover: bool = False,
            enable_wal: bool = False,
            risk_stack=None,
    ):        # ВАЖНО: ничего не ломаем
        # Если стек передан — используем его
        # Иначе создаём дефолтный через factory
        if risk_stack is not None:
            self.risk_stack = risk_stack
        else:
            self.risk_stack = build_risk_stack()
        self._seq = 0
        self._fill_counter = 0
        self._snapshot_interval = 100

        self.enable_wal = enable_wal
        self.journal = FillJournal() if enable_wal else None

        self.cash = float(starting_cash)
        self.starting_cash = float(starting_cash)

        self._applied_fills = set()
        self.processed_fills = set()

        self.positions: Dict[str, Position] = defaultdict(
            lambda: Position(symbol="")
        )

        self.realized_pnl = 0.0
        self.unrealized_pnl = 0.0
        self.daily_realized_pnl = 0.0
        self._peak_equity = float(starting_cash)

        self.risk_engine = None
        self.snapshot_repo = SnapshotRepository()

    def attach_risk_engine(self, risk_engine):
        """
        Attach external RiskEngine instance to PositionManager.
        """
        self.risk_engine = risk_engine
    # --------------------------------------------------
    def apply_fill(self, fill, from_replay: bool = False):
        """
        Apply execution fill to portfolio state.

        from_replay=True:
            - do NOT write to WAL
            - still respect idempotency
        """
        if self.risk_engine:
            if not self.risk_engine.validate(fill):
                return
        if not from_replay:
            self._seq += 1
            fill_seq = self._seq
        else:
            fill_seq = getattr(fill, "seq", None)
        # --------------------------------------------------
        # 1) WAL append (only for live fills)
        # --------------------------------------------------
        if self.enable_wal and not from_replay:
            fill_dict = {
                "seq": fill_seq,
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
        self._fill_counter += 1

        if self._fill_counter >= self._snapshot_interval:
            self.save_snapshot_and_rotate()
            self._fill_counter = 0
        # ---------------------      #

        if from_replay and fill_seq:
            if fill_seq > self._seq:
                self._seq = fill_seq
        # ---------------------------
        if from_replay:
            fill_seq = getattr(fill, "seq", None)
            if fill_seq and fill_seq > self._seq:
                self._seq = fill_seq
        #---------------------

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

        return self.cash + market_value
    # --------------------------------------------------

    def get_context(self):


        equity = self.total_equity()

        gross_exposure = sum(
            abs(pos.qty) * pos.avg_price
            for pos in self.positions.values()
        )

        # ---- Portfolio heat calculation ----
        portfolio_heat = 0.0

        for pos in self.positions.values():
            if pos.qty == 0:
                continue

            atr = getattr(pos, "atr", None)

            if atr:
                portfolio_heat += abs(pos.qty) * atr
            else:
                portfolio_heat += abs(pos.qty) * pos.avg_price

        return RiskContext(
            symbol=None,
            trade_value=0.0,
            portfolio_value=equity,
            current_symbol_exposure=0.0,
            total_exposure=gross_exposure,

            equity=equity,
            gross_exposure=gross_exposure,
            portfolio_heat=portfolio_heat,
            positions=self.positions,
            realized_pnl=self.realized_pnl,
            unrealized_pnl=self.unrealized_pnl,
            daily_realized_pnl=self.daily_realized_pnl,
            starting_capital=self.starting_cash,
        )
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
            "seq": self._seq,
            "applied_fills": list(self.processed_fills),
            "cash": self.cash,
            "realized_pnl": self.realized_pnl,
            "daily_realized_pnl": self.daily_realized_pnl,
            "peak_equity": self._peak_equity,
            "positions": {
                symbol: {
                    "qty": pos.qty,
                    "avg_price": pos.avg_price,
                    "mark_price": pos.mark_price,
                    "realized_pnl": pos.realized_pnl,
                }
                for symbol, pos in self.positions.items()
            },
            "risk_state": self.risk_stack.get_state(),  # ← добавлено
        }

    def load_snapshot(self, snapshot: dict) -> None:
        if not snapshot:
            return
        self.processed_fills = set(snapshot.get("applied_fills", []))
        self.cash = snapshot["cash"]
        self.realized_pnl = snapshot["realized_pnl"]
        self._seq = snapshot.get("seq", 0)
        self.positions.clear()
        if "risk_state" in snapshot:
            self.risk_stack.load_state(snapshot["risk_state"])
        for symbol, data in snapshot["positions"].items():
            pos = self.positions[symbol]
            pos.qty = data["qty"]
            pos.avg_price = data["avg_price"]
            pos.mark_price = data["mark_price"]

    def recover_from_journal(self):
        if not self.enable_wal or self.journal is None:
            return

        snapshot_seq = self._seq

        for record in self.journal.read_all():

            if not isinstance(record, dict):
                continue

            # WAL may store either:
            # 1) {"seq": ..., ...}
            # 2) {"ts": ..., "fill": {...}}
            fill_data = record.get("fill", record)

            if not isinstance(fill_data, dict):
                continue

            record_seq = fill_data.get("seq")

            # Apply fencing ONLY if seq is present (new WAL format).
            # Legacy WAL entries without seq must always be applied.
            if record_seq is not None and record_seq <= snapshot_seq:
                continue

            # Skip malformed or incomplete WAL entries
            # (e.g. corrupted lines or wrapper records without symbol)
            if "symbol" not in fill_data:
                continue

            class DummyFill:
                pass

            fill = DummyFill()
            for k, v in fill_data.items():
                setattr(fill, k, v)

            # Skip malformed WAL entries missing required fields
            if not hasattr(fill, "symbol") or fill.symbol is None:
                continue

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

    def save_snapshot_and_rotate(self):
        if not hasattr(self, "snapshot_repo"):
            return

        snapshot = self.get_snapshot()
        self.snapshot_repo.save(snapshot)
        if self.enable_wal:
            self.journal.reset()

    def commit_snapshot(self):
        with self._snapshot_lock:
            snapshot = self.get_snapshot()

            # 1. save snapshot atomically
            self.snapshot_repo.save_atomic(snapshot)

            # 2. fsync directory (защита от power-loss)
            self.snapshot_repo.fsync_dir()

            # 3. reset WAL only after snapshot committed
            if self.enable_wal:
                self.journal.reset()

    def persist_state(self, snapshot_repo: SnapshotRepository):
        snapshot = self.get_snapshot()
        snapshot_repo.save(snapshot)

        if self.enable_wal and self.journal:
            self.journal.reset()

    def current_drawdown(self):
        """
        Backward-compatible helper.
        Real drawdown logic now lives in risk layer.
        """
        equity = self.total_equity()

        if self.starting_cash == 0:
            return 0.0

        return (equity - self.starting_cash) / self.starting_cash

    def current_drawdown(self):
        equity = self.total_equity()
        if self.starting_cash == 0:
            return 0.0
        return (equity - self.starting_cash) / self.starting_cash
