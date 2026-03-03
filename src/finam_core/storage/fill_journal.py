import os
import json
import hashlib
from datetime import datetime, UTC
from pathlib import Path


class FillJournal:
    def __init__(self, path: str = "storage/fill_wal.jsonl"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._last_hash = "GENESIS"

        # если WAL уже существует — восстановим последний hash
        if self.path.exists():
            self._recover_last_hash()

    # ---------------------------------------------------------
    # INTERNAL: restore last hash from existing WAL
    # ---------------------------------------------------------
    def _recover_last_hash(self):
        last_hash = "GENESIS"

        with self.path.open("r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    last_hash = record.get("hash", last_hash)
                except Exception:
                    break

        self._last_hash = last_hash

    # ---------------------------------------------------------
    # APPEND (bank-grade durable)
    # ---------------------------------------------------------
    def append(self, payload: dict) -> None:
        record = {
            "ts": datetime.now(UTC).isoformat(),
            "payload": payload,
            "prev_hash": self._last_hash,
        }

        raw_for_hash = json.dumps(
            {
                "ts": record["ts"],
                "payload": record["payload"],
                "prev_hash": record["prev_hash"],
            },
            sort_keys=True,
        )

        record_hash = hashlib.sha256(raw_for_hash.encode()).hexdigest()
        record["hash"] = record_hash

        line = json.dumps(record, sort_keys=True)

        with self.path.open("a") as f:
            f.write(line + "\n")
            f.flush()
            os.fsync(f.fileno())  # ← CRITICAL durability

        self._last_hash = record_hash

    # ---------------------------------------------------------
    # READ + VERIFY HASH CHAIN
    # ---------------------------------------------------------
    # ---------------------------------------------------------
    # READ (skip corrupted lines, return payload only)
    # ---------------------------------------------------------
    def read_all(self):
        if not self.path.exists():
            return []

        entries = []

        with self.path.open("r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    # skip corrupted lines
                    continue

                payload = record.get("payload")
                if isinstance(payload, dict):
                    entries.append(payload)

        return entries

    # ---------------------------------------------------------
    # RESET WAL (after snapshot rotation)
    # ---------------------------------------------------------
    def reset(self):
        if not self.path.exists():
            return

        with self.path.open("w") as f:
            f.truncate(0)

        # reset hash chain
        self._last_hash = "GENESIS"