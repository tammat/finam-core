#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
TEMPLATE = ROOT / "src/ui/templates/v3_dashboard.html"

MARKER = "OPERATIONAL_DASHBOARD_METRICS_SUMMARY_V1"
INSERT_AFTER = """  {% elif operational_positions_v1 %}
"""

METRICS_BLOCK = r'''
    <!-- OPERATIONAL_DASHBOARD_METRICS_SUMMARY_V1 BEGIN -->
    {% set current_position_count = namespace(value=0) %}
    {% set clean_flat_count = namespace(value=0) %}
    {% set quarantine_count = namespace(value=0) %}
    {% set excluded_count = namespace(value=0) %}
    {% set current_net_qty_sum = namespace(value=0) %}

    {% for row in operational_positions_v1 %}
      {% if row.operational_status == 'OPEN_PAPER_LONG_TAIL' %}
        {% set current_position_count.value = current_position_count.value + 1 %}
        {% set current_net_qty_sum.value = current_net_qty_sum.value + row.net_qty %}
      {% elif row.operational_status == 'CLEAN_V3_FLAT' %}
        {% set clean_flat_count.value = clean_flat_count.value + 1 %}
      {% elif row.operational_status == 'QUARANTINE_CONTAMINATED_TAIL' %}
        {% set quarantine_count.value = quarantine_count.value + 1 %}
      {% elif row.operational_status == 'EXCLUDE_HISTORICAL_TAIL' %}
        {% set excluded_count.value = excluded_count.value + 1 %}
      {% endif %}
    {% endfor %}

    <div id="operational-metrics-summary-v1" style="display: grid; grid-template-columns: repeat(5, minmax(120px, 1fr)); gap: 10px; margin: 12px 0 20px 0;">
      <div style="padding: 10px; border: 1px solid #ccc; border-radius: 6px;">
        <div style="font-size: 12px;">Текущих paper-позиций</div>
        <div style="font-size: 20px; font-weight: 600;">{{ current_position_count.value }}</div>
      </div>
      <div style="padding: 10px; border: 1px solid #ccc; border-radius: 6px;">
        <div style="font-size: 12px;">Clean V3 flat</div>
        <div style="font-size: 20px; font-weight: 600;">{{ clean_flat_count.value }}</div>
      </div>
      <div style="padding: 10px; border: 1px solid #ccc; border-radius: 6px;">
        <div style="font-size: 12px;">В карантине</div>
        <div style="font-size: 20px; font-weight: 600;">{{ quarantine_count.value }}</div>
      </div>
      <div style="padding: 10px; border: 1px solid #ccc; border-radius: 6px;">
        <div style="font-size: 12px;">Исключено</div>
        <div style="font-size: 20px; font-weight: 600;">{{ excluded_count.value }}</div>
      </div>
      <div style="padding: 10px; border: 1px solid #ccc; border-radius: 6px;">
        <div style="font-size: 12px;">Текущий net qty</div>
        <div style="font-size: 20px; font-weight: 600;">{{ current_net_qty_sum.value }}</div>
      </div>
    </div>
    <!-- OPERATIONAL_DASHBOARD_METRICS_SUMMARY_V1 END -->
'''


def main() -> int:
    print("=== OPERATIONAL DASHBOARD METRICS SUMMARY V1 ===")
    print("mode=patch_template")
    print("runtime_allow=0")
    print("execution_enabled=0")

    if not TEMPLATE.exists():
        raise SystemExit(f"FAIL: template not found: {TEMPLATE}")

    text = TEMPLATE.read_text()

    if MARKER in text:
        print(f"TEMPLATE_ALREADY_PATCHED={TEMPLATE}")
        print("OPERATIONAL_DASHBOARD_METRICS_SUMMARY_V1_OK")
        return 0

    if INSERT_AFTER not in text:
        raise SystemExit("FAIL: operational_positions_v1 block marker not found")

    text = text.replace(INSERT_AFTER, INSERT_AFTER + METRICS_BLOCK, 1)
    TEMPLATE.write_text(text)

    print(f"TEMPLATE_PATCHED={TEMPLATE}")
    print("OPERATIONAL_DASHBOARD_METRICS_SUMMARY_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
