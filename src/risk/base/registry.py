from __future__ import annotations

from risk.base.rule import RiskRule


class RiskRuleRegistry:
    _registry: dict[str, type[RiskRule]] = {}

    @classmethod
    def register(cls, rule_cls: type[RiskRule]) -> type[RiskRule]:
        name = getattr(rule_cls, "name", "")
        if not name:
            raise ValueError("risk rule name is required")
        cls._registry[name] = rule_cls
        return rule_cls

    @classmethod
    def enabled(cls) -> list[type[RiskRule]]:
        return [r for r in cls._registry.values() if getattr(r, "enabled", True)]

    @classmethod
    def get(cls, name: str) -> type[RiskRule] | None:
        return cls._registry.get(name)

    @classmethod
    def clear_for_tests(cls) -> None:
        cls._registry.clear()
