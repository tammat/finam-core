#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/runtime/runtime_policy_mode_resolver.py \
  src/finam_core/runtime/active_policy_reader.py

python - <<'PY'
from finam_core.runtime.active_policy_reader import ActivePolicyDecision
from finam_core.runtime.runtime_policy_mode_resolver import RuntimePolicyModeResolver

resolver = RuntimePolicyModeResolver()

base = resolver.resolve(None)
assert base.selected_mode == "BASE"
assert base.apply_adaptive_risk is False

limited = resolver.resolve(ActivePolicyDecision(
    decision_id="d1",
    objective="balanced",
    selected_mode="LIMITED",
    score=1.0,
    net_pnl=1.0,
    expectancy=1.0,
    winrate=0.5,
    active=True,
))
assert limited.apply_adaptive_risk is True
assert limited.allow_multiplier is True
assert limited.allow_blocking is False

selective = resolver.resolve(ActivePolicyDecision(
    decision_id="d2",
    objective="conservative",
    selected_mode="SELECTIVE",
    score=1.0,
    net_pnl=1.0,
    expectancy=1.0,
    winrate=0.5,
    active=True,
))
assert selective.apply_adaptive_risk is True
assert selective.allow_multiplier is True
assert selective.allow_blocking is True

print("OK: runtime policy mode resolver")
PY
