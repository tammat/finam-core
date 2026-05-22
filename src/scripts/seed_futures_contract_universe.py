from __future__ import annotations

from finam_core.research.futures_contract_universe_repository import (
    FuturesContractUniverseRepository,
)


def main() -> int:
    repo = FuturesContractUniverseRepository()
    repo.migrate()

    contracts = [
        # =========================================================
        # BRENT
        # =========================================================
        ("BR", "BRM6@RTSX", "2026-06-01", 10, "RESEARCH"),
        ("BR", "BRN6@RTSX", "2026-07-01", 20, "RESEARCH"),
        ("BR", "BRQ6@RTSX", "2026-08-01", 30, "RESEARCH"),
        ("BR", "BRU6@RTSX", "2026-09-01", 40, "RESEARCH"),
        ("BR", "BRV6@RTSX", "2026-10-01", 50, "RESEARCH"),
        ("BR", "BRX6@RTSX", "2026-11-01", 60, "RESEARCH"),
        ("BR", "BRZ6@RTSX", "2026-12-01", 70, "RESEARCH"),

        # =========================================================
        # NATURAL GAS
        # =========================================================
        ("NG", "NGK6@RTSX", "2026-05-01", 10, "QUARANTINE"),
        ("NG", "NGM6@RTSX", "2026-06-01", 20, "RESEARCH"),
        ("NG", "NGN6@RTSX", "2026-07-01", 30, "RESEARCH"),
        ("NG", "NGQ6@RTSX", "2026-08-01", 40, "RESEARCH"),
        ("NG", "NGU6@RTSX", "2026-09-01", 50, "RESEARCH"),
        ("NG", "NGV6@RTSX", "2026-10-01", 60, "RESEARCH"),
        ("NG", "NGX6@RTSX", "2026-11-01", 70, "RESEARCH"),
        ("NG", "NGZ6@RTSX", "2026-12-01", 80, "RESEARCH"),

        # =========================================================
        # USD/RUB
        # =========================================================
        ("USD", "USDRUBF@RTSX", "2026-06-01", 10, "RESEARCH"),
        ("USD", "USDRUBG@RTSX", "2026-07-01", 20, "RESEARCH"),
        ("USD", "USDRUBH@RTSX", "2026-08-01", 30, "RESEARCH"),
        ("USD", "USDRUBJ@RTSX", "2026-09-01", 40, "RESEARCH"),
        ("USD", "USDRUBK@RTSX", "2026-10-01", 50, "RESEARCH"),
        ("USD", "USDRUBM@RTSX", "2026-11-01", 60, "RESEARCH"),
        ("USD", "USDRUBN@RTSX", "2026-12-01", 70, "RESEARCH"),
    ]

    for root, contract, expiration, priority, status in contracts:
        repo.upsert_contract(
            root_symbol=root,
            contract_symbol=contract,
            expiration_date=expiration,
            roll_priority=priority,
            status=status,
        )

        print(
            "FUTURES_CONTRACT_UPSERT "
            f"root={root} "
            f"contract={contract} "
            f"expiration={expiration} "
            f"status={status}",
            flush=True,
        )

    print(
        "FUTURES_CONTRACT_UNIVERSE_SEEDED "
        f"contracts={len(contracts)}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
