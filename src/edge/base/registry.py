from __future__ import annotations

from edge.base.rule import EdgeRule


class EdgeRuleRegistry:
    _registry: dict[str, type[EdgeRule]] = {}

    @classmethod
    def register(cls, rule_cls: type[EdgeRule]) -> type[EdgeRule]:
        name = getattr(rule_cls, "name", "")
        if not name:
            raise ValueError("edge rule name is required")
        cls._registry[name] = rule_cls
        return rule_cls

    @classmethod
    def enabled(cls) -> list[type[EdgeRule]]:
        return [
            rule_cls
            for rule_cls in cls._registry.values()
            if getattr(rule_cls, "enabled", True)
        ]

    @classmethod
    def get(cls, name: str) -> type[EdgeRule] | None:
        return cls._registry.get(name)

    @classmethod
    def clear_for_tests(cls) -> None:
        cls._registry.clear()
