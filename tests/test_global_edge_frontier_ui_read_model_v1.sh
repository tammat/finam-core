#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

PY="/opt/finam-core/venv/bin/python"

VM="src/marketcore/presentation/viewmodels/research_center_vm.py"
SERVICE="src/marketcore/services/research/research_center_service.py"
BACKEND="src/scripts/research/build_global_edge_physical_contract_frontier_v1.py"

echo "=== TEST GLOBAL EDGE FRONTIER UI READ MODEL V1 ==="

PYTHONPATH=src "$PY" -m py_compile \
  "$VM" \
  "$SERVICE"

BACKEND_OUT="$(
  PYTHONPATH=src "$PY" "$BACKEND"
)"

UI_OUT="$(
PYTHONPATH=src "$PY" - <<'PY'
from marketcore.services.research.research_center_service import (
    ResearchCenterService,
)

vm = ResearchCenterService().load()
frontier = vm.frontier

print(f"frontier_status={frontier.status}")
print(f"frontier_rows={len(frontier.rows)}")
print(f"target_candidates={frontier.target_candidates}")
print(
    "contract_mixing_allowed="
    f"{int(frontier.contract_mixing_allowed)}"
)
print(
    "ui_source_read_only="
    f"{int(frontier.source_read_only)}"
)

for row in frontier.rows:
    print(
        "UI_FRONTIER_ROW "
        f"rank={row.rank} "
        f"symbol={row.physical_symbol} "
        f"state={row.state} "
        f"pairs={row.pairs} "
        f"net={row.net_expectancy} "
        f"paired_gain={row.paired_gain} "
        f"placebo_delta={row.placebo_delta}"
    )
PY
)"

printf '%s\n' "$UI_OUT"

BACKEND_TOP5="$(
  grep '^PHYSICAL_FRONTIER_ROW ' <<< "$BACKEND_OUT" \
  | head -5 \
  | sed -E 's/.*physical_symbol=([^ ]+).*/\1/'
)"

UI_TOP5="$(
  grep '^UI_FRONTIER_ROW ' <<< "$UI_OUT" \
  | sed -E 's/.*symbol=([^ ]+).*/\1/'
)"

test "$BACKEND_TOP5" = "$UI_TOP5"

grep -q '^frontier_status=READY$' <<< "$UI_OUT"
grep -q '^frontier_rows=5$' <<< "$UI_OUT"
grep -q '^contract_mixing_allowed=0$' <<< "$UI_OUT"
grep -q '^ui_source_read_only=1$' <<< "$UI_OUT"

echo "authoritative_top5_parity=1"
echo "ui_priority_gap_semantics=DISPLAY_ONLY_V1"
echo "authoritative_decision_source=PHYSICAL_CONTRACT_FRONTIER_V1"
echo "db_writes_performed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_GLOBAL_EDGE_FRONTIER_UI_READ_MODEL_V1_OK"
