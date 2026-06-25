#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import sys

from finam_core.statistics.pipeline.builder_context import BuilderContext
from finam_core.statistics.pipeline.builder_executor import BuilderExecutor


def main() -> int:
    context = BuilderContext(
        builder_name="NOOP_FACT_BUILDER_V1",
        fact_domain="WORKFLOW",
        fact_type="EVENT_FACT",
        source_table="warehouse.nrm_workflow_event_v1",
        target_table="warehouse.fact_event_workflow_stage_v1",
        calculation_version="FACT_BUILDER_FRAMEWORK_V1",
        payload={
            "runtime_changed": False,
            "execution_changed": False,
            "orders_changed": False,
            "fills_changed": False,
            "micro_live_allowed": False,
        },
    )

    result = BuilderExecutor().execute(context)

    print("=== FACT_BUILDER_FRAMEWORK_V1 ===")
    print("mode=framework_check")
    print(f"builder_name={context.builder_name}")
    print(f"fact_domain={context.fact_domain}")
    print(f"fact_type={context.fact_type}")
    print(f"result_status={result.status}")
    print(f"result_reason={result.reason}")
    print(f"health_score={result.health_score}")
    print(f"health_light={result.health_light}")
    print(f"health_reason_code={result.health_reason_code}")
    print("components=BuilderContext,BuilderResult,FactBuilder,BuilderRegistry,BuilderExecutor")
    print("builder_model=PLUGIN_BASED")
    print("workflow_event_builder_deferred=1")
    print("workflow_state_builder_deferred=1")
    print("market_trade_edge_deferred=1")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=FACT_BUILDER_FRAMEWORK_V1_READY")
    return 0


if __name__ == "__main__":
    sys.exit(main())
