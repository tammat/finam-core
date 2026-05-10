from __future__ import annotations

import os
import time
from dataclasses import dataclass

import psycopg2

from finam_core.events.dead_letter_replay_service import DeadLetterReplayService


@dataclass(frozen=True)
class DeadLetterAutoReplayTickResult:
    ok: bool
    scanned: int
    replayed: int
    failed: int


class DeadLetterAutoReplayWorker:
    """Русский комментарий: безопасно пытается replay unresolved DLQ events."""

    def __init__(
        self,
        *,
        database_url: str | None = None,
        replay_service: DeadLetterReplayService | None = None,
        interval_sec: float | None = None,
        limit: int | None = None,
    ) -> None:
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if not self.database_url:
            raise RuntimeError("DATABASE_URL is required for DeadLetterAutoReplayWorker")

        self.replay_service = replay_service or DeadLetterReplayService(database_url=self.database_url)
        self.interval_sec = float(
            interval_sec if interval_sec is not None else os.getenv("DLQ_REPLAY_WORKER_INTERVAL_SEC", "60")
        )
        self.limit = int(
            limit if limit is not None else os.getenv("DLQ_REPLAY_WORKER_LIMIT", "10")
        )

    def _connect(self):
        return psycopg2.connect(self.database_url)

    def _load_unresolved_ids(self) -> list[int]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id
                    FROM event_dead_letters
                    WHERE resolved = false
                    ORDER BY id ASC
                    LIMIT %s
                    """,
                    (int(self.limit),),
                )
                rows = cur.fetchall()

        return [int(row[0]) for row in rows]

    def tick(self) -> DeadLetterAutoReplayTickResult:
        ids = self._load_unresolved_ids()

        replayed = 0
        failed = 0

        for dlq_id in ids:
            try:
                result = self.replay_service.replay_one(dlq_id=dlq_id)

                if result.ok:
                    replayed += 1
                    print(
                        f"DLQ_AUTO_REPLAY_OK id={dlq_id} reason={result.reason}",
                        flush=True,
                    )
                else:
                    failed += 1
                    print(
                        f"DLQ_AUTO_REPLAY_SKIP id={dlq_id} reason={result.reason}",
                        flush=True,
                    )

            except Exception as exc:
                failed += 1
                print(
                    f"DLQ_AUTO_REPLAY_FAILED id={dlq_id} error={exc}",
                    flush=True,
                )

        print(
            f"DLQ_AUTO_REPLAY_TICK_OK scanned={len(ids)} replayed={replayed} failed={failed}",
            flush=True,
        )

        return DeadLetterAutoReplayTickResult(
            ok=True,
            scanned=len(ids),
            replayed=replayed,
            failed=failed,
        )

    def run_forever(self) -> None:
        print(
            f"DLQ_AUTO_REPLAY_WORKER_STARTED interval_sec={self.interval_sec} limit={self.limit}",
            flush=True,
        )

        while True:
            self.tick()
            time.sleep(self.interval_sec)


def main() -> None:
    worker = DeadLetterAutoReplayWorker()
    worker.run_forever()


if __name__ == "__main__":
    main()
