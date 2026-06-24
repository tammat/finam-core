from finam_core.research.exit_policy.policy_base import ClosedTradeInput, VirtualExitResult
from finam_core.research.exit_policy.policy_registry import PolicyRegistry


class ReplayEngine:
    def __init__(self, registry: PolicyRegistry):
        self.registry = registry

    def replay(self, trades: list[ClosedTradeInput]) -> list[VirtualExitResult]:
        results: list[VirtualExitResult] = []
        for trade in trades:
            for policy in self.registry.all():
                results.append(policy.simulate(trade))
        return results
