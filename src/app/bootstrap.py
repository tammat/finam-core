from core.orchestrator import TradingPipeline
from risk.risk_engine import RiskEngine
from risk.MaxPositionPctRule import MaxPositionPctRule
from risk.MaxGrossExposureRule import MaxGrossExposureRule
from risk.DrawdownRule import DrawdownRule
from sizing_engine import FixedFractionSizing
from config.settings import Settings
sizing_engine = FixedFractionSizing(0.1)

pipeline = TradingPipeline(
    market_data=...,
    strategy=...,
    sizing_engine=sizing_engine,
    risk_engine=risk_engine,
    execution=...,
    accounting=...,
    storage=...,
)
def build_pipeline():

    # ---- Risk 2.0 ----
    risk_engine = RiskEngine([
        MaxPositionPctRule(Settings.MAX_POSITION_PCT or 0.2),
        MaxGrossExposureRule(Settings.MAX_GROSS_EXPOSURE_PCT or 1.5),
        DrawdownRule(Settings.MAX_DRAWDOWN_PCT or 0.15),
    ])
    pipeline = TradingPipeline(
        market_data=...,
        strategy=...,
        risk_engine=risk_engine,
        portfolio=...,
        execution=...,
        accounting=...,
        storage=...,
    )

    return pipeline