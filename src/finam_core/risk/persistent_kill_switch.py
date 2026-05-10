from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import psycopg2
import psycopg2.extras


@dataclass(frozen=True)
class KillSwitchState:
    active: bool
    scope: str
    symbol: str | None
    reason: str
    source: str


class PersistentKillSwitch:
    """Русский комментарий: persistent kill switch хранит freeze-состояние в PostgreSQL."""

    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if not self.database_url:
            raise RuntimeError("DATABASE_URL is required for PersistentKillSwitch")

    def _connect(self):
        return psycopg2.connect(self.database_url)

    def ensure_schema(self) -> None:
        with open("sql/20260510_persistent_kill_switch.sql", "r", encoding="utf-8") as f:
            sql = f.read()

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)

    def activate(
        self,
        *,
        reason: str,
        scope: str = "GLOBAL",
        symbol: str | None = None,
        source: str = "system",
    ) -> KillSwitchState:
        self.ensure_schema()

        scope = str(scope or "GLOBAL").upper()
        symbol_value = symbol if symbol else None

        with self._connect() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    INSERT INTO persistent_kill_switch (
                        scope, symbol, active, reason, source, created_at, updated_at
                    )
                    VALUES (%s, %s, true, %s, %s, now(), now())
                    ON CONFLICT (scope, COALESCE(symbol, ''))
                    DO UPDATE SET
                        active = true,
                        reason = EXCLUDED.reason,
                        source = EXCLUDED.source,
                        updated_at = now()
                    RETURNING active, scope, symbol, reason, source
                    """,
                    (scope, symbol_value, reason, source),
                )
                row = cur.fetchone()

        return KillSwitchState(**dict(row))

    def deactivate(
        self,
        *,
        scope: str = "GLOBAL",
        symbol: str | None = None,
        reason: str = "manual_clear",
        source: str = "operator",
    ) -> KillSwitchState:
        self.ensure_schema()

        scope = str(scope or "GLOBAL").upper()
        symbol_value = symbol if symbol else None

        with self._connect() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    INSERT INTO persistent_kill_switch (
                        scope, symbol, active, reason, source, created_at, updated_at
                    )
                    VALUES (%s, %s, false, %s, %s, now(), now())
                    ON CONFLICT (scope, COALESCE(symbol, ''))
                    DO UPDATE SET
                        active = false,
                        reason = EXCLUDED.reason,
                        source = EXCLUDED.source,
                        updated_at = now()
                    RETURNING active, scope, symbol, reason, source
                    """,
                    (scope, symbol_value, reason, source),
                )
                row = cur.fetchone()

        return KillSwitchState(**dict(row))

    def get_state(self, *, scope: str = "GLOBAL", symbol: str | None = None) -> KillSwitchState:
        self.ensure_schema()

        scope = str(scope or "GLOBAL").upper()
        symbol_value = symbol if symbol else None

        with self._connect() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT active, scope, symbol, reason, source
                    FROM persistent_kill_switch
                    WHERE scope = %s AND COALESCE(symbol, '') = COALESCE(%s, '')
                    ORDER BY updated_at DESC
                    LIMIT 1
                    """,
                    (scope, symbol_value),
                )
                row = cur.fetchone()

        if not row:
            return KillSwitchState(
                active=False,
                scope=scope,
                symbol=symbol_value,
                reason="not_set",
                source="system",
            )

        return KillSwitchState(**dict(row))

    def is_active(self, *, symbol: str | None = None) -> bool:
        global_state = self.get_state(scope="GLOBAL")
        if global_state.active:
            return True

        if symbol:
            symbol_state = self.get_state(scope="SYMBOL", symbol=symbol)
            return symbol_state.active

        return False

    def assert_not_active(self, *, symbol: str | None = None) -> None:
        if self.is_active(symbol=symbol):
            state = self.get_state(scope="GLOBAL")
            if symbol and not state.active:
                state = self.get_state(scope="SYMBOL", symbol=symbol)
            raise RuntimeError(
                f"PERSISTENT_KILL_SWITCH_ACTIVE scope={state.scope} "
                f"symbol={state.symbol} reason={state.reason}"
            )
