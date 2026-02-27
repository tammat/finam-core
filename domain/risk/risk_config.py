from dataclasses import dataclass


@dataclass(frozen=True)
class RiskConfig:
    """
    Конфигурация риск-лимитов.

    frozen=True:
    - запрет мутаций после создания
    - детерминированность
    - безопасность для продакшена
    """

    max_total_exposure: float = 0.6       # макс доля капитала в рынке
    max_symbol_exposure: float = 0.2      #     # макс доля на один инструмент
    max_drawdown: float = 0.2   # ← ДОБАВИТЬ
    max_daily_loss: float = 0.05   # ← добавить