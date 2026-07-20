from __future__ import annotations

import time
import os
import uuid
from dataclasses import dataclass

from finam_core.runtime.research_contract_key_v1 import normalize_research_contract_key_v1


@dataclass(frozen=True)
class TradeGateDecision:
    allowed: bool
    reason: str
    adjusted_qty: float | None = None
    reservation_id: str | None = None


class TradeGateService:
    """
    Русский комментарий:
    Единый runtime gate для entry path.

    Этап 1:
    - cooldown;
    - trade limit;
    - без изменения текущей логики pipeline.
    """

    def __init__(
        self,
        base_cooldown_sec: float = 45.0,
        max_trades_per_hour: int = 5,
        max_trades_per_symbol: int = 2,
        connection_factory=None,
    ) -> None:
        self.base_cooldown_sec = float(base_cooldown_sec)
        self.max_trades_per_hour = int(max_trades_per_hour)
        self.max_trades_per_symbol = int(max_trades_per_symbol)
        self.connection_factory = connection_factory

        self.symbol_last_trade_ts: dict[str, float] = {}
        self.trade_timestamps: list[float] = []
        self.symbol_trade_timestamps: dict[str, list[float]] = {}
        self._reservations: dict[tuple[str, str, str, str], str] = {}

    def cooldown_allows(self, symbol: str, price: float, atr: float | None = None) -> TradeGateDecision:
        now_ts = time.time()

        try:
            atr_pct = abs(float(atr or 0.0) / float(price)) if price else 0.0

            if atr_pct > 0.015:
                cooldown_sec = self.base_cooldown_sec * 0.6
            elif atr_pct < 0.005:
                cooldown_sec = self.base_cooldown_sec * 1.5
            else:
                cooldown_sec = self.base_cooldown_sec
        except Exception:
            cooldown_sec = self.base_cooldown_sec

        last_trade_ts = self.symbol_last_trade_ts.get(symbol, 0.0)

        if now_ts - last_trade_ts < cooldown_sec:
            return TradeGateDecision(
                allowed=False,
                reason=f"cooldown_block:symbol={symbol}:cooldown={round(cooldown_sec, 3)}",
            )

        return TradeGateDecision(allowed=True, reason="cooldown_ok")

    def trade_limit_allows(
        self,
        symbol: str,
        *,
        strategy: str = "UNKNOWN",
        regime: str = "UNKNOWN",
        execution_mode: str = "PAPER",
        timeframe: str = "UNKNOWN",
        side: str = "UNKNOWN",
        session_name: str = "UNKNOWN",
    ) -> TradeGateDecision:
        if callable(self.connection_factory):
            return self._reserve_db_quota(
                symbol=symbol,strategy=strategy,regime=regime,
                execution_mode=execution_mode,timeframe=timeframe,
                side=side,session_name=session_name,
            )

        # Совместимость только для изолированных unit-тестов без БД. Боевой
        # pipeline всегда передаёт connection_factory и не использует этот путь.
        now_ts = time.time()

        trades = [t for t in self.trade_timestamps if now_ts - t < 3600]
        if len(trades) >= self.max_trades_per_hour:
            self.trade_timestamps = trades
            return TradeGateDecision(False, "trade_limit_block_global")

        sym_trades = self.symbol_trade_timestamps.get(symbol, [])
        sym_trades = [t for t in sym_trades if now_ts - t < 3600]

        if len(sym_trades) >= self.max_trades_per_symbol:
            self.symbol_trade_timestamps[symbol] = sym_trades
            return TradeGateDecision(False, f"trade_limit_block_symbol:{symbol}")

        return TradeGateDecision(True, "trade_limit_ok")

    def account_trade(
        self,
        symbol: str,
        *,
        strategy: str = "UNKNOWN",
        regime: str = "UNKNOWN",
        execution_mode: str = "PAPER",
        timeframe: str = "UNKNOWN",
        side: str = "UNKNOWN",
        session_name: str = "UNKNOWN",
    ) -> TradeGateDecision:
        if callable(self.connection_factory):
            key = normalize_research_contract_key_v1(
                symbol=symbol,strategy=strategy,timeframe=timeframe,side=side,
                session_name=session_name,regime=regime,execution_mode=execution_mode,
            )
            quota_key = (key.execution_mode,key.normalized_symbol,key.strategy,key.regime_code)
            reservation_id = self._reservations.pop(quota_key, None)
            if reservation_id is None:
                return TradeGateDecision(False,"db_quota_missing_reservation")
            conn = self.connection_factory()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """UPDATE analytics.paper_research_quota_reservation_v1
                           SET status_code='FILLED',filled_at=clock_timestamp()
                           WHERE reservation_id=%s AND status_code='RESERVED'
                             AND expires_at>clock_timestamp()""",
                        (reservation_id,),
                    )
                    if cur.rowcount != 1:
                        conn.rollback()
                        return TradeGateDecision(False,"db_quota_reservation_expired",reservation_id=reservation_id)
                conn.commit()
                self.symbol_last_trade_ts[symbol] = time.time()
                return TradeGateDecision(True,"db_quota_fill_accounted",reservation_id=reservation_id)
            finally:
                conn.close()

        now_ts = time.time()

        self.symbol_last_trade_ts[symbol] = now_ts

        trades = [t for t in self.trade_timestamps if now_ts - t < 3600]
        trades.append(now_ts)
        self.trade_timestamps = trades

        sym_trades = self.symbol_trade_timestamps.get(symbol, [])
        sym_trades = [t for t in sym_trades if now_ts - t < 3600]
        sym_trades.append(now_ts)
        self.symbol_trade_timestamps[symbol] = sym_trades

        return TradeGateDecision(
            True,
            f"trade_accounted:global={len(trades)}:symbol={len(sym_trades)}",
        )

    def _reserve_db_quota(
        self, *, symbol: str, strategy: str, regime: str, execution_mode: str,
        timeframe: str, side: str, session_name: str,
    ) -> TradeGateDecision:
        key = normalize_research_contract_key_v1(
            symbol=symbol,strategy=strategy,timeframe=timeframe,side=side,
            session_name=session_name,regime=regime,execution_mode=execution_mode,
        )
        quota_key = (key.execution_mode,key.normalized_symbol,key.strategy,key.regime_code)
        existing = self._reservations.get(quota_key)
        if existing is not None:
            return TradeGateDecision(True,"db_quota_reservation_reused",reservation_id=existing)
        conn = self.connection_factory()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))",("|".join(quota_key),))
                cur.execute(
                    """UPDATE analytics.paper_research_quota_reservation_v1
                       SET status_code='EXPIRED'
                       WHERE status_code='RESERVED' AND expires_at<=clock_timestamp()"""
                )
                cur.execute(
                    """SELECT policy_code,window_seconds,max_fills,reservation_ttl_seconds
                       FROM analytics.paper_research_quota_policy_v1
                       WHERE enabled AND execution_mode=%s
                         AND normalized_symbol IN (%s,'*')
                         AND strategy IN (%s,'*')
                         AND regime_code IN (%s,'ANY')
                       ORDER BY (normalized_symbol=%s) DESC,(strategy=%s) DESC,
                                (regime_code=%s) DESC,priority
                       LIMIT 1""",
                    (key.execution_mode,key.normalized_symbol,key.strategy,key.regime_code,
                     key.normalized_symbol,key.strategy,key.regime_code),
                )
                policy = cur.fetchone()
                if policy is None:
                    conn.rollback()
                    return TradeGateDecision(False,"db_quota_policy_missing")
                policy_code,window_seconds,max_fills,ttl_seconds = policy
                cur.execute(
                    """SELECT count(*) FROM analytics.paper_research_quota_reservation_v1
                       WHERE execution_mode=%s AND normalized_symbol=%s AND strategy=%s
                         AND regime_code=%s
                         AND ((status_code='FILLED' AND filled_at>=clock_timestamp()-(%s*interval '1 second'))
                           OR (status_code='RESERVED' AND expires_at>clock_timestamp()))""",
                    (*quota_key,window_seconds),
                )
                used = int(cur.fetchone()[0])
                if used >= int(max_fills):
                    conn.rollback()
                    return TradeGateDecision(False,f"db_quota_exhausted:{policy_code}:{used}/{max_fills}")
                reservation_id = str(uuid.uuid4())
                cur.execute(
                    """INSERT INTO analytics.paper_research_quota_reservation_v1(
                       reservation_id,execution_mode,normalized_symbol,strategy,regime_code,
                       policy_code,status_code,expires_at,source_process,evidence)
                       VALUES(%s,%s,%s,%s,%s,%s,'RESERVED',
                              clock_timestamp()+(%s*interval '1 second'),%s,
                              jsonb_build_object('timeframe',%s,'side',%s,'session',%s,'raw_symbol',%s))""",
                    (reservation_id,*quota_key,policy_code,ttl_seconds,
                     f"paper_pipeline:{os.getpid()}",key.timeframe,key.side,key.session_name,symbol),
                )
            conn.commit()
            self._reservations[quota_key] = reservation_id
            return TradeGateDecision(True,f"db_quota_reserved:{policy_code}:{used+1}/{max_fills}",reservation_id=reservation_id)
        except Exception as exc:
            conn.rollback()
            return TradeGateDecision(False,f"db_quota_error:{type(exc).__name__}")
        finally:
            conn.close()
