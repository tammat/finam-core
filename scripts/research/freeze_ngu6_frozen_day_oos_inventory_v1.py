from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


VERSION = "NGU6_FROZEN_DAY_OOS_INVENTORY_FREEZER_V1"

OOS3_BOUNDARY = "2026-08-08T12:45:00+00:00"

ROOT = Path(
    os.getenv(
        "FINAM_CORE_ROOT",
        "/opt/finam-core",
    )
)

FREEZE_DIR = (
    ROOT
    / "runtime"
    / "ngu6-frozen-day-oos-inventory-v1"
)


class FreezeContractError(RuntimeError):
    pass


def parse_monitor_output(
    path: Path,
) -> dict[str, object]:
    lines = path.read_text(
        encoding="utf-8"
    ).splitlines()

    def last_value(
        prefix: str,
        *,
        required: bool = True,
    ) -> str | None:
        for line in reversed(lines):
            if line.startswith(prefix):
                return line[len(prefix):].strip()

        if required:
            raise FreezeContractError(
                f"required_field_missing:{prefix}"
            )

        return None

    verdict = last_value("VERDICT=")

    if verdict != "NEW_FROZEN_DAY_INVENTORY_READY":
        raise FreezeContractError(
            f"unexpected_verdict:{verdict}"
        )

    pnl_revealed = last_value(
        "PNL_REVEALED="
    )

    if pnl_revealed != "0":
        raise FreezeContractError(
            "pnl_revealed_contract_violation"
        )

    raw_identities = [
        line[len("TRADE_IDENTITY="):].strip()
        for line in lines
        if line.startswith("TRADE_IDENTITY=")
    ]

    if not raw_identities:
        raise FreezeContractError(
            "trade_identity_inventory_empty"
        )

    if len(raw_identities) != len(
        set(raw_identities)
    ):
        raise FreezeContractError(
            "duplicate_trade_identity"
        )

    # Canonical order independent of stdout ordering.
    identities = tuple(
        sorted(raw_identities)
    )

    new_completed = int(
        last_value(
            "NEW_COMPLETED_DAY_TRADES="
        )
    )

    if new_completed != len(identities):
        raise FreezeContractError(
            "trade_identity_count_mismatch:"
            f"declared={new_completed}:"
            f"actual={len(identities)}"
        )

    return {
        "freezer_version": VERSION,
        "frozen_at_utc": (
            datetime.now(timezone.utc)
            .isoformat()
        ),
        "symbol": "NGU6@RTSX",
        "timeframe": "M5",
        "dataset_version": (
            "NATIVE_FINAM_M5_V1"
        ),
        "dataset_rows": int(
            last_value("DATASET_ROWS=")
        ),
        "dataset_last": last_value(
            "DATASET_LAST="
        ),
        "oos3_boundary": OOS3_BOUNDARY,
        "new_completed_day_trades": (
            new_completed
        ),
        "trade_identities": identities,
        "inventory_frozen": True,
        "pnl_revealed": False,
        "parameter_search": False,
        "strategy_changed": False,
        "monitor_verdict": verdict,
    }


def canonical_identity_payload(
    inventory: dict[str, object],
) -> bytes:
    payload = {
        "symbol": inventory["symbol"],
        "timeframe": inventory["timeframe"],
        "dataset_version": (
            inventory["dataset_version"]
        ),
        "oos3_boundary": (
            inventory["oos3_boundary"]
        ),
        "trade_identities": (
            inventory["trade_identities"]
        ),
    }

    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def freeze(
    monitor_output: Path,
) -> tuple[str, Path, str]:
    inventory = parse_monitor_output(
        monitor_output
    )

    identity_sha = hashlib.sha256(
        canonical_identity_payload(inventory)
    ).hexdigest()

    inventory["identity_sha256"] = (
        identity_sha
    )

    serialized = (
        json.dumps(
            inventory,
            sort_keys=True,
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    ).encode("utf-8")

    artifact_sha = hashlib.sha256(
        serialized
    ).hexdigest()

    FREEZE_DIR.mkdir(
        parents=True,
        exist_ok=True,
        mode=0o755,
    )

    destination = (
        FREEZE_DIR
        / f"inventory_{identity_sha}.json"
    )

    if destination.exists():
        existing = destination.read_bytes()

        existing_data = json.loads(
            existing.decode("utf-8")
        )

        if (
            existing_data.get(
                "identity_sha256"
            )
            != identity_sha
        ):
            raise FreezeContractError(
                "existing_inventory_identity_mismatch"
            )

        return (
            "ALREADY_FROZEN",
            destination,
            hashlib.sha256(
                existing
            ).hexdigest(),
        )

    fd, temp_name = tempfile.mkstemp(
        prefix=".inventory.",
        suffix=".tmp",
        dir=FREEZE_DIR,
    )

    temp_path = Path(temp_name)

    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(serialized)
            handle.flush()
            os.fsync(handle.fileno())

        # Atomic create semantics: never overwrite.
        try:
            os.link(
                temp_path,
                destination,
            )
        except FileExistsError:
            return (
                "ALREADY_FROZEN",
                destination,
                hashlib.sha256(
                    destination.read_bytes()
                ).hexdigest(),
            )

        dir_fd = os.open(
            FREEZE_DIR,
            os.O_RDONLY,
        )

        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)

    finally:
        temp_path.unlink(
            missing_ok=True
        )

    actual = hashlib.sha256(
        destination.read_bytes()
    ).hexdigest()

    if actual != artifact_sha:
        raise FreezeContractError(
            "post_freeze_sha256_mismatch"
        )

    return (
        "CREATED",
        destination,
        artifact_sha,
    )


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: "
            "freeze_ngu6_frozen_day_oos_inventory_v1.py "
            "<monitor-output>",
            file=sys.stderr,
        )
        return 2

    status, path, sha = freeze(
        Path(sys.argv[1])
    )

    print(f"FREEZE_STATUS={status}")
    print(f"FREEZE_PATH={path}")
    print(f"FREEZE_SHA256={sha}")
    print("INVENTORY_FROZEN=1")
    print("PNL_REVEALED=0")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
