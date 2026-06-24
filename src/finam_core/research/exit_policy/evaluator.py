from dataclasses import dataclass

from finam_core.research.exit_policy.policy_base import VirtualExitResult


@dataclass(frozen=True)
class PolicyMetrics:
    policy_name: str
    trades: int
    wins: int
    losses: int
    winrate: float
    gross_pnl: float
    expectancy: float
    profit_factor: float


class PolicyEvaluator:
    def evaluate(self, results: list[VirtualExitResult]) -> list[PolicyMetrics]:
        grouped: dict[str, list[VirtualExitResult]] = {}

        for result in results:
            grouped.setdefault(result.policy_name, []).append(result)

        metrics: list[PolicyMetrics] = []

        for policy_name, rows in grouped.items():
            trades = len(rows)
            wins = sum(1 for r in rows if r.virtual_net_pnl > 0)
            losses = trades - wins
            gross_pnl = sum(r.virtual_net_pnl for r in rows)
            gross_profit = sum(r.virtual_net_pnl for r in rows if r.virtual_net_pnl > 0)
            gross_loss = abs(sum(r.virtual_net_pnl for r in rows if r.virtual_net_pnl <= 0))

            metrics.append(
                PolicyMetrics(
                    policy_name=policy_name,
                    trades=trades,
                    wins=wins,
                    losses=losses,
                    winrate=wins / trades if trades else 0.0,
                    gross_pnl=gross_pnl,
                    expectancy=gross_pnl / trades if trades else 0.0,
                    profit_factor=gross_profit / gross_loss if gross_loss else 0.0,
                )
            )

        return sorted(metrics, key=lambda x: x.profit_factor, reverse=True)
