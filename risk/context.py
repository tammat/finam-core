from dataclasses import dataclass

@dataclass
class RiskContext:
    equity: float
    cash: float
    gross_exposure: float
    net_exposure: float