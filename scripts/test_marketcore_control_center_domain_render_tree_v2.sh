#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

renderer="src/marketcore/presentation/workspace_v2/renderer/control_center_v2_domain_renderer.py"

test -f "$renderer"

PYTHONPYCACHEPREFIX=/tmp/marketcore_control_center_domain_render_tree_v2 \
PYTHONPATH=src \
python3 -m py_compile "$renderer"

if grep -nE 'ThemeResolver|UiI18nResolver|"class"|"style"|"href"|data-|action_target' "$renderer"
then
  echo "CONTROL_CENTER_V2_PLATFORM_OR_LEGACY_ACTION_FOUND"
  exit 1
fi

PYTHONPATH=src python3 - <<'PY'
from datetime import datetime, timezone

from marketcore.presentation.render_tree.v2 import render_document_v2_to_json, validate_render_document_v2
from marketcore.presentation.workspace_v2.renderer.control_center_v2_domain_renderer import render_control_center_domain_v2
from marketcore.presentation.workspace_v2.viewmodel.control_center_v2_viewmodel import (
    ControlCenterTrafficLightV2,
    ControlCenterV2ViewModel,
    RelationshipCandidateV2,
    SignalFunnelStageV2,
    SignalLossReasonV2,
)


now = datetime(2026, 7, 15, 16, 0, tzinfo=timezone.utc)
view_model = ControlCenterV2ViewModel(
    title="legacy title",
    subtitle="legacy subtitle",
    traffic_lights=(ControlCenterTrafficLightV2("edge", "legacy label", "OOS PASS: 0", "BLOCKED", "/legacy/action", "research.control.traffic.edge.value", (("passed", 0),)),),
    relationship_summary={},
    relationships=(RelationshipCandidateV2("family", "A", "B", "ALL", "MAIN", 10, 1.2, 3.0, 80.0, "PASS", "OK"),),
    funnel_stages=(SignalFunnelStageV2("Candidate", 10, "50%", "OK"),),
    loss_reasons=(SignalLossReasonV2("DATA", "Data", 2, "Refresh", "WARNING", "/legacy/refresh"),),
    funnel_comparable=True,
    shadow_summary={"closed": 5, "net_pnl": -10.5},
    execution_quality=(),
    execution_variants=(),
    volatility_analysis=({"regime": "HIGH", "duration_hours": 2.5},),
    risk_analysis=(),
    entry_analysis=(),
    market_prerequisites=(),
    exit_analysis=(),
    block_analysis=(),
    shadow_requirements=(),
)

document = render_control_center_domain_v2(view_model, generated_at=now)
validate_render_document_v2(document)
payload = render_document_v2_to_json(document)

assert '"timezone_code":"Europe/Moscow"' in payload
assert '"format_code":"DURATION_HM","value":9000' in payload
assert "стратегия_заблокирована_по_статистике" not in payload
assert "/legacy/action" not in payload
assert "/legacy/refresh" not in payload
assert "legacy title" not in payload
assert "legacy subtitle" not in payload
assert "OOS PASS: 0" not in payload
assert '"class"' not in payload
assert '"style"' not in payload
assert '"href"' not in payload

print("control_center_v2_schema=OK")
print("raw_analytics=OK")
print("duration_hours_normalized=OK")
print("legacy_action_urls_exported=0")
print("platform_semantics=0")
PY

echo "state_changing_actions_enabled=0"
echo "runtime_switch=0"
echo "service_restart=0"
echo "VERDICT=TEST_MARKETCORE_CONTROL_CENTER_DOMAIN_RENDER_TREE_V2_OK"
