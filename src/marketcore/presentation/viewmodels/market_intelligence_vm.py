from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class MarketMetricVM:
    title: str
    value: str
    status: str
    action_label: str = "Подробнее"
    action_href: str = "#"


@dataclass(frozen=True)
class MarketInstrumentVM:
    symbol: str
    asset_class: str
    bars: str
    last_ts: str
    freshness: str
    status: str


@dataclass(frozen=True)
class MarketQualityVM:
    check: str
    object_name: str
    rows_checked: str
    bad_rows: str
    status: str


@dataclass(frozen=True)
class MarketIntelligenceVM:
    title: str = "Рынок"
    subtitle: str = "Market Intelligence"

    overview: list[MarketMetricVM] = field(default_factory=list)
    quality: list[MarketQualityVM] = field(default_factory=list)
    instruments: list[MarketInstrumentVM] = field(default_factory=list)
    actions: list[MarketMetricVM] = field(default_factory=list)


def build_default_market_intelligence_vm() -> MarketIntelligenceVM:
    return MarketIntelligenceVM(
        overview=[
            MarketMetricVM("Бары", "876K", "READY", "Детали", "/market"),
            MarketMetricVM("Тики", "71.1M", "READY", "Детали", "/market"),
            MarketMetricVM("Инстр.", "59", "READY", "Детали", "/market"),
            MarketMetricVM("Fresh", "59", "READY", "Детали", "/market"),
        ],
        quality=[
            MarketQualityVM("OHLC", "market_bars", "876K", "0", "READY"),
            MarketQualityVM("Volume", "market_bars", "876K", "0", "READY"),
            MarketQualityVM("Ticks", "market_ticks", "71.1M", "0", "READY"),
        ],
        instruments=[
            MarketInstrumentVM("BRN6@RTSX", "Futures", "41K", "2026-06-30", "FRESH", "READY"),
            MarketInstrumentVM("SBER@MISX", "Equity", "19K", "2026-07-01", "FRESH", "READY"),
            MarketInstrumentVM("BTCUSD", "Crypto", "46K", "2026-07-01", "FRESH", "READY"),
        ],
        actions=[
            MarketMetricVM("Диагн.", "Open", "INFO", "Открыть", "/system"),
            MarketMetricVM("Риски", "Open", "HIGH", "Открыть", "/risk"),
            MarketMetricVM("Исслед.", "Open", "READY", "Открыть", "/research"),
        ],
    )
