from __future__ import annotations

from finam_core.research.futures_context_normalizer import (
    FuturesContextNormalizer,
)


def main() -> int:
    normalizer = FuturesContextNormalizer()
    normalizer.migrate()
    saved = normalizer.rebuild()

    print(
        "FUTURES_CONTEXT_SNAPSHOTS_REBUILT "
        f"saved={saved}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
