#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export DATABASE_URL="${DATABASE_URL:-postgresql://finam:finam@localhost:5432/finam_core}"

REASON="${1:-manual_operator_freeze}"
SCOPE="${2:-GLOBAL}"
SYMBOL="${3:-}"

python - <<PY
from finam_core.risk.persistent_kill_switch import PersistentKillSwitch

ks = PersistentKillSwitch()

state = ks.activate(
    scope="${SCOPE}",
    symbol="${SYMBOL}" or None,
    reason="${REASON}",
    source="cli",
)

print(
    f"KILL_SWITCH_ON active={state.active} "
    f"scope={state.scope} symbol={state.symbol} reason={state.reason}"
)
PY
