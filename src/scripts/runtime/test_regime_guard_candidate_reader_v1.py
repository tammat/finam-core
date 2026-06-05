#!/usr/bin/env python3
from __future__ import annotations

from finam_core.governance.regime_guard_candidate_reader import RegimeGuardCandidateReader


def main() -> None:
    reader = RegimeGuardCandidateReader()
    rows = reader.load()

    print("=== REGIME GUARD CANDIDATE READER V1 ===")
    print(f"ROWS_FOUND={len(rows)}")

    block = sum(1 for x in rows.values() if x.classification == "BLOCK_CANDIDATE")
    allow = sum(1 for x in rows.values() if x.classification == "ALLOW_CANDIDATE")
    weak = sum(1 for x in rows.values() if x.classification == "INSUFFICIENT_SAMPLE")

    print(f"BLOCK_CANDIDATE_FOUND={block}")
    print(f"ALLOW_CANDIDATE_FOUND={allow}")
    print(f"INSUFFICIENT_SAMPLE_FOUND={weak}")

    if rows:
        sample = next(iter(rows.values()))
        print(
            f"SAMPLE scope={sample.scope} key={sample.regime_key} "
            f"classification={sample.classification} reason={sample.reason} "
            f"trades={sample.trades} expectancy={sample.expectancy:.8f}"
        )

    print("VERDICT=OK")


if __name__ == "__main__":
    main()
