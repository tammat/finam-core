# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RadarCandidate:
    symbol: str
    name: str
    last: float
    change_pct: float
    relative_strength: float
    value_today: float
    volume_today: float
    num_trades: int
    score: float
    direction: str
    status: str


class MarketRadar:
    """
    Русский комментарий:
    Radar не торгует.
    Он фильтрует рынок и отдаёт shortlist.
    """

    ETF_BLACKLIST = (
        "LQDT",
        "AKMM",
        "SBMM",
        "TMON",
        "BCSD",
        "EQMX",
        "FXMM",
    )

    def __init__(
        self,
        min_value_today: float = 50_000_000,
        min_abs_change_pct: float = 0.5,
        max_abs_change_pct: float = 20.0,
    ) -> None:
        self.min_value_today = float(min_value_today)
        self.min_abs_change_pct = float(min_abs_change_pct)
        self.max_abs_change_pct = float(max_abs_change_pct)

    def build(
        self,
        data: dict,
        top_n: int = 10,
        imoex_change_pct: float = 0.0,
    ) -> dict[str, list[RadarCandidate]]:

        sec_cols = data["securities"]["columns"]
        md_cols = data["marketdata"]["columns"]

        securities = {}

        for row in data["securities"]["data"]:
            rec = dict(zip(sec_cols, row))
            secid = str(rec.get("SECID") or "")
            securities[secid] = str(rec.get("SHORTNAME") or secid)

        candidates: list[RadarCandidate] = []

        for row in data["marketdata"]["data"]:
            rec = dict(zip(md_cols, row))

            secid = str(rec.get("SECID") or "")
            if not secid or secid not in securities:
                continue

            name = securities[secid]

            last = self._num(rec.get("LAST"))
            change_pct = self._num(rec.get("CHANGE"))
            value_today = self._num(rec.get("VALTODAY"))
            volume_today = self._num(rec.get("VOLTODAY"))
            num_trades = int(self._num(rec.get("NUMTRADES")))

            if last <= 0:
                continue

            if value_today < self.min_value_today:
                continue

            abs_change = abs(change_pct)

            # Русский комментарий:
            # Отсекаем ETF/денежные фонды с околонулевым движением.
            if secid.startswith(self.ETF_BLACKLIST):
                continue

            if abs_change < self.min_abs_change_pct:
                continue

            status = "CANDIDATE"

            # Русский комментарий:
            # Слишком большое движение — подозрение на corporate action/split/dividend gap.
            if abs_change > self.max_abs_change_pct:
                status = "ANOMALY"

            direction = "GAINER" if change_pct > 0 else "LOSER"

            relative_strength = round(change_pct - imoex_change_pct, 4)

            score = (
                abs_change * 0.45
                + min(value_today / 1_000_000_000, 5.0) * 0.35
                + min(num_trades / 20_000, 3.0) * 0.20
            )

            candidates.append(
                RadarCandidate(
                    symbol=f"{secid}@MISX",
                    name=name,
                    last=round(last, 6),
                    change_pct=round(change_pct, 4),
                    relative_strength=relative_strength,
                    value_today=round(value_today, 2),
                    volume_today=round(volume_today, 2),
                    num_trades=num_trades,
                    score=round(score, 6),
                    direction=direction,
                    status=status,
                )
            )

        clean_candidates = [x for x in candidates if x.status == "CANDIDATE"]

        gainers = sorted(
            [x for x in clean_candidates if x.direction == "GAINER"],
            key=lambda x: x.score,
            reverse=True,
        )[:top_n]

        losers = sorted(
            [x for x in clean_candidates if x.direction == "LOSER"],
            key=lambda x: x.score,
            reverse=True,
        )[:top_n]

        anomalies = sorted(
            [x for x in candidates if x.status == "ANOMALY"],
            key=lambda x: abs(x.change_pct),
            reverse=True,
        )[:top_n]

        return {
            "gainers": gainers,
            "losers": losers,
            "anomalies": anomalies,
        }

    @staticmethod
    def _num(value) -> float:
        try:
            if value is None or value == "":
                return 0.0
            return float(value)
        except Exception:
            return 0.0
