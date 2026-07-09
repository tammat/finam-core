from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import psycopg2
import psycopg2.extras


@dataclass(frozen=True, slots=True)
class InstrumentPresentation:
    symbol: str
    display_name: str
    short_name: str
    asset_class: str
    exchange: str
    currency: str
    source_table: str
    fallback_used: bool

    title_key: str
    subtitle_key: str
    tooltip_key: str
    brand_icon_key: str
    badge_key: str


class InstrumentDisplayResolverV1:
    def __init__(self) -> None:
        self._cache: dict[str, InstrumentPresentation] = {}

    def resolve(self, symbol: str) -> InstrumentPresentation:
        key = symbol.strip().upper()

        if key in self._cache:
            return self._cache[key]

        with psycopg2.connect("postgresql:///finam_core") as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                result = (
                    self._from_knowledge(cur, key)
                    or self._from_analytics(cur, key)
                    or self._from_moex(cur, key)
                    or self._fallback(key)
                )

        self._cache[key] = result
        return result

    def _exists(self, cur: Any, full_table: str) -> bool:
        cur.execute("SELECT to_regclass(%s) IS NOT NULL AS exists_flag", (full_table,))
        return bool(cur.fetchone()["exists_flag"])

    def _from_knowledge(self, cur: Any, symbol: str) -> InstrumentPresentation | None:
        if not self._exists(cur, "knowledge.instrument_v1"):
            return None

        cur.execute(
            """
            SELECT *
            FROM knowledge.instrument_v1
            WHERE upper(symbol)=upper(%s)
            LIMIT 1
            """,
            (symbol,),
        )
        row = cur.fetchone()
        if not row:
            return None

        return self._build(symbol, row, "knowledge.instrument_v1", False)

    def _from_analytics(self, cur: Any, symbol: str) -> InstrumentPresentation | None:
        if not self._exists(cur, "analytics.market_instrument_v1"):
            return None

        cur.execute(
            """
            SELECT *
            FROM analytics.market_instrument_v1
            WHERE upper(symbol)=upper(%s)
            LIMIT 1
            """,
            (symbol,),
        )
        row = cur.fetchone()
        if not row:
            return None

        return self._build(symbol, row, "analytics.market_instrument_v1", False)

    def _from_moex(self, cur: Any, symbol: str) -> InstrumentPresentation | None:
        if not self._exists(cur, "public.moex_top_universe"):
            return None

        cur.execute(
            """
            SELECT
                symbol,
                board,
                asset_class,
                short_name
            FROM public.moex_top_universe
            WHERE upper(symbol)=upper(%s)
            LIMIT 1
            """,
            (symbol,),
        )
        row = cur.fetchone()
        if not row:
            return None

        return InstrumentPresentation(
            symbol=symbol,
            display_name=str(row.get("short_name") or symbol),
            short_name=str(row.get("short_name") or symbol),
            asset_class=str(row.get("asset_class") or "UNKNOWN"),
            exchange=str(row.get("board") or "MOEX"),
            currency="RUB",
            source_table="public.moex_top_universe",
            fallback_used=False,

            title_key="instrument.title",
            subtitle_key="instrument.subtitle",
            tooltip_key="instrument.tooltip.default",
            brand_icon_key="brand.default",
            badge_key="instrument.asset_class",
        )

    def _build(
        self,
        symbol: str,
        row: dict[str, Any],
        source_table: str,
        fallback_used: bool,
    ) -> InstrumentPresentation:
        name = (
            row.get("instrument_name")
            or row.get("short_name")
            or row.get("name")
            or row.get("secname")
            or symbol
        )

        short_name = row.get("short_name") or row.get("shortname") or name

        return InstrumentPresentation(
            symbol=symbol,
            display_name=str(name),
            short_name=str(short_name),
            asset_class=str(row.get("asset_class") or "UNKNOWN"),
            exchange=str(row.get("exchange") or row.get("boardid") or "UNKNOWN"),
            currency=str(row.get("currency") or "RUB"),
            source_table=source_table,
            fallback_used=fallback_used,

            title_key="instrument.title",
            subtitle_key="instrument.subtitle",
            tooltip_key="instrument.tooltip.default",
            brand_icon_key="brand.default",
            badge_key="instrument.asset_class",
        )

    def _fallback(self, symbol: str) -> InstrumentPresentation:
        return InstrumentPresentation(
            symbol=symbol,
            display_name=symbol,
            short_name=symbol,
            asset_class="UNKNOWN",
            exchange="UNKNOWN",
            currency="UNKNOWN",
            source_table="fallback",
            fallback_used=True,

            title_key="instrument.title",
            subtitle_key="instrument.subtitle",
            tooltip_key="instrument.tooltip.default",
            brand_icon_key="brand.default",
            badge_key="instrument.asset_class",
        )


def resolve_instrument_display(symbol: str) -> InstrumentPresentation:
    return InstrumentDisplayResolverV1().resolve(symbol)
