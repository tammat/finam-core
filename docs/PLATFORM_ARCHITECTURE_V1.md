# FINAM CORE PLATFORM
# Architecture Freeze V6

==============================================================================
PLATFORM LAYERS
==============================================================================

L0  RAW MARKET

    public.market_bars


L1  MARKET PLATFORM

    market_snapshot_v1

    instrument_reference_v1


L2  FEATURE PLATFORM

    feature_snapshot_v1

    feature_store_health_v1


L3  STRATEGY PLATFORM

    strategy_registry_v1

    strategy_configuration_v1

    strategy_feature_dependency_v1

    strategy_signal_snapshot_v1


L4  EDGE PLATFORM

    edge_pipeline_snapshot_v1


L5  RISK PLATFORM


L6  TRADING PLATFORM


L7  PORTFOLIO PLATFORM


L8  PRESENTATION

    Platform API

    UI



==============================================================================
PLATFORM ENGINES
==============================================================================

Market Engine

↓

Feature Engine

↓

Strategy Engine

↓

Edge Engine

↓

Risk Engine

↓

Trading Engine

↓

Portfolio Engine



==============================================================================
STRATEGY PLATFORM
==============================================================================

FeatureSnapshot

↓

StrategyLoader

↓

StrategyExecutor

↓

Strategy

↓

StrategyDiagnostics

↓

StrategyResult

↓

StrategyBuilder

↓

strategy_signal_snapshot_v1



==============================================================================
STRATEGY STANDARD
==============================================================================

Input

    FeatureSnapshot


Output

    StrategyResult


StrategyResult

    Signal

    StrategyDiagnostics

    Feature Version

    Strategy Version

    Reason



==============================================================================
STRATEGY DIAGNOSTICS
==============================================================================

passed_filters

failed_filters

feature_values

thresholds

score_breakdown

execution_time_ms



==============================================================================
BUILDER STANDARD
==============================================================================

Builder

    loads configuration

    loads strategies

    loads features

    executes strategies

    stores signals

Builder never implements strategy logic.



==============================================================================
PLATFORM API STANDARD
==============================================================================

UI

↓

Platform API

↓

PostgreSQL


UI never performs SQL.



==============================================================================
PLATFORM UI STANDARD
==============================================================================

BaseDashboardPage

↓

PresentationContext

↓

display_label()

↓

Registry

↓

Router

↓

Platform API



==============================================================================
GOLDEN RULES
==============================================================================

1.

Single Source Of Truth.


2.

Every domain has exactly one canonical storage.


3.

Builder owns persistence.


4.

Strategy never writes PostgreSQL.


5.

Strategy never talks to Broker.


6.

Strategy never talks to Portfolio.


7.

Strategy never talks to Risk.


8.

Strategy never talks to Trading.


9.

Strategy receives only FeatureSnapshot.


10.

Strategy returns only StrategyResult.


11.

Every strategy returns StrategyDiagnostics.


12.

Every strategy is a plugin.


13.

Configuration lives only in

analytics.strategy_configuration_v1


14.

UI uses Platform API only.


15.

Architecture Freeze V6.


==============================================================================
CURRENT EPIC
==============================================================================

MULTI_STRATEGY_ENGINE

    □ Builder

    □ Research Workbench

    □ API

    □ UI

    □ Health

    □ Statistics

    □ Checkpoint



==============================================================================
NEXT EPICS
==============================================================================

EDGE PLATFORM

↓

RISK PLATFORM

↓

TRADING PLATFORM

↓

PORTFOLIO PLATFORM

↓

LIVE



==============================================================================
PROJECT STATUS
==============================================================================

Market Platform                    COMPLETE

Instrument Platform                COMPLETE

Feature Platform                   COMPLETE

Strategy Platform                  IN PROGRESS

Edge Platform                      PLANNED

Risk Platform                      PLANNED

Trading Platform                   PLANNED

Portfolio Platform                 PLANNED

Research Platform                  PLANNED

Live Platform                      PLANNED

