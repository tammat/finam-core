#!/usr/bin/env bash
set -euo pipefail

PYTHONPATH=src python - <<'PY'
from finam_core.risk.unified_decision import UnifiedRiskDecision, RiskDecisionRecorder

d1 = UnifiedRiskDecision.allow(
    layer="portfolio_heat",
    symbol="BRM6@RTSX",
    side="BUY",
    qty=1,
    payload={"projected_heat": 0.1},
)
assert d1.allowed is True
assert d1.reason == "ok"
assert d1.to_dict()["payload"]["projected_heat"] == 0.1

d2 = UnifiedRiskDecision.reject(
    layer="kill_switch",
    reason="daily_loss_limit_exceeded",
    symbol="BRM6@RTSX",
    side="SELL",
    qty=1,
)
assert d2.allowed is False
assert d2.reason == "daily_loss_limit_exceeded"

RiskDecisionRecorder().emit(d2)

print("OK unified_risk_decision")
PY
