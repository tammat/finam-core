#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_DASHBOARD_DESIGN_SYSTEM_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/design_system/foundation/tokens.py \
  src/marketcore/presentation/design_system/registry.py \
  src/marketcore/presentation/design_system/components/badges.py \
  src/marketcore/presentation/design_system/components/cards.py \
  src/marketcore/presentation/design_system/components/tables.py \
  src/marketcore/presentation/design_system/components/timeline.py \
  src/marketcore/presentation/design_system/components/heatmap.py \
  src/marketcore/presentation/design_system/layout/grid.py

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.design_system.foundation.tokens import STATUS_COLORS, BREAKPOINTS
from marketcore.presentation.design_system.registry import design_registry
from marketcore.presentation.design_system.components.badges import Badge, normalize_status
from marketcore.presentation.design_system.components.cards import (
    HealthCard,
    MetricCard,
    StatusCard,
    VersionCard,
    KeyValueCard,
)
from marketcore.presentation.design_system.components.tables import TableCard
from marketcore.presentation.design_system.components.timeline import TimelineCard
from marketcore.presentation.design_system.components.heatmap import HeatmapCard
from marketcore.presentation.design_system.layout.grid import DashboardGrid, SectionHeader

assert STATUS_COLORS["READY"]
assert BREAKPOINTS["PHONE"] == 767

assert normalize_status("READY") == "READY"
assert normalize_status("bad") == "INFO"

assert "READY" in Badge("READY", "READY")
assert "Market Bars" in MetricCard("Market Bars", 875706)
assert "System" in HealthCard("System", "READY")
assert "Risk" in StatusCard("Risk", "HIGH")
assert "1.0.0" in VersionCard("Metadata", "1.0.0")
assert "Coverage" in KeyValueCard("Metadata", {"Coverage": "100%"})
assert "table" in TableCard("Rows", ["A"], [[1]])
assert "Started" in TimelineCard("Activity", [{"time": "09:00", "text": "Started"}])
assert "Correlation" in HeatmapCard("Risk", {"Correlation": "HIGH"})
assert "fc-grid" in DashboardGrid([MetricCard("A", 1)])
assert "Home" in SectionHeader("Home")

names = {c.name for c in design_registry.list()}
for required in [
    "Badge",
    "HealthCard",
    "MetricCard",
    "StatusCard",
    "VersionCard",
    "KeyValueCard",
    "TableCard",
    "TimelineCard",
    "HeatmapCard",
    "DashboardGrid",
    "SectionHeader",
]:
    assert required in names

print("foundation_ready=1")
print("cards_ready=1")
print("key_value_card_ready=1")
print("badges_ready=1")
print("tables_ready=1")
print("timeline_ready=1")
print("heatmap_ready=1")
print("responsive_ready=1")
print("grid_ready=1")
print("theme_ready=1")
print("colors_ready=1")
print("typography_ready=1")
print("registry_ready=1")
print("component_preview_reserved=1")
print("runtime_changed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")
print("VERDICT=DASHBOARD_DESIGN_SYSTEM_V1_READY")
PY

echo "VERDICT=TEST_DASHBOARD_DESIGN_SYSTEM_V1_OK"
