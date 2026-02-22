from dataclasses import dataclass
from typing import Dict
from datetime import datetime


@dataclass
class Position:
    symbol: str
    qty: float = 0.0
    avg_price: float = 0.0
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    exposure: float = 0.0
    updated_ts: datetime | None = None


class PositionManager:

    def __init__(self):
        self.positions: Dict[str, Position] = {}

    def get(self, symbol: str) -> Position:
        return self.positions.get(symbol, Position(symbol))

    def update_fill(
        self,
        symbol: str,
        side: str,
        qty: float,
        price: float,
        commission: float,
        timestamp: datetime
    ) -> Position:

        pos = self.positions.get(symbol, Position(symbol))

        signed_qty = qty if side.upper() == "BUY" else -qty
        new_qty = pos.qty + signed_qty

        # --- Если позиция увеличивается в ту же сторону ---
        if pos.qty == 0 or (pos.qty > 0 and signed_qty > 0) or (pos.qty < 0 and signed_qty < 0):
            total_cost = pos.avg_price * abs(pos.qty) + price * abs(signed_qty)
            total_qty = abs(pos.qty) + abs(signed_qty)

            pos.avg_price = total_cost / total_qty if total_qty != 0 else 0
            pos.qty = new_qty

        # --- Если частично или полностью закрываем ---
        else:
            closing_qty = min(abs(pos.qty), abs(signed_qty))

            pnl_per_unit = (
                price - pos.avg_price
                if pos.qty > 0
                else pos.avg_price - price
            )

            pos.realized_pnl += pnl_per_unit * closing_qty - commission

            pos.qty = new_qty

            # если переворот
            if pos.qty != 0 and abs(signed_qty) > closing_qty:
                pos.avg_price = price
            elif pos.qty == 0:
                pos.avg_price = 0.0

        pos.exposure = pos.qty * price
        pos.updated_ts = timestamp

        self.positions[symbol] = pos
        return pos

    def mark_to_market(self, symbol: str, market_price: float):

        pos = self.positions.get(symbol)
        if not pos or pos.qty == 0:
            return None
        from dataclasses import dataclass
        from typing import Dict
        from datetime import datetime

        @dataclass
        class Position:
            symbol: str
            qty: float = 0.0
            avg_price: float = 0.0
            realized_pnl: float = 0.0
            unrealized_pnl: float = 0.0
            exposure: float = 0.0
            updated_ts: datetime | None = None

        class PositionManager:

            def __init__(self):
                self._positions: Dict[str, Position] = {}

            # ----------------------------------------------------
            # Public API
            # ----------------------------------------------------

            def get(self, symbol: str) -> Position:
                return self._positions.get(symbol, Position(symbol))

            def update_fill(
                    self,
                    symbol: str,
                    side: str,
                    qty: float,
                    price: float,
                    commission: float,
                    timestamp: datetime
            ) -> Position:

                pos = self._positions.get(symbol)

                if pos is None:
                    pos = Position(symbol)
                    self._positions[symbol] = pos

                signed_qty = qty if side.upper() == "BUY" else -qty

                if pos.qty == 0:
                    self._open_new_position(pos, signed_qty, price)

                elif self._same_direction(pos.qty, signed_qty):
                    self._increase_position(pos, signed_qty, price)

                else:
                    self._reduce_or_flip_position(pos, signed_qty, price)

                pos.realized_pnl -= commission
                pos.exposure = pos.qty * price
                pos.updated_ts = timestamp

                return pos

            def mark_to_market(self, symbol: str, market_price: float):

                pos = self._positions.get(symbol)
                if not pos or pos.qty == 0:
                    return None

                if pos.qty > 0:
                    pos.unrealized_pnl = (market_price - pos.avg_price) * pos.qty
                else:
                    pos.unrealized_pnl = (pos.avg_price - market_price) * abs(pos.qty)

                pos.exposure = pos.qty * market_price
                return pos

            def total_realized(self) -> float:
                return sum(p.realized_pnl for p in self._positions.values())

            def total_unrealized(self) -> float:
                return sum(p.unrealized_pnl for p in self._positions.values())

            def total_exposure(self) -> float:
                return sum(abs(p.exposure) for p in self._positions.values())

            # ----------------------------------------------------
            # Internal mechanics
            # ----------------------------------------------------

            def _same_direction(self, current_qty: float, new_qty: float) -> bool:
                return (current_qty > 0 and new_qty > 0) or (current_qty < 0 and new_qty < 0)

            def _open_new_position(self, pos: Position, signed_qty: float, price: float):
                pos.qty = signed_qty
                pos.avg_price = price

            def _increase_position(self, pos: Position, signed_qty: float, price: float):

                total_abs_qty = abs(pos.qty) + abs(signed_qty)

                weighted_price = (
                                         pos.avg_price * abs(pos.qty) +
                                         price * abs(signed_qty)
                                 ) / total_abs_qty

                pos.qty += signed_qty
                pos.avg_price = weighted_price

            def _reduce_or_flip_position(self, pos: Position, signed_qty: float, price: float):

                closing_qty = min(abs(pos.qty), abs(signed_qty))

                # realized pnl
                if pos.qty > 0:
                    pnl = (price - pos.avg_price) * closing_qty
                else:
                    pnl = (pos.avg_price - price) * closing_qty

                pos.realized_pnl += pnl

                new_qty = pos.qty + signed_qty

                # --- Full close ---
                if new_qty == 0:
                    pos.qty = 0
                    pos.avg_price = 0
                    return

                # --- Flip ---
                if abs(signed_qty) > closing_qty:
                    pos.qty = new_qty
                    pos.avg_price = price
                    return

                # --- Partial reduce ---
                pos.qty = new_qty
        if pos.qty > 0:
            pos.unrealized_pnl = (market_price - pos.avg_price) * pos.qty
        else:
            pos.unrealized_pnl = (pos.avg_price - market_price) * abs(pos.qty)

        pos.exposure = pos.qty * market_price
        return pos

    def total_realized(self) -> float:
        return sum(p.realized_pnl for p in self.positions.values())

    def total_unrealized(self) -> float:
        return sum(p.unrealized_pnl for p in self.positions.values())

    def total_exposure(self) -> float:
        return sum(abs(p.exposure) for p in self.positions.values())