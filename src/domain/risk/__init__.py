"""
Compatibility shim.

Legacy imports: domain.risk.*
Canonical implementation: finam_core.domain.risk.*

This package should contain *no logic* — only re-exports.
"""
from finam_core.domain.risk.risk_decision import RiskDecision
from finam_core.domain.risk.risk_context import RiskContext
from finam_core.domain.risk.risk_stack import RiskStack
from finam_core.domain.risk.risk_factory import build_risk_stack
