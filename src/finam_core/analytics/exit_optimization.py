from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class IntrabarTradeSample:
    pnl: float
    mae: float
    mfe: float
    exit_efficiency: float


@dataclass(frozen=True)
class ExitOptimizationProfile:
    trades: int
    avg_pnl: float
    avg_mfe: float
    avg_mae: float
    avg_exit_efficiency: float
    p50_mfe: float
    p70_mfe: float
    p80_mfe: float
    p50_mae_abs: float
    p70_mae_abs: float
    p80_mae_abs: float
    recommended_take_50: float
    recommended_take_70: float
    recommended_take_80: float
    recommended_stop_50: float
    recommended_stop_70: float
    recommended_stop_80: float


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0

    ordered = sorted(values)
    index = (len(ordered) - 1) * percentile
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)

    if lower == upper:
        return ordered[lower]

    weight = index - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def build_exit_optimization_profile(
    trades: Iterable[IntrabarTradeSample],
) -> ExitOptimizationProfile:
    items = list(trades)

    if not items:
        return ExitOptimizationProfile(
            trades=0,
            avg_pnl=0.0,
            avg_mfe=0.0,
            avg_mae=0.0,
            avg_exit_efficiency=0.0,
            p50_mfe=0.0,
            p70_mfe=0.0,
            p80_mfe=0.0,
            p50_mae_abs=0.0,
            p70_mae_abs=0.0,
            p80_mae_abs=0.0,
            recommended_take_50=0.0,
            recommended_take_70=0.0,
            recommended_take_80=0.0,
            recommended_stop_50=0.0,
            recommended_stop_70=0.0,
            recommended_stop_80=0.0,
        )

    pnls = [float(x.pnl) for x in items]
    mfes = [max(float(x.mfe), 0.0) for x in items]
    mae_abs = [abs(min(float(x.mae), 0.0)) for x in items]
    efficiencies = [float(x.exit_efficiency) for x in items]

    p50_mfe = _percentile(mfes, 0.50)
    p70_mfe = _percentile(mfes, 0.70)
    p80_mfe = _percentile(mfes, 0.80)

    p50_mae = _percentile(mae_abs, 0.50)
    p70_mae = _percentile(mae_abs, 0.70)
    p80_mae = _percentile(mae_abs, 0.80)

    return ExitOptimizationProfile(
        trades=len(items),
        avg_pnl=round(sum(pnls) / len(pnls), 10),
        avg_mfe=round(sum(mfes) / len(mfes), 10),
        avg_mae=round(sum(float(x.mae) for x in items) / len(items), 10),
        avg_exit_efficiency=round(sum(efficiencies) / len(efficiencies), 10),
        p50_mfe=round(p50_mfe, 10),
        p70_mfe=round(p70_mfe, 10),
        p80_mfe=round(p80_mfe, 10),
        p50_mae_abs=round(p50_mae, 10),
        p70_mae_abs=round(p70_mae, 10),
        p80_mae_abs=round(p80_mae, 10),
        recommended_take_50=round(p50_mfe, 10),
        recommended_take_70=round(p70_mfe, 10),
        recommended_take_80=round(p80_mfe, 10),
        recommended_stop_50=round(-p50_mae, 10),
        recommended_stop_70=round(-p70_mae, 10),
        recommended_stop_80=round(-p80_mae, 10),
    )
