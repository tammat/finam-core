from __future__ import annotations

from finam_core.research.futures_regime_governance_repository import (
    FuturesRegimeGovernanceRepository,
)


def main() -> int:
    repo = FuturesRegimeGovernanceRepository()
    repo.migrate()
    saved = repo.rebuild()

    print(
        "FUTURES_REGIME_GOVERNANCE_SUMMARY "
        f"saved={saved}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
