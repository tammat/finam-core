from dataclasses import dataclass


@dataclass
class RiskConfig:
    trading_enabled: bool = True

    max_total_exposure: float = 1_000_000
    max_symbol_exposure: float = 1_000_000

    daily_loss_limit: float = 1.0        # в долях (0.05 = 5%)
    max_drawdown: float = 1.0            # в долях

    max_portfolio_heat: float = 2.0      # абсолютная доля (0.2 = 20%)