from __future__ import annotations

import argparse
import os

import psycopg

from finam_core.analytics.statistics_repository import build_psycopg_url


TEST_PREFIX = "test-runtime-guard-%"


def cleanup(dry_run: bool) -> int:
    database_url = os.getenv("DATABASE_URL") or build_psycopg_url()

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            if dry_run:
                cur.execute("""
                select count(*)
                from runtime_guard_signal_registry_v1
                where signal_id like %s
                """, (TEST_PREFIX,))
                count = int(cur.fetchone()[0])
                print(
                    f"RUNTIME_GUARD_REGISTRY_CLEANUP_V1_DRY_RUN matched={count}",
                    flush=True,
                )
                return count

            cur.execute("""
            delete from runtime_guard_signal_registry_v1
            where signal_id like %s
            """, (TEST_PREFIX,))
            deleted = cur.rowcount

        conn.commit()

    print(
        f"RUNTIME_GUARD_REGISTRY_CLEANUP_V1_OK deleted={deleted}",
        flush=True,
    )
    return int(deleted or 0)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    cleanup(dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
