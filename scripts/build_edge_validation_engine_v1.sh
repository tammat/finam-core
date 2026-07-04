#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_EDGE_VALIDATION_ENGINE_V1 ==="

mkdir -p src/edge/base src/edge/sample_rule scripts

touch src/edge/__init__.py
touch src/edge/base/__init__.py
touch src/edge/sample_rule/__init__.py

cat > src/edge/base/validation_result.py <<'PY'
from __future__ import annotations
from dataclasses import dataclass
from typing import Any

@dataclass(slots=True, frozen=True)
class EdgeValidationDiagnostics:
    passed_rules: list[str]
    failed_rules: list[str]
    input_values: dict[str, float]
    thresholds: dict[str, float]
    component_scores: dict[str, float]
    execution_time_ms: float
    details: dict[str, Any]

@dataclass(slots=True, frozen=True)
class EdgeValidationResult:
    rule_name: str
    rule_version: str
    validation_score: float
    passed: bool
    diagnostics: EdgeValidationDiagnostics
    reason_code: str
PY

cat > src/edge/base/validation_rule.py <<'PY'
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any
from edge.base.validation_result import EdgeValidationResult

class EdgeValidationRule(ABC):
    name: str
    version: str
    enabled: bool = True

    @abstractmethod
    def run(self, edge_snapshot: dict[str, Any]) -> EdgeValidationResult:
        raise NotImplementedError
PY

cat > src/edge/base/validation_registry.py <<'PY'
from __future__ import annotations
from edge.base.validation_rule import EdgeValidationRule

class EdgeValidationRegistry:
    _registry: dict[str, type[EdgeValidationRule]] = {}

    @classmethod
    def register(cls, rule_cls: type[EdgeValidationRule]) -> type[EdgeValidationRule]:
        name = getattr(rule_cls, "name", "")
        if not name:
            raise ValueError("validation rule name is required")
        cls._registry[name] = rule_cls
        return rule_cls

    @classmethod
    def enabled(cls) -> list[type[EdgeValidationRule]]:
        return [r for r in cls._registry.values() if getattr(r, "enabled", True)]

    @classmethod
    def get(cls, name: str) -> type[EdgeValidationRule] | None:
        return cls._registry.get(name)

    @classmethod
    def clear_for_tests(cls) -> None:
        cls._registry.clear()
PY

cat > src/edge/base/validation_executor.py <<'PY'
from __future__ import annotations
from edge.base.validation_result import EdgeValidationResult
from edge.base.validation_rule import EdgeValidationRule

class EdgeValidationExecutor:
    def execute(self, rule: EdgeValidationRule, edge_snapshot: dict) -> EdgeValidationResult:
        return rule.run(edge_snapshot)
PY

cat > src/edge/sample_rule/config.py <<'PY'
from __future__ import annotations
from dataclasses import dataclass
from typing import Any

@dataclass(slots=True, frozen=True)
class EdgeSampleRuleConfig:
    min_samples: int = 30
    min_edge_score: float = 0.60

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "EdgeSampleRuleConfig":
        data = data or {}
        defaults = cls()
        return cls(
            min_samples=int(data.get("min_samples", defaults.min_samples)),
            min_edge_score=float(data.get("min_edge_score", defaults.min_edge_score)),
        )
PY

cat > src/edge/sample_rule/rule.py <<'PY'
from __future__ import annotations
import time
from typing import Any

from edge.base.validation_registry import EdgeValidationRegistry
from edge.base.validation_result import EdgeValidationDiagnostics, EdgeValidationResult
from edge.base.validation_rule import EdgeValidationRule
from edge.sample_rule.config import EdgeSampleRuleConfig

def _num(value: object, default: float = 0.0) -> float:
    try:
        return default if value is None else float(value)
    except (TypeError, ValueError):
        return default

@EdgeValidationRegistry.register
class EdgeSampleRule(EdgeValidationRule):
    name = "EDGE_SAMPLE_RULE"
    version = "v1"
    enabled = True

    def __init__(self, config: EdgeSampleRuleConfig | None = None) -> None:
        self.config = config or EdgeSampleRuleConfig()

    def run(self, edge_snapshot: dict[str, Any]) -> EdgeValidationResult:
        started = time.perf_counter()
        cfg = self.config

        edge_score = _num(edge_snapshot.get("edge_score"))
        samples = int(_num(edge_snapshot.get("samples")))

        edge_score_ok = edge_score >= cfg.min_edge_score
        samples_ok = samples >= cfg.min_samples
        passed = edge_score_ok and samples_ok

        checks = {"edge_score": edge_score_ok, "samples": samples_ok}

        return EdgeValidationResult(
            rule_name=self.name,
            rule_version=self.version,
            validation_score=1.0 if passed else 0.0,
            passed=passed,
            reason_code="VALIDATION_PASS" if passed else "VALIDATION_FAIL",
            diagnostics=EdgeValidationDiagnostics(
                passed_rules=[k for k, ok in checks.items() if ok],
                failed_rules=[k for k, ok in checks.items() if not ok],
                input_values={"edge_score": edge_score, "samples": float(samples)},
                thresholds={"min_edge_score": cfg.min_edge_score, "min_samples": float(cfg.min_samples)},
                component_scores={"edge_score_ok": float(edge_score_ok), "samples_ok": float(samples_ok), "total": float(passed)},
                execution_time_ms=(time.perf_counter() - started) * 1000.0,
                details={},
            ),
        )
PY

cat > src/edge/sample_rule/__init__.py <<'PY'
from edge.sample_rule.rule import EdgeSampleRule
__all__ = ["EdgeSampleRule"]
PY

cat > scripts/test_edge_validation_engine_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_VALIDATION_ENGINE_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/edge/base/validation_result.py \
  src/edge/base/validation_rule.py \
  src/edge/base/validation_registry.py \
  src/edge/base/validation_executor.py \
  src/edge/sample_rule/config.py \
  src/edge/sample_rule/rule.py \
  src/edge/sample_rule/__init__.py

PYTHONPATH=src python - <<'PY'
from edge.base.validation_executor import EdgeValidationExecutor
from edge.base.validation_registry import EdgeValidationRegistry
import edge.sample_rule
from edge.sample_rule.rule import EdgeSampleRule

assert EdgeValidationRegistry.get("EDGE_SAMPLE_RULE") is EdgeSampleRule

rule = EdgeSampleRule()
executor = EdgeValidationExecutor()

assert executor.execute(rule, {"edge_score": 0.80, "samples": 50}).passed is True
assert executor.execute(rule, {"edge_score": 0.30, "samples": 50}).passed is False
assert executor.execute(rule, {"edge_score": 0.80, "samples": 2}).passed is False
assert executor.execute(rule, {"edge_score": None, "samples": None}).passed is False
PY

echo "VERDICT=EDGE_VALIDATION_ENGINE_V1_READY"
echo "VERDICT=TEST_EDGE_VALIDATION_ENGINE_V1_OK"
SH_TEST

chmod +x scripts/test_edge_validation_engine_v1.sh
scripts/test_edge_validation_engine_v1.sh

echo "VERDICT=BUILD_EDGE_VALIDATION_ENGINE_V1_OK"
