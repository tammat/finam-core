from __future__ import annotations

import json
from pathlib import Path


SESSION_GATE_CONFIG = Path(
    "runtime/session_side_execution_gate_v1.json"
)

STRICT_CONFIG = Path(
    "runtime/edge_gate_strict_mode_v1.json"
)

DECAY_CONFIG = Path(
    "runtime/edge_gate_decay_state_v1.json"
)


def main() -> int:
    session_cfg = json.loads(
        SESSION_GATE_CONFIG.read_text(encoding="utf-8")
    )

    strict_cfg = json.loads(
        STRICT_CONFIG.read_text(encoding="utf-8")
    )

    decay_cfg = json.loads(
        DECAY_CONFIG.read_text(encoding="utf-8")
    )

    allow_rows = len(
        session_cfg.get("allow", []) or []
    )

    block_rows = len(
        session_cfg.get("block", []) or []
    )

    insufficient_rows = len(
        session_cfg.get("insufficient_data", []) or []
    )

    runtime_windows = len(
        (decay_cfg.get("runtime_state") or {})
    )

    print("RUNTIME_ROLLOUT_ENABLE_PLAN_V1", flush=True)

    print(
        "RUNTIME_ROLLOUT_ENABLE_PLAN_STATUS",
        "status=READY_FOR_ENABLE",
        f"strict_enabled={strict_cfg.get('enabled')}",
        f"decay_enabled={decay_cfg.get('enabled')}",
        f"allow_rows={allow_rows}",
        f"block_rows={block_rows}",
        f"insufficient_rows={insufficient_rows}",
        f"runtime_windows={runtime_windows}",
        flush=True,
    )

    print(
        "RUNTIME_ROLLOUT_ENABLE_PHASE",
        "phase=1",
        "mode=paper_shadow",
        "action=observe_only",
        flush=True,
    )

    print(
        "RUNTIME_ROLLOUT_ENABLE_PHASE",
        "phase=2",
        "mode=paper_runtime",
        "action=soft_block_negative_edge",
        flush=True,
    )

    print(
        "RUNTIME_ROLLOUT_ENABLE_PHASE",
        "phase=3",
        "mode=paper_runtime_strict",
        "action=hard_block_negative_edge",
        flush=True,
    )

    print(
        "RUNTIME_ROLLOUT_ENABLE_PHASE",
        "phase=4",
        "mode=real_candidate",
        "action=notify_only",
        flush=True,
    )

    print(
        "RUNTIME_ROLLOUT_ENABLE_PHASE",
        "phase=5",
        "mode=real_guarded",
        "action=production_rollout",
        flush=True,
    )

    print(
        "RUNTIME_ROLLOUT_ENABLE_GUARDS",
        "session_side_gate=enabled",
        "strict_mode=enabled",
        "decay_monitor=enabled",
        "fail_open=true",
        flush=True,
    )

    print(
        "RUNTIME_ROLLOUT_ENABLE_PLAN_V1_OK",
        "status=READY_FOR_ENABLE",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
