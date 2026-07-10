from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
INVENTORY_REPORT = (
    PROJECT_ROOT
    / "reports"
    / "marketcore_ui_runtime_inventory_v1.txt"
)


@dataclass(frozen=True, slots=True)
class UiRuntimeInventoryFactsV1:
    javascript_typescript_files: int
    css_files: int
    html_template_files: int
    runtime_marker_rows: int
    render_tree_endpoint_reference_rows: int
    ui_runtime_candidate_files: int


def read_metric(report: str, metric_name: str) -> int:
    pattern = re.compile(
        rf"^{re.escape(metric_name)}=(\d+)$",
        re.MULTILINE,
    )
    match = pattern.search(report)

    if match is None:
        raise RuntimeError(
            f"INVENTORY_METRIC_NOT_FOUND:{metric_name}"
        )

    return int(match.group(1))


def load_facts() -> UiRuntimeInventoryFactsV1:
    if not INVENTORY_REPORT.exists():
        raise RuntimeError(
            f"INVENTORY_REPORT_NOT_FOUND:{INVENTORY_REPORT}"
        )

    report = INVENTORY_REPORT.read_text(encoding="utf-8")

    if (
        "VERDICT=MARKETCORE_UI_RUNTIME_INVENTORY_V1_READY"
        not in report
    ):
        raise RuntimeError("INVENTORY_REPORT_NOT_READY")

    return UiRuntimeInventoryFactsV1(
        javascript_typescript_files=read_metric(
            report,
            "javascript_typescript_files",
        ),
        css_files=read_metric(
            report,
            "css_files",
        ),
        html_template_files=read_metric(
            report,
            "html_template_files",
        ),
        runtime_marker_rows=read_metric(
            report,
            "runtime_marker_rows",
        ),
        render_tree_endpoint_reference_rows=read_metric(
            report,
            "render_tree_endpoint_reference_rows",
        ),
        ui_runtime_candidate_files=read_metric(
            report,
            "ui_runtime_candidate_files",
        ),
    )


def determine_runtime_status(
    facts: UiRuntimeInventoryFactsV1,
) -> str:
    if facts.ui_runtime_candidate_files > 0:
        return "EXISTING_RUNTIME_FOUND"

    if facts.javascript_typescript_files > 0:
        return "PARTIAL_RUNTIME_FOUND"

    return "RUNTIME_NOT_FOUND"


def main() -> None:
    facts = load_facts()
    runtime_status = determine_runtime_status(facts)

    endpoints_ready = (
        facts.render_tree_endpoint_reference_rows > 0
    )
    design_system_available = facts.css_files > 0
    legacy_templates_present = facts.html_template_files > 0

    print("======================================================")
    print("MARKETCORE_UI_RUNTIME_INVENTORY_ANALYSIS_V1")
    print("======================================================")

    print()
    print("FACTS")
    print(
        "javascript_typescript_files="
        f"{facts.javascript_typescript_files}"
    )
    print(f"css_files={facts.css_files}")
    print(
        "html_template_files="
        f"{facts.html_template_files}"
    )
    print(
        "runtime_marker_rows="
        f"{facts.runtime_marker_rows}"
    )
    print(
        "render_tree_endpoint_reference_rows="
        f"{facts.render_tree_endpoint_reference_rows}"
    )
    print(
        "ui_runtime_candidate_files="
        f"{facts.ui_runtime_candidate_files}"
    )

    print()
    print("ANALYSIS")
    print(f"ui_runtime_status={runtime_status}")
    print(
        "render_tree_json_endpoints="
        f"{'READY' if endpoints_ready else 'MISSING'}"
    )
    print(
        "existing_design_system_css="
        f"{'AVAILABLE' if design_system_available else 'MISSING'}"
    )
    print(
        "legacy_html_templates="
        f"{'PRESENT' if legacy_templates_present else 'ABSENT'}"
    )

    print()
    print("DECISION")

    if runtime_status == "RUNTIME_NOT_FOUND":
        print("selected_variant=C")
        print("decision=CREATE_UI_RUNTIME_CONTRACT_FIRST")
        print(
            "reason=no_javascript_or_typescript_runtime_exists"
        )
    elif runtime_status == "PARTIAL_RUNTIME_FOUND":
        print("selected_variant=B")
        print("decision=EXTEND_EXISTING_PARTIAL_RUNTIME")
    else:
        print("selected_variant=A")
        print("decision=REUSE_EXISTING_RUNTIME")

    print()
    print("REUSE")
    print(
        "reuse_render_tree_endpoints="
        f"{int(endpoints_ready)}"
    )
    print(
        "reuse_design_system_css="
        f"{int(design_system_available)}"
    )

    print()
    print("DO_NOT_REUSE_AS_RUNTIME")
    print(
        "python_inline_javascript="
        "NOT_UI_RUNTIME"
    )
    print(
        "legacy_html_templates="
        "NOT_RENDER_TREE_RUNTIME"
    )
    print(
        "cli_fetch_functions="
        "NOT_BROWSER_FETCH"
    )

    print()
    print("NEXT_STEP")
    print("MARKETCORE_UI_RUNTIME_CONTRACT_V1")

    print()
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print(
        "VERDICT="
        "MARKETCORE_UI_RUNTIME_INVENTORY_ANALYSIS_V1_READY"
    )


if __name__ == "__main__":
    main()
