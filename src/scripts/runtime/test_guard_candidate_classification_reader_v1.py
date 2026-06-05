#!/usr/bin/env python3
from __future__ import annotations

from finam_core.governance.guard_candidate_classification_reader import GuardCandidateClassificationReader


def main() -> None:
    reader = GuardCandidateClassificationReader()
    rows = reader.load_all()

    block_ready = sum(1 for r in rows.values() if r.classification == "BLOCK_READY")
    research_only = sum(1 for r in rows.values() if r.classification == "RESEARCH_ONLY")
    keep_watch = sum(1 for r in rows.values() if r.classification == "KEEP_WATCH")

    print("=== GUARD CANDIDATE CLASSIFICATION READER V1 ===")
    print(f"ROWS_FOUND={len(rows)}")
    print(f"BLOCK_READY_FOUND={block_ready}")
    print(f"RESEARCH_ONLY_FOUND={research_only}")
    print(f"KEEP_WATCH_FOUND={keep_watch}")

    sample = reader.get(
        symbol="NGN6@RTSX",
        strategy="NG_CONSERVATIVE_BREAKOUT_M1",
        timeframe="M1",
        side="LONG",
        session_bucket="MOEX_DAY",
    )

    if sample is None:
        raise SystemExit("CLASSIFICATION_SAMPLE_NOT_FOUND")

    print(
        "SAMPLE "
        f"symbol={sample.symbol} strategy={sample.strategy} timeframe={sample.timeframe} "
        f"side={sample.side} session={sample.session_bucket} "
        f"classification={sample.classification} reason={sample.reason} "
        f"trades={sample.total_trades} expectancy={sample.expectancy:.8f} "
        f"stop_rate={sample.stop_rate:.4f}"
    )

    if len(rows) <= 0:
        raise SystemExit("CLASSIFICATION_READER_EMPTY")

    if block_ready <= 0:
        raise SystemExit("CLASSIFICATION_READER_NO_BLOCK_READY")

    print("VERDICT=OK")


if __name__ == "__main__":
    main()
