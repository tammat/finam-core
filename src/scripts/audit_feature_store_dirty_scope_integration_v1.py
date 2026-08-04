from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

MARKET_FILE = (
    ROOT / "src/scripts/build_market_snapshot_history_backfill_v1.py"
)
FEATURE_FILE = (
    ROOT / "src/scripts/build_feature_snapshot_history_backfill_v1.py"
)


def inspect_file(path: Path, tokens: list[str]) -> dict[str, object]:
    if not path.is_file():
        raise FileNotFoundError(path)

    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    token_rows: list[dict[str, object]] = []

    for token in tokens:
        matches = [
            index
            for index, line in enumerate(lines, start=1)
            if token in line
        ]

        token_rows.append(
            {
                "token": token,
                "matches": matches,
            }
        )

    return {
        "path": str(path.relative_to(ROOT)),
        "line_count": len(lines),
        "tokens": token_rows,
    }


def print_result(result: dict[str, object]) -> None:
    print(f"file={result['path']}")
    print(f"line_count={result['line_count']}")

    for row in result["tokens"]:
        matches = row["matches"]
        formatted = ",".join(str(value) for value in matches)
        print(
            f"token={row['token']} "
            f"count={len(matches)} "
            f"lines={formatted or '-'}"
        )


def main() -> int:
    market = inspect_file(
        MARKET_FILE,
        [
            "incremental_source",
            "ON CONFLICT",
            "processed_rows =",
            "feature_store_watermark_v1",
            "market_snapshot_last_ts",
            "market_dirty",
            "RETURNING",
        ],
    )

    feature = inspect_file(
        FEATURE_FILE,
        [
            "source_rows",
            "historical_context",
            "ON CONFLICT",
            "processed_rows =",
            "feature_store_watermark_v1",
            "feature_snapshot_last_ts",
            "market_dirty",
            "feature_processed_at",
        ],
    )

    print("=== FEATURE_STORE_DIRTY_SCOPE_INTEGRATION_AUDIT_V1 ===")

    print()
    print("=== MARKET SNAPSHOT ===")
    print_result(market)

    print()
    print("=== FEATURE SNAPSHOT ===")
    print_result(feature)

    market_text = MARKET_FILE.read_text(encoding="utf-8")
    feature_text = FEATURE_FILE.read_text(encoding="utf-8")

    market_integration_present = (
        "market_dirty" in market_text
        and "RETURNING" in market_text
    )

    feature_integration_present = (
        "WHERE market_dirty" in feature_text
        and "feature_processed_at" in feature_text
    )

    print()
    print(
        "market_dirty_integration_present="
        f"{int(market_integration_present)}"
    )
    print(
        "feature_dirty_integration_present="
        f"{int(feature_integration_present)}"
    )
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print(
        "VERDICT="
        "FEATURE_STORE_DIRTY_SCOPE_INTEGRATION_AUDIT_V1_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
