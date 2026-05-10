#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export DATABASE_URL="${DATABASE_URL:-postgresql://finam:finam@localhost:5432/finam_core}"

SCOPE="${1:-GLOBAL}"
SYMBOL="${2:-}"

python - <<PY
from finam_core.risk.persistent_kill_switch import PersistentKillSwitch

ks = PersistentKillSwitch()

state = ks.get_state(
    scope="${SCOPE}",
    symbol="${SYMBOL}" or None,
)

print(
    f"KILL_SWITCH_STATUS active={state.active} "
    f"scope={state.scope} symbol={state.symbol} "
    f"reason={state.reason} source={state.source}"
)
PY
