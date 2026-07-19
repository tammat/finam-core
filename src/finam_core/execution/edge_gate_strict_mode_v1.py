from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class EdgeGateStrictDecisionV1:
    allowed: bool
    reason: str
    expectancy_points: float | None
    closed_trades: int | None
    matched_symbol: str | None = None
    matched_strategy: str | None = None
    session_name: str | None = None
    hour_msk: int | None = None


class EdgeGateStrictModeV1:
    """
    Русский комментарий:
    Строгий runtime-фильтр поверх session-side gate.
    Пропускает только окна с положительным expectancy и достаточной выборкой.
    """

    def __init__(
        self,
        config_path: str | Path = "runtime/edge_gate_strict_mode_v1.json",
        *,
        connection_factory=None,
        reload_seconds: float = 60.0,
    ) -> None:
        self.config_path = Path(config_path)
        self.config = json.loads(self.config_path.read_text(encoding="utf-8"))

        self.enabled = bool(self.config.get("enabled", False))
        self.threshold = float(self.config.get("strict_expectancy_threshold", 0.0))
        self.min_closed_trades = int(self.config.get("strict_min_closed_trades", 30))
        self.connection_factory = connection_factory
        self.reload_seconds = max(5.0, float(reload_seconds))
        self._last_db_load_monotonic = 0.0
        self._db_rows: list[dict] = []

        self.rows: list[dict] = []

        for src in self.config.get("sources", []):
            p = Path(src)
            if not p.exists():
                continue

            data = json.loads(p.read_text(encoding="utf-8"))

            self.rows.extend(data.get("allow", []))
            self.rows.extend(data.get("block", []))
            self.rows.extend(data.get("insufficient_data", []))

    @staticmethod
    def session_name_for_hour(hour_msk: int) -> str:
        if 0 <= hour_msk <= 5:
            return "азиатская_сессия"
        if 6 <= hour_msk <= 11:
            return "утро_мск"
        if 12 <= hour_msk <= 15:
            return "московская_середина"
        if 16 <= hour_msk <= 20:
            return "вечерняя_сессия"
        return "ночь"

    def _load_db_rows_if_due(self) -> None:
        if not callable(self.connection_factory):
            return
        now = time.monotonic()
        if now - self._last_db_load_monotonic < self.reload_seconds:
            return
        self._last_db_load_monotonic = now
        conn = self.connection_factory()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT normalized_symbol,strategy,entry_side,session_name,
                              closed_trades,expectancy_after_costs AS expectancy_points,
                              rule_action
                       FROM analytics.edge_strict_rule_v2
                       WHERE enabled"""
                )
                columns = [item[0] for item in cur.description]
                self._db_rows = [dict(zip(columns, row)) for row in cur.fetchall()]
                cur.execute(
                    """SELECT min_closed_trades,min_expectancy_after_costs,reload_seconds
                       FROM analytics.edge_strict_rule_policy_v2
                       WHERE enabled ORDER BY updated_at DESC LIMIT 1"""
                )
                policy = cur.fetchone()
                if policy:
                    self.min_closed_trades = int(policy[0])
                    self.threshold = float(policy[1])
                    self.reload_seconds = max(5.0, float(policy[2]))
        except Exception:
            # Таблица появляется миграцией; до неё остаётся безопасный JSON fallback.
            self._db_rows = []
        finally:
            conn.close()

    @staticmethod
    def _current_hour_msk() -> int:
        return int(datetime.now(tz=ZoneInfo("Europe/Moscow")).hour)

    @staticmethod
    def _symbol_matches(row_symbol: str, symbol: str) -> bool:
        if row_symbol == "BR_CONT" and symbol.startswith("BR") and symbol.endswith("@RTSX"):
            return True
        if row_symbol == "NG_CONT" and symbol.startswith("NG") and symbol.endswith("@RTSX"):
            return True
        if row_symbol == "USDRUB_CONT" and symbol.startswith("USDRUB"):
            return True
        return (
            row_symbol == symbol
            or (
                row_symbol == "BR_ROLLING@RTSX"
                and symbol.startswith("BR")
                and symbol.endswith("@RTSX")
            )
        )

    def evaluate(
        self,
        *,
        symbol: str,
        strategy: str | None = None,
        side: str,
        session_name: str | None = None,
        hour_msk: int | None = None,
    ) -> EdgeGateStrictDecisionV1:
        if hour_msk is None:
            hour_msk = self._current_hour_msk()

        if not self.enabled:
            return EdgeGateStrictDecisionV1(
                allowed=True,
                reason="strict_mode_disabled",
                expectancy_points=None,
                closed_trades=None,
                hour_msk=hour_msk,
            )

        side_norm = str(side or "").upper().strip()
        strategy_norm = str(strategy or "").upper().strip()
        session_norm = str(session_name or self.session_name_for_hour(hour_msk)).strip()
        self._load_db_rows_if_due()

        matched: dict | None = None

        rows = self._db_rows if self._db_rows else self.rows
        using_db_rows = bool(self._db_rows)
        for row in rows:
            row_symbol = str(row.get("normalized_symbol") or row.get("symbol") or "")
            row_strategy = str(row.get("strategy") or "").upper().strip()
            row_side = str(row.get("entry_side") or "").upper().strip()
            row_session = str(row.get("session_name") or "").strip()
            row_hour = int(row.get("hour_msk") or -1)

            strategy_ok = not strategy_norm or row_strategy == strategy_norm
            session_ok = row_session == session_norm if using_db_rows else row_hour == int(hour_msk)

            if (
                self._symbol_matches(row_symbol, str(symbol))
                and strategy_ok
                and row_side == side_norm
                and session_ok
            ):
                matched = row
                break

        if matched is None:
            return EdgeGateStrictDecisionV1(
                allowed=False,
                reason="strict_mode_no_match",
                expectancy_points=None,
                closed_trades=None,
                session_name=session_norm,
                hour_msk=hour_msk,
            )

        expectancy = float(matched.get("expectancy_points") or 0.0)
        closed_trades = int(matched.get("closed_trades") or 0)
        matched_symbol = str(matched.get("symbol") or "")
        if using_db_rows:
            matched_symbol = str(matched.get("normalized_symbol") or "")
        matched_strategy = str(matched.get("strategy") or "")

        if closed_trades < self.min_closed_trades:
            return EdgeGateStrictDecisionV1(
                allowed=False,
                reason="strict_mode_low_sample",
                expectancy_points=expectancy,
                closed_trades=closed_trades,
                matched_symbol=matched_symbol,
                matched_strategy=matched_strategy,
                session_name=session_norm,
                hour_msk=hour_msk,
            )

        if expectancy <= self.threshold:
            return EdgeGateStrictDecisionV1(
                allowed=False,
                reason="strict_mode_non_positive_expectancy",
                expectancy_points=expectancy,
                closed_trades=closed_trades,
                matched_symbol=matched_symbol,
                matched_strategy=matched_strategy,
                session_name=session_norm,
                hour_msk=hour_msk,
            )

        return EdgeGateStrictDecisionV1(
            allowed=True,
            reason="strict_mode_positive_expectancy",
            expectancy_points=expectancy,
            closed_trades=closed_trades,
            matched_symbol=matched_symbol,
            matched_strategy=matched_strategy,
            session_name=session_norm,
            hour_msk=hour_msk,
        )
