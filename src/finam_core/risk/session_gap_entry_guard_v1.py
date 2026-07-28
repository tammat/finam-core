from __future__ import annotations

from dataclasses import dataclass
from datetime import timezone
from statistics import fmean
from typing import Any


@dataclass(frozen=True)
class GapEntryDecisionV1:
    allowed: bool
    decision_code: str
    reason_code: str
    gap_atr_ratio: float | None
    confirmation_remaining: int


class SessionGapEntryGuardV1:
    """DB-driven защита новых входов после ценового разрыва.

    ATR строится только по свечам, предшествующим проверяемому бару. Текущий
    гэп не может искусственно увеличить собственную базу сравнения.
    """

    def __init__(self, logger: Any):
        self._logger = logger
        self._policy_cache: dict[tuple[str, str], dict[str, Any] | None] = {}
        self._history: dict[tuple[str, str], list[tuple[float, float, float]]] = {}
        self._confirmation_remaining: dict[tuple[str, str], int] = {}

    def evaluate(self, bar: Any) -> GapEntryDecisionV1:
        symbol = str(getattr(bar, "symbol", "") or "")
        timeframe = str(getattr(bar, "timeframe", "") or "").upper()
        key = (symbol, timeframe)
        policy = self._policy(key)
        if not policy:
            return self._finish(
                bar,
                GapEntryDecisionV1(False, "BLOCK", "GAP_POLICY_MISSING", None, 0),
                None,
                None,
            )

        history = self._history.setdefault(key, self._load_history(bar, policy))
        lookback = int(policy["atr_lookback"])
        if len(history) < lookback + 1:
            self._append(history, bar, lookback)
            return self._finish(
                bar,
                GapEntryDecisionV1(
                    False,
                    "BLOCK",
                    "GAP_HISTORY_INSUFFICIENT",
                    None,
                    self._confirmation_remaining.get(key, 0),
                ),
                None,
                None,
            )

        prior = history[-(lookback + 1) :]
        true_ranges = []
        for index in range(1, len(prior)):
            high, low, _ = prior[index]
            previous_close = prior[index - 1][2]
            true_ranges.append(
                max(high - low, abs(high - previous_close), abs(low - previous_close))
            )
        atr = fmean(true_ranges) if true_ranges else 0.0
        previous_close = prior[-1][2]
        opening = float(getattr(bar, "open", 0.0) or 0.0)
        ratio = abs(opening - previous_close) / atr if atr > 0 else None
        remaining = self._confirmation_remaining.get(key, 0)

        if ratio is None:
            decision = GapEntryDecisionV1(
                False, "BLOCK", "GAP_ATR_UNAVAILABLE", None, remaining
            )
        elif ratio >= float(policy["extreme_gap_atr"]):
            remaining = int(policy["confirmation_bars"])
            self._confirmation_remaining[key] = remaining
            decision = GapEntryDecisionV1(
                False, "BLOCK", "EXTREME_SESSION_GAP", ratio, remaining
            )
        elif ratio >= float(policy["elevated_gap_atr"]):
            remaining = int(policy["confirmation_bars"])
            self._confirmation_remaining[key] = remaining
            decision = GapEntryDecisionV1(
                False, "BLOCK", "ELEVATED_SESSION_GAP", ratio, remaining
            )
        elif remaining > 0:
            remaining -= 1
            self._confirmation_remaining[key] = remaining
            decision = GapEntryDecisionV1(
                False, "BLOCK", "GAP_CONFIRMATION_PENDING", ratio, remaining
            )
        else:
            decision = GapEntryDecisionV1(
                True, "ALLOW", "GAP_CHECK_PASSED", ratio, 0
            )

        self._append(history, bar, lookback)
        return self._finish(bar, decision, previous_close, atr)

    def _policy(self, key: tuple[str, str]) -> dict[str, Any] | None:
        if key in self._policy_cache:
            return self._policy_cache[key]
        symbol, timeframe = key
        policy = None
        try:
            with self._logger._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        select atr_lookback,elevated_gap_atr,extreme_gap_atr,
                               confirmation_bars
                        from analytics.session_gap_entry_policy_v1
                        where active
                          and %s like symbol_pattern
                          and timeframe = %s
                        order by priority desc, policy_id
                        limit 1
                        """,
                        (symbol, timeframe),
                    )
                    row = cur.fetchone()
            if row:
                policy = {
                    "atr_lookback": int(row[0]),
                    "elevated_gap_atr": float(row[1]),
                    "extreme_gap_atr": float(row[2]),
                    "confirmation_bars": int(row[3]),
                }
        except Exception:
            policy = None
        self._policy_cache[key] = policy
        return policy

    def _load_history(self, bar: Any, policy: dict[str, Any]):
        symbol = str(getattr(bar, "symbol", "") or "")
        timeframe = str(getattr(bar, "timeframe", "") or "").upper()
        ts = getattr(bar, "ts", None)
        limit = int(policy["atr_lookback"]) + 2
        rows = []
        statements = (
            """
            select high,low,close_price from market_data
            where symbol=%s and timeframe=%s and ts < %s
            order by ts desc limit %s
            """,
            """
            select high,low,close from market_bars
            where symbol=%s and timeframe=%s and ts < %s
            order by ts desc limit %s
            """,
        )
        for statement in statements:
            try:
                with self._logger._connect() as conn:
                    with conn.cursor() as cur:
                        cur.execute(statement, (symbol, timeframe, ts, limit))
                        rows = cur.fetchall()
                if rows:
                    break
            except Exception:
                continue
        return [
            (float(row[0]), float(row[1]), float(row[2]))
            for row in reversed(rows)
        ]

    @staticmethod
    def _append(history: list, bar: Any, lookback: int) -> None:
        history.append(
            (
                float(getattr(bar, "high", 0.0) or 0.0),
                float(getattr(bar, "low", 0.0) or 0.0),
                float(getattr(bar, "close_price", 0.0) or 0.0),
            )
        )
        del history[: max(0, len(history) - lookback - 2)]

    def _finish(self, bar, decision, previous_close, atr):
        try:
            ts = getattr(bar, "ts", None)
            if getattr(ts, "tzinfo", None) is None and ts is not None:
                ts = ts.replace(tzinfo=timezone.utc)
            with self._logger._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        insert into analytics.session_gap_entry_decision_v1(
                          symbol,timeframe,bar_ts,previous_close,bar_open,
                          prior_atr,gap_atr_ratio,decision_code,reason_code,
                          confirmation_remaining
                        ) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        on conflict(symbol,timeframe,bar_ts) do update set
                          previous_close=excluded.previous_close,
                          bar_open=excluded.bar_open,
                          prior_atr=excluded.prior_atr,
                          gap_atr_ratio=excluded.gap_atr_ratio,
                          decision_code=excluded.decision_code,
                          reason_code=excluded.reason_code,
                          confirmation_remaining=excluded.confirmation_remaining,
                          decided_at=now()
                        """,
                        (
                            str(getattr(bar, "symbol", "") or ""),
                            str(getattr(bar, "timeframe", "") or "").upper(),
                            ts,
                            previous_close,
                            float(getattr(bar, "open", 0.0) or 0.0),
                            atr,
                            decision.gap_atr_ratio,
                            decision.decision_code,
                            decision.reason_code,
                            decision.confirmation_remaining,
                        ),
                    )
                conn.commit()
        except Exception:
            pass
        return decision
