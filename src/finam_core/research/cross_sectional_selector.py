from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class InstrumentPerformance:
    symbol: str
    trades: int
    net_pnl: float
    expectancy: float
    winrate: float


@dataclass(frozen=True)
class SelectedInstrument:
    symbol: str
    rank: int
    score: float
    decision: str
    reason: str


class CrossSectionalSelector:
    """Русский комментарий: выбирает лучшие инструменты по устойчивости результата."""

    def select(
        self,
        items: list[InstrumentPerformance],
        *,
        top_n: int = 2,
        min_trades: int = 3,
        min_expectancy: float = 0.0,
    ) -> list[SelectedInstrument]:
        scored: list[tuple[InstrumentPerformance, float]] = []

        for item in items:
            if item.trades < min_trades:
                continue

            if item.expectancy <= min_expectancy:
                continue

            score = (
                item.expectancy * 1.0
                + item.winrate * 10.0
                + max(0.0, item.net_pnl) * 0.01
            )

            scored.append((item, round(score, 6)))

        scored.sort(key=lambda x: x[1], reverse=True)

        selected: list[SelectedInstrument] = []

        for rank, (item, score) in enumerate(scored[:top_n], start=1):
            selected.append(
                SelectedInstrument(
                    symbol=item.symbol,
                    rank=rank,
                    score=score,
                    decision="ВЫБРАТЬ",
                    reason=(
                        f"expectancy={item.expectancy:.6f};"
                        f"winrate={item.winrate:.4f};"
                        f"trades={item.trades}"
                    ),
                )
            )

        return selected
