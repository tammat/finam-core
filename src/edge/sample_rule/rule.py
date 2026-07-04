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
