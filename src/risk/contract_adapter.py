from dataclasses import dataclass
import math


@dataclass(frozen=True)
class ContractSpec:
    tick_size: float
    lot_size: int = 1


class ContractAdapter:
    def __init__(self, spec: ContractSpec):
        self.spec = spec

    def normalize_qty(self, qty: float) -> int:
        if qty <= 0:
            return 0

        lots = qty / self.spec.lot_size
        return int(math.floor(lots)) * self.spec.lot_size