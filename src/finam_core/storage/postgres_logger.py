# -*- coding: utf-8 -*-
"""
PostgresLogger — запись торговых событий в PostgreSQL.
Русский коммент: ошибки логирования не должны ломать торговый pipeline.
"""

from __future__ import annotations

import os
import json
import logging
from dataclasses import asdict, is_dataclass
from datetime import datetime

import psycopg2

LOG = logging.getLogger(__name__)


class PostgresLogger:
    def __init__(self) -> None:
        self.database_url = os.getenv("DATABASE_URL", "").strip()
        self.enabled = bool(self.database_url)

    def _connect(self):
        return psycopg2.connect(self.database_url)

    def _payload(self, obj):
        try:
            if is_dataclass(obj):
                data = asdict(obj)
            elif isinstance(obj, dict):
                data = dict(obj)
            else:
                data = dict(getattr(obj, "__dict__", {}))

            for k, v in list(data.items()):
                if isinstance(v, datetime):
                    data[k] = v.isoformat()

            return json.dumps(data, ensure_ascii=False)
        except Exception:
            return json.dumps({"raw": str(obj)}, ensure_ascii=False)

    def log_fill(self, fill) -> None:
        if not self.enabled:
            return

        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO trades
                            (symbol, side, qty, price, commission, fill_id, origin, payload)
                        VALUES
                            (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                        """,
                        (
                            getattr(fill, "symbol", None),
                            getattr(fill, "side", None),
                            float(getattr(fill, "qty", 0.0) or 0.0),
                            float(getattr(fill, "price", 0.0) or 0.0),
                            float(getattr(fill, "commission", 0.0) or 0.0),
                            getattr(fill, "fill_id", None),
                            getattr(fill, "origin", None),
                            self._payload(fill),
                        ),
                    )
        except Exception as exc:
            LOG.warning("POSTGRES LOG FILL FAILED: %s", exc)
