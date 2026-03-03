from pathlib import Path
import json
import os
import tempfile
from typing import Optional, Dict


# Schema version for snapshot files
SCHEMA_VERSION = 1



class SnapshotRepository:
    def __init__(self, file_path: str = "data/snapshot.json"):
        self.path = Path(file_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> Optional[Dict]:
        if not self.path.exists():
            return None

        with self.path.open("r") as f:
            payload = json.load(f)

            if "schema" not in payload:
                # backward compatibility (v0 snapshots)
                return payload

            if payload.get("schema") != SCHEMA_VERSION:
                raise ValueError(f"Unsupported snapshot schema: {payload.get('schema')}")

            return payload.get("data")

    def save(self, snapshot: Dict):
        """
        Atomic snapshot commit protocol:
        1) Wrap snapshot with schema + data
        2) Write to temporary file
        3) fsync
        4) Atomic replace
        """

        payload = {
            "schema": SCHEMA_VERSION,
            "data": snapshot,
        }

        tmp_path = self.path.with_suffix(".tmp")

        # Phase 1 — write tmp
        with tmp_path.open("w") as f:
            json.dump(payload, f)
            f.flush()
            os.fsync(f.fileno())

        # Phase 2 — atomic rename (POSIX atomic)
        os.replace(tmp_path, self.path)

    def save_atomic(self, snapshot: dict):
        tmp_path = self.path.with_suffix(".tmp")

        with tmp_path.open("w") as f:
            json.dump(snapshot, f)
            f.flush()
            os.fsync(f.fileno())

        tmp_path.replace(self.path)  # atomic rename

    def fsync_dir(self):
        dir_fd = os.open(str(self.path.parent), os.O_DIRECTORY)
        os.fsync(dir_fd)
        os.close(dir_fd)