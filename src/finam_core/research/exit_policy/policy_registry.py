from finam_core.research.exit_policy.policy_base import ExitPolicy


class PolicyRegistry:
    def __init__(self):
        self._policies: dict[str, ExitPolicy] = {}

    def register(self, policy: ExitPolicy) -> None:
        self._policies[policy.name] = policy

    def all(self) -> list[ExitPolicy]:
        return list(self._policies.values())

    def names(self) -> list[str]:
        return sorted(self._policies)
