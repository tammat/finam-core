from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


TIMER_UNIT = "finam-ngu6-frozen-day-oos-monitor.timer"
SERVICE_UNIT = "finam-ngu6-frozen-day-oos-monitor.service"

DATASET_VERSION = "NATIVE_FINAM_M5_V1"
OOS3_BOUNDARY = "2026-08-08T12:45:00+00:00"

ROOT = Path(
    os.getenv(
        "FINAM_CORE_ROOT",
        "/opt/finam-core",
    )
)

CONTINUATION_SCRIPT = (
    ROOT
    / "scripts"
    / "research"
    / "continue_native_finam_m5_dataset_v1.py"
)


FREEZE_DIR = (
    ROOT
    / "runtime"
    / "ngu6-frozen-day-oos-inventory-v1"
)


@dataclass(frozen=True, slots=True)
class Ngu6FrozenDayOosEventV1:
    event_type: str
    text: str


@dataclass(frozen=True, slots=True)
class Ngu6FrozenDayOosStatusV1:
    health_code: str

    timer_active: str
    timer_substate: str
    last_trigger: str
    next_trigger: str

    service_result: str
    service_exec_status: str

    dataset_version: str
    dataset_rows: int
    dataset_last: datetime | None
    dataset_age_seconds: int | None
    dataset_freshness: str
    dataset_fingerprint: str

    oos3_boundary: str
    new_completed_day_trades: int
    inventory_frozen: bool
    freeze_artifact_count: int
    latest_freeze_identity_sha256: str
    latest_frozen_trade_count: int
    latest_frozen_at_utc: str
    pnl_revealed: bool
    last_verdict: str

    events: tuple[Ngu6FrozenDayOosEventV1, ...]


def _run(
    args: list[str],
) -> str:
    result = subprocess.run(
        args,
        text=True,
        capture_output=True,
        timeout=5,
        check=False,
    )

    if result.returncode != 0:
        return ""

    return result.stdout


def _systemctl_show(
    unit: str,
    properties: tuple[str, ...],
) -> dict[str, str]:
    args = [
        "systemctl",
        "show",
        unit,
        "--no-pager",
    ]

    for prop in properties:
        args.extend(["-p", prop])

    output = _run(args)

    values: dict[str, str] = {}

    for line in output.splitlines():
        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        values[key] = value

    return values


def _timer_next_trigger() -> str:
    output = _run(
        [
            "systemctl",
            "status",
            TIMER_UNIT,
            "--no-pager",
            "-l",
        ]
    )

    for line in output.splitlines():
        match = re.match(
            r"\s*Trigger:\s*(.+?)\s*$",
            line,
        )

        if match:
            return match.group(1)

    return "UNAVAILABLE"


def _journal_lines() -> list[str]:
    output = _run(
        [
            "journalctl",
            "-u",
            SERVICE_UNIT,
            "-n",
            "400",
            "--no-pager",
            "-o",
            "cat",
        ]
    )

    return output.splitlines()


def _last_value(
    lines: list[str],
    prefix: str,
    default: str,
) -> str:
    for line in reversed(lines):
        stripped = line.strip()

        if stripped.startswith(prefix):
            return stripped[len(prefix):].strip()

    return default


def _int_value(
    value: str,
    default: int = 0,
) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _bool_value(
    value: str,
) -> bool:
    return str(value).strip().upper() in {
        "1",
        "YES",
        "TRUE",
    }


def _journal_fail_closed_events(
    lines: list[str],
) -> tuple[Ngu6FrozenDayOosEventV1, ...]:
    items: list[Ngu6FrozenDayOosEventV1] = []
    seen: set[str] = set()

    for line in reversed(lines):
        stripped = line.strip()

        if "MONITOR_FAIL_CLOSED=YES" not in stripped:
            continue

        if stripped in seen:
            continue

        seen.add(stripped)

        items.append(
            Ngu6FrozenDayOosEventV1(
                event_type="FAIL_CLOSED",
                text=stripped,
            )
        )

        if len(items) >= 10:
            break

    return tuple(items)


def _load_freeze_artifacts() -> list[dict[str, object]]:
    if not FREEZE_DIR.exists():
        return []

    artifacts: list[dict[str, object]] = []

    for path in sorted(
        FREEZE_DIR.glob("inventory_*.json")
    ):
        try:
            raw = path.read_bytes()
            data = json.loads(
                raw.decode("utf-8")
            )

            if not isinstance(data, dict):
                continue

            identity_sha = str(
                data.get("identity_sha256", "")
            )

            expected_name = (
                f"inventory_{identity_sha}.json"
            )

            if (
                not identity_sha
                or path.name != expected_name
            ):
                continue

            if (
                data.get("inventory_frozen")
                is not True
            ):
                continue

            if (
                data.get("pnl_revealed")
                is not False
            ):
                continue

            if (
                data.get("parameter_search")
                is not False
            ):
                continue

            if (
                data.get("strategy_changed")
                is not False
            ):
                continue

            if (
                data.get("dataset_version")
                != DATASET_VERSION
            ):
                continue

            if (
                data.get("oos3_boundary")
                != OOS3_BOUNDARY
            ):
                continue

            trade_identities = data.get(
                "trade_identities"
            )

            if (
                not isinstance(
                    trade_identities,
                    list,
                )
                and not isinstance(
                    trade_identities,
                    tuple,
                )
            ):
                continue

            if not trade_identities:
                continue

            artifacts.append(
                {
                    "path": str(path),
                    "identity_sha256": (
                        identity_sha
                    ),
                    "artifact_sha256": (
                        hashlib.sha256(
                            raw
                        ).hexdigest()
                    ),
                    "frozen_at_utc": str(
                        data.get(
                            "frozen_at_utc",
                            "",
                        )
                    ),
                    "trade_count": len(
                        trade_identities
                    ),
                    "dataset_rows": int(
                        data.get(
                            "dataset_rows",
                            0,
                        )
                    ),
                    "dataset_last": str(
                        data.get(
                            "dataset_last",
                            "",
                        )
                    ),
                }
            )

        except (
            OSError,
            ValueError,
            TypeError,
            json.JSONDecodeError,
        ):
            # UI fail-soft: invalid artifact does not
            # make the entire Research workspace fail.
            continue

    artifacts.sort(
        key=lambda item: (
            str(
                item.get(
                    "frozen_at_utc",
                    "",
                )
            ),
            str(
                item.get(
                    "identity_sha256",
                    "",
                )
            ),
        ),
        reverse=True,
    )

    return artifacts


def _freeze_events(
    artifacts: list[dict[str, object]],
) -> tuple[Ngu6FrozenDayOosEventV1, ...]:
    items: list[Ngu6FrozenDayOosEventV1] = []

    for artifact in artifacts[:10]:
        items.append(
            Ngu6FrozenDayOosEventV1(
                event_type="INVENTORY_FROZEN",
                text=(
                    "frozen_at="
                    f"{artifact['frozen_at_utc']} "
                    "trades="
                    f"{artifact['trade_count']} "
                    "identity_sha256="
                    f"{artifact['identity_sha256']} "
                    "artifact_sha256="
                    f"{artifact['artifact_sha256']}"
                ),
            )
        )

    return tuple(items)


def _merge_events(
    freeze_events: tuple[
        Ngu6FrozenDayOosEventV1,
        ...
    ],
    journal_events: tuple[
        Ngu6FrozenDayOosEventV1,
        ...
    ],
) -> tuple[Ngu6FrozenDayOosEventV1, ...]:
    return (
        freeze_events
        + journal_events
    )[:10]


def _load_canonical_dataset():
    spec = importlib.util.spec_from_file_location(
        "marketcore_ui_ngu6_oos_dataset_v1",
        CONTINUATION_SCRIPT,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            "ngu6_oos_dataset_module_import_failed"
        )

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    bars = module.load_persisted_dataset_snapshot()
    reference = module.load_reference_builder()

    return (
        bars,
        reference.dataset_fingerprint(bars),
    )


def resolve_ngu6_frozen_day_oos_status_v1(
) -> Ngu6FrozenDayOosStatusV1:
    timer = _systemctl_show(
        TIMER_UNIT,
        (
            "ActiveState",
            "SubState",
            "LastTriggerUSec",
        ),
    )

    service = _systemctl_show(
        SERVICE_UNIT,
        (
            "Result",
            "ExecMainStatus",
        ),
    )

    lines = _journal_lines()

    last_verdict = _last_value(
        lines,
        "VERDICT=",
        "UNAVAILABLE",
    )

    new_completed = _int_value(
        _last_value(
            lines,
            "NEW_COMPLETED_DAY_TRADES=",
            "0",
        )
    )

    freeze_artifacts = (
        _load_freeze_artifacts()
    )

    inventory_frozen = bool(
        freeze_artifacts
    )

    latest_freeze = (
        freeze_artifacts[0]
        if freeze_artifacts
        else None
    )

    freeze_artifact_count = len(
        freeze_artifacts
    )

    latest_freeze_identity_sha256 = (
        str(
            latest_freeze[
                "identity_sha256"
            ]
        )
        if latest_freeze
        else "NONE"
    )

    latest_frozen_trade_count = (
        int(
            latest_freeze[
                "trade_count"
            ]
        )
        if latest_freeze
        else 0
    )

    latest_frozen_at_utc = (
        str(
            latest_freeze[
                "frozen_at_utc"
            ]
        )
        if latest_freeze
        else "NONE"
    )

    pnl_revealed = _bool_value(
        _last_value(
            lines,
            "PNL_REVEALED=",
            "0",
        )
    )

    dataset_rows = 0
    dataset_last = None
    dataset_fingerprint = "UNAVAILABLE"
    dataset_age_seconds = None
    dataset_freshness = "UNAVAILABLE"

    try:
        bars, dataset_fingerprint = (
            _load_canonical_dataset()
        )

        dataset_rows = len(bars)

        if bars:
            dataset_last = bars[-1].ts

            now = datetime.now(timezone.utc)

            dataset_age_seconds = max(
                0,
                int(
                    (
                        now
                        - dataset_last.astimezone(
                            timezone.utc
                        )
                    ).total_seconds()
                ),
            )

            dataset_freshness = (
                "CURRENT"
                if dataset_age_seconds <= 7200
                else "STALE"
            )

    except Exception:
        dataset_freshness = "UNAVAILABLE"

    timer_active = timer.get(
        "ActiveState",
        "unknown",
    )

    timer_substate = timer.get(
        "SubState",
        "unknown",
    )

    service_result = service.get(
        "Result",
        "unknown",
    )

    service_exec_status = service.get(
        "ExecMainStatus",
        "unknown",
    )

    healthy = (
        timer_active == "active"
        and timer_substate == "waiting"
        and service_result in {
            "success",
            "",
        }
        and service_exec_status in {
            "0",
            "",
        }
        and last_verdict
        in {
            "NO_NEW_FROZEN_DAY_TRADES",
            "NEW_FROZEN_DAY_INVENTORY_READY",
        }
        and not pnl_revealed
    )

    health_code = (
        "HEALTHY"
        if healthy
        else "ATTENTION"
    )

    return Ngu6FrozenDayOosStatusV1(
        health_code=health_code,

        timer_active=timer_active,
        timer_substate=timer_substate,
        last_trigger=timer.get(
            "LastTriggerUSec",
            "UNAVAILABLE",
        ),
        next_trigger=_timer_next_trigger(),

        service_result=service_result,
        service_exec_status=service_exec_status,

        dataset_version=DATASET_VERSION,
        dataset_rows=dataset_rows,
        dataset_last=dataset_last,
        dataset_age_seconds=dataset_age_seconds,
        dataset_freshness=dataset_freshness,
        dataset_fingerprint=dataset_fingerprint,

        oos3_boundary=OOS3_BOUNDARY,
        new_completed_day_trades=new_completed,
        inventory_frozen=inventory_frozen,
        freeze_artifact_count=(
            freeze_artifact_count
        ),
        latest_freeze_identity_sha256=(
            latest_freeze_identity_sha256
        ),
        latest_frozen_trade_count=(
            latest_frozen_trade_count
        ),
        latest_frozen_at_utc=(
            latest_frozen_at_utc
        ),
        pnl_revealed=pnl_revealed,
        last_verdict=last_verdict,

        events=_merge_events(
            _freeze_events(
                freeze_artifacts
            ),
            _journal_fail_closed_events(
                lines
            ),
        ),
    )
