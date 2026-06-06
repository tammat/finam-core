# src/finam_core/pipelines/paper_pipeline.py
# Русский коммент: Pipeline B (event-driven).
# QUOTE -> Strategy -> Risдавайk -> PaperExecution -> publish(FILL) -> Accounting(PM.apply_fill)

from __future__ import annotations
from finam_core.governance.runtime_guard_reader import RuntimeGuardReader

from finam_core.governance.guard_candidate_classification_reader import GuardCandidateClassificationReader
from finam_core.governance.guard_shadow_accumulator import GuardShadowAccumulator, GuardShadowEvent

from finam_core.runtime.exit_policy_advisor import RuntimeExitPolicyAdvisor
from finam_core.runtime.portfolio_heat_advisor import RuntimePortfolioHeatAdvisor
from finam_core.runtime.portfolio_governance_advisor import PortfolioGovernanceAdvisor
from finam_core.runtime.portfolio_governance_repository import PortfolioGovernanceRepository
from finam_core.runtime.runtime_governance_coordinator_v2 import RuntimeGovernanceCoordinatorV2
from finam_core.analytics.incremental_exit_intelligence import IncrementalExitInput, build_incremental_exit_advice
from finam_core.analytics.symbol_strategy_resolver import SymbolStrategyResolver

from finam_core.runtime.trend_gate_service import TrendGateService

from finam_core.runtime.regime_runtime_control_service import RegimeRuntimeControlService

from finam_core.runtime.entry_gate_coordinator import EntryGateCoordinator

from finam_core.regime.regime_labeler import RegimeLabeler

from finam_core.signals.strategy_intent_adapter import StrategyIntentAdapter

from finam_core.pipelines.pipeline_orchestrator import PipelineOrchestrator, QuoteEventContext
from finam_core.storage.postgres_logger import PostgresLogger
import os
from finam_core.config.runtime_config import RuntimeConfig
from finam_core.risk.portfolio_risk_gate import PortfolioRiskGate
from finam_core.notifications.risk_notification_bridge_v1 import RiskNotificationBridgeV1, RiskNotificationInputV1
from finam_core.execution.session_side_execution_gate_v1 import SessionSideExecutionGateV1
from finam_core.execution.edge_gate_strict_mode_v1 import EdgeGateStrictModeV1
from finam_core.execution.runtime_edge_governance_soft_block_v1 import RuntimeEdgeGovernanceSoftBlockV1
from finam_core.execution.runtime_governance_live_accumulation_v1 import (
    RuntimeGovernanceLiveAccumulatorV1,
    RuntimeGovernanceLiveDecisionV1,
)
from finam_core.execution.session_side_gate_runtime_audit_v1 import SessionSideGateRuntimeAuditV1
from finam_core.risk.context_builders import build_risk_context
import json
import logging
import os
import time
from finam_core.strategy.ng_volatility_breakout import NgVolatilityBreakout
from finam_core.strategy.br_regime_layer import BRRegimeLayer
from finam_core.strategy.br_volatility_intelligence import BRVolatilityIntelligence
from finam_core.features.volume_features import BarVolumeFeatureEngine
from finam_core.strategy.exit_engine import ExitEngine, ExitStateMachine
from types import SimpleNamespace

from finam_core.execution.execution_fill import ExecutionFill
from finam_core.execution.trailing_order_manager import TrailingOrderManager
from finam_core.execution.real_protective_lifecycle import RealProtectiveLifecycleEngine
from finam_core.execution.protective_order_link_repository import ProtectiveOrderLinkRepository
from finam_core.execution.profit_lock_engine import ProfitLockEngine
from finam_core.execution.take_profit_engine import TakeProfitEngine
from finam_core.execution.partial_close_engine import PartialCloseEngine
from finam_core.execution.position_lifecycle_state_repository import PositionLifecycleStateRepository
from finam_core.execution.position_lifecycle_reconciler import PositionLifecycleReconciler
from finam_core.execution.position_lifecycle_reconcile_event_repository import PositionLifecycleReconcileEventRepository
from finam_core.execution.position_lifecycle_self_healer import PositionLifecycleSelfHealer
from finam_core.execution.exit_lifecycle_manager import ExitLifecycleInput, ExitLifecycleManager
from finam_core.execution.position_lifecycle_service import PositionLifecycleInput, PositionLifecycleService
from finam_core.execution.take_profit_event_repository import TakeProfitEventRepository
from finam_core.execution.profit_lock_event_repository import ProfitLockEventRepository
from finam_core.execution.trailing_order_event_repository import TrailingOrderEventRepository
from finam_core.execution.position_order_tracker import PositionOrderTracker
from finam_core.reconciliation.portfolio_reconciliation_repair import PortfolioReconciliationRepair
from finam_core.execution.open_orders_sync import OpenOrdersSync
from finam_core.execution.broker_reconciliation import BrokerReconciliationEngine
from finam_core.portfolio.position_intent_repository import PositionIntentRepository
from finam_core.execution.real_execution import RealExecutionEngine
from finam_core.execution.cancel_replace_stop_manager import CancelReplaceStopManager
from finam_core.execution.execution_decision_layer import ExecutionDecisionLayer
from finam_core.execution.order_router import OrderRouter
from finam_core.execution.execution_dispatcher import ExecutionDispatcher
from finam_core.execution.execution_gateway import ExecutionGateway, ExecutionGatewayInput
from finam_core.execution.fill_metadata_factory import FillMetadataFactory
from finam_core.execution.fill_persistence_service import FillPersistenceService
from finam_core.runtime.strategy_runtime_control_service import StrategyRuntimeControlService
from finam_core.runtime.trade_gate_service import TradeGateService
from finam_core.engine.trading_engine_coordinator import TradingEngineCoordinator
from finam_core.engine.coordinator_flags import CoordinatorFlags
from finam_core.engine.restart_recovery_coordinator import RestartRecoveryCoordinator
from finam_core.portfolio.portfolio_reconciliation_layer import PortfolioReconciliationLayer
from finam_core.execution.entry_point_selector import EntryPointSelector
from finam_core.execution.oco_order_manager import OcoOrderManager
from finam_core.adapters.grpc.orders_client import FinamOrdersClient
from finam_core.accounting.fees import FeeTaxModel
from finam_core.risk.trailing_exit import TrailingExitEngine
from finam_core.notifications.telegram_notifier import TelegramNotifier
from finam_core.storage.postgres_logger import PostgresLogger
from finam_core.risk.sl_tp_cooldown import SlTpCooldownEngine
from finam_core.risk.volatility_risk import VolatilityRiskEngine
from finam_core.risk.live_atr import LiveAtrEstimator
from finam_core.risk.portfolio_heat import PortfolioHeatEngine
from finam_core.risk.kill_switch import KillSwitchEngine
from finam_core.risk.correlation_risk import CorrelationRiskEngine
from finam_core.risk.unified_decision import UnifiedRiskDecision, RiskDecisionRecorder
from finam_core.risk.risk_router import RiskRouteInput, RiskRouter
from finam_core.signals.signal_router import SignalRouter as SignalIntentRouter
from finam_core.runtime.regime_runtime_override_repository import RuntimeRegimeOverrideRepository
from finam_core.risk.runtime_override_gate import apply_runtime_override_gate
from finam_core.features.live_feature_buffer import LiveFeatureBuffer
from finam_core.regime.regime_engine import RegimeEngine
from finam_core.data.mtf_aggregator import MTFBarAggregator
from core.instrument_resolver import InstrumentResolver
from finam_core.strategy.br_conservative_breakout import BrConservativeBreakout
from finam_core.strategy.futures.ng_conservative_breakout_m1 import NgConservativeBreakoutM1
from finam_core.research.runtime_selection_gate import RuntimeSelectionGate
from finam_core.risk.finam_limits_adapter import FinamLimitsAdapter
from finam_core.risk.regime_policy import RegimePolicy, SymbolDrawdownGuard, SymbolLossStreakGuard, PortfolioGuard
from finam_core.notifications.signal_alert_sender import send_signal_alert_from_intent
from finam_core.instruments.br_point_value import get_br_rub_per_point
from finam_core.analytics.signal_repository import SignalRepository
from finam_core.analytics.closed_trade_attribution_service import ClosedTradeAttributionService
from finam_core.strategy.strategy_factory import StrategyFactory
from finam_core.strategy.strategy_runtime import StrategyRuntime
from finam_core.strategy.quote_signal_processor import QuoteSignalInput, QuoteSignalProcessor
from finam_core.strategy.signal_router import SignalRouteInput, SignalRouter as QuoteSignalRouter
from finam_core.strategy.trend_filter import TrendFilter

# br_long_shadow_pipeline_hook_v1:
# Governance-фильтр BR LONG. В shadow-режиме блокирует BR BUY/LONG,
# но пишет исследовательское событие в PostgreSQL.
from finam_core.governance.br_long_governance_v1 import BrLongGovernanceV1
from finam_core.governance.br_short_shadow_policy_v1 import BrShortShadowPolicyV1
from finam_core.governance.br_short_shadow_accumulator_v1 import (
    BrShortShadowAccumulatorV1,
    BrShortShadowEventV1,
)
from finam_core.governance.br_long_shadow_accumulator_v1 import (
    BrLongShadowAccumulatorV1,
    BrLongShadowEventV1,
)

# === RISK CLUSTERS (упрощённая корреляция) ===
CLUSTERS = {
    "energy": ["NG", "BR"],
    "metals": ["GC", "SI"],
    "fx": ["SR"],
}

LOG = logging.getLogger(__name__)

# Русский комментарий: глобальный debug-флаг pipeline.
PIPE_DEBUG = os.getenv("PIPE_DEBUG", "0") == "1"


# PIPELINE DEBUG FLAG



def _decision_allowed(decision) -> bool:
    """Русский комментарий: единая проверка allowed для разных форматов RiskDecision."""
    if decision is None:
        return False
    if isinstance(decision, dict):
        return bool(decision.get("allowed", False))
    return bool(getattr(decision, "allowed", False))


def _decision_reason(decision) -> str:
    """Русский комментарий: безопасно извлекает reason из RiskDecision."""
    if decision is None:
        return "none"
    if isinstance(decision, dict):
        return str(decision.get("reason") or "unknown")
    return str(getattr(decision, "reason", None) or "unknown")

def _safe_float(value, default: float = 0.0) -> float:
    """Русский комментарий: безопасное преобразование market data значений в float."""
    try:
        if value is None:
            return float(default)
        return float(value)
    except Exception:
        return float(default)

def _coerce_mtf_ts(ts):
    """Русский комментарий: SimFeed может отдавать timestamp как float; MTF ждёт datetime с tzinfo."""
    from datetime import datetime, timezone

    if isinstance(ts, (int, float)):
        return datetime.fromtimestamp(float(ts), tz=timezone.utc)
    if getattr(ts, "tzinfo", None) is None:
        return ts.replace(tzinfo=timezone.utc)
    return ts


def _selection_gate_allowed(pipeline, *, strategy: str, symbol: str, regime: str) -> bool:
    """Русский комментарий: проверяет допуск strategy + root_symbol + regime перед RiskEngine."""
    gate = getattr(pipeline, "runtime_selection_gate", None)

    if gate is None:
        gate = RuntimeSelectionGate()
        pipeline.runtime_selection_gate = gate

    decision = gate.is_allowed(
        strategy=strategy,
        symbol=symbol,
        regime=regime,
    )

    if decision.allowed:
        print(
            "PIPE_SELECTION_GATE_ACCEPTED "
            f"strategy={strategy} "
            f"symbol={symbol} "
            f"root_symbol={decision.root_symbol} "
            f"regime={regime}",
            flush=True,
        )
        return True

    print(
        "PIPE_SELECTION_GATE_REJECTED "
        f"strategy={strategy} "
        f"symbol={symbol} "
        f"root_symbol={decision.root_symbol} "
        f"regime={regime} "
        f"reason={decision.reason}",
        flush=True,
    )
    return False


class RealPositionQtyProvider:
    """Русский комментарий: provider broker/local qty для финального hard block перед real PlaceOrder."""

    def __init__(self, pipeline) -> None:
        self.pipeline = pipeline

    def get_position_qty_pair(self, symbol: str) -> dict:
        broker_qty = self._broker_qty(symbol)
        local_qty = self._local_qty(symbol)
        return {"broker_qty": broker_qty, "local_qty": local_qty}

    def _broker_qty(self, symbol: str) -> float:
        for attr_name in ("broker_positions", "_broker_positions", "finam_positions", "_finam_positions"):
            positions = getattr(self.pipeline, attr_name, None)
            if isinstance(positions, dict) and symbol in positions:
                value = positions[symbol]
                if isinstance(value, dict):
                    return float(value.get("qty", value.get("quantity", 0.0)) or 0.0)
                return float(getattr(value, "qty", getattr(value, "quantity", value)) or 0.0)
        return 0.0

    def _local_qty(self, symbol: str) -> float:
        for attr_name in ("position_manager", "positions", "portfolio", "portfolio_manager"):
            obj = getattr(self.pipeline, attr_name, None)
            if obj is None:
                continue

            for method_name in ("get_position_qty", "qty", "quantity", "get_qty"):
                method = getattr(obj, method_name, None)
                if callable(method):
                    try:
                        return float(method(symbol) or 0.0)
                    except Exception:
                        continue

            if isinstance(obj, dict) and symbol in obj:
                value = obj[symbol]
                if isinstance(value, dict):
                    return float(value.get("qty", value.get("quantity", 0.0)) or 0.0)
                return float(getattr(value, "qty", getattr(value, "quantity", value)) or 0.0)

        return 0.0




def _edge_gate_enrich_payload_for_paper(payload, signal_like=None):
    # Русский комментарий: soft telemetry для статистического edge-gate.
    # Функция не блокирует исполнение и не меняет решение Risk/Execution.
    import os
    from datetime import UTC, datetime

    from finam_core.execution.edge_execution_gate import evaluate_edge_execution_gate
    from finam_core.execution.edge_telemetry import (
        build_edge_telemetry_snapshot,
        merge_edge_telemetry,
    )

    result = dict(payload or {})

    if os.environ.get("EDGE_GATE_SOFT", "1") != "1":
        return result

    signal_obj = signal_like if signal_like is not None else result
    nested_payload = result.get("payload") if isinstance(result.get("payload"), dict) else {}

    # Русский комментарий: если signal не содержит strategy/timeframe,
    # используем top-level payload и вложенный payload.payload как источник атрибуции.
    signal_dict = {
        "symbol": (
            result.get("symbol")
            or nested_payload.get("symbol")
            or getattr(signal_obj, "symbol", None)
        ),
        "strategy": (
            result.get("strategy")
            or nested_payload.get("strategy")
            or getattr(signal_obj, "strategy", None)
            or result.get("source")
            or nested_payload.get("source")
        ),
        "timeframe": (
            result.get("timeframe")
            or nested_payload.get("timeframe")
            or getattr(signal_obj, "timeframe", None)
            or result.get("horizon")
            or nested_payload.get("horizon")
        ),
    }

    ts = datetime.now(UTC)
    decision = evaluate_edge_execution_gate(signal_dict, ts=ts)

    telemetry = build_edge_telemetry_snapshot(
        decision=decision,
        ts=ts,
        mode="soft",
    )

    enriched = merge_edge_telemetry(result, telemetry)

    label = "EDGE_ALLOWED" if decision.allowed else "EDGE_REJECTED"
    print(
        label,
        f"symbol={decision.symbol}",
        f"strategy={decision.strategy}",
        f"timeframe={decision.timeframe}",
        f"hour={decision.hour_utc}",
        f"reason={decision.reason}",
        flush=True,
    )

    if not decision.allowed:
        print(
            "EDGE_GATE_SOFT_BYPASS",
            f"symbol={decision.symbol}",
            f"reason={decision.reason}",
            flush=True,
        )

    return enriched




def _save_trade_context_snapshot_for_paper_trade(
    trade_id: str,
    db_trade_id,
    trade_payload: dict,
) -> None:
    # Русский комментарий: explainability snapshot сохраняется только как observability.
    # Он не влияет на Risk, Execution и Accounting.
    import os

    if os.getenv("TRADE_CONTEXT_SNAPSHOT_ENABLED", "1") != "1":
        return

    try:
        from finam_core.analytics.trade_context_snapshot_repository import (
            TradeContextSnapshot,
            TradeContextSnapshotRepository,
        )
        from finam_core.contracts.continuous_contract_resolver import ContinuousContractResolver

        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            return

        payload = dict(trade_payload or {})
        snapshot = {
            "market": {
                "regime_direction": payload.get("regime_direction"),
                "regime_atr_pct": payload.get("regime_atr_pct"),
                "regime_strength": payload.get("regime_strength"),
            },
            "strategy": {
                "reason": payload.get("reason"),
                "entry_price": payload.get("entry_price"),
                "stop_loss": payload.get("stop_loss"),
                "take_profit": payload.get("take_profit"),
                "horizon": payload.get("horizon"),
            },
            "execution": {
                "execution_type": payload.get("execution_type"),
                "paper_only": payload.get("paper_only"),
                "run_id": payload.get("run_id"),
            },
            "risk": {
                "edge_gate": (
                    payload.get("trade_context_snapshot", {})
                    .get("edge_gate")
                    if isinstance(payload.get("trade_context_snapshot"), dict)
                    else None
                ),
            },
            "raw_payload": payload,
        }

        repo = TradeContextSnapshotRepository(database_url)
        repo.save(
            TradeContextSnapshot(
                trade_id=str(trade_id),
                db_trade_id=int(db_trade_id) if db_trade_id is not None else None,
                run_id=str(payload.get("run_id") or ""),
                symbol=str(payload.get("symbol") or ""),
                continuous_symbol=str(
                    payload.get("continuous_symbol")
                    or ContinuousContractResolver.resolve(str(payload.get("symbol") or ""))
                    if str(payload.get("symbol") or "")
                    else ""
                ),
                strategy=str(payload.get("strategy") or "UNKNOWN"),
                timeframe=str(payload.get("timeframe") or "UNKNOWN"),
                side=str(payload.get("side") or ""),
                qty=float(payload.get("qty")) if payload.get("qty") is not None else None,
                price=float(payload.get("price")) if payload.get("price") is not None else None,
                reason=str(payload.get("reason") or ""),
                source=str(payload.get("source") or "paper_pipeline"),
                event_type="paper_trade",
                snapshot=snapshot,
            )
        )
        print(f"TRADE_CONTEXT_SNAPSHOT_SAVED trade_id={trade_id}", flush=True)

    except Exception as exc:
        print(
            f"TRADE_CONTEXT_SNAPSHOT_SAVE_FAILED trade_id={trade_id} error={type(exc).__name__}:{exc}",
            flush=True,
        )


class PaperTradingPipeline:
    """MarketData → Strategy → Risk → PaperExecution → publish(FILL) → PM.apply_fill"""

    def __init__(self, bus, portfolio, position_manager, risk, paper, strategy, done=None, filter_engine=None, filter_context_builder=None):
        from finam_core.strategy.mean_reversion import MeanReversionStrategy
        from finam_core.session.session_manager import SessionManager

        self.session = SessionManager()
        self.mean_reversion = MeanReversionStrategy()

        self.bus = bus
        self.portfolio = portfolio
        self.pm = position_manager
        self.risk = risk
        # Русский комментарий: runtime selection gate включается перед RiskEngine.
        self.runtime_selection_gate = RuntimeSelectionGate()
        self.paper = paper
        # Русский комментарий: runtime_config должен быть создан до первого обращения к EXECUTION_MODE.
        self.runtime_config = RuntimeConfig()
        # Русский комментарий: единый режим исполнения. real_dry_run не отправляет заявки брокеру.
        self.execution_mode = self.runtime_config.get("EXECUTION_MODE", "paper").strip().lower()
        self.orders_client = FinamOrdersClient(position_qty_provider=RealPositionQtyProvider(self))
        self.real_execution = RealExecutionEngine(orders_client=self.orders_client)
        # Русский комментарий: менеджер безопасной замены защитных стоп-заявок.
        self.cancel_replace_stop_manager = CancelReplaceStopManager(
            orders_client=self.orders_client,
            order_event_store=getattr(self.real_execution, "order_event_store", None),
        )
        # Русский комментарий: OCO manager связывает пары условных заявок и ставит SL/TP после исполнения одной из них.
        self.oco_order_manager = OcoOrderManager(
            orders_client=self.orders_client,
            order_event_store=getattr(self.real_execution, "order_event_store", None),
        )
        self.fee_tax = FeeTaxModel()
        self.strategy = strategy
        # Русский коммент: единый pre-risk фильтр сигналов. По умолчанию отключён.
        self.filter_engine = filter_engine
        self.filter_context_builder = filter_context_builder
        self._done = done

        self._mkt: dict[str, dict] = {}
        # === MTF buffers ===
        self._mtf = {}  # symbol -> buffers
        self.features = {}  # live feature buffers
        self._filled_once = False

        # Русский коммент: троттлинг логов котировок
        self._last_quote_log_ts = 0.0
        self._quote_log_every = float(os.getenv("QUOTE_LOG_EVERY", "0"))  # 0 = выключено
        self.trailing_exit = TrailingExitEngine()
        # Русский комментарий: dry-run менеджер trailing stop-заявок. В dry-run заявки брокеру не отправляются.
        self.trailing_order_manager = TrailingOrderManager(
            trail_abs=float(os.getenv("TRAILING_ORDER_TRAIL_ABS", "0.40")),
            min_replace_step=float(os.getenv("TRAILING_ORDER_MIN_REPLACE_STEP", "0.10")),
        )
        # Русский комментарий:
        # Реальный lifecycle защитных stop-заявок выключен по умолчанию hard-gate env.
        # Русский комментарий:
        # В dry-run не создаём FinamOrdersClient, чтобы не требовать real broker credentials.
        self.real_protective_lifecycle = None
        if (
            os.getenv("REAL_PROTECTIVE_LIFECYCLE_ENABLED", "0") == "1"
            and os.getenv("TRAILING_ORDER_DRY_RUN", "1") == "0"
        ):
            self.real_protective_lifecycle = RealProtectiveLifecycleEngine(
                orders_client=FinamOrdersClient(),
                link_repository=ProtectiveOrderLinkRepository(),
            )
        # Русский комментарий:
        # ProfitLockEngine сопровождает прибыль до trailing:
        # qty=1 — только перенос stop; qty>1 — partial close + перенос stop.
        self.profit_lock_engine = ProfitLockEngine()
        self.take_profit_engine = TakeProfitEngine()
        self.partial_close_engine = PartialCloseEngine()
        self.position_lifecycle_state_repository = PositionLifecycleStateRepository()
        self.position_lifecycle_reconciler = PositionLifecycleReconciler()
        self.position_lifecycle_reconcile_event_repository = PositionLifecycleReconcileEventRepository()
        self.position_lifecycle_self_healer = PositionLifecycleSelfHealer()
        self.position_lifecycle_service = PositionLifecycleService(self)
        self.exit_lifecycle_manager = ExitLifecycleManager(self)
        self.take_profit_event_repository = TakeProfitEventRepository()
        self.profit_lock_event_repository = ProfitLockEventRepository()
        self._trailing_order_stop_by_symbol = {}

        # Русский комментарий:
        # Защита от AttributeError в multi-symbol strategy path.
        # Если strategy map не создана отдельной фабрикой, держим пустой словарь.
        self.strategy_by_symbol = getattr(self, "strategy_by_symbol", {})
        # Русский комментарий:
        # Новый runtime-слой стратегий. Старый strategy_by_symbol оставлен
        # временно для обратной совместимости и безопасного rollback.
        self.strategy_runtime = StrategyRuntime()
        self.quote_signal_processor = QuoteSignalProcessor(self.strategy_runtime)
        self.signal_router = QuoteSignalRouter(self.quote_signal_processor)
        self.signal_intent_router = SignalIntentRouter()
        # Русский комментарий: отдельный router валидирует уже сформированный raw_intent.
        self.signal_intent_router = SignalIntentRouter()
        self.pipeline_orchestrator = PipelineOrchestrator(self)
        self.trend_filter = TrendFilter()
        self.trailing_order_event_repository = TrailingOrderEventRepository()
        # Русский комментарий: read-only сопоставление позиций и активных защитных заявок.
        self.position_order_tracker = PositionOrderTracker()
        self._broker_orders_by_symbol = {}
        # Русский комментарий: SubscribeOrders read-only listener обновляет broker orders snapshot.
        self._subscribe_orders_listener_started = False
        self._subscribe_orders_last_error = None
        # Русский комментарий: throttle для SubscribeOrders, чтобы не открывать stream на каждый quote.
        self._subscribe_orders_next_poll_ts = 0.0
        self._subscribe_orders_empty_poll_count = 0
        self.fill_event_router = None
        self._position_order_state_last_key = {}
        # Русский комментарий: read-only сверка локальной позиции с брокером перед real orders.
        self.broker_reconciliation = BrokerReconciliationEngine(
            qty_tolerance=float(os.getenv("BROKER_RECONCILIATION_QTY_TOLERANCE", "1e-9"))
        )
        # Русский комментарий: authoritative repair layer. По умолчанию только halt, без автопочинки.
        self.portfolio_reconciliation_repair = PortfolioReconciliationRepair(
            qty_tolerance=float(os.getenv("BROKER_RECONCILIATION_QTY_TOLERANCE", "1e-9"))
        )
        self._trading_halt_reason = None
        # Русский комментарий: DB-driven политика горизонта позиции.
        self.position_intent_repo = PositionIntentRepository(
            ttl_sec=float(os.getenv("POSITION_INTENT_CACHE_TTL_SEC", "60"))
        )
        # Русский комментарий: state machine не задерживает выход, а только подавляет дубли exit-заявок.
        self.exit_state_machine = ExitStateMachine(
            ttl_sec=float(os.getenv("EXIT_STATE_TTL_SEC", "30"))
        )
        self._cooldown_until = {}
        self.notifier = TelegramNotifier()
        self.pg_logger = PostgresLogger()
        self.strategy_runtime_control_service = StrategyRuntimeControlService(self.pg_logger)
        self.regime_runtime_control_service = RegimeRuntimeControlService(self.pg_logger)
        # Русский комментарий: gate-сервисы должны существовать до создания EntryGateCoordinator.
        if not hasattr(self, "trade_gate_service"):
            self.trade_gate_service = TradeGateService(
                base_cooldown_sec=float(os.getenv("TRADE_COOLDOWN_SEC", "45")),
                max_trades_per_hour=int(os.getenv("MAX_TRADES_PER_HOUR", "5")),
                max_trades_per_symbol=int(os.getenv("MAX_TRADES_PER_SYMBOL", "2")),
            )

        if not hasattr(self, "trend_gate_service"):
            self.trend_gate_service = TrendGateService()

        if not hasattr(self, "strategy_runtime_control_service"):
            self.strategy_runtime_control_service = StrategyRuntimeControlService(self.pg_logger)

        if not hasattr(self, "regime_runtime_control_service"):
            self.regime_runtime_control_service = RegimeRuntimeControlService(self.pg_logger)

        self.entry_gate_coordinator = EntryGateCoordinator(
            trade_gate_service=self.trade_gate_service,
            runtime_control_service=self.strategy_runtime_control_service,
            trend_gate_service=self.trend_gate_service,
            regime_runtime_control_service=self.regime_runtime_control_service,
        )
        self.trade_gate_service = TradeGateService(
            base_cooldown_sec=float(os.getenv("TRADE_COOLDOWN_SEC", "45")),
            max_trades_per_hour=int(os.getenv("MAX_TRADES_PER_HOUR", "5")),
            max_trades_per_symbol=int(os.getenv("MAX_TRADES_PER_SYMBOL", "2")),
        )
        self.strategy_runtime_control_service = StrategyRuntimeControlService(self.pg_logger)
        self.regime_runtime_control_service = RegimeRuntimeControlService(self.pg_logger)
        self.entry_gate_coordinator = EntryGateCoordinator(
            trade_gate_service=self.trade_gate_service,
            runtime_control_service=self.strategy_runtime_control_service,
            trend_gate_service=self.trend_gate_service,
            regime_runtime_control_service=self.regime_runtime_control_service,
        )
        self.trade_gate_service = TradeGateService(
            base_cooldown_sec=float(os.getenv("TRADE_COOLDOWN_SEC", "45")),
            max_trades_per_hour=int(os.getenv("MAX_TRADES_PER_HOUR", "5")),
            max_trades_per_symbol=int(os.getenv("MAX_TRADES_PER_SYMBOL", "2")),
        )
        # Русский комментарий: fill persistence должен работать даже если SignalRepository недоступен.
        self.signal_repository = None
        self.closed_trade_attribution_service = None

        try:
            conn = getattr(self.pg_logger, "conn", None)
            if conn is not None:
                self.signal_repository = SignalRepository(conn)
                self.closed_trade_attribution_service = ClosedTradeAttributionService(self.signal_repository)
        except Exception as exc:
            print(f"PIPE_SIGNAL_REPOSITORY_INIT_FAILED error={exc}", flush=True)

        self.fill_persistence_service = FillPersistenceService(
            pg_logger=self.pg_logger,
            attribution_service=self.closed_trade_attribution_service,
        )
        # Русский коммент: агрегатор закрытых M1/M5/M15 свечей из live quote потока.
        self.mtf_aggregator = MTFBarAggregator(("M1", "M5", "M15"))
        self.exit_engine = SlTpCooldownEngine()
        self.vol_risk = VolatilityRiskEngine()
        self.live_atr = LiveAtrEstimator()
        self.portfolio_heat = PortfolioHeatEngine()
        self.kill_switch = KillSwitchEngine()
        self.correlation_risk = CorrelationRiskEngine()
        self.risk_recorder = RiskDecisionRecorder(self.pg_logger)
        self.risk_router = RiskRouter(self)

        self.edge_gate_strict_mode_v1 = EdgeGateStrictModeV1(
            "runtime/edge_gate_strict_mode_v1.json"
        )

        self.runtime_edge_governance_soft_block_v1 = RuntimeEdgeGovernanceSoftBlockV1()
        self.runtime_governance_live_accumulator_v1 = RuntimeGovernanceLiveAccumulatorV1()
        self.signal_router = QuoteSignalRouter(self.quote_signal_processor)
        self.signal_intent_router = SignalIntentRouter()
        # Русский комментарий: отдельный router валидирует уже сформированный raw_intent.
        self.signal_intent_router = SignalIntentRouter()
        # Русский комментарий: EntryPointSelector рассчитывает entry/stop/take до выбора типа заявки.
        self.entry_point_selector = EntryPointSelector(
            tick_size=float(os.getenv("ENTRY_TICK_SIZE", "0.01")),
            stop_atr_mult=float(os.getenv("ENTRY_STOP_ATR_MULT", "1.5")),
            take_atr_mult=float(os.getenv("ENTRY_TAKE_ATR_MULT", "2.0")),
        )
        # Русский комментарий: ExecutionDecisionLayer выбирает MARKET/STOP/LIMIT/SKIP, но не отправляет заявки.
        self.execution_decision_layer = ExecutionDecisionLayer()
        # Русский комментарий: OrderRouter строит маршрут заявки после ExecutionDecisionLayer, не вмешиваясь в raw_fill path.
        self.order_router = OrderRouter()
        # Русский комментарий: ExecutionDispatcher исполняет маршрут STOP/LIMIT/MARKET, выбранный OrderRouter.
        self.execution_dispatcher = ExecutionDispatcher(
            orders_client=self.orders_client,
            real_execution_engine=self.real_execution,
        )
        self.execution_gateway = ExecutionGateway(self)

        # Русский комментарий: Coordinator orchestrates kernel/execution/reconciliation.
        self.engine_coordinator = TradingEngineCoordinator(
            pipeline_kernel=getattr(self, 'pipeline_kernel', None),
            execution_gateway=getattr(self, 'execution_gateway', None),
            portfolio_reconciliation_layer=getattr(self, 'portfolio_reconciliation_layer', None),
        )
        self.regime_engine = RegimeEngine()
        # Русский комментарий: BRRegimeLayer блокирует слабые breakout-сигналы до PaperExecution.
        self.br_regime_layer = BRRegimeLayer()
        # Русский комментарий: volatility-aware параметры для BR regime/confirmation.
        self.br_volatility_intelligence = BRVolatilityIntelligence()
        # Русский комментарий: BAR VOLUME feature layer для подтверждения BR breakout/impulse.
        self.br_volume_features = BarVolumeFeatureEngine(
            lookback=int(os.getenv("BR_VOLUME_LOOKBACK", "20")),
            confirm_ratio=float(os.getenv("BR_VOLUME_CONFIRM_RATIO", "1.5")),
        )
        self._br_volume_bars_by_symbol = {}
        # Русский комментарий: pending confirmation state для слабых BR breakout.
        self._br_confirm_pending = {}
        self._broker_position_qty_by_symbol = {}
        # Русский комментарий: hard-gate по рассинхрону брокерской и локальной позиции.
        self._broker_position_halt_by_symbol = {}
        self._broker_position_halt_last_key = None
        self._broker_position_hard_gate_order_block_seen = set()
        # Русский комментарий: защита от новых входов при broker position без stop/take.
        self._broker_protection_missing_seen = set()
        # Русский комментарий: restart recovery выполняется один раз после запуска pipeline.
        self._restart_recovery_done = False
        self.restart_recovery_coordinator = RestartRecoveryCoordinator(self)
        # Русский комментарий: дедупликация повторяющихся operational-логов.
        self._dedup_log_seen = {}
        # Русский комментарий: read-only слой активных брокерских заявок.
        self.open_orders_sync = OpenOrdersSync()

        # Русский комментарий: единый слой orchestration для reconciliation path.
        self.portfolio_reconciliation_layer = PortfolioReconciliationLayer(
            position_sync_layer=None,
            open_orders_sync=self.open_orders_sync,
            reconciliation_repair=self.portfolio_reconciliation_repair,
        )

        # Русский комментарий: обновляем Coordinator после создания reconciliation layer.
        if hasattr(self, "engine_coordinator"):
            self.engine_coordinator.portfolio_reconciliation_layer = self.portfolio_reconciliation_layer

        self._broker_orders_by_symbol = {}
        self._broker_orders_sync_ts = 0.0
        self._broker_position_avg_by_symbol = {}

        # Русский комментарий:
        # Rate-limit для Incremental Exit Intelligence advisory,
        # чтобы не спамить лог на каждом quote/tick.
        self._last_incremental_exit_advice_by_symbol = {}
        self._incremental_exit_advice_every_sec = float(
            os.getenv("INCREMENTAL_EXIT_ADVICE_EVERY_SEC", "60")
        )

        # Русский комментарий:
        # Rate-limit для Incremental Exit Intelligence advisory,
        # чтобы не спамить лог на каждом quote/tick.
        self._last_incremental_exit_advice_by_symbol = {}
        self._incremental_exit_advice_every_sec = float(
            os.getenv("INCREMENTAL_EXIT_ADVICE_EVERY_SEC", "60")
        )
        self._broker_position_sync_ts = 0.0
        # Русский комментарий: BR_CONSERVATIVE_BREAKOUT работает только в PAPER и только как генератор сигналов.
        self.br_breakout_enabled = (
            self.runtime_config.get("EXECUTION_MODE", "paper").lower() == "paper"
            and os.getenv("ENABLE_BR_CONSERVATIVE_BREAKOUT", "0") == "1"
        )
        self.br_breakout_symbol = os.getenv("BR_BREAKOUT_SYMBOL", "BRM6@RTSX")
        self.br_breakout = BrConservativeBreakout(symbol=self.br_breakout_symbol) if self.br_breakout_enabled else None

        # Русский комментарий: NG_CONSERVATIVE_BREAKOUT_M1 работает только в PAPER и только как генератор M1-сигналов.
        self.ng_m1_breakout_enabled = (
            self.runtime_config.get("EXECUTION_MODE", "paper").lower() == "paper"
            and os.getenv("ENABLE_NG_CONSERVATIVE_BREAKOUT_M1", "0") == "1"
        )
        self.ng_m1_breakout_symbol = os.getenv("NG_M1_BREAKOUT_SYMBOL", "NGM6@RTSX")
        self.ng_m1_breakout = (
            NgConservativeBreakoutM1(symbol=self.ng_m1_breakout_symbol)
            if self.ng_m1_breakout_enabled
            else None
        )

        # Русский комментарий:
        # Advisory-only лог выбранной exit policy для BR breakout.
        # Не влияет на заявки, RiskEngine, stop/take и execution.
        log_exit_policy_advisory(
            database_url=os.getenv('DATABASE_URL') or os.getenv('POSTGRES_DSN') or '',
            symbol=self.br_breakout_symbol,
            strategy="br_conservative_breakout",
            timeframe=os.getenv("BR_BREAKOUT_TIMEFRAME", "M5").strip().upper(),
        )

        log_portfolio_heat_advisory(
            database_url=os.getenv("DATABASE_URL") or os.getenv("POSTGRES_DSN") or "",
        )

        log_portfolio_governance_advisory(
            database_url=os.getenv("DATABASE_URL") or os.getenv("POSTGRES_DSN") or "",
            symbol=self.br_breakout_symbol,
            strategy=SymbolStrategyResolver(
                os.getenv("DATABASE_URL") or os.getenv("POSTGRES_DSN") or ""
            ).resolve(self.br_breakout_symbol),
            timeframe=os.getenv("BR_BREAKOUT_TIMEFRAME", "M5").strip().upper(),
        )

        log_runtime_governance_decision(
            database_url=os.getenv("DATABASE_URL") or os.getenv("POSTGRES_DSN") or "",
            symbol=self.br_breakout_symbol,
            strategy=SymbolStrategyResolver(
                os.getenv("DATABASE_URL") or os.getenv("POSTGRES_DSN") or ""
            ).resolve(self.br_breakout_symbol),
            timeframe=os.getenv("BR_BREAKOUT_TIMEFRAME", "M5").strip().upper(),
        )
        self.finam_limits_adapter = FinamLimitsAdapter()
        self.regime_policy = RegimePolicy()
        self.symbol_drawdown_guard = SymbolDrawdownGuard()
        self.symbol_loss_streak_guard = SymbolLossStreakGuard()
        self.portfolio_guard = PortfolioGuard()

        # Русский комментарий: после рестарта восстанавливаем PnL-состояние для kill-switch.
        self._restore_portfolio_stats_from_postgres()
        # === REGIME CONFIG (единая точка управления) ===
        self.regime_enabled = os.getenv("REGIME_ENABLE", "1") == "1"

        # параметры (можно потом вынести в config.py)
        self.regime_min_atr_pct = float(os.getenv("REGIME_MIN_ATR_PCT", "0.001"))
        self.regime_trend_mode = os.getenv("REGIME_TREND_MODE", "ema")  # ema / simple

        # debug
        LOG.info(
            "REGIME INIT enabled=%s min_atr_pct=%.5f trend_mode=%s",
            self.regime_enabled,
            self.regime_min_atr_pct,
            self.regime_trend_mode,
        )
        self._regime_last_log_ts = 0.0

    def _record_live_quote_to_storage(self, symbol: str, price: float, volume: float, ts) -> None:
        """Русский коммент: сохраняет live tick и закрытые MTF-свечи в PostgreSQL."""
        try:
            self.pg_logger.log_market_tick(
                symbol=symbol,
                price=float(price),
                volume=float(volume or 0.0),
            )
        except Exception as exc:
            LOG.warning("PIPE_MARKET_TICK_LOG_FAILED symbol=%s error=%s", symbol, exc)

        try:
            closed_bars = self.mtf_aggregator.update(
                symbol=symbol,
                price=float(price),
                volume=float(volume or 0.0),
                ts=_coerce_mtf_ts(ts),
            )

            for bar in closed_bars:
                self.pg_logger.log_market_bar(
                    symbol=bar.symbol,
                    timeframe=bar.timeframe,
                    ts=bar.ts,
                    open_price=bar.open,
                    high_price=bar.high,
                    low_price=bar.low,
                    close_price=bar.close_price,
                    volume=bar.volume,
                )
                self._process_br_closed_bar_for_paper_signal(bar)
                self._process_ng_m1_closed_bar_for_paper_signal(bar)
                LOG.info(
                    "PIPE_MTF_BAR_CLOSED symbol=%s tf=%s ts=%s close=%s volume=%s",
                    bar.symbol,
                    bar.timeframe,
                    bar.ts,
                    bar.close_price,
                    bar.volume,
                )
        except Exception as exc:
            LOG.warning("PIPE_MTF_AGG_FAILED symbol=%s error=%s", symbol, exc)


    def _current_position_qty_for_symbol(self, symbol: str) -> float:
        """Русский комментарий: текущая PAPER-позиция по символу для anti-reentry."""
        pm = getattr(self, "position_manager", None) or getattr(self, "pm", None)
        if pm is None:
            pm = getattr(self, "positions", None) or getattr(self, "position_mgr", None)

        positions = getattr(pm, "positions", None) if pm is not None else None
        if isinstance(positions, dict) and symbol in positions:
            pos = positions[symbol]
            if isinstance(pos, dict):
                return float(pos.get("qty") or pos.get("quantity") or 0.0)
            for attr in ("qty", "quantity", "position_qty"):
                if hasattr(pos, attr):
                    return float(getattr(pos, attr) or 0.0)

        try:
            return float(self._current_replay_position_for_br(symbol))
        except Exception:
            return 0.0

    def _entry_cooldown_sec_for_symbol(self, symbol: str) -> float:
        """Русский комментарий: cooldown повторного входа по символу через env."""
        safe_key = str(symbol).replace("@", "_").replace(".", "_").replace("-", "_").upper()
        raw = os.getenv(
            f"ENTRY_COOLDOWN_SEC_{safe_key}",
            os.getenv("ENTRY_COOLDOWN_SEC_DEFAULT", "60"),
        )
        return float(raw or 0.0)

    def _anti_reentry_allows(self, symbol: str, side: str) -> tuple[bool, str]:
        """Русский комментарий: запрещает повторный вход при открытой позиции или активном cooldown."""
        qty = self._current_position_qty_for_symbol(symbol)
        if abs(qty) > 0:
            return False, f"ANTI_REENTRY_OPEN_POSITION symbol={symbol} qty={qty}"

        cooldown = self._entry_cooldown_sec_for_symbol(symbol)
        if cooldown <= 0:
            return True, "ANTI_REENTRY_OK_NO_COOLDOWN"

        state = getattr(self, "_anti_reentry_last_entry_ts", None)
        if state is None:
            state = {}
            self._anti_reentry_last_entry_ts = state

        key = f"{symbol}:{side}"
        now = time.monotonic()
        last = float(state.get(key, 0.0) or 0.0)

        if last > 0 and now - last < cooldown:
            return False, (
                f"ANTI_REENTRY_COOLDOWN symbol={symbol} side={side} "
                f"left={round(cooldown - (now - last), 2)}"
            )

        return True, "ANTI_REENTRY_OK"

    def _mark_anti_reentry_entry(self, symbol: str, side: str) -> None:
        """Русский комментарий: фиксирует успешный вход для cooldown."""
        state = getattr(self, "_anti_reentry_last_entry_ts", None)
        if state is None:
            state = {}
            self._anti_reentry_last_entry_ts = state

        state[f"{symbol}:{side}"] = time.monotonic()
        self._anti_reentry_entry_count = int(getattr(self, "_anti_reentry_entry_count", 0)) + 1


    def _pipeline_log_throttle_allow(self, key: str, interval_sec: float | None = None) -> bool:
        """Русский комментарий: runtime throttle для шумных повторяющихся логов pipeline."""
        raw_interval = os.getenv("LOG_THROTTLE_SEC", "30")
        interval = float(raw_interval or 30.0) if interval_sec is None else float(interval_sec)

        state = getattr(self, "_pipeline_log_throttle_state", None)
        if state is None:
            state = {}
            self._pipeline_log_throttle_state = state

        now = time.monotonic()
        last = float(state.get(key, 0.0) or 0.0)

        if last > 0 and now - last < interval:
            return False

        state[key] = now
        return True

    def _should_log_routed_signal(self, routed) -> bool:
        """Русский комментарий: duplicate_signal по умолчанию не печатаем, чтобы не забивать live-paper лог."""
        reason = str(getattr(routed, "reason", "") or "")
        if reason != "duplicate_signal":
            return True

        if os.getenv("LOG_DUPLICATE_SIGNAL", "0") != "1":
            return False

        intent = getattr(routed, "intent", None)
        symbol = str(getattr(intent, "symbol", "") or "unknown")
        side = str(getattr(intent, "side", "") or "unknown")
        source = str(getattr(intent, "source", "") or "unknown")
        key = f"duplicate_signal:{symbol}:{side}:{source}"
        return self._pipeline_log_throttle_allow(key)

    def attach(self):
        # Русский коммент: Pipeline B — подписываемся на QUOTE, а FILL применяем централизованно.
        self.bus.subscribe("QUOTE", self._on_quote)
        self.bus.subscribe("FILL", self._on_fill)
        LOG.debug("PIPE attach(): subscribed QUOTE/FILL")


    def _portfolio_stats_state(self) -> dict:
        """Русский комментарий: runtime-состояние PnL портфеля для live-paper."""
        state = getattr(self, "_portfolio_stats", None)
        if state is None:
            state = {
                "realized_pnl_total": 0.0,
                "realized_pnl_by_symbol": {},
                "equity_peak": 0.0,
                "max_drawdown": 0.0,
            }
            self._portfolio_stats = state
        return state

    def _update_portfolio_stats(self, symbol: str, realized_pnl: float) -> dict:
        """Русский комментарий: обновляет накопленный realized PnL и drawdown по live-paper."""
        state = self._portfolio_stats_state()
        pnl = float(realized_pnl or 0.0)

        state["realized_pnl_total"] = float(state.get("realized_pnl_total", 0.0) or 0.0) + pnl

        by_symbol = state.setdefault("realized_pnl_by_symbol", {})
        by_symbol[symbol] = float(by_symbol.get(symbol, 0.0) or 0.0) + pnl

        equity = float(state["realized_pnl_total"])
        state["equity_peak"] = max(float(state.get("equity_peak", 0.0) or 0.0), equity)

        drawdown = equity - float(state.get("equity_peak", 0.0) or 0.0)
        state["max_drawdown"] = min(float(state.get("max_drawdown", 0.0) or 0.0), drawdown)

        return state


    def _portfolio_kill_switch_allows(self) -> tuple[bool, str]:
        """Русский комментарий: портфельный kill-switch по cumulative PnL и max drawdown."""
        state = self._portfolio_stats_state()

        cumulative_pnl = float(state.get("realized_pnl_total", 0.0) or 0.0)
        max_drawdown = float(state.get("max_drawdown", 0.0) or 0.0)

        max_loss = float(os.getenv("PORTFOLIO_MAX_CUMULATIVE_LOSS", "0") or 0.0)
        if max_loss > 0 and cumulative_pnl <= -abs(max_loss):
            return False, f"PORTFOLIO_CUMULATIVE_LOSS_LIMIT pnl={round(cumulative_pnl, 4)} limit={-abs(max_loss)}"

        dd_limit = float(os.getenv("PORTFOLIO_MAX_DRAWDOWN", "0") or 0.0)
        if dd_limit > 0 and max_drawdown <= -abs(dd_limit):
            return False, f"PORTFOLIO_DRAWDOWN_LIMIT drawdown={round(max_drawdown, 4)} limit={-abs(dd_limit)}"

        return True, "PORTFOLIO_KILL_SWITCH_OK"


    def _postgres_dsn_for_pnl(self) -> str:
        """Русский комментарий: DSN PostgreSQL для записи live-paper PnL."""
        explicit = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_DSN")
        if explicit:
            return explicit

        host = os.getenv("PGHOST", "127.0.0.1")
        port = os.getenv("PGPORT", "5432")
        db = os.getenv("PGDATABASE", "finam")
        user = os.getenv("PGUSER", "finam")
        password = os.getenv("PGPASSWORD", "finam")

        return f"host={host} port={port} dbname={db} user={user} password={password}"


    def _restore_portfolio_stats_from_postgres(self) -> None:
        """Русский комментарий: восстанавливает cumulative PnL/max drawdown из PostgreSQL после рестарта."""
        try:
            import psycopg2

            with psycopg2.connect(self._postgres_dsn_for_pnl()) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT cumulative_pnl, max_drawdown
                        FROM portfolio_pnl_events
                        ORDER BY id DESC
                        LIMIT 1
                        """
                    )
                    row = cur.fetchone()

            if not row:
                return

            cumulative_pnl = float(row[0] or 0.0)
            max_drawdown = float(row[1] or 0.0)

            state = self._portfolio_stats_state()
            state["realized_pnl_total"] = cumulative_pnl
            state["equity_peak"] = max(cumulative_pnl, 0.0)
            state["max_drawdown"] = max_drawdown

            print(
                f"PIPE_PORTFOLIO_STATE_RESTORED cumulative_pnl={round(cumulative_pnl, 4)} "
                f"max_drawdown={round(max_drawdown, 4)}",
                flush=True,
            )

        except Exception as exc:
            LOG.warning("PIPE_PORTFOLIO_STATE_RESTORE_FAILED error=%s", exc)


    def _log_portfolio_pnl_to_postgres(
        self,
        *,
        symbol: str,
        realized_pnl: float,
        cumulative_pnl: float,
        max_drawdown: float,
        reason: str,
        fill,
        extra: dict | None = None,
    ) -> None:
        """Русский комментарий: пишет live-paper PnL event в PostgreSQL без влияния на торговый цикл."""
        try:
            import psycopg2

            run_id = str(getattr(self, "run_id", "live-paper"))
            payload = {
                "run_id": run_id,
            "continuous_symbol": continuous_symbol,
                "paper_only": True,
                "reason": reason,
                "fill_id": str(getattr(fill, "fill_id", "") or ""),
                "side": str(getattr(fill, "side", "") or ""),
                "qty": float(getattr(fill, "qty", 0.0) or 0.0),
                "price": float(getattr(fill, "price", 0.0) or 0.0),
                "extra": extra or {},
            }

            with psycopg2.connect(self._postgres_dsn_for_pnl()) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS portfolio_pnl_events (
                            id BIGSERIAL PRIMARY KEY,
                            ts TIMESTAMPTZ NOT NULL DEFAULT now(),
                            run_id TEXT NOT NULL,
                            symbol TEXT NOT NULL,
                            realized_pnl DOUBLE PRECISION NOT NULL,
                            cumulative_pnl DOUBLE PRECISION NOT NULL,
                            max_drawdown DOUBLE PRECISION NOT NULL,
                            reason TEXT,
                            raw_json JSONB NOT NULL DEFAULT '{}'::jsonb
                        )
                        """
                    )
                    cur.execute(
                        """
                        INSERT INTO portfolio_pnl_events (
                            run_id,
                            symbol,
                            realized_pnl,
                            cumulative_pnl,
                            max_drawdown,
                            reason,
                            raw_json
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
                        """,
                        (
                            run_id,
                            symbol,
                            float(realized_pnl),
                            float(cumulative_pnl),
                            float(max_drawdown),
                            reason,
                            json.dumps(payload, ensure_ascii=False),
                        ),
                    )

        except Exception as exc:
            LOG.warning("PIPE_PORTFOLIO_PNL_LOG_FAILED symbol=%s error=%s", symbol, exc)



    def _sync_broker_positions_readonly(self) -> None:
        """Русский комментарий: read-only синхронизация позиций Finam для ExitEngine."""
        if os.getenv("ENABLE_BROKER_POSITION_SYNC", "0") != "1":
            return

        now = time.time()
        interval = float(os.getenv("BROKER_POSITION_SYNC_INTERVAL_SEC", "30"))
        if now - float(getattr(self, "_broker_position_sync_ts", 0.0) or 0.0) < interval:
            return

        self._broker_position_sync_ts = now

        try:
            import grpc
            from finam_core.auth.token_manager import FinamTokenManager
            from finam_proto.grpc.tradeapi.v1.accounts import accounts_service_pb2, accounts_service_pb2_grpc

            account_id = os.getenv("FINAM_ACCOUNT_ID", "").strip()
            if not account_id:
                print("PIPE_BROKER_POSITION_SYNC_SKIP reason=FINAM_ACCOUNT_ID_not_set", flush=True)
                return

            jwt = FinamTokenManager().get_token()
            endpoint = os.getenv("FINAM_GRPC_ENDPOINT", "api.finam.ru:443").strip()

            channel = grpc.secure_channel(endpoint, grpc.ssl_channel_credentials())
            stub = accounts_service_pb2_grpc.AccountsServiceStub(channel)

            resp = stub.GetAccount(
                accounts_service_pb2.GetAccountRequest(account_id=account_id),
                metadata=(("authorization", f"Bearer {jwt}"),),
                timeout=float(os.getenv("BROKER_POSITION_SYNC_TIMEOUT_SEC", "10")),
            )

            qty_by_symbol = {}
            avg_by_symbol = {}

            for pos in resp.positions:
                symbol = str(getattr(pos, "symbol", "") or "")
                if not symbol:
                    continue

                try:
                    qty = float(getattr(getattr(pos, "quantity", None), "value", "0") or 0.0)
                except Exception:
                    qty = 0.0

                try:
                    avg = float(getattr(getattr(pos, "average_price", None), "value", "0") or 0.0)
                except Exception:
                    avg = 0.0

                qty_by_symbol[symbol] = qty
                if avg > 0:
                    avg_by_symbol[symbol] = avg

            self._broker_position_qty_by_symbol = qty_by_symbol
            self._broker_position_avg_by_symbol = avg_by_symbol
            self._refresh_broker_position_hard_gate()

            snapshot_key = tuple(sorted(qty_by_symbol.items()))
            last_snapshot_key = getattr(self, "_broker_position_last_snapshot_key", None)
            last_sync_log_ts = float(getattr(self, "_broker_position_last_sync_log_ts", 0.0) or 0.0)
            heartbeat_sec = float(os.getenv("BROKER_POSITION_SYNC_LOG_HEARTBEAT_SEC", "300"))
            now_log_ts = time.time()

            if snapshot_key != last_snapshot_key or now_log_ts - last_sync_log_ts >= heartbeat_sec:
                print(
                    f"PIPE_BROKER_POSITION_SYNC_OK count={len(qty_by_symbol)} "
                    f"{self.br_breakout_symbol}={qty_by_symbol.get(self.br_breakout_symbol, 0.0)} "
                    f"{self.br_breakout_symbol}_avg={avg_by_symbol.get(self.br_breakout_symbol, 0.0)}",
                    flush=True,
                )
                self._broker_position_last_snapshot_key = snapshot_key
                self._broker_position_last_sync_log_ts = now_log_ts

        except Exception as exc:
            self._log_dedup(
                f"PIPE_BROKER_POSITION_SYNC_ERROR:{type(exc).__name__}",
                f"PIPE_BROKER_POSITION_SYNC_ERROR error={exc}",
            )


    def _local_position_qty_for_hard_gate(self, symbol: str) -> float:
        """Русский комментарий: безопасно получает локальное количество позиции для broker hard-gate."""
        if os.getenv("BROKER_POSITION_HARD_GATE_USE_BROKER_AS_LOCAL", "0") == "1":
            return float((getattr(self, "_broker_position_qty_by_symbol", {}) or {}).get(symbol, 0.0) or 0.0)

        try:
            qty = self._position_qty_for_symbol(symbol)
            return float(qty or 0.0)
        except Exception:
            pass

        try:
            pm = self._get_position_manager_for_exit()
            positions = getattr(pm, "positions", {}) or {}
            pos = positions.get(symbol)
            if pos is None:
                return 0.0
            for field in ("qty", "quantity", "position_qty", "size"):
                value = getattr(pos, field, None)
                if value is not None:
                    return float(value or 0.0)
        except Exception:
            pass

        return 0.0


    def _refresh_broker_position_hard_gate(self) -> None:
        """Русский комментарий: ставит/снимает HALT по символам при рассинхроне broker/local qty."""
        if os.getenv("ENABLE_BROKER_POSITION_HARD_GATE", "0") != "1":
            return

        tolerance = float(os.getenv("BROKER_POSITION_HARD_GATE_QTY_TOLERANCE", "1e-9"))
        broker_positions = getattr(self, "_broker_position_qty_by_symbol", {}) or {}
        symbols = set(broker_positions.keys())

        try:
            pm = self._get_position_manager_for_exit()
            symbols.update((getattr(pm, "positions", {}) or {}).keys())
        except Exception:
            pass

        new_halts = {}
        for symbol in sorted(symbols):
            local_qty = self._local_position_qty_for_hard_gate(symbol)
            broker_qty = float(broker_positions.get(symbol, 0.0) or 0.0)
            if abs(local_qty - broker_qty) > tolerance:
                new_halts[symbol] = f"broker_position_desync:{symbol}:local={local_qty}:broker={broker_qty}"

        old_halts = getattr(self, "_broker_position_halt_by_symbol", {}) or {}
        if new_halts != old_halts:
            for symbol, reason in new_halts.items():
                if old_halts.get(symbol) != reason:
                    print(f"PIPE_BROKER_POSITION_HARD_GATE_ON symbol={symbol} reason={reason}", flush=True)

            for symbol in sorted(set(old_halts.keys()) - set(new_halts.keys())):
                print(f"PIPE_BROKER_POSITION_HARD_GATE_OFF symbol={symbol}", flush=True)

            self._broker_position_halt_by_symbol = new_halts


    def _broker_protection_gate_allows_order(self, symbol: str, side: str, current_qty: float) -> tuple[bool, str]:
        """Русский комментарий: запрещает новые входы, если брокерская позиция не защищена stop/take."""
        if os.getenv("ENABLE_BROKER_PROTECTION_GATE", "0") != "1":
            return True, "broker_protection_gate_disabled"

        broker_qty = float((getattr(self, "_broker_position_qty_by_symbol", {}) or {}).get(symbol, 0.0) or 0.0)
        if abs(broker_qty) <= 1e-9:
            return True, "broker_protection_gate_no_broker_position"

        order_side = str(side or "").upper()
        is_reduce = (broker_qty > 0 and order_side == "SELL") or (broker_qty < 0 and order_side == "BUY")
        if is_reduce:
            return True, "broker_protection_gate_reduce_allowed"

        orders = (getattr(self, "_broker_orders_by_symbol", {}) or {}).get(symbol, [])
        active_statuses = {"WATCHING", "ACTIVE", "WORKING", "ACCEPTED", "NEW", "PARTIAL_FILLED"}
        expected_protection_side = "SELL" if broker_qty > 0 else "BUY"

        for order in orders:
            order_status = str(order.get("status") or "").upper()
            if order_status and order_status not in active_statuses:
                continue

            order_side = str(order.get("side") or "").upper()
            if order_side != expected_protection_side:
                continue

            order_type = str(order.get("order_type") or order.get("type") or "").upper()
            stop_value = order.get("stop_price") or order.get("stop") or order.get("trigger_price")
            price_value = order.get("price") or order.get("limit_price") or order.get("take_price")

            is_stop_like = ("STOP" in order_type) or bool(stop_value)
            is_take_like = ("TAKE" in order_type) or bool(price_value)

            if is_stop_like or is_take_like:
                return True, "broker_protection_gate_protected"

        return False, f"broker_position_unprotected:{symbol}:broker_qty={broker_qty}:orders={len(orders)}"


    def _broker_position_hard_gate_allows_order(self, symbol: str, side: str, current_qty: float) -> tuple[bool, str]:
        """Русский комментарий: при HALT запрещает увеличение риска; сокращение позиции разрешает."""
        if os.getenv("ENABLE_BROKER_POSITION_HARD_GATE", "0") != "1":
            return True, "broker_position_hard_gate_disabled"

        reason = (getattr(self, "_broker_position_halt_by_symbol", {}) or {}).get(symbol)
        if not reason:
            return True, "broker_position_hard_gate_ok"

        local_qty = float(current_qty or 0.0)
        broker_qty = float((getattr(self, "_broker_position_qty_by_symbol", {}) or {}).get(symbol, 0.0) or 0.0)
        order_side = str(side or "").upper()

        # Русский комментарий: при рассинхроне сокращение разрешается только если оно сокращает и broker, и local.
        is_broker_reduce = (broker_qty > 0 and order_side == "SELL") or (broker_qty < 0 and order_side == "BUY")
        is_local_reduce = (local_qty > 0 and order_side == "SELL") or (local_qty < 0 and order_side == "BUY")

        if is_broker_reduce and is_local_reduce:
            return True, "broker_position_hard_gate_reduce_allowed"

        return False, reason


    def _apply_broker_order_event_to_snapshot(self, event: dict) -> None:
        """Русский комментарий: применяет событие SubscribeOrders к _broker_orders_by_symbol."""
        symbol = str(event.get("symbol") or "")
        order_id = str(event.get("order_id") or "")
        if not symbol or not order_id:
            return

        snapshot = getattr(self, "_broker_orders_by_symbol", {}) or {}
        orders = list(snapshot.get(symbol, []) or [])

        status = str(event.get("status") or "").upper()
        inactive_statuses = {"FILLED", "CANCELED", "CANCELLED", "REJECTED", "DISABLED", "EXPIRED", "SL_EXECUTED"}

        if status in inactive_statuses:
            orders = [o for o in orders if str(o.get("order_id") or "") != order_id]
        else:
            replaced = False
            for idx, order in enumerate(orders):
                if str(order.get("order_id") or "") == order_id:
                    orders[idx] = event
                    replaced = True
                    break
            if not replaced:
                orders.append(event)

        if orders:
            snapshot[symbol] = orders
        elif symbol in snapshot:
            del snapshot[symbol]

        self._broker_orders_by_symbol = snapshot


    def _handle_oco_order_event_if_enabled(self, event: dict) -> None:
        """Русский комментарий: передаёт SubscribeOrders/GetOrders event в OcoOrderManager."""
        if os.getenv("ENABLE_OCO_ORDER_MANAGER", "0") != "1":
            return

        manager = getattr(self, "oco_order_manager", None)
        if manager is None:
            return

        result = manager.handle_order_event(event)
        if result is None:
            return

        print(
            f"PIPE_OCO_EVENT_RESULT group_id={result.group_id} status={result.status} "
            f"triggered_order_id={result.triggered_order_id} canceled_order_id={result.canceled_order_id} "
            f"stop_loss_order_id={result.stop_loss_order_id} take_profit_order_id={result.take_profit_order_id} "
            f"reason={result.reason}",
            flush=True,
        )


    def _handle_trade_management_fill_event_if_enabled(self, event: dict) -> None:
        """Русский комментарий: передаёт FILLED события в TradeManagementService."""
        router = getattr(self, "fill_event_router", None)
        if router is None:
            return

        status = str(event.get("status") or "").upper()
        if status not in ("FILLED", "EXECUTED", "ORDER_STATUS_FILLED", "ORDER_STATUS_EXECUTED"):
            return

        try:
            router.on_fill(event)
        except Exception as e:
            self._subscribe_orders_last_error = e

    def _poll_subscribe_orders_once_if_enabled(self) -> None:
        """Русский комментарий: безопасно читает ограниченное число событий SubscribeOrders."""
        if os.getenv("ENABLE_SUBSCRIBE_ORDERS_LISTENER", "0") != "1":
            return

        now_ts = time.time()
        next_poll_ts = float(getattr(self, "_subscribe_orders_next_poll_ts", 0.0) or 0.0)
        if next_poll_ts and now_ts < next_poll_ts:
            return

        poll_interval = float(os.getenv("SUBSCRIBE_ORDERS_POLL_INTERVAL_SEC", "15"))
        self._subscribe_orders_next_poll_ts = now_ts + poll_interval

        orders_client = getattr(self, "orders_client", None) or getattr(self, "finam_orders_client", None)
        if orders_client is None or not hasattr(orders_client, "subscribe_orders"):
            return

        try:
            max_events = int(os.getenv("SUBSCRIBE_ORDERS_MAX_EVENTS_PER_POLL", "1"))
            events = orders_client.subscribe_orders(max_events=max_events)

            for event in events:
                self._apply_broker_order_event_to_snapshot(event)
                self._handle_oco_order_event_if_enabled(event)
                self._handle_trade_management_fill_event_if_enabled(event)

            if events:
                now_log_ts = time.time()
                heartbeat = float(os.getenv("SUBSCRIBE_ORDERS_APPLIED_HEARTBEAT_SEC", "300"))
                last_log_ts = float(getattr(self, "_subscribe_orders_applied_last_log_ts", 0.0) or 0.0)
                if not last_log_ts or now_log_ts - last_log_ts >= heartbeat:
                    print(f"PIPE_SUBSCRIBE_ORDERS_APPLIED events={len(events)}", flush=True)
                    self._subscribe_orders_applied_last_log_ts = now_log_ts

        except Exception as exc:
            key = f"PIPE_SUBSCRIBE_ORDERS_ERROR:{type(exc).__name__}"
            msg = f"PIPE_SUBSCRIBE_ORDERS_ERROR error={exc}"
            if hasattr(self, "_log_dedup"):
                self._log_dedup(
                    key,
                    msg,
                    heartbeat_sec=float(os.getenv("SUBSCRIBE_ORDERS_ERROR_HEARTBEAT_SEC", "300")),
                )
            else:
                print(msg, flush=True)


    def _sync_broker_open_orders_if_needed(self) -> None:
        self._poll_subscribe_orders_once_if_enabled()
        """Русский комментарий: read-only синхронизация активных заявок брокера для PositionOrderTracker."""
        if os.getenv("ENABLE_BROKER_OPEN_ORDERS_SYNC", "0") != "1":
            return

        interval_sec = float(os.getenv("BROKER_OPEN_ORDERS_SYNC_INTERVAL_SEC", "30"))
        now_ts = time.time()
        last_ts = float(getattr(self, "_broker_orders_sync_ts", 0.0) or 0.0)
        if now_ts - last_ts < interval_sec:
            return

        try:
            orders_client = getattr(self, "orders_client", None) or getattr(self, "finam_orders_client", None)
            if orders_client is None:
                return

            if hasattr(orders_client, "list_open_orders"):
                raw_orders = orders_client.list_open_orders()
            elif hasattr(orders_client, "get_open_orders"):
                raw_orders = orders_client.get_open_orders()
            else:
                return

            self._broker_orders_by_symbol = self.open_orders_sync.build_orders_by_symbol(raw_orders or [])
            self._broker_orders_sync_ts = now_ts

            snapshot_key = tuple(
                sorted((symbol, len(items)) for symbol, items in self._broker_orders_by_symbol.items())
            )
            last_snapshot_key = getattr(self, "_broker_orders_last_snapshot_key", None)

            if snapshot_key != last_snapshot_key:
                print("PIPE_BROKER_OPEN_ORDERS_SYNC_OK", flush=True)
                self._broker_orders_last_snapshot_key = snapshot_key

        except Exception as exc:
            self._log_dedup(
                f"PIPE_BROKER_OPEN_ORDERS_SYNC_ERROR:{type(exc).__name__}",
                f"PIPE_BROKER_OPEN_ORDERS_SYNC_ERROR error={exc}",
            )


    def _runtime_log_allowed(self, key: str, ttl_seconds: int = 60) -> bool:
        """
        Русский комментарий:
        throttling одинаковых runtime логов.
        """
        import time

        now = time.time()

        # Русский комментарий: self-healing init на случай старого/альтернативного конструктора pipeline.
        if not hasattr(self, "_runtime_log_dedup") or self._runtime_log_dedup is None:
            self._runtime_log_dedup = {}

        # Русский комментарий:
        # отдельный экземпляр стратегии на каждый symbol, чтобы не смешивать state.
        self.strategy_by_symbol = {}


        last = self._runtime_log_dedup.get(key)

        if last is not None and (now - last) < ttl_seconds:
            return False

        self._runtime_log_dedup[key] = now
        return True


    def _notify_telegram_event(self, text: str) -> None:
        """Русский комментарий: безопасная отправка Telegram-уведомления без влияния на торговый цикл."""
        try:
            notifier = getattr(self, "notifier", None)
            if notifier is None:
                return
            if hasattr(notifier, "send"):
                # Русский комментарий: старый универсальный Telegram-канал отключён.
                # В Telegram теперь должны уходить только SignalAlert: вход / стоп / тейк.
                # notifier.send(text)
                return
        except Exception as exc:
            LOG.warning("PIPE_TELEGRAM_NOTIFY_FAILED error=%s", exc)



    def _is_ng_symbol(self, symbol: str) -> bool:
        """Русский комментарий: отдельный маршрут для газовых фьючерсов NG."""
        return str(symbol or "").upper().startswith("NG")

    def _ng_strategy_for_symbol(self, symbol: str) -> NgVolatilityBreakout:
        """Русский комментарий: stateful NG-стратегия на каждый газовый контракт."""
        strategies = getattr(self, "_ng_strategy_by_symbol", None)
        if strategies is None:
            strategies = {}
            self._ng_strategy_by_symbol = strategies
        if symbol not in strategies:
            strategies[symbol] = NgVolatilityBreakout(symbol=symbol)
        return strategies[symbol]

    def _ng_bar_buffer_for_symbol(self, symbol: str) -> list[dict]:
        """Русский комментарий: буфер synthetic bars для NG strategy."""
        buffers = getattr(self, "_ng_bar_buffer_by_symbol", None)
        if buffers is None:
            buffers = {}
            self._ng_bar_buffer_by_symbol = buffers
        if symbol not in buffers:
            buffers[symbol] = []
        return buffers[symbol]

    def _append_ng_bar(self, symbol: str, price: float, high=None, low=None) -> None:
        """Русский комментарий: добавляет бар в NG-буфер."""
        px = float(price)
        buf = self._ng_bar_buffer_for_symbol(symbol)
        buf.append({
            "open": px,
            "high": float(high if high is not None else px),
            "low": float(low if low is not None else px),
            "close": px,
        })
        if len(buf) > 500:
            del buf[:-500]

    def _build_ng_intent_if_any(self, symbol: str, price: float, high=None, low=None) -> dict | None:
        """Русский комментарий: строит raw_intent для NG volatility breakout."""
        self._append_ng_bar(symbol, price, high=high, low=low)
        sig = self._ng_strategy_for_symbol(symbol).on_bars(self._ng_bar_buffer_for_symbol(symbol))
        if sig is None:
            return None
        return {
            "symbol": sig.symbol,
            "side": sig.side,
            "qty": sig.qty,
            "price": sig.price,
            "source": "ng_volatility_breakout",
            "confidence": 1.0,
            "reason": sig.reason,
            "features": dict(sig.features or {}),
        }



    def _exit_engine_for_symbol(self, symbol: str) -> ExitEngine:
        """Русский комментарий: один ExitEngine на символ, без права отправлять заявки напрямую."""
        engines = getattr(self, "_exit_engine_by_symbol", None)
        if engines is None:
            engines = {}
            self._exit_engine_by_symbol = engines
        if symbol not in engines:
            engines[symbol] = ExitEngine()
        return engines[symbol]

    def _exit_state_for_symbol(self, symbol: str) -> dict:
        """Русский комментарий: состояние удержания позиции для ExitEngine."""
        states = getattr(self, "_exit_state_by_symbol", None)
        if states is None:
            states = {}
            self._exit_state_by_symbol = states
        if symbol not in states:
            states[symbol] = {
                "bars_held": 0,
                "prev_close": None,
                "stop_price": None,
                "last_qty": 0.0,
            }
        return states[symbol]


    def _get_position_manager_for_exit(self):
        """Русский комментарий: ищем PositionManager по всем используемым в проекте именам."""
        for attr in ("position_manager", "pm", "_position_manager", "_pm"):
            value = getattr(self, attr, None)
            if value is not None and hasattr(value, "positions"):
                return value

        portfolio = getattr(self, "portfolio_manager", None)
        if portfolio is not None:
            value = getattr(portfolio, "position_manager", None)
            if value is not None and hasattr(value, "positions"):
                return value

        return None

    def _position_qty_for_symbol(self, symbol: str) -> float:
        """Русский комментарий: безопасно получаем текущий paper qty по символу."""
        pm = self._get_position_manager_for_exit()
        if pm is None:
            print(f"PIPE_EXIT_ENGINE_NO_PM symbol={symbol}", flush=True)
            return 0.0

        positions = getattr(pm, "positions", {}) or {}
        pos = positions.get(symbol)
        if pos is None:
            return 0.0

        for field in ("qty", "quantity", "net_qty", "size", "position"):
            value = getattr(pos, field, None)
            if value is not None:
                return float(value or 0.0)

        print(
            f"PIPE_EXIT_ENGINE_NO_QTY_FIELD symbol={symbol} "
            f"pos_type={type(pos).__name__} fields={list(vars(pos).keys())}",
            flush=True,
        )
        return 0.0


    def _position_avg_price_for_symbol(self, symbol: str) -> float | None:
        """Русский комментарий: безопасно получаем среднюю цену paper-позиции."""
        broker_avg = float(getattr(self, "_broker_position_avg_by_symbol", {}).get(symbol, 0.0) or 0.0)
        if broker_avg > 0:
            return broker_avg

        pm = self._get_position_manager_for_exit()
        if pm is None:
            return None

        positions = getattr(pm, "positions", {}) or {}
        pos = positions.get(symbol)
        if pos is None:
            return None

        for field in ("avg_price", "average_price", "entry_price", "price"):
            value = getattr(pos, field, None)
            if value is not None:
                return float(value)

        print(
            f"PIPE_EXIT_ENGINE_NO_AVG_FIELD symbol={symbol} "
            f"pos_type={type(pos).__name__} fields={list(vars(pos).keys())}",
            flush=True,
        )
        return None


    def _exit_fallback_atr(self, symbol: str, price: float) -> float:
        """Русский комментарий: fallback ATR для live quote events без поля atr."""
        pct = float(os.getenv("EXIT_FALLBACK_ATR_PCT", "0.003"))
        return abs(float(price)) * pct


    def _self_heal_position_lifecycle_state(
        self,
        *,
        symbol: str,
        actual_qty: float,
        strategy: str = "default",
    ) -> None:
        """Русский комментарий: очищает orphan/stale lifecycle state без торговых действий."""
        if os.getenv("ENABLE_POSITION_LIFECYCLE_SELF_HEALING", "1") != "1":
            return

        try:
            repo = getattr(self, "position_lifecycle_state_repository", None)
            event_repo = getattr(self, "position_lifecycle_reconcile_event_repository", None)
            healer = getattr(self, "position_lifecycle_self_healer", None)

            if repo is None or healer is None:
                return

            state = repo.load_state(symbol=symbol, strategy=strategy)
            if not state:
                return

            decision = healer.evaluate(
                state_exists=True,
                actual_qty=float(actual_qty or 0.0),
                trailing_active=bool(state.get("trailing_active", False)),
                current_stop=state.get("current_stop"),
            )

            if decision.action in ("NOOP", "OK"):
                return

            if event_repo is not None:
                event_repo.log_event(
                    symbol=symbol,
                    strategy=strategy,
                    action=decision.action,
                    expected_qty=state.get("remaining_qty"),
                    actual_qty=float(actual_qty or 0.0),
                    reason=decision.reason,
                    raw={
                        "source": "position_lifecycle_self_healing",
                        "state": state,
                    },
                )

            if decision.should_clear_trailing_cache:
                self._trailing_order_stop_by_symbol.pop(symbol, None)

            if decision.should_delete_state:
                deleted = repo.delete_state(symbol=symbol, strategy=strategy)
                print(
                    f"PIPE_POSITION_LIFECYCLE_SELF_HEAL_DELETE symbol={symbol} "
                    f"actual_qty={actual_qty} deleted={int(bool(deleted))} reason={decision.reason}",
                    flush=True,
                )
                return

            print(
                f"PIPE_POSITION_LIFECYCLE_SELF_HEAL_MARK symbol={symbol} "
                f"actual_qty={actual_qty} action={decision.action} reason={decision.reason}",
                flush=True,
            )

        except Exception as exc:
            print(f"PIPE_POSITION_LIFECYCLE_SELF_HEAL_FAILED symbol={symbol} error={exc}", flush=True)


    def _reconcile_position_lifecycle_state(
        self,
        *,
        symbol: str,
        actual_qty: float,
        strategy: str = "default",
    ) -> None:
        """Русский комментарий: сверяет persistent lifecycle state с фактической позицией."""
        if os.getenv("ENABLE_POSITION_LIFECYCLE_RECONCILIATION", "1") != "1":
            return

        try:
            repo = getattr(self, "position_lifecycle_state_repository", None)
            reconciler = getattr(self, "position_lifecycle_reconciler", None)

            if repo is None or reconciler is None:
                return

            state = repo.load_state(symbol=symbol, strategy=strategy)
            if not state:
                return

            decision = reconciler.reconcile(
                symbol=symbol,
                expected_remaining_qty=state.get("remaining_qty"),
                actual_qty=actual_qty,
            )

            if decision.action == "OK":
                return

            event_repo = getattr(self, "position_lifecycle_reconcile_event_repository", None)
            if event_repo is not None:
                event_repo.log_event(
                    symbol=symbol,
                    strategy=strategy,
                    action=decision.action,
                    expected_qty=decision.expected_qty,
                    actual_qty=decision.actual_qty,
                    reason=decision.reason,
                    raw={"source": "paper_pipeline"},
                )

            if decision.action == "CLEAR_STATE":
                deleted = repo.delete_state(symbol=symbol, strategy=strategy)
                self._trailing_order_stop_by_symbol.pop(symbol, None)
                print(
                    f"PIPE_POSITION_LIFECYCLE_RECONCILE_CLEAR symbol={symbol} "
                    f"expected_qty={decision.expected_qty} actual_qty={decision.actual_qty} "
                    f"deleted={int(bool(deleted))} reason={decision.reason}",
                    flush=True,
                )
                return

            if decision.action == "UPDATE_REMAINING_QTY":
                repo.upsert_state(
                    symbol=symbol,
                    strategy=strategy,
                    remaining_qty=decision.actual_qty,
                    raw={
                        "source": "position_lifecycle_reconciliation",
                        "reason": decision.reason,
                        "expected_qty": decision.expected_qty,
                        "actual_qty": decision.actual_qty,
                    },
                )
                print(
                    f"PIPE_POSITION_LIFECYCLE_RECONCILE_UPDATE symbol={symbol} "
                    f"expected_qty={decision.expected_qty} actual_qty={decision.actual_qty} "
                    f"reason={decision.reason}",
                    flush=True,
                )

        except Exception as exc:
            print(f"PIPE_POSITION_LIFECYCLE_RECONCILE_FAILED symbol={symbol} error={exc}", flush=True)


    def _load_position_lifecycle_state_for_symbol(
        self,
        symbol: str,
        strategy: str = "default",
    ) -> dict | None:
        """Русский комментарий: загружает persistent lifecycle state позиции при runtime/startup."""
        try:
            repo = getattr(self, "position_lifecycle_state_repository", None)
            if repo is None:
                return None

            state = repo.load_state(symbol=symbol, strategy=strategy)
            if not state:
                return None

            # Русский комментарий: восстанавливаем trailing stop runtime cache.
            current_stop = state.get("current_stop")
            if current_stop is not None:
                self._trailing_order_stop_by_symbol[symbol] = float(current_stop)

            # Русский комментарий: штатная загрузка lifecycle-состояния слишком шумная для live-журнала.
            if os.getenv("RUNTIME_DEBUG_LOGS", "0") == "1":
                print(
                    f"PIPE_POSITION_LIFECYCLE_STATE_LOADED symbol={symbol} "
                    f"strategy={strategy} remaining_qty={state.get('remaining_qty')} "
                    f"tp1_done={state.get('tp1_done')} tp2_done={state.get('tp2_done')} "
                    f"trailing_active={state.get('trailing_active')} current_stop={state.get('current_stop')} "
                    f"current_take_profit={state.get('current_take_profit')}",
                    flush=True,
                )

            return state

        except Exception as exc:
            print(f"PIPE_POSITION_LIFECYCLE_STATE_LOAD_FAILED symbol={symbol} error={exc}", flush=True)
            return None


    def _save_position_lifecycle_state(
        self,
        *,
        symbol: str,
        strategy: str = "default",
        entry_price: float | None = None,
        initial_qty: float | None = None,
        remaining_qty: float | None = None,
        tp1_done: bool | None = None,
        tp2_done: bool | None = None,
        profit_lock_done: bool | None = None,
        trailing_active: bool | None = None,
        current_stop: float | None = None,
        current_take_profit: float | None = None,
        source: str = "paper_pipeline",
    ) -> None:
        """Русский комментарий: сохраняет persistent lifecycle state позиции."""
        try:
            repo = getattr(self, "position_lifecycle_state_repository", None)
            if repo is None:
                return

            repo.upsert_state(
                symbol=symbol,
                strategy=strategy,
                entry_price=entry_price,
                initial_qty=initial_qty,
                remaining_qty=remaining_qty,
                tp1_done=tp1_done,
                tp2_done=tp2_done,
                profit_lock_done=profit_lock_done,
                trailing_active=trailing_active,
                current_stop=current_stop,
                current_take_profit=current_take_profit,
                raw={"source": source},
            )
        except Exception as exc:
            print(f"PIPE_POSITION_LIFECYCLE_STATE_SAVE_FAILED symbol={symbol} error={exc}", flush=True)


    def _evaluate_partial_close_engine(
        self,
        symbol: str,
        qty: float,
        price: float,
        avg_price: float | None = None,
        stop_price: float | None = None,
    ) -> None:
        """Русский комментарий: dry-run расчёт частичного закрытия без отправки заявок."""
        if os.getenv("ENABLE_PARTIAL_CLOSE_ENGINE", "0") != "1":
            return

        try:
            if qty <= 0 or price <= 0:
                return

            entry_price = float(avg_price or price)
            base_stop = float(stop_price or (entry_price * (1.0 - float(os.getenv("PARTIAL_CLOSE_DEFAULT_STOP_PCT", "0.01")))))

            lifecycle_state = self._load_position_lifecycle_state_for_symbol(symbol) or {}

            decision = self.partial_close_engine.evaluate_long(
                qty=float(qty),
                entry_price=entry_price,
                current_price=float(price),
                stop_price=base_stop,
                tp1_done=bool(lifecycle_state.get("tp1_done", False)),
                tp2_done=bool(lifecycle_state.get("tp2_done", False)),
            )

            if decision.action == "HOLD":
                return

            self._log_dedup(
                f"PIPE_PARTIAL_CLOSE_DECISION:{symbol}:{decision.stage}:{decision.reason}",
                f"PIPE_PARTIAL_CLOSE_DECISION symbol={symbol} action={decision.action} "
                f"stage={decision.stage} qty={qty} qty_to_close={decision.qty_to_close} "
                f"remaining_qty={decision.remaining_qty} price={price} entry={entry_price} "
                f"base_stop={base_stop} reason={decision.reason} dry_run=1",
                heartbeat_sec=300,
            )

            self._save_position_lifecycle_state(
                symbol=symbol,
                entry_price=entry_price,
                initial_qty=qty,
                remaining_qty=decision.remaining_qty,
                tp1_done=(decision.stage == "TP1"),
                tp2_done=(decision.stage == "TP2"),
                source="partial_close_engine",
            )

        except Exception as exc:
            print(f"PIPE_PARTIAL_CLOSE_ERROR symbol={symbol} error={exc}", flush=True)


    def _evaluate_take_profit_engine(
        self,
        symbol: str,
        qty: float,
        price: float,
        avg_price: float | None = None,
        stop_price: float | None = None,
    ) -> None:
        """Русский комментарий: dry-run take-profit расчёт без отправки заявок брокеру."""
        if os.getenv("ENABLE_TAKE_PROFIT_ENGINE", "0") != "1":
            return

        try:
            if qty <= 0 or price <= 0:
                return

            entry_price = float(avg_price or price)
            base_stop = float(stop_price or (entry_price * (1.0 - float(os.getenv("TAKE_PROFIT_DEFAULT_STOP_PCT", "0.01")))))

            decision = self.take_profit_engine.evaluate_long(
                qty=float(qty),
                entry_price=entry_price,
                current_price=float(price),
                stop_price=base_stop,
            )

            if decision.action == "HOLD":
                return

            self._log_dedup(
                f"PIPE_TAKE_PROFIT_DECISION:{symbol}:{decision.action}:{decision.reason}",
                f"PIPE_TAKE_PROFIT_DECISION symbol={symbol} action={decision.action} "
                f"qty={qty} qty_to_close={decision.qty_to_close} "
                f"price={price} entry={entry_price} base_stop={base_stop} "
                f"take_price={decision.take_price} reason={decision.reason} dry_run=1",
                heartbeat_sec=300,
            )

            self.take_profit_event_repository.log_event(
                symbol=symbol,
                action=decision.action,
                qty=qty,
                qty_to_close=decision.qty_to_close,
                price=price,
                entry_price=entry_price,
                base_stop=base_stop,
                take_price=decision.take_price,
                reason=decision.reason,
                dry_run=True,
                raw={"source": "paper_pipeline", "engine": "TakeProfitEngine"},
            )

            self._save_position_lifecycle_state(
                symbol=symbol,
                entry_price=entry_price,
                initial_qty=qty,
                remaining_qty=max(0.0, float(qty) - float(decision.qty_to_close or 0.0)),
                current_take_profit=decision.take_price,
                source="take_profit_engine",
            )

        except Exception as exc:
            print(f"PIPE_TAKE_PROFIT_ERROR symbol={symbol} error={exc}", flush=True)


    def _evaluate_profit_lock_engine(
        self,
        symbol: str,
        qty: float,
        price: float,
        avg_price: float | None = None,
        stop_price: float | None = None,
    ) -> None:
        """Русский комментарий: dry-run profit-lock до trailing stop."""
        if os.getenv("ENABLE_PROFIT_LOCK_ENGINE", "0") != "1":
            return

        try:
            if qty <= 0 or price <= 0:
                return

            entry_price = float(avg_price or price)
            base_stop = float(stop_price or (entry_price * (1.0 - float(os.getenv("PROFIT_LOCK_DEFAULT_STOP_PCT", "0.01")))))

            decision = self.profit_lock_engine.evaluate_long(
                qty=float(qty),
                entry_price=entry_price,
                current_price=float(price),
                stop_price=base_stop,
            )

            if decision.action == "HOLD":
                return

            self._log_dedup(
                f"PIPE_PROFIT_LOCK_DECISION:{symbol}:{decision.action}:{decision.reason}",
                f"PIPE_PROFIT_LOCK_DECISION symbol={symbol} action={decision.action} "
                f"qty={qty} qty_to_close={decision.qty_to_close} "
                f"price={price} entry={entry_price} base_stop={base_stop} "
                f"new_stop={decision.new_stop} reason={decision.reason} dry_run=1",
                heartbeat_sec=300,
            )

            self.profit_lock_event_repository.log_event(
                symbol=symbol,
                action=decision.action,
                qty=qty,
                qty_to_close=decision.qty_to_close,
                price=price,
                entry_price=entry_price,
                base_stop=base_stop,
                new_stop=decision.new_stop,
                reason=decision.reason,
                dry_run=True,
                raw={
                    "source": "paper_pipeline",
                    "engine": "ProfitLockEngine",
                },
            )

            self._save_position_lifecycle_state(
                symbol=symbol,
                entry_price=entry_price,
                remaining_qty=qty,
                profit_lock_done=True,
                current_stop=decision.new_stop,
                source="profit_lock_engine",
            )

            # Русский комментарий:
            # В dry-run режиме не отправляем close/replace orders брокеру.
            # На следующем этапе decision будет транслироваться в managed exit intent.

        except Exception as exc:
            print(f"PIPE_PROFIT_LOCK_ERROR symbol={symbol} error={exc}", flush=True)


    def _evaluate_trailing_order_manager(self, symbol: str, qty: float, price: float) -> None:
        """Русский комментарий: dry-run оценка trailing stop-заявки без отправки брокеру."""
        if os.getenv("ENABLE_TRAILING_ORDER_MANAGER", "0") != "1":
            return

        if os.getenv("ENABLE_POSITION_INTENT_GATE", "0") == "1":
            policy = self.position_intent_repo.get(symbol)
            if not policy.enabled or not policy.allow_trailing:
                state = self._exit_state_for_symbol(symbol)
                now_ts = time.time()
                last_ts = float(state.get("last_trailing_intent_block_log_ts", 0.0) or 0.0)
                if now_ts - last_ts >= float(os.getenv("POSITION_INTENT_TRAILING_BLOCK_LOG_INTERVAL_SEC", "300")):
                    state["last_trailing_intent_block_log_ts"] = now_ts
                    print(
                        f"PIPE_POSITION_INTENT_TRAILING_BLOCK symbol={symbol} "
                        f"horizon={policy.horizon} enabled={policy.enabled} allow_trailing={policy.allow_trailing}",
                        flush=True,
                    )
                return

        dry_run = os.getenv("TRAILING_ORDER_DRY_RUN", "1") == "1"
        if not dry_run:
            # Русский комментарий:
            # Реальный режим: trailing decision может быть отправлен брокеру только через
            # RealProtectiveLifecycleEngine, который имеет собственные hard-gates.
            pass

        qty = float(qty or 0.0)
        price = float(price)

        if qty <= 0:
            self._trailing_order_stop_by_symbol.pop(symbol, None)
            return

        lifecycle_state = self._load_position_lifecycle_state_for_symbol(symbol) or {}
        current_stop = self._trailing_order_stop_by_symbol.get(symbol)

        if current_stop is None and lifecycle_state.get("current_stop") is not None:
            current_stop = float(lifecycle_state["current_stop"])

        decision = self.trailing_order_manager.evaluate_long(
            symbol=symbol,
            qty=qty,
            last_price=price,
            current_stop=current_stop,
        )

        if decision.action in ("PLACE_STOP", "REPLACE_STOP"):
            self._trailing_order_stop_by_symbol[symbol] = decision.stop_price

        if decision.action != "HOLD":
            print(
                f"PIPE_TRAILING_ORDER_DECISION action={decision.action} "
                f"symbol={decision.symbol} side={decision.side} qty={decision.qty} "
                f"stop={decision.stop_price} reason={decision.reason} dry_run=1",
                flush=True,
            )

            self.trailing_order_event_repository.log_event(
                symbol=decision.symbol,
                action=decision.action,
                side=decision.side,
                qty=decision.qty,
                stop_price=decision.stop_price,
                reason=decision.reason,
                dry_run=True,
                raw={
                    "source": "paper_pipeline",
                    "manager": "TrailingOrderManager",
                },
            )

            self._save_position_lifecycle_state(
                symbol=decision.symbol,
                remaining_qty=decision.qty,
                trailing_active=True,
                current_stop=decision.stop_price,
                source="trailing_order_manager",
            )

            if not dry_run:
                result = self.real_protective_lifecycle.place_or_replace_stop(
                    symbol=decision.symbol,
                    side=decision.side,
                    qty=decision.qty,
                    stop_price=decision.stop_price,
                    entry_order_id=None,
                    old_order_id=None,
                    reason=decision.reason,
                )
                print(
                    f"PIPE_REAL_PROTECTIVE_LIFECYCLE_RESULT symbol={decision.symbol} "
                    f"action={result.action} executed={int(result.executed)} "
                    f"status={result.status} order_id={result.order_id} reason={result.reason}",
                    flush=True,
                )
            else:
                self._handle_trailing_replace_stop_decision(decision)


    def _log_position_order_state_if_changed(self, symbol: str, qty: float) -> None:
        """Русский комментарий: логирует защищённость позиции заявками только при изменении состояния."""
        if os.getenv("ENABLE_POSITION_ORDER_TRACKER", "0") != "1":
            return

        orders = list(getattr(self, "_broker_orders_by_symbol", {}).get(symbol, []) or [])
        state = self.position_order_tracker.evaluate(symbol, qty, orders)

        key = (
            round(float(state.position_qty), 8),
            round(float(state.stop_qty), 8),
            round(float(state.take_qty), 8),
            bool(state.protected),
            round(float(state.protection_gap_qty), 8),
        )

        last_key = getattr(self, "_position_order_state_last_key", {}).get(symbol)
        if last_key == key:
            return

        if not hasattr(self, "_position_order_state_last_key"):
            self._position_order_state_last_key = {}

        self._position_order_state_last_key[symbol] = key

        print(
            f"PIPE_POSITION_ORDER_STATE symbol={state.symbol} "
            f"qty={state.position_qty} stop_qty={state.stop_qty} take_qty={state.take_qty} "
            f"protected={state.protected} gap={state.protection_gap_qty}",
            flush=True,
        )


    def _position_intent_allows_exit_engine(self, symbol: str) -> tuple[bool, str]:
        """Русский комментарий: ExitEngine работает только для позиций с разрешённым intraday exit."""
        if os.getenv("ENABLE_POSITION_INTENT_GATE", "0") != "1":
            return True, "intent_gate_disabled"

        policy = self.position_intent_repo.get(symbol)
        if not policy.enabled:
            return False, f"intent_disabled_or_unknown:{policy.horizon}"

        if not policy.allow_intraday_exit:
            return False, f"intent_blocks_intraday_exit:{policy.horizon}"

        return True, f"intent_allows_intraday_exit:{policy.horizon}"


    def _reconciliation_allows_real_order(self, symbol: str, local_qty: float) -> tuple[bool, str]:
        """Русский комментарий: hard-gate перед реальной заявкой — локальная позиция должна совпадать с брокером."""
        if os.getenv("ENABLE_BROKER_RECONCILIATION_GATE", "0") != "1":
            return True, "reconciliation_gate_disabled"

        broker_qty = float(getattr(self, "_broker_position_qty_by_symbol", {}).get(symbol, 0.0) or 0.0)
        result = self.broker_reconciliation.check_position(symbol, local_qty, broker_qty)

        if result.ok:
            return True, result.reason

        repair_decision = self.portfolio_reconciliation_repair.evaluate(
            symbol=symbol,
            local_qty=result.local_qty,
            broker_qty=result.broker_qty,
            allow_repair=os.getenv("ALLOW_PORTFOLIO_REPAIR", "0") == "1",
        )

        if repair_decision.status == "REPAIRED":
            if hasattr(self.pm, "sync_authoritative_position"):
                self.pm.sync_authoritative_position(
                    symbol=symbol,
                    qty=float(repair_decision.repaired_qty or 0.0),
                    source="broker_reconciliation",
                    reason=repair_decision.reason,
                )

            if hasattr(self.pg_logger, "log_execution_event"):
                self.pg_logger.log_execution_event(
                    event="PORTFOLIO_RECONCILIATION_REPAIR",
                    symbol=symbol,
                    qty=float(repair_decision.repaired_qty or 0.0),
                    status=repair_decision.status,
                    reason=repair_decision.reason,
                    raw_json={
                        "local_qty": repair_decision.local_qty,
                        "broker_qty": repair_decision.broker_qty,
                        "repaired_qty": repair_decision.repaired_qty,
                    },
                )

            print(
                f"PIPE_PORTFOLIO_RECONCILIATION_REPAIRED symbol={symbol} "
                f"local_qty={repair_decision.local_qty} broker_qty={repair_decision.broker_qty} "
                f"repaired_qty={repair_decision.repaired_qty}",
                flush=True,
            )
            return True, repair_decision.reason

        self._trading_halt_reason = (
            f"broker_desync:{symbol}:local={result.local_qty}:broker={result.broker_qty}"
        )

        mismatch_key = (
            symbol,
            result.local_qty,
            result.broker_qty,
            self._trading_halt_reason,
        )
        last_mismatch_key = getattr(self, "_last_reconciliation_mismatch_key", None)

        if mismatch_key != last_mismatch_key:
            print(
                f"PIPE_RECONCILIATION_MISMATCH symbol={symbol} "
                f"local_qty={result.local_qty} broker_qty={result.broker_qty} "
                f"halt_reason={self._trading_halt_reason}",
                flush=True,
            )
            self._last_reconciliation_mismatch_key = mismatch_key
        return False, self._trading_halt_reason

    def _account_trade_after_fill_v1(self, symbol: str) -> None:
        """
        Русский комментарий:
        Учитывает сделку в runtime trade limit только после успешного создания FILL.
        Это предотвращает блокировку лимита на rejected/blocked попытках.
        """
        try:
            trade_gate = getattr(self, "trade_gate_service", None)
            if trade_gate is None:
                return

            accounted_decision = trade_gate.account_trade(str(symbol))
            print(f"PIPE_TRADE_LIMIT_ACCOUNTED {accounted_decision.reason}", flush=True)
        except Exception as exc:
            print(
                "PIPE_TRADE_LIMIT_ACCOUNT_ERROR",
                f"symbol={symbol}",
                f"error={type(exc).__name__}:{exc}",
                flush=True,
            )


    def _position_intent_allows_order(self, symbol: str, side: str, current_qty: float) -> tuple[bool, str]:
        """Русский комментарий: запрещает добор/наращивание позиции по DB position_intents."""
        if os.getenv("ENABLE_POSITION_INTENT_GATE", "0") != "1":
            return True, "intent_gate_disabled"

        policy = self.position_intent_repo.get(symbol)
        side_u = str(side or "").upper()
        qty = float(current_qty or 0.0)

        # Русский комментарий: неизвестные/disabled позиции не разрешаем увеличивать.
        if not policy.enabled:
            return False, f"intent_disabled_or_unknown:{policy.horizon}:{policy.trade_role}"

        # Русский комментарий: watch_only — робот не имеет права торговать инструментом.
        if policy.trade_role == "watch_only":
            return False, "intent_watch_only_blocks_all_orders"

        # Русский комментарий: определяем, увеличивает ли заявка текущую позицию.
        increases_long = qty > 0 and side_u == "BUY"
        increases_short = qty < 0 and side_u == "SELL"
        opens_new = abs(qty) <= 1e-9 and side_u in ("BUY", "SELL")
        increases_position = increases_long or increases_short or opens_new

        # Русский комментарий: reduce_only — разрешено только сокращение, но не открытие/добор.
        if policy.trade_role == "reduce_only" and increases_position:
            return False, "intent_reduce_only_blocks_increase"

        if increases_position and not policy.allow_increase:
            return False, f"intent_allow_increase_false:{policy.trade_role}"

        # Русский комментарий: если заявка сокращает позицию, проверяем allow_reduce.
        reduces_long = qty > 0 and side_u == "SELL"
        reduces_short = qty < 0 and side_u == "BUY"
        if (reduces_long or reduces_short) and not policy.allow_reduce:
            return False, f"intent_allow_reduce_false:{policy.trade_role}"

        return True, f"intent_order_allowed:{policy.horizon}:{policy.trade_role}"


    def _build_exit_intent_if_any(self, symbol: str, price: float, atr: float | None = None) -> dict | None:
        """Русский комментарий: строит raw_intent для закрытия позиции через общий execution path."""
        self._sync_broker_positions_readonly()
        self._sync_broker_open_orders_if_needed()

        state = self._exit_state_for_symbol(symbol)

        qty = self._position_qty_for_symbol(symbol)
        broker_qty = float(getattr(self, "_broker_position_qty_by_symbol", {}).get(symbol, 0.0) or 0.0)

        # Русский комментарий: broker snapshot не должен автоматически превращаться в paper-позицию.
        if os.getenv("ENABLE_BROKER_POSITION_APPLY_TO_PM", "0") == "1" and abs(broker_qty) > 1e-9:
            prev_broker_qty = float(
                state.get("last_broker_qty_logged", 0.0) or 0.0
            )

            qty = broker_qty

            if abs(prev_broker_qty - broker_qty) > 1e-9:
                print(
                    f"PIPE_BROKER_POSITION_APPLIED symbol={symbol}",
                    flush=True,
                )
                state["last_broker_qty_logged"] = broker_qty

        self._log_position_order_state_if_changed(symbol, qty)

        # Русский комментарий: lifecycle должен использовать тот же strategy key, что и trades/runtime-control.
        lifecycle_strategy = self._strategy_name_for_symbol(symbol)

        self._reconcile_position_lifecycle_state(
            symbol=symbol,
            actual_qty=float(qty or 0.0),
            strategy=lifecycle_strategy,
        )
        self._self_heal_position_lifecycle_state(
            symbol=symbol,
            actual_qty=float(qty or 0.0),
            strategy=lifecycle_strategy,
        )

        now_ts = time.time()
        has_position = abs(float(qty or 0.0)) > 1e-9
        qty_key = "last_nonzero_qty_log_ts" if has_position else "last_zero_qty_log_ts"
        interval_key = "EXIT_NONZERO_QTY_LOG_INTERVAL_SEC" if has_position else "EXIT_ZERO_QTY_LOG_INTERVAL_SEC"
        default_interval = "15" if has_position else "60"

        last_log_ts = float(state.get(qty_key, 0.0) or 0.0)
        should_log_exit_check = now_ts - last_log_ts >= float(os.getenv(interval_key, default_interval))

        if should_log_exit_check and (
            abs(float(qty or 0.0)) > 1e-9 or os.getenv("EXIT_ENGINE_DEBUG", "0") == "1"
        ):
            state[qty_key] = now_ts
            # Русский комментарий: регулярная проверка ExitEngine пишется только в debug-режиме.
            if os.getenv("RUNTIME_DEBUG_LOGS", "0") == "1":
                print(
                    f"PIPE_EXIT_ENGINE_CHECK symbol={symbol} qty={qty} "
                    f"price={round(float(price), 6)} atr_in={atr}",
                    flush=True,
                )

        if qty == 0:
            state["bars_held"] = 0
            state["prev_close"] = float(price)
            state["stop_price"] = None
            state["last_qty"] = 0.0
            state["opened_at_ts"] = None
            try:
                self.exit_state_machine.on_position(symbol, 0.0)
            except Exception:
                pass
            return None

        exit_allowed, exit_reason = self._position_intent_allows_exit_engine(symbol)
        if not exit_allowed:
            now_ts = time.time()
            last_intent_block_ts = float(state.get("last_intent_block_log_ts", 0.0) or 0.0)
            if now_ts - last_intent_block_ts >= float(os.getenv("POSITION_INTENT_BLOCK_LOG_INTERVAL_SEC", "300")):
                state["last_intent_block_log_ts"] = now_ts
                print(
                    f"PIPE_POSITION_INTENT_EXIT_BLOCK symbol={symbol} qty={qty} reason={exit_reason}",
                    flush=True,
                )
            return None

        avg_price = self._position_avg_price_for_symbol(symbol)
        if avg_price is None:
            now_ts = time.time()
            last_no_avg_ts = float(state.get("last_no_avg_log_ts", 0.0) or 0.0)

            if now_ts - last_no_avg_ts >= float(os.getenv("EXIT_NO_AVG_LOG_INTERVAL_SEC", "300")):
                state["last_no_avg_log_ts"] = now_ts
                print(
                    f"PIPE_EXIT_ENGINE_NO_AVG symbol={symbol} qty={qty} "
                    f"price={round(float(price), 6)}",
                    flush=True,
                )

            return None

        if float(state.get("last_qty") or 0.0) == 0.0:
            state["bars_held"] = 0
            state["stop_price"] = None
            # Русский комментарий: фиксируем момент открытия новой позиции для защиты от мгновенного time_exit.
            state["opened_at_ts"] = time.time()

        state["bars_held"] = int(state.get("bars_held") or 0) + 1
        state["last_qty"] = float(qty)

        side = "BUY" if qty > 0 else "SELL"
        close_side = "SELL" if qty > 0 else "BUY"
        effective_atr = float(atr if atr is not None else 0.0)

        if effective_atr <= 0:
            effective_atr = self._exit_fallback_atr(symbol, price)
            log_key = f"ATR_FALLBACK:{symbol}"

            if self._runtime_log_allowed(log_key, ttl_seconds=300):
                print(
                    f"PIPE_EXIT_ENGINE_ATR_FALLBACK symbol={symbol} "
                    f"atr={round(effective_atr, 6)} price={round(float(price), 6)}",
                    flush=True,
                )

        # Русский комментарий:
        # Lazy fallback: сервис мог не инициализироваться в __init__ после refactoring.
        if not hasattr(self, "position_lifecycle_service"):
            self.position_lifecycle_service = PositionLifecycleService(self)

        # Русский комментарий:
        # lifecycle сопровождения запускаем через отдельный сервис.
        self.position_lifecycle_service.on_position_quote(
            PositionLifecycleInput(
                symbol=symbol,
                qty=float(qty),
                price=float(price),
                avg_price=float(avg_price),
                strategy=lifecycle_strategy,
            )
        )

        bars_for_exit = int(state["bars_held"])

        # Русский комментарий: BR/NG в live идут частыми quote/tick-событиями, поэтому bars_held
        # не равен количеству M1-баров. Не даём time_exit закрыть свежую PAPER-позицию.
        if str(symbol).startswith(("NG", "BR")):
            min_hold_sec = float(os.getenv("ENERGY_TIME_EXIT_MIN_HOLD_SEC", os.getenv("NG_MIN_HOLD_SEC", "1800")))
            opened_at_ts = state.get("opened_at_ts")
            position_age_sec = time.time() - float(opened_at_ts or time.time())

            if position_age_sec < min_hold_sec:
                bars_for_exit = 0
                if self._runtime_log_allowed(f"ENERGY_TIME_EXIT_GUARD:{symbol}", ttl_seconds=60):
                    print(
                        f"PIPE_ENERGY_TIME_EXIT_GUARD symbol={symbol} "
                        f"age_sec={round(position_age_sec, 3)} min_hold_sec={min_hold_sec} "
                        f"raw_bars_held={state['bars_held']}",
                        flush=True,
                    )

        decision = self._exit_engine_for_symbol(symbol).evaluate(
            side=side,
            entry_price=float(avg_price),
            current_price=float(price),
            atr=effective_atr,
            bars_held=bars_for_exit,
            prev_close=state.get("prev_close"),
            current_stop=state.get("stop_price"),
        )

        state["prev_close"] = float(price)
        state["stop_price"] = decision.stop_price

        if not decision.should_exit:
            hold_key = f"EXIT_HOLD:{symbol}:{side}:{decision.reason}"

            if self._runtime_log_allowed(hold_key, ttl_seconds=300):
                print(
                    f"PIPE_EXIT_ENGINE_HOLD symbol={symbol} side={side} qty={abs(qty)} "
                    f"price={round(float(price), 6)} reason={decision.reason} stop={decision.stop_price}",
                    flush=True,
                )

            return None

        try:
            self.exit_state_machine.on_position(symbol, float(qty))
            allowed, sm_reason = self.exit_state_machine.allow_request(
                symbol=symbol,
                side=close_side,
                qty=abs(float(qty)),
                reason=str(decision.reason),
            )
            if not allowed:
                log_key = f"DUPLICATE_BLOCK:{symbol}:{decision.reason}"

                if self._runtime_log_allowed(log_key, ttl_seconds=120):
                    print(
                        f"PIPE_EXIT_ENGINE_DUPLICATE_BLOCK symbol={symbol} "
                        f"side={close_side} "
                        f"qty={abs(float(qty))} "
                        f"reason={decision.reason} "
                        f"sm_reason={sm_reason}",
                        flush=True,
                    )
                return None
        except Exception as exc:
            print(f"PIPE_EXIT_ENGINE_SM_ERROR symbol={symbol} error={exc}", flush=True)

        print(
            f"PIPE_EXIT_ENGINE_SIGNAL symbol={symbol} close_side={close_side} qty={abs(qty)} "
            f"price={round(float(price), 6)} reason={decision.reason}",
            flush=True,
        )

        return {
            "symbol": symbol,
            "side": close_side,
            "qty": abs(float(qty)),
            "price": float(price),
            "source": "exit_engine",
            "confidence": 1.0,
            "reason": decision.reason,
            "features": {
                "entry": float(avg_price),
                "exit_price": float(price),
                "atr": effective_atr,
                "bars_held": int(state["bars_held"]),
                "stop": decision.stop_price,
                "exit_engine": True,
            },
        }


    def _run_restart_recovery_if_needed(self) -> None:
        """Русский комментарий: thin-wrapper для RestartRecoveryCoordinator."""
        coordinator = getattr(self, "restart_recovery_coordinator", None)
        if coordinator is None:
            coordinator = RestartRecoveryCoordinator(self)
            self.restart_recovery_coordinator = coordinator

        coordinator.run_if_needed()


    def _handle_trailing_replace_stop_decision(self, decision) -> None:
        """Русский комментарий: исполняет trailing REPLACE_STOP через CancelReplaceStopManager."""
        action = str(getattr(decision, "action", "") or "").upper()
        if action != "REPLACE_STOP":
            return

        symbol = str(getattr(decision, "symbol", "") or "")
        side = str(getattr(decision, "side", "") or "").upper()
        qty = float(getattr(decision, "qty", 0.0) or 0.0)
        stop_price = float(getattr(decision, "stop", getattr(decision, "stop_price", 0.0)) or 0.0)
        old_order_id = str(getattr(decision, "order_id", getattr(decision, "old_order_id", "")) or "")

        if not old_order_id:
            orders = (getattr(self, "_broker_orders_by_symbol", {}) or {}).get(symbol, [])
            active_statuses = {"WATCHING", "ACTIVE", "WORKING", "ACCEPTED", "NEW", "PARTIAL_FILLED"}

            candidates = []
            for order in orders:
                order_id = str(order.get("order_id") or "")
                if not order_id:
                    continue

                order_type = str(order.get("order_type") or order.get("type") or "").upper()
                order_side = str(order.get("side") or "").upper()
                order_status = str(order.get("status") or "").upper()
                stop_value = order.get("stop_price") or order.get("stop") or order.get("trigger_price")

                # Русский комментарий: Finam может вернуть стоп как ORDER_TYPE_STOP,
                # как WATCHING-заявку со stop_price или как условную заявку с trigger_price.
                is_active = (not order_status) or order_status in active_statuses
                is_same_side = order_side == side
                is_stop_like = ("STOP" in order_type) or bool(stop_value)

                if is_active and is_same_side and is_stop_like:
                    candidates.append(order)

            if candidates:
                # Русский комментарий: если стопов несколько, берём последнюю/наиболее свежую заявку из snapshot.
                old_order_id = str(candidates[-1].get("order_id") or "")

        if not old_order_id:
            orders_count = len((getattr(self, "_broker_orders_by_symbol", {}) or {}).get(symbol, []))
            print(
                f"PIPE_TRAILING_REPLACE_STOP_BLOCK symbol={symbol} "
                f"reason=missing_old_stop_order broker_orders={orders_count}",
                flush=True,
            )
            return

        result = self.cancel_replace_stop_manager.replace_stop(
            symbol=symbol,
            old_order_id=old_order_id,
            side=side,
            qty=qty,
            stop_price=stop_price,
        )

        print(
            f"PIPE_TRAILING_REPLACE_STOP_RESULT symbol={symbol} old_order_id={old_order_id} "
            f"new_order_id={result.new_order_id} status={result.status} reason={result.reason}",
            flush=True,
        )


    def _log_dedup(self, key: str, message: str, heartbeat_sec: float | None = None) -> None:
        """Русский комментарий: печатает повторяющийся лог только по heartbeat."""
        now_ts = time.time()
        hb = float(heartbeat_sec if heartbeat_sec is not None else os.getenv("PIPE_DEDUP_LOG_HEARTBEAT_SEC", "300"))
        state = getattr(self, "_dedup_log_seen", {}) or {}
        last_ts = float(state.get(key, 0.0) or 0.0)

        if last_ts and now_ts - last_ts < hb:
            return

        print(message, flush=True)
        state[key] = now_ts
        self._dedup_log_seen = state


    def _apply_execution_decision_if_enabled(self, intent: dict, market_state: dict) -> dict | None:
        # Русский комментарий: exit-intent должен закрывать позицию напрямую,
        # без entry-point optimizer/retest/limit-логики для входов.
        if isinstance(intent, dict) and intent.get("intent_type") == "EXIT":
            return intent
        """Русский комментарий: применяет ExecutionDecisionLayer перед исполнением заявки."""
        if os.getenv("ENABLE_EXECUTION_DECISION_LAYER", "0") != "1":
            return intent

        layer = getattr(self, "execution_decision_layer", None)
        if layer is None:
            return intent

        decision = layer.decide(intent, market_state)
        print(
            f"PIPE_EXECUTION_DECISION symbol={decision.symbol} side={decision.side} "
            f"action={decision.action} order_type={decision.order_type} reason={decision.reason} "
            f"stop_price={decision.stop_price} limit_price={decision.limit_price} confidence={decision.confidence}",
            flush=True,
        )

        if decision.action == "SKIP":
            return None

        routed = dict(intent)
        routed["execution_action"] = decision.action
        routed["order_type"] = decision.order_type
        routed["execution_reason"] = decision.reason
        routed["confidence"] = max(
            float(routed.get("confidence", 0.0) or 0.0),
            float(decision.confidence or 0.0),
        )

        if decision.stop_price is not None:
            routed["stop_price"] = decision.stop_price
        if decision.limit_price is not None:
            routed["limit_price"] = decision.limit_price
        if decision.price is not None and routed.get("price") is None:
            routed["price"] = decision.price

        return routed



    def _execute_routed_order_if_needed(self, intent: dict, market_state: dict) -> bool:
        """Русский комментарий: исполняет маршруты OrderRouter, которые не должны уходить в raw_fill/market path."""
        route = str(intent.get("order_route") or "").upper()

        if route == "LIMIT_ORDER":
            dispatcher = getattr(self, "execution_dispatcher", None)
            if dispatcher is None:
                print("PIPE_EXECUTION_DISPATCH_LIMIT_SKIP reason=dispatcher_not_configured", flush=True)
                return True

            result = dispatcher.place_limit_order(
                symbol=str(intent.get("symbol")),
                side=str(intent.get("side")).upper(),
                qty=float(intent.get("qty") or 0.0),
                limit_price=float(intent.get("limit_price") or intent.get("entry_price") or intent.get("price")),
            )

            print(
                f"PIPE_EXECUTION_DISPATCH_LIMIT symbol={intent.get('symbol')} side={intent.get('side')} "
                f"qty={intent.get('qty')} limit_price={intent.get('limit_price') or intent.get('entry_price') or intent.get('price')} "
                f"status={result.get('status') if isinstance(result, dict) else getattr(result, 'status', None)} "
                f"reason={result.get('reason') if isinstance(result, dict) else getattr(result, 'reason', None)}",
                flush=True,
            )
            return True

        if route == "STOP_ORDER":
            print("PIPE_EXECUTION_DISPATCH_STOP_SKIP reason=stop_route_not_enabled_yet", flush=True)
            return True

        return False



    def _route_order_if_enabled(self, intent: dict, market_state: dict) -> dict | None:
        """Русский комментарий: применяет ExecutionDecisionLayer и OrderRouter без прямого вызова raw_fill."""
        routed_intent = self._apply_execution_decision_if_enabled(intent, market_state)
        if routed_intent is None:
            return None

        if os.getenv("ENABLE_ORDER_ROUTER", "0") != "1":
            return routed_intent

        router = getattr(self, "order_router", None)
        if router is None:
            return routed_intent

        route = router.route(routed_intent, market_state)
        print(
            f"PIPE_ORDER_ROUTER symbol={route.get('symbol')} side={route.get('side')} "
            f"route={route.get('route')} order_type={route.get('order_type')} "
            f"reason={route.get('reason')}",
            flush=True,
        )

        if route.get("route") == "SKIP":
            return None

        result = dict(routed_intent)
        result["order_route"] = route.get("route")
        result["order_type"] = route.get("order_type", result.get("order_type"))
        result["route_reason"] = route.get("reason")

        if route.get("stop_price") is not None:
            result["stop_price"] = route.get("stop_price")
        if route.get("limit_price") is not None:
            result["limit_price"] = route.get("limit_price")

        return result


    def _dispatch_order_if_enabled(self, intent: dict, market_state: dict):
        """Русский комментарий: gated execution route через TradingEngineCoordinator."""
        if CoordinatorFlags.execution_route_enabled():
            coordinator = getattr(self, "engine_coordinator", None)
            if coordinator is not None:
                routed = coordinator.route_execution(intent, market_state)
                print(
                    f"PIPE_ENGINE_COORDINATOR_EXECUTION_ROUTE "
                    f"symbol={routed.get('symbol') if isinstance(routed, dict) else getattr(routed, 'symbol', None)} "
                    f"side={routed.get('side') if isinstance(routed, dict) else getattr(routed, 'side', None)}",
                    flush=True,
                )
            else:
                routed = self._route_order_if_enabled(intent, market_state)
        else:
            routed = self._route_order_if_enabled(intent, market_state)

        if routed is None:
            print("PIPE_EXECUTION_DISPATCH_SKIP reason=route_none", flush=True)
            return None

        if os.getenv("ENABLE_EXECUTION_DISPATCHER", "0") != "1":
            return routed

        dispatcher = getattr(self, "execution_dispatcher", None)
        if dispatcher is None:
            return routed

        result = dispatcher.dispatch(routed, market_state)
        print(
            f"PIPE_EXECUTION_DISPATCH_RESULT symbol={getattr(result, 'symbol', None)} "
            f"side={getattr(result, 'side', None)} route={getattr(result, 'route', None)} "
            f"status={getattr(result, 'status', None)} order_id={getattr(result, 'order_id', None)} "
            f"reason={getattr(result, 'reason', None)}",
            flush=True,
        )
        return result


    def _dispatch_live_route_if_enabled(self, intent: dict, market_state: dict):
        """Русский комментарий: live-route через ExecutionDispatcher по отдельному флагу."""
        if os.getenv("ENABLE_EXECUTION_DISPATCHER_LIVE_ROUTE", "0") != "1":
            return None

        symbol = str(intent.get("symbol") or market_state.get("symbol") or "")
        qty = float(intent.get("qty") or 0.0)

        allowlist_raw = os.getenv("EXECUTION_DISPATCHER_LIVE_SYMBOL_ALLOWLIST", "BRM6@RTSX")
        allowlist = {item.strip() for item in allowlist_raw.split(",") if item.strip()}
        if allowlist and symbol not in allowlist:
            print(f"PIPE_EXECUTION_DISPATCH_LIVE_BLOCK symbol={symbol} reason=symbol_not_in_allowlist", flush=True)
            return None

        max_qty = float(os.getenv("EXECUTION_DISPATCHER_LIVE_MAX_QTY", "1"))
        if abs(qty) > max_qty:
            print(f"PIPE_EXECUTION_DISPATCH_LIVE_BLOCK symbol={symbol} reason=qty_exceeds_max:{qty}>{max_qty}", flush=True)
            return None

        result = self._dispatch_order_if_enabled(intent, market_state)
        if result is None:
            print("PIPE_EXECUTION_DISPATCH_LIVE_SKIP reason=dispatch_none", flush=True)
            return None

        print(
            f"PIPE_EXECUTION_DISPATCH_LIVE_RESULT symbol={getattr(result, 'symbol', None)} "
            f"side={getattr(result, 'side', None)} route={getattr(result, 'route', None)} "
            f"status={getattr(result, 'status', None)} order_id={getattr(result, 'order_id', None)} "
            f"reason={getattr(result, 'reason', None)}",
            flush=True,
        )
        return result


    def _on_quote(self, event) -> None:
        """Русский комментарий: thin-wrapper quote path с безопасным флагом Coordinator."""
        if CoordinatorFlags.on_quote_enabled():
            coordinator = getattr(self, "engine_coordinator", None)
            if coordinator is not None:
                # Русский комментарий: сохраняем startup/restart recovery перед новым coordinator quote path.
                self._run_restart_recovery_if_needed()
                result = coordinator.on_quote(event)
                if getattr(result, "errors", None):
                    print(
                        f"PIPE_ENGINE_COORDINATOR_ON_QUOTE_ERROR errors={result.errors}",
                        flush=True,
                    )
                return

        return self.pipeline_orchestrator.on_quote(
            QuoteEventContext(event=event)
        )


    def _record_smart_money_features_if_enabled(self, symbol: str, price: float, volume: float, event: dict) -> None:
        """Русский комментарий: считает smart-money признаки по quote и пишет только значимые события."""
        try:
            import os
            import time

            if os.getenv("ENABLE_SMART_MONEY_FEATURES", "0") != "1":
                return

            threshold = float(os.getenv("SMART_MONEY_MIN_SCORE", "0.45"))
            min_interval = float(os.getenv("SMART_MONEY_SAVE_INTERVAL_SEC", "60"))

            last_map = getattr(self, "_smart_money_last_save_ts", None)
            if last_map is None:
                last_map = {}
                self._smart_money_last_save_ts = last_map

            now_ts = time.time()
            if now_ts - float(last_map.get(symbol, 0.0) or 0.0) < min_interval:
                return

            from finam_core.orderflow.smart_money_features import SmartMoneyFeatureLayer
            from finam_core.orderflow.smart_money_feature_repository import SmartMoneyFeatureRepository

            layer = getattr(self, "smart_money_feature_layer", None)
            if layer is None:
                layer = SmartMoneyFeatureLayer(
                    window=int(os.getenv("SMART_MONEY_WINDOW", "20")),
                )
                self.smart_money_feature_layer = layer

            repo = getattr(self, "smart_money_feature_repository", None)
            if repo is None:
                repo = SmartMoneyFeatureRepository(getattr(self, "pg_logger", None))
                self.smart_money_feature_repository = repo

            high = event.get("high") or event.get("ask") or price
            low = event.get("low") or event.get("bid") or price
            avg_volume = event.get("avg_volume")

            features = layer.update(
                symbol=symbol,
                price=price,
                volume=volume,
                high=high,
                low=low,
                avg_volume=avg_volume,
            )

            if features.smart_money_score < threshold:
                return

            repo.save(features)
            last_map[symbol] = now_ts

            print(
                f"PIPE_SMART_MONEY_FEATURE symbol={symbol} "
                f"score={features.smart_money_score} label={features.label} "
                f"rvol={features.rvol} absorption={features.absorption_score} "
                f"impulse={features.impulse_score}",
                flush=True,
            )

        except Exception as exc:
            self._log_dedup(
                f"PIPE_SMART_MONEY_FEATURE_ERROR:{symbol}",
                f"PIPE_SMART_MONEY_FEATURE_ERROR symbol={symbol} error={type(exc).__name__}:{exc}",
                heartbeat_sec=300,
            )

    def _on_quote_impl(self, event: dict):
        raw_intent = None
        is_exit_intent = False
        is_force_intent = False
        self._resolver = getattr(self, "_resolver", InstrumentResolver())

        raw_sym = event.get("symbol")
        sym = self._resolver.resolve(raw_sym)
        if not sym:
            return

        self._run_restart_recovery_if_needed()

        # === STATE UPDATE ===
        st = self._mkt.get(sym, {})
        prev_price = st.get("last")

        st.update(event)

        # prev_price НЕ обновляем здесь (используется в fallback)
        if "prev_price" not in st:
            st["prev_price"] = prev_price
        self._mkt[sym] = st

        last = st.get("last") or st.get("price") or st.get("bid") or st.get("ask")
        if last is None:
            return

        price = float(last)

        volume = _safe_float(event.get("volume", event.get("qty", 0.0)) or 0.0, default=0.0)
        ts = event.get("ts") or event.get("timestamp")
        if ts is None:
            from datetime import datetime, timezone
            ts = datetime.now(timezone.utc)

        # Русский коммент: рыночные данные сохраняем до session/risk/strategy фильтров.
        self._record_live_quote_to_storage(
            symbol=sym,
            price=price,
            volume=volume,
            ts=ts,
        )

        # =========================================================
        # === PORTFOLIO KILL-SWITCH HARD GATE (BEFORE SESSION) ===
        # =========================================================
        kill_ok, kill_reason = self._portfolio_kill_switch_allows()
        if not kill_ok:
            if self._pipeline_log_throttle_allow("PIPE_PORTFOLIO_KILL_SWITCH_BLOCK", 30):
                msg = f"PIPE_PORTFOLIO_KILL_SWITCH_BLOCK {kill_reason}"
                print(msg, flush=True)
                self._notify_telegram_event(f"🛑 Portfolio kill-switch\n{kill_reason}")
            return

        # =========================================================
        # === SESSION LAYER (ЕДИНЫЙ ИСТОЧНИК)
        # =========================================================
        session = self.session.get_regime(sym)
        # === FORCE OVERRIDE (DEV MODE) ===
        if os.getenv("SESSION_OVERRIDE", "0") == "1":
            self._log_dedup(
                "PIPE_SESSION_OVERRIDE_ACTIVE",
                "PIPE_SESSION_OVERRIDE_ACTIVE",
                heartbeat_sec=float(os.getenv("SESSION_OVERRIDE_LOG_SEC", "30")),
            )
            session = {
                "phase": "override",
                "allow_entries": True,
            }

        # =========================================================
        self._record_smart_money_features_if_enabled(
            symbol=sym,
            price=price,
            volume=volume,
            event=event,
        )

        # === REGIME V2: STRATEGY ROUTER (АДАПТИВНЫЙ)
        # =========================================================
        regime_type = session.get("phase")

        # временная логика (дальше улучшим)
        if regime_type == "core":
            strategy_mode = "mr"   # mean reversion
        elif regime_type == "override":
            strategy_mode = "mr"
        else:
            strategy_mode = None

        # === SESSION FILTER (FIX: do not block in SIM/OVERRIDE) ===
        if not session.get("allow_entries", False):
            if os.getenv("SESSION_OVERRIDE", "0") == "1" or self.runtime_config.get_bool("SIMULATE_MARKET", False):
                self._log_dedup(
                    "PIPE_SESSION_BYPASS",
                    "PIPE_SESSION_BYPASS (override/sim)",
                    heartbeat_sec=float(os.getenv("SESSION_BYPASS_LOG_SEC", "60")),
                )
            else:
                try:
                    preload_symbols = list(getattr(self, "_runtime_active_symbols", []) or [])

                    base_symbol = str(sym) if "sym" in locals() else ""
                    if base_symbol and base_symbol not in preload_symbols:
                        preload_symbols.insert(0, base_symbol)

                    if not preload_symbols:
                        preload_symbols = [base_symbol] if base_symbol else []

                    self._runtime_symbol_reload_if_due(preload_symbols)
                except Exception as reload_exc:
                    self._log_dedup(
                        "PIPE_RUNTIME_SYMBOL_RELOAD_PRE_SESSION_ERROR",
                        f"PIPE_RUNTIME_SYMBOL_RELOAD_PRE_SESSION_ERROR {type(reload_exc).__name__}:{reload_exc}",
                        heartbeat_sec=300,
                    )

                if os.getenv("FINAM_CORE_FEED") == "sim":
                    self._log_dedup(
                        f"PIPE_SESSION_BYPASS:{session.get('phase')}",
                        f"PIPE_SESSION_BYPASS feed=sim phase={session.get('phase')}",
                        heartbeat_sec=float(os.getenv("SESSION_OVERRIDE_LOG_SEC", "30")),
                    )
                else:
                    self._log_dedup(
                        f"PIPE_SESSION_BLOCK:{session.get('phase')}",
                        f"PIPE_SESSION_BLOCK phase={session.get('phase')}",
                        heartbeat_sec=float(os.getenv("SESSION_BLOCK_LOG_SEC", "300")),
                    )
                    if (
                        os.getenv("RUNTIME_GOVERNANCE_OBSERVATION_BYPASS_SESSION_PREOPEN", "0") == "1"
                    ):
                        print(
                            "PIPE_SESSION_BLOCK_BYPASS_OBSERVATION",
                            "phase=preopen",
                            "reason=runtime_governance_population",
                            flush=True,
                        )
                    else:
                        return


        # === FIX CRITICAL (GLOBAL PRICE) ===

        curr_price = price

        # =========================================================
        # === EXIT ENGINE ROUTE (position management)
        # =========================================================
        exit_raw_intent = self._build_exit_intent_if_any(
            sym,
            curr_price,
            atr=event.get("atr"),
        )
        if exit_raw_intent is not None:
            raw_intent = exit_raw_intent
            # Русский комментарий: exit-intent обязан идти на закрытие позиции сразу.
            # Его нельзя фильтровать как новый вход по MTF/trend/impulse/position guards.
            raw_intent["intent_type"] = "EXIT"
            raw_intent["source"] = "ExitEngine"
            raw_intent.setdefault("features", {})["is_exit"] = True
            # Русский комментарий: preopen/closed могут генерировать один и тот же time_exit каждую минуту.
            # Логируем route с dedup, чтобы не засорять journal до открытия торгов.
            self._log_dedup(
                f"PIPE_EXIT_ENGINE_ROUTE:{sym}:{raw_intent.get('side')}:{raw_intent.get('reason')}",
                f"PIPE_EXIT_ENGINE_ROUTE symbol={sym} side={raw_intent.get('side')} "
                f"qty={raw_intent.get('qty')} reason={raw_intent.get('reason')}",
                heartbeat_sec=300,
            )

            # Русский комментарий: broker snapshot не должен закрываться через paper-fill.
            if (
                os.getenv("ENABLE_BROKER_POSITION_APPLY_TO_PM", "0") != "1"
                and abs(float(getattr(self, "_broker_position_qty_by_symbol", {}).get(sym, 0.0) or 0.0)) > 1e-9
            ):
                skip_key = (sym, raw_intent.get("side"), raw_intent.get("reason"))
                if getattr(self, "_last_exit_broker_snapshot_skip", None) != skip_key:
                    print(
                        f"PIPE_EXIT_ENGINE_BROKER_SNAPSHOT_SKIP symbol={sym} "
                        f"side={raw_intent.get('side')} reason={raw_intent.get('reason')}",
                        flush=True,
                    )
                    self._last_exit_broker_snapshot_skip = skip_key
                return

            # Русский комментарий: hard-close route для ExitEngine.
            # Закрытие позиции не должно проходить через entry-фильтры MTF/trend/impulse/position guard.
            try:
                intent = dict(raw_intent)
                if intent.get("price") is None:
                    px = st.get("last") or st.get("price") or st.get("bid") or st.get("ask") or price
                    intent["price"] = float(px)

                print(f"PIPE_RISK_ROUTE_START symbol={sym} side={intent.get('side')} qty={intent.get('qty')}", flush=True)
                decision = self.risk_router.route(
                    RiskRouteInput(
                        symbol=sym,
                        intent=intent,
                        state=st,
                        label="PIPE_EXIT_HARD_RISK",
                    )
                )
                if not getattr(decision, "allowed", False):
                    print(
                        f"PIPE_EXIT_HARD_RISK_REJECT reason={getattr(decision, 'reason', 'unknown')} "
                        f"value={getattr(getattr(self.risk_router, 'last_context', None), 'trade_value', None)} exposure={getattr(getattr(self.risk_router, 'last_context', None), 'total_exposure', None)}",
                        flush=True,
                    )
                    return

                print("PIPE_EXIT_HARD_RISK_OK", flush=True)

                if hasattr(self, "entry_point_selector") and not is_exit_intent and not (isinstance(intent, dict) and intent.get("intent_type") == "EXIT"):
                    intent = self.entry_point_selector.enrich_intent(intent, st) or intent
                    print(
                        f"PIPE_ENTRY_POINT_SELECTED symbol={intent.get('symbol')} side={intent.get('side')} "
                        f"entry_type={intent.get('entry_type')} price={intent.get('price')} "
                        f"stop_loss={intent.get('stop_loss')} take_profit={intent.get('take_profit')} "
                        f"reason={intent.get('entry_reason')}",
                        flush=True,
                    )

                intent = self._apply_execution_decision_if_enabled(intent, st)
                if intent is None:
                    print("PIPE_EXECUTION_DECISION_SKIP source=exit_engine", flush=True)
                    return

                if self.execution_mode in ("real_dry_run", "real"):
                    real_result = self.execution_dispatcher.execute(intent=intent, market_state=st)
                    print(
                        f"PIPE_REAL_EXECUTION_RESULT mode={self.execution_mode} symbol={getattr(real_result, 'symbol', None)} "
                        f"side={getattr(real_result, 'side', None)} qty={getattr(real_result, 'qty', None)} price={getattr(real_result, 'price', None)} "
                        f"status={getattr(real_result, 'status', None)} order_id={getattr(real_result, 'order_id', None)} reason={getattr(real_result, 'reason', None)}",
                        flush=True,
                    )
                    return

                if not self.runtime_config.get_bool("ENABLE_PAPER_FILLS", True):
                    self._log_dedup("PIPE_PAPER_FILL_BLOCKED:exit_engine", "PIPE_PAPER_FILL_BLOCKED source=exit_engine")
                    return
                raw_fill = self.paper.execute(intent, st)
                raw_qty = float(getattr(raw_fill, "qty", intent.get("qty", 0.0)) or 0.0)
                fill_side = "SELL" if raw_qty < 0 else "BUY"
                exec_price = float(getattr(raw_fill, "price", intent.get("price") or st.get("last") or price) or 0.0)

                commission = 0.0
                if hasattr(self.fee_tax, "commission"):
                    commission = self.fee_tax.commission(
                        symbol=intent.get("symbol"),
                        qty=abs(raw_qty),
                        price=exec_price,
                    )

                fill = ExecutionFill(
                    symbol=intent.get("symbol"),
                    side=fill_side,
                    qty=abs(raw_qty),
                    price=exec_price,
                    commission=commission,
                    fill_id=getattr(raw_fill, "fill_id", None),
                )

                # Русский комментарий: exit/hard-close PAPER fill тоже должен нести metadata для analytics lineage.
                FillMetadataFactory.attach(fill, intent=intent, market_state=st, raw_fill=raw_fill)

                # Русский комментарий: NG_SIGNAL_SOURCE_PROPAGATION_V2 для exit/hard-close ветки.
                try:
                    if not hasattr(self, "_fill_intent_payload_by_fill_id"):
                        self._fill_intent_payload_by_fill_id = {}
                    fill_key = str(getattr(fill, "fill_id", None) or "")
                    if fill_key:
                        self._fill_intent_payload_by_fill_id[fill_key] = dict(intent or {})
                except Exception as exc:
                    print(f"PIPE_SIGNAL_SOURCE_CACHE_FAILED symbol={intent.get('symbol')} error={exc}", flush=True)

                self.bus.publish({"type": "FILL", "fill": fill})
                try:
                    self.exit_state_machine.on_fill(str(intent.get("symbol") or ""))
                    self._restore_pm_position_from_projection_v1(str(intent.get("symbol") or ""))
                    pos_after = self.pm.positions.get(str(intent.get("symbol") or ""))
                    qty_after = float(getattr(pos_after, "qty", 0.0) or 0.0) if pos_after else 0.0
                    self.exit_state_machine.on_position(str(intent.get("symbol") or ""), qty_after)
                    print(
                        f"PIPE_EXIT_ENGINE_SM_FILLED symbol={intent.get('symbol')} qty_after={qty_after}",
                        flush=True,
                    )
                except Exception as exc:
                    print(f"PIPE_EXIT_ENGINE_SM_FILL_ERROR symbol={intent.get('symbol')} error={exc}", flush=True)

                return
            except Exception as exc:
                print(f"PIPE_EXIT_HARD_EXEC_ERROR {exc}", flush=True)
                return


        # =========================================================
        # === FORCE TEST SIGNAL (E2E PIPELINE SMOKE)
        # =========================================================
        force_signal_mode = os.getenv("FORCE_ONCE_BUY", "0") == "1"
        if force_signal_mode:
            try:
                if not getattr(self, "_force_signal_sent", False):
                    force_price = (
                        st.get("last")
                        or st.get("price")
                        or st.get("bid")
                        or st.get("ask")
                        or price
                    )

                    raw_intent = {
                        "symbol": sym,
                        "side": "BUY",
                        "qty": 1.0,
                        "price": float(force_price),
                        "strategy": "force_once_buy",
                        "features": {
                            "forced": True,
                        },
                    }

                    self._force_signal_sent = True

                    print(
                        f"PIPE_FORCE_SIGNAL symbol={sym} price={force_price}",
                        flush=True,
                    )
            except Exception as e:
                print(f"PIPE_FORCE_SIGNAL_ERROR {e}", flush=True)

        # =========================================================
        # === NG STRATEGY ROUTE (gas-specific volatility breakout)
        # =========================================================
        if raw_intent is None and self._is_ng_symbol(sym):
            raw_intent = self._build_ng_intent_if_any(
                sym,
                curr_price,
                high=event.get("high"),
                low=event.get("low"),
            )
            if raw_intent is None:
                # Русский комментарий:
                # Не выходим из обработки NG здесь. Для NG M1 основной сигнал
                # формируется ниже на закрытом MTF-баре через on_signal_bar().
                # Ранний return ломал live-контур: replay видел сигналы,
                # а pipeline не доходил до MTF aggregation.
                # Русский комментарий: отсутствие NG-intent на отдельном тике — штатное состояние.
                if os.getenv("RUNTIME_DEBUG_LOGS", "0") == "1":
                    print(
                        f"PIPE_NG_TICK_ROUTE_NO_INTENT_CONTINUE_MTF symbol={sym}",
                        flush=True,
                    )
            else:
                print(
                    f"PIPE_NG_SIGNAL side={raw_intent.get('side')} "
                    f"price={raw_intent.get('price')} reason={raw_intent.get('reason')}",
                    flush=True,
                )

        # === SIMULATION MOVE (CRITICAL) ===
        if self.runtime_config.get_bool("SIMULATE_MARKET", False):
            import random
            price = price * (1 + random.uniform(-0.002, 0.002))
            st["last"] = price
        # =========================================================
        # === MTF AGGREGATION (M1/M5/M15)
        # =========================================================
        mtf = self._mtf.setdefault(sym, {"m1": [], "m5": None, "m15": None})

        mtf["m1"].append(price)

        # ограничим буфер
        if len(mtf["m1"]) > 20:
            mtf["m1"] = mtf["m1"][-20:]

        if len(mtf["m1"]) >= 5:
            mtf["m5"] = sum(mtf["m1"][-5:]) / 5

        if len(mtf["m1"]) >= 15:
            mtf["m15"] = sum(mtf["m1"][-15:]) / 15

        st["m5"] = mtf["m5"]
        st["m15"] = mtf["m15"]

        # === LIVE ATR ===
        try:
            st["atr"] = self.live_atr.update(price)
        except Exception:
            pass

        # === MARK TO MARKET ===
        try:
            if hasattr(self.portfolio, "mark_price"):
                self.portfolio.mark_price(sym, price)
        except Exception:
            pass

        # =========================================================
        # === LEGACY EXIT BLOCK DISABLED ===
        # =========================================================
        # Русский комментарий: старый SL/TP exit отключён.
        # Выход теперь строится через _build_exit_intent_if_any() выше и далее идёт
        # через общий путь: SignalRouter -> Risk -> PaperExecution -> FILL -> PositionManager.
        # Здесь нельзя делать return, иначе ExitEngine будет генерировать route без fill.
        qty_now = 0.0
        avg_now = 0.0

        # === PROFIT PROTECTION (BREAK-EVEN + TRAILING) ===
        try:
            if avg_now > 0:
                if qty_now > 0:
                    pnl_pct = (price - avg_now) / avg_now
                else:
                    pnl_pct = (avg_now - price) / avg_now

                # === BREAK-EVEN ===
                if pnl_pct > 0.003:  # +0.3%
                    if qty_now > 0:
                        be_price = avg_now * 1.0005
                        if price > be_price:
                            self.exit_engine._dynamic_stops[sym] = be_price
                            print(f"PIPE_BE_LONG {be_price}", flush=True)
                    else:
                        be_price = avg_now * 0.9995
                        if price < be_price:
                            self.exit_engine._dynamic_stops[sym] = be_price
                            print(f"PIPE_BE_SHORT {be_price}", flush=True)

                # === TRAILING ===
                if pnl_pct > 0.006:  # +0.6%
                    trail_distance = max(st.get("atr", 0.0), price * 0.003)

                    if qty_now > 0:
                        trail_price = price - trail_distance
                        self.exit_engine._dynamic_stops[sym] = trail_price
                        print(f"PIPE_TRAIL_LONG {trail_price}", flush=True)
                    else:
                        trail_price = price + trail_distance
                        self.exit_engine._dynamic_stops[sym] = trail_price
                        print(f"PIPE_TRAIL_SHORT {trail_price}", flush=True)

        except Exception as e:
            print(f"PIPE_PROFIT_PROTECT_ERROR {e}", flush=True)
        # =========================================================
        # === FEATURES + REGIME (ОДИН РАЗ)
        # =========================================================

        prev_price = st.get("prev_price", price)

        # === ATR FIX (ограничение и нормализация) ===
        raw_atr = st.get("atr") or abs(price - prev_price) or price * 0.003
        atr = min(raw_atr, price * 0.02)  # максимум 2% от цены
        st["atr"] = atr

        # EMA trend
        alpha_fast = 2 / (5 + 1)
        alpha_slow = 2 / (20 + 1)

        ema_fast = alpha_fast * price + (1 - alpha_fast) * st.get("ema_fast", price)
        ema_slow = alpha_slow * price + (1 - alpha_slow) * st.get("ema_slow", price)

        st["ema_fast"] = ema_fast
        st["ema_slow"] = ema_slow

        if ema_fast > ema_slow:
            trend = "up"
        elif ema_fast < ema_slow:
            trend = "down"
        else:
            trend = "flat"

        features = {
            "atr": atr,
            "trend": trend,
            "m5": st.get("m5"),
            "m15": st.get("m15"),
        }

        # === REGIME ===
        if not self.regime_enabled:
            regime = SimpleNamespace(
                trend="any",
                volatility="any",
                atr=atr,
                is_tradeable=lambda: True,
            )
        else:
            regime = self.regime_engine.evaluate(price, features)

        # === SAVE REGIME STATE (robust, deterministic) ===
        trend_val = getattr(regime, "trend", "unknown")
        vol_val = getattr(regime, "volatility", "unknown")
        atr_val = _safe_float(getattr(regime, "atr", 0.0), 0.0)

        st["regime_trend"] = trend_val
        st["regime_vol"] = vol_val
        st["regime_atr"] = atr_val

        # === CONTROLLED LOG (ONLY ON CHANGE, WITH TIME GUARD) ===
        prev_trend = st.get("_last_logged_trend")
        prev_vol = st.get("_last_logged_vol")
        now_ts = time.time()

        # логируем либо при изменении режима, либо раз в 10 сек (антишум)
        if (
            (prev_trend != trend_val)
            or (prev_vol != vol_val)
            or (now_ts - self._regime_last_log_ts > 10)
        ):
            # Русский комментарий: анти-спам для regime-логов в systemd.
            now_ts = time.time()
            log_every_sec = float(os.getenv("PIPE_REGIME_LOG_EVERY_SEC", "60"))
            if (now_ts - float(getattr(self, "_last_regime_log_ts", 0.0) or 0.0)) >= log_every_sec:
                self._last_regime_log_ts = now_ts
                print(
                    f"REGIME trend={trend_val} vol={vol_val} atr={round(atr_val, 5)}",
                    flush=True,
                )

            st["_last_logged_trend"] = trend_val
            st["_last_logged_vol"] = vol_val
            self._regime_last_log_ts = now_ts

        is_exit_intent = isinstance(raw_intent, dict) and raw_intent.get("intent_type") == "EXIT"
        is_force_intent = isinstance(raw_intent, dict) and raw_intent.get("strategy") == "force_once_buy"

        # === TREND + VOL FILTER (LEVEL 2 STABLE) ===
        try:
            atr_pct = abs(regime.atr / price) if price else 0

            # === 1. Слабая волатильность → нет сделки
            replay_accumulation_mode = (
                self.runtime_config.get_bool("SIMULATE_MARKET", False)
                and os.getenv("REPLAY_ACCUMULATION_MODE", "0") == "1"
            )

            static_atr_threshold = float(os.getenv("ATR_MIN_PCT", "0.002"))

            if os.getenv("BR_ADAPTIVE_VOL_GATE_ENABLED", "1") == "1":
                from finam_core.risk.br_adaptive_volatility_gate import BrAdaptiveVolatilityGate

                if not hasattr(self, "br_adaptive_volatility_gate"):
                    self.br_adaptive_volatility_gate = BrAdaptiveVolatilityGate(
                        min_threshold=float(os.getenv("BR_ADAPTIVE_VOL_MIN_THRESHOLD", "0.0008")),
                        max_threshold=float(os.getenv("BR_ADAPTIVE_VOL_MAX_THRESHOLD", "0.0025")),
                    )

                vol_decision = self.br_adaptive_volatility_gate.decide(
                    atr_pct=float(atr_pct or 0.0),
                    static_threshold=static_atr_threshold,
                    regime_volatility=str(getattr(regime, "volatility", "") or ""),
                )
                low_vol_block = not vol_decision.allowed
                effective_atr_threshold = vol_decision.threshold
                vol_gate_mode = vol_decision.mode
                vol_gate_reason = vol_decision.reason
            else:
                low_vol_block = float(atr_pct or 0.0) < static_atr_threshold
                effective_atr_threshold = static_atr_threshold
                vol_gate_mode = "static"
                vol_gate_reason = "static_atr_min"

            # Русский комментарий: диагностический лог успешного прохождения adaptive volatility gate.
            if (not is_exit_intent) and (not is_force_intent) and (not low_vol_block):
                now_ts = time.time()
                log_every_sec = float(os.getenv("PIPE_VOL_GATE_OK_LOG_EVERY_SEC", "120"))
                if (now_ts - float(getattr(self, "_last_vol_gate_ok_log_ts", 0.0) or 0.0)) >= log_every_sec:
                    self._last_vol_gate_ok_log_ts = now_ts
                    print(
                        "PIPE_VOL_GATE_OK",
                        f"atr_pct={round(float(atr_pct or 0.0), 6)}",
                        f"threshold={round(float(effective_atr_threshold or 0.0), 6)}",
                        f"static_threshold={round(float(static_atr_threshold or 0.0), 6)}",
                        f"mode={vol_gate_mode}",
                        f"reason={vol_gate_reason}",
                        f"atr={round(float(getattr(regime, 'atr', 0.0) or 0.0), 6)}",
                        f"price={round(float(price or 0.0), 6)}",
                        flush=True,
                    )

            if (not is_exit_intent) and (not is_force_intent) and low_vol_block:
                if replay_accumulation_mode:
                    self._log_dedup(
                        "PIPE_VOL_LOW_BYPASS_REPLAY_ACCUMULATION",
                        "PIPE_VOL_LOW_BYPASS_REPLAY_ACCUMULATION",
                        heartbeat_sec=float(os.getenv("PIPE_VOL_LOW_BLOCK_LOG_EVERY_SEC", "60")),
                    )
                else:
                    # Русский комментарий: анти-спам для повторяющихся low-volatility блокировок.
                    now_ts = time.time()
                    log_every_sec = float(os.getenv("PIPE_VOL_LOW_BLOCK_LOG_EVERY_SEC", "60"))
                    if (now_ts - float(getattr(self, "_last_vol_low_block_log_ts", 0.0) or 0.0)) >= log_every_sec:
                        self._last_vol_low_block_log_ts = now_ts
                        print(
                            "PIPE_VOL_LOW_BLOCK",
                            f"atr_pct={round(float(atr_pct or 0.0), 6)}",
                            f"threshold={round(float(effective_atr_threshold or 0.0), 6)}",
                            f"static_threshold={round(float(static_atr_threshold or 0.0), 6)}",
                            f"mode={vol_gate_mode}",
                            f"reason={vol_gate_reason}",
                            f"atr={round(float(getattr(regime, 'atr', 0.0) or 0.0), 6)}",
                            f"price={round(float(price or 0.0), 6)}",
                            flush=True,
                        )
                        # Русский комментарий: сохраняем pre-signal low-vol block в аудит.
                        self._save_pre_signal_block_audit_v1(
                            symbol=str(sym),
                            strategy=self._strategy_name_for_symbol(str(sym)),
                            timeframe=str(getattr(self, "timeframe", None) or st.get("timeframe") or "M5"),
                            block_type="VOL_LOW_BLOCK",
                            block_reason=str(vol_gate_reason),
                            price=price,
                            atr=getattr(regime, "atr", None),
                            atr_pct=atr_pct,
                            threshold=effective_atr_threshold,
                            regime=str(getattr(regime, "type", None) or ""),
                            trend=str(getattr(regime, "trend", None) or ""),
                            volatility=str(getattr(regime, "volatility", None) or ""),
                            payload={
                                "static_threshold": static_atr_threshold,
                                "vol_gate_mode": vol_gate_mode,
                                "source": "paper_pipeline",
                            },
                        )

                    if os.getenv("BR_COMPRESSION_WATCH_ENABLED", "1") == "1":
                        from finam_core.risk.br_compression_watch import BrCompressionWatch

                        if not hasattr(self, "br_compression_watch"):
                            self.br_compression_watch = BrCompressionWatch(
                                activation_ratio=float(os.getenv("BR_COMPRESSION_WATCH_RATIO", "0.65"))
                            )

                        compression_decision = self.br_compression_watch.decide(
                            atr_pct=float(atr_pct or 0.0),
                            threshold=float(effective_atr_threshold or 0.0),
                        )

                        if compression_decision.active:
                            compression_log_every_sec = float(os.getenv("PIPE_BR_COMPRESSION_WATCH_LOG_EVERY_SEC", "120"))
                            if (now_ts - float(getattr(self, "_last_br_compression_watch_log_ts", 0.0) or 0.0)) >= compression_log_every_sec:
                                self._last_br_compression_watch_log_ts = now_ts
                                print(
                                    "PIPE_BR_COMPRESSION_WATCH",
                                    f"atr_pct={round(compression_decision.atr_pct, 6)}",
                                    f"threshold={round(compression_decision.threshold, 6)}",
                                    f"compression_ratio={round(compression_decision.compression_ratio, 4)}",
                                    f"reason={compression_decision.reason}",
                                    f"mode={vol_gate_mode}",
                                    f"price={round(float(price or 0.0), 6)}",
                                    flush=True,
                                )
                                # Русский комментарий: сохраняем pre-signal compression watch в аудит.
                                self._save_pre_signal_block_audit_v1(
                                    symbol=str(sym),
                                    strategy=self._strategy_name_for_symbol(str(sym)),
                                    timeframe=str(getattr(self, "timeframe", None) or st.get("timeframe") or "M5"),
                                    block_type="COMPRESSION_WATCH",
                                    block_reason=str(compression_decision.reason),
                                    price=price,
                                    atr=getattr(regime, "atr", None),
                                    atr_pct=compression_decision.atr_pct,
                                    threshold=compression_decision.threshold,
                                    compression_ratio=compression_decision.compression_ratio,
                                    regime=str(getattr(regime, "type", None) or ""),
                                    trend=str(getattr(regime, "trend", None) or ""),
                                    volatility=str(getattr(regime, "volatility", None) or ""),
                                    payload={
                                        "vol_gate_mode": vol_gate_mode,
                                        "source": "paper_pipeline",
                                    },
                                )

                    # Русский комментарий:
                    # В PAPER-режиме разрешаем advisory-only проход через low-vol filter
                    # для накопления live-статистики сделок.
                    vol_low_advisory_only = (
                        str(os.getenv("EXECUTION_MODE", "paper")).lower() == "paper"
                        and os.getenv("VOL_LOW_ADVISORY_ONLY", "0") == "1"
                    )
                    if vol_low_advisory_only:
                        print(
                            "PIPE_VOL_LOW_ADVISORY_CONTINUE",
                            f"symbol={sym}",
                            f"vol={regime.volatility}",
                            f"trend={regime.trend}",
                            "paper_only=1",
                            flush=True,
                        )
                    else:
                        return

            # === 2. Слишком высокая вола → шум
            if (not is_exit_intent) and (not is_force_intent) and atr_pct > 0.03:
                print("PIPE_VOL_HIGH_BLOCK", flush=True)
                return

            # === 3. СЛАБЫЙ ТРЕНД (главный фикс)
            if (not is_exit_intent) and (not is_force_intent) and regime.trend in ("up", "down"):
                trend_strength = abs(st.get("ema_fast", price) - st.get("ema_slow", price)) / price

                if trend_strength < float(os.getenv("TREND_STRENGTH_MIN","0.0003")) and regime.volatility != "high":  # ключевой параметр
                    print("PIPE_TREND_WEAK_BLOCK", flush=True)
                    return

        except Exception:
            pass


        # === NOISE FILTER (ATR sanity) ===
        try:
            if atr is not None and price is not None:
                atr_pct = abs(atr / price)
                if (not is_force_intent) and atr_pct > 0.1:  # >10% — мусорный сигнал
                    print("PIPE_NOISE_BLOCK high_atr", flush=True)
                    return
        except Exception:
            pass

        # =========================================================
        # === STRATEGY SELECTION (FIXED REGIME V2)
        # =========================================================

        # ВАЖНО: используем РЕАЛЬНЫЙ regime (из regime_engine), а не session
        if PIPE_DEBUG:
            print(f"DEBUG REGIME_ROUTER trend={regime.trend} vol={regime.volatility}", flush=True)

        try:
            # === MTF FILTER (WEAK VERSION, no blocking) ===
            m5 = st.get("m5")
            if m5:
                trend = regime.trend

                if trend == "up" and not (price > m5):
                    self._log_dedup("PIPE_MTF_WEAK_LONG", "PIPE_MTF_WEAK_LONG")

                if trend == "down" and not (price < m5):
                    self._log_dedup("PIPE_MTF_WEAK_SHORT", "PIPE_MTF_WEAK_SHORT")

            # === TREND MODE (BREAKOUT ONLY, STRATEGY DISABLED) ===
            if (not is_exit_intent) and (not is_force_intent) and regime.trend in ("up", "down"):
                if PIPE_DEBUG:
                    print("DEBUG breakout mode (strategy disabled)", flush=True)
                raw_intent = None  # force fallback breakout logic

            # === MEAN REVERSION ===
            elif regime.trend == "flat":
                if PIPE_DEBUG:
                    print("DEBUG using mean_reversion", flush=True)

                if not is_force_intent:
                    # Русский комментарий:
                    # выбираем стратегию по symbol; если явной стратегии нет — используется default.
                    raw_intent = self.signal_router.route(
                        SignalRouteInput(
                            symbol=sym,
                            state=st,
                        )
                    )
                if PIPE_DEBUG:
                    print("DEBUG MR result:", raw_intent, flush=True)

                # fallback to breakout if no MR signal
                if raw_intent is None:
                    if PIPE_DEBUG:
                        print("DEBUG fallback to breakout", flush=True)

        except Exception as e:
            print(f"STRATEGY_ERROR {e}", flush=True)
            return

        # === GLOBAL SAFETY (ensure variables always defined) ===
        curr_price = st.get("last")
        if curr_price is None:
            return

        atr = st.get("atr") or 0.0

        history = st.setdefault("price_history", [])
        if len(history) < 2:
            history.append(curr_price)
            if not (isinstance(raw_intent, dict) and raw_intent.get('strategy') == 'force_once_buy'):
                return

        local_high = max(history[-10:])
        local_low = min(history[-10:])

        history.append(curr_price)
        if len(history) > 20:
            st["price_history"] = history[-20:]

        # === GLOBAL FALLBACK (BREAKOUT LEVELS + ATR) ===
        # PATCH: SMART ENTRY (RETEST MODE)
        # вставить в fallback breakout блок

        # === SMART ENTRY STATE ===
        st.setdefault("pending_breakout", None)
        st.setdefault("last_breakout_key", None)
        st.setdefault("last_breakout_ts", 0.0)

        # === DETECT BREAKOUT (не входим сразу) ===
        if (not is_force_intent) and curr_price > local_high - atr * 0.5:
            now_breakout_ts = time.time()
            breakout_level = self._breakout_bucketed_level(sym, local_high)
            breakout_key = f"BUY:{breakout_level}"
            breakout_ttl = float(os.getenv("BREAKOUT_DEDUP_TTL", "30"))

            if (
                st.get("pending_breakout") is None
                and not (
                    st.get("last_breakout_key") == breakout_key
                    and now_breakout_ts - float(st.get("last_breakout_ts", 0.0) or 0.0) < breakout_ttl
                )
            ):
                st["pending_breakout"] = {
                    "side": "BUY",
                    "level": local_high,
                    "key": breakout_key,
                    "ts": now_breakout_ts,
                }
                st["last_breakout_key"] = breakout_key
                st["last_breakout_ts"] = now_breakout_ts
                self._log_breakout_detected_dedup_v1(str(sym), "BUY", local_high)

        elif (not is_force_intent) and curr_price < local_low + atr * 0.5:
            now_breakout_ts = time.time()
            breakout_level = self._breakout_bucketed_level(sym, local_low)
            breakout_key = f"SELL:{breakout_level}"
            breakout_ttl = float(os.getenv("BREAKOUT_DEDUP_TTL", "30"))

            if (
                st.get("pending_breakout") is None
                and not (
                    st.get("last_breakout_key") == breakout_key
                    and now_breakout_ts - float(st.get("last_breakout_ts", 0.0) or 0.0) < breakout_ttl
                )
            ):
                st["pending_breakout"] = {
                    "side": "SELL",
                    "level": local_low,
                    "key": breakout_key,
                    "ts": now_breakout_ts,
                }
                st["last_breakout_key"] = breakout_key
                st["last_breakout_ts"] = now_breakout_ts
                self._log_breakout_detected_dedup_v1(str(sym), "SELL", local_low)

        # === RETEST ENTRY ===
        pb = st.get("pending_breakout")

        if pb:
            side = pb["side"]
            level = pb["level"]

            # TTL (устаревание сигнала)
            if time.time() - pb["ts"] > 60:
                st["pending_breakout"] = None
                return

            # BUY RETEST
            if side == "BUY":
                if curr_price <= level + atr * 0.2:
                    if self._pipeline_log_throttle_allow(f"PIPE_SMART_ENTRY:{sym}:BUY", float(os.getenv("PIPE_SMART_ENTRY_LOG_TTL_SEC", "60"))):
                        print(f"PIPE_SMART_ENTRY BUY symbol={sym}", flush=True)
                    entry_side = "BUY"
                else:
                    return

            # SELL RETEST
            elif side == "SELL":
                if curr_price >= level - atr * 0.2:
                    if self._pipeline_log_throttle_allow(f"PIPE_SMART_ENTRY:{sym}:SELL", float(os.getenv("PIPE_SMART_ENTRY_LOG_TTL_SEC", "60"))):
                        print(f"PIPE_SMART_ENTRY SELL symbol={sym}", flush=True)
                    entry_side = "SELL"
                else:
                    return

            # === EXECUTE ENTRY ===
            risk_per_trade = 0.01
            capital = getattr(self.portfolio, "starting_cash", 100000)
            risk_amount = capital * risk_per_trade

            atr_safe = max(atr, curr_price * 0.002)
            stop_distance = max(atr_safe * 2.0, curr_price * 0.01, 0.15)
            stop_distance = max(stop_distance, 0.05)

            qty = round(risk_amount / stop_distance, 3)
            qty = max(min(qty, 1.0), 0.1)

            rr = 2.0
            take_distance = stop_distance * rr

            strategy_name = self._strategy_name_for_symbol(sym)

            raw_intent = {
                "symbol": sym,
                "side": entry_side,
                "qty": qty,
                "price": curr_price,
                "entry_price": curr_price,
                "stop_loss": curr_price - stop_distance if entry_side == "BUY" else curr_price + stop_distance,
                "take_profit": curr_price + take_distance if entry_side == "BUY" else curr_price - take_distance,
                "reason": "smart_entry_retest_br_manual_candidate" if str(sym).startswith("BR") else "smart_entry_retest",
                "strategy": strategy_name,
                "source": "smart_entry_retest",
                "signal_id": f"smart-{sym}-{int(time.time() * 1000)}",
                "horizon": "INTRADAY",
                "timeframe": "LIVE",
                "features": {
                    "strategy": strategy_name,
                    "stop": curr_price - stop_distance if entry_side == "BUY" else curr_price + stop_distance,
                    "take": curr_price + take_distance if entry_side == "BUY" else curr_price - take_distance,
                    "rr": rr,
                    "breakout_level": level,
                    "atr": atr,
                    "stop_distance": stop_distance,
                    "take_distance": take_distance,
                }
            }

            if str(sym).startswith("BR"):
                rub_per_point = get_br_rub_per_point(getattr(self, "market_state", None))
                commission_per_contract = float(os.getenv("BR_COMMISSION_RUB_PER_CONTRACT", "10"))
                commission_rub = qty * commission_per_contract * 2.0

                gross_risk_rub = abs(raw_intent["entry_price"] - raw_intent["stop_loss"]) * qty * rub_per_point
                gross_profit_rub = abs(raw_intent["take_profit"] - raw_intent["entry_price"]) * qty * rub_per_point

                raw_intent["risk_rub"] = gross_risk_rub + commission_rub
                raw_intent["profit_rub"] = gross_profit_rub - commission_rub
                raw_intent["commission_rub"] = commission_rub

                print(
                    f"BR_MANUAL_ENTRY_CANDIDATE "
                    f"symbol={sym} side={entry_side} "
                    f"entry={curr_price} "
                    f"stop_loss={raw_intent['features'].get('stop')} "
                    f"take_profit={raw_intent['features'].get('take')} "
                    f"rr={rr} qty={qty} "
                    f"level={level} atr={atr} "
                    f"stop_distance={stop_distance} take_distance={take_distance}",
                    flush=True,
                )

            # сброс состояния
            st["pending_breakout"] = None

        else:

            _runtime_guard_advisory_v1(
                symbol=str(sym),
                strategy=str(
                    raw_intent.get("strategy")
                    if isinstance(raw_intent, dict) and raw_intent.get("strategy")
                    else self._strategy_name_for_symbol(str(sym))
                ),
                timeframe=str(raw_intent.get("timeframe") or "LIVE") if isinstance(raw_intent, dict) else "LIVE",
                side=(
                    "LONG" if isinstance(raw_intent, dict) and str(raw_intent.get("side") or "").upper() == "BUY"
                    else "SHORT" if isinstance(raw_intent, dict) and str(raw_intent.get("side") or "").upper() == "SELL"
                    else "UNKNOWN"
                ),
                session_bucket=str(
                    (
                        raw_intent.get("session_bucket")
                        or (raw_intent.get("payload") or {}).get("session_bucket")
                        or "UNKNOWN"
                    )
                    if isinstance(raw_intent, dict)
                    else "UNKNOWN"
                ),
            )

            _guard_classification_advisory_v1(
                symbol=str(sym),
                strategy=str(
                    raw_intent.get("strategy")
                    if isinstance(raw_intent, dict) and raw_intent.get("strategy")
                    else self._strategy_name_for_symbol(str(sym))
                ),
                timeframe=str(raw_intent.get("timeframe") or "LIVE") if isinstance(raw_intent, dict) else "LIVE",
                side=(
                    "LONG" if isinstance(raw_intent, dict) and str(raw_intent.get("side") or "").upper() == "BUY"
                    else "SHORT" if isinstance(raw_intent, dict) and str(raw_intent.get("side") or "").upper() == "SELL"
                    else "UNKNOWN"
                ),
                session_bucket=str(
                    (
                        raw_intent.get("session_bucket")
                        or (raw_intent.get("payload") or {}).get("session_bucket")
                        or "UNKNOWN"
                    )
                    if isinstance(raw_intent, dict)
                    else "UNKNOWN"
                ),
            )


            if not (isinstance(raw_intent, dict) and raw_intent.get('strategy') == 'force_once_buy'):
                return

        # === ROLLBACK PROTECTION (анти-плохой вход) ===
        try:
            last_price = st.get("last")
            prev_price = st.get("prev_price")

            if last_price and prev_price and raw_intent and not (isinstance(raw_intent, dict) and raw_intent.get('strategy') == 'force_once_buy'):
                move = abs(last_price - prev_price)

                # 1. слишком маленькое движение → шум
                if move < (st.get("atr", 0.0) or 0.0) * 0.1:
                    print("PIPE_ROLLBACK_BLOCK small_move", flush=True)
                    if self._is_ng_symbol(str(sym)):
                        print(
                            f"PIPE_NG_INTENT_ROLLBACK_BLOCK symbol={sym} reason=small_move "
                            f"side={side} last_price={last_price} prev_price={prev_price} "
                            f"move={move} atr={st.get('atr', 0.0)}",
                            flush=True,
                        )
                    return

                # 2. вход против импульса
                side = raw_intent.get("side")
                if side == "BUY" and last_price < prev_price:
                    print("PIPE_ROLLBACK_BLOCK wrong_direction", flush=True)
                    if self._is_ng_symbol(str(sym)):
                        print(
                            f"PIPE_NG_INTENT_ROLLBACK_BLOCK symbol={sym} reason=wrong_direction_buy "
                            f"side={side} last_price={last_price} prev_price={prev_price}",
                            flush=True,
                        )
                    return

                if side == "SELL" and last_price > prev_price:
                    print("PIPE_ROLLBACK_BLOCK wrong_direction", flush=True)
                    if self._is_ng_symbol(str(sym)):
                        print(
                            f"PIPE_NG_INTENT_ROLLBACK_BLOCK symbol={sym} reason=wrong_direction_sell "
                            f"side={side} last_price={last_price} prev_price={prev_price}",
                            flush=True,
                        )
                    return

        except Exception as e:
            print(f"PIPE_ROLLBACK_ERROR {e}", flush=True)

        if PIPE_DEBUG:
            print(f"DEBUG raw_intent:", raw_intent, flush=True)
        if PIPE_DEBUG:
            print(f"DEBUG price_in_state last={st.get('last')} bid={st.get('bid')} ask={st.get('ask')}", flush=True)
        # === ENSURE PRICE IN INTENT (FIX no_price) ===
        try:
            if isinstance(raw_intent, dict):
                if "price" not in raw_intent or raw_intent.get("price") is None:
                    px = st.get("last") or st.get("price") or st.get("bid") or st.get("ask")
                    if px is not None:
                        raw_intent["price"] = float(px)
            else:
                if hasattr(raw_intent, "price"):
                    if getattr(raw_intent, "price", None) is None:
                        px = st.get("last") or st.get("price") or st.get("bid") or st.get("ask")
                        if px is not None:
                            raw_intent.price = float(px)
        except Exception as e:
            print(f"PRICE_INJECT_ERROR {e}", flush=True)
        # === INJECT FEATURES ===
        if isinstance(raw_intent, dict):
            raw_intent.setdefault("features", {})
            raw_intent["features"].update({
                "atr": regime.atr,
                "trend": regime.trend,
                "volatility": regime.volatility,
            })

            regime_label = RegimeLabeler.label(
                state=st,
                features=raw_intent.get("features", {}),
            )
            raw_intent["features"]["regime_label"] = regime_label
            raw_intent["regime"] = regime_label
        else:
            if hasattr(raw_intent, "features"):
                raw_intent.features.update({
                    "atr": regime.atr,
                    "trend": regime.trend,
                    "volatility": regime.volatility,
                })

                regime_label = RegimeLabeler.label(
                    state=st,
                    features=raw_intent.features,
                )
                raw_intent.features["regime_label"] = regime_label
                raw_intent.regime = regime_label

        # =========================================================
        # === REGIME FILTER
        # =========================================================
        if (not is_force_intent) and not regime.is_tradeable():
            print(
                f"PIPE_REGIME_BLOCK trend={regime.trend} vol={regime.volatility}",
                flush=True,
            )
            return
        # =========================================================
        # === SIGNAL INTENT V2 COMPATIBILITY BRIDGE
        # =========================================================
        try:
            normalized_signal_intent = StrategyIntentAdapter.normalize(raw_intent)
            raw_intent = StrategyIntentAdapter.to_pipeline_dict(normalized_signal_intent)
        except Exception as exc:
            print(f"PIPE_SIGNAL_INTENT_ADAPTER_ERROR {type(exc).__name__}:{exc}", flush=True)
            return

        # =========================================================
        # === ROUTER
        # =========================================================
        routed = self.signal_intent_router.route(raw_intent)

        if self._should_log_routed_signal(routed):
            if PIPE_DEBUG:
                print(f"DEBUG routed: {routed}", flush=True)

        # =========================================================
        # === SESSION FILTER (ЕДИНЫЙ ИСТОЧНИК, POST-ROUTER)
        # =========================================================
        try:
            session = self.session.get_regime(sym)

            if not session.get("allow_entries", False):
                if os.getenv("SESSION_OVERRIDE", "0") == "1" or self.runtime_config.get_bool("SIMULATE_MARKET", False):
                    self._log_dedup(
                        "PIPE_SESSION_BYPASS_AFTER_ROUTER",
                        "PIPE_SESSION_BYPASS_AFTER_ROUTER",
                        heartbeat_sec=float(os.getenv("SESSION_OVERRIDE_LOG_SEC", "30")),
                    )
                else:
                    self._log_dedup(
                        f"PIPE_SESSION_BLOCK_AFTER_ROUTER:{session.get('phase')}",
                        f"PIPE_SESSION_BLOCK_AFTER_ROUTER phase={session.get('phase')}",
                        heartbeat_sec=float(os.getenv("SESSION_BLOCK_LOG_SEC", "300")),
                    )
                    return

        except Exception as e:
            print(f"PIPE_SESSION_ERROR {e}", flush=True)
            return

        # =========================================================
        # === OVERRIDE LAYER
        # =========================================================
        override = os.getenv("OVERRIDE_MODE", "0") == "1"

        if override:
            print("PIPE_OVERRIDE_ACTIVE", flush=True)
            try:
                routed.allowed = True
            except Exception:
                pass


        # =========================================================
        # === SIGNAL VALIDATION (FIRST!)
        # =========================================================
        if not routed.allowed:
            # suppress noisy duplicate logs
            if routed.reason != "duplicate_signal":
                print(f"PIPE_SIGNAL_REJECT reason={routed.reason}", flush=True)
            return

        intent = routed.intent.to_dict()

        # Русский комментарий: SIGNAL SNAPSHOT V1 — сохраняем наблюдаемый контекст сигнала до risk/order gate.
        try:
            features = intent.get("features") if isinstance(intent.get("features"), dict) else {}
            intent["signal_quality_snapshot"] = {
                "version": "v1",
                "source": intent.get("source"),
                "strategy": intent.get("strategy") or features.get("strategy"),
                "symbol": intent.get("symbol"),
                "side": intent.get("side"),
                "entry_price": intent.get("entry_price") or intent.get("price") or intent.get("limit_price"),
                "stop_loss": intent.get("stop_loss") or features.get("stop"),
                "take_profit": intent.get("take_profit") or features.get("take"),
                "rr": intent.get("rr") or features.get("rr"),
                "qty": intent.get("qty"),
                "risk_rub": intent.get("risk_rub"),
                "profit_rub": intent.get("profit_rub"),
                "commission_rub": intent.get("commission_rub"),
                "breakout_level": features.get("breakout_level"),
                "local_high": features.get("local_high"),
                "local_low": features.get("local_low"),
                "atr": features.get("atr"),
                "stop_distance": features.get("stop_distance"),
                "take_distance": features.get("take_distance"),
                "regime": intent.get("regime") or features.get("regime"),
                "volatility_regime": intent.get("volatility_regime") or features.get("volatility_regime"),
                "session_type": intent.get("session_type") or features.get("session_type"),
                "confidence": intent.get("confidence") or features.get("confidence") or features.get("regime_confidence"),
                "policy_version": (
                    intent.get("br_filtered_policy", {}).get("version")
                    if isinstance(intent.get("br_filtered_policy"), dict)
                    else None
                ),
                "size_multiplier": (
                    intent.get("br_filtered_policy", {}).get("size_multiplier")
                    if isinstance(intent.get("br_filtered_policy"), dict)
                    else None
                ),
            }
        except Exception as exc:
            LOG.warning("PIPE_SIGNAL_QUALITY_SNAPSHOT_FAILED error=%s", exc)

        # Русский комментарий: сохраняем каждый валидный торговый intent до risk/order gate.
        try:
            if getattr(self, "signal_repository", None) is not None:
                signal_id = self.signal_repository.save_signal(intent)
                intent["signal_id"] = signal_id

                # Русский комментарий: runtime guard soft-block enrichment — только обогащение features, без блокировки исполнения.
                try:
                    soft_block = getattr(self, "runtime_guard_soft_block_mode_v1", None)
                    if soft_block is None:
                        from finam_core.analytics.runtime_guard_soft_block_mode_v1 import RuntimeGuardSoftBlockModeV1
                        soft_block = RuntimeGuardSoftBlockModeV1()
                        setattr(self, "runtime_guard_soft_block_mode_v1", soft_block)

                    guard_decision = soft_block.apply(intent)

                    # Русский комментарий: сохраняем runtime guard telemetry в PostgreSQL, без влияния на execution.
                    try:
                        registry = getattr(self, "runtime_guard_signal_registry_v1", None)
                        if registry is None:
                            from finam_core.analytics.runtime_guard_signal_registry_v1 import RuntimeGuardSignalRegistryV1
                            registry = RuntimeGuardSignalRegistryV1()
                            registry.migrate()
                            setattr(self, "runtime_guard_signal_registry_v1", registry)

                        registry.save(signal=intent, decision=guard_decision)
                    except Exception as registry_exc:
                        print(f"RUNTIME_GUARD_SIGNAL_REGISTRY_FAILED error={registry_exc}", flush=True)

                except Exception as exc:
                    print(f"RUNTIME_GUARD_SOFT_BLOCK_FAILED error={exc}", flush=True)

                # Русский комментарий: runtime guard observability — только логирование, без блокировки исполнения.
                try:
                    hook = getattr(self, "runtime_guard_observability_hook_v1", None)
                    if hook is None:
                        from finam_core.analytics.runtime_guard_observability_hook_v1 import RuntimeGuardObservabilityHookV1
                        hook = RuntimeGuardObservabilityHookV1()
                        setattr(self, "runtime_guard_observability_hook_v1", hook)

                    hook.observe_signal(intent)
                except Exception as exc:
                    print(f"RUNTIME_GUARD_OBSERVABILITY_FAILED error={exc}", flush=True)
        except Exception as exc:
            LOG.warning("PIPE_SIGNAL_SAVE_FAILED error=%s", exc)


        # Русский комментарий: Telegram получает торговую точку сразу после формирования валидного intent.
        # Заявка при этом не выставляется; отправляются только вход, стоп-лосс и тейк-профит.
        try:
            send_signal_alert_from_intent(self.notifier, intent)
        except Exception as exc:
            LOG.warning("PIPE_SIGNAL_ALERT_FAILED error=%s", exc)

        # === CONTRACT RESOLVE BEFORE EXECUTION ===
        try:
            intent["symbol"] = self._resolver.resolve(intent["symbol"])
        except Exception:
            pass
        # === HARD PRICE INJECTION (FIX missing_price) ===
        try:
            if intent.get("price") is None:
                px = st.get("last") or st.get("price") or st.get("bid") or st.get("ask")
                if px is not None:
                    intent["price"] = float(px)
                    if PIPE_DEBUG:
                        print(f"DEBUG PRICE INJECTED {intent['price']}", flush=True)
                else:
                    print("PIPE_PRICE_INJECT_FAIL", flush=True)
        except Exception as e:
            print(f"PRICE_INJECT_ERROR {e}", flush=True)

        # =========================================================
        # === TREND FLIP GUARD (prevents rapid direction changes) ===
        try:
            prev_trend = st.get("prev_trend")
            if prev_trend and prev_trend != regime.trend:
                if (not is_exit_intent) and abs(regime.atr / price) < 0.01:
                    print("PIPE_TREND_FLIP_BLOCK", flush=True)
                    return
            st["prev_trend"] = regime.trend
        except Exception:
            pass

        # =========================================================
        # === STRICT TREND ALIGNMENT (breakout only in trend direction) ===
        # =========================================================
        try:
            trend = regime.trend
            side = intent.get("side")

            # Русский комментарий: current_qty нужен для trade_role gate до основного execution-блока.
            try:
                current_qty
            except UnboundLocalError:
                current_qty = float(
                    getattr(self, "_broker_position_qty_by_symbol", {}).get(sym, 0.0) or 0.0
                )

            intent_allowed, intent_reason = self._position_intent_allows_order(sym, side, current_qty)
            if not intent_allowed:
                msg = (
                    f"PIPE_POSITION_INTENT_ORDER_BLOCK symbol={sym} side={side} "
                    f"current_qty={current_qty} reason={intent_reason}"
                )
                if hasattr(self, "_log_dedup"):
                    self._log_dedup(
                        f"PIPE_POSITION_INTENT_ORDER_BLOCK:{sym}:{side}:{intent_reason}",
                        msg,
                        heartbeat_sec=float(os.getenv("POSITION_INTENT_BLOCK_HEARTBEAT_SEC", "300")),
                    )
                else:
                    print(msg, flush=True)
                return

            hard_gate_allowed, hard_gate_reason = self._broker_position_hard_gate_allows_order(sym, side, current_qty)
            if not hard_gate_allowed:
                block_key = (sym, side, hard_gate_reason)
                seen = getattr(self, "_broker_position_hard_gate_order_block_seen", set())

                if block_key not in seen:
                    print(
                        f"PIPE_BROKER_POSITION_HARD_GATE_ORDER_BLOCK symbol={sym} side={side} "
                        f"reason={hard_gate_reason}",
                        flush=True,
                    )
                    seen.add(block_key)
                    self._broker_position_hard_gate_order_block_seen = seen

                return

            protection_allowed, protection_reason = self._broker_protection_gate_allows_order(sym, side, current_qty)
            if not protection_allowed:
                block_key = (sym, side, protection_reason)
                seen = getattr(self, "_broker_protection_missing_seen", set())

                if block_key not in seen:
                    print(
                        f"PIPE_BROKER_PROTECTION_GATE_ORDER_BLOCK symbol={sym} side={side} "
                        f"reason={protection_reason}",
                        flush=True,
                    )
                    seen.add(block_key)
                    self._broker_protection_missing_seen = seen

                return

            if self.runtime_config.get("EXECUTION_MODE", "paper").lower() == "real":
                recon_allowed, recon_reason = self._reconciliation_allows_real_order(sym, current_qty)
                if not recon_allowed:
                    print(
                        f"PIPE_RECONCILIATION_ORDER_BLOCK symbol={sym} side={side} "
                        f"current_qty={current_qty} reason={recon_reason}",
                        flush=True,
                    )
                    return

            # === PRIMARY TREND ALIGNMENT ===
            if not is_exit_intent:
                expected_side = None

                if trend == "up":
                    expected_side = "BUY"
                elif trend == "down":
                    expected_side = "SELL"

                trend_decision = self.trend_filter.check(
                    expected=expected_side,
                    actual=side,
                )

                if not trend_decision.allowed:
                    self._log_dedup(
                        f"PIPE_TREND_BLOCK:{sym}:{trend_decision.expected}:{trend_decision.actual}",
                        f"PIPE_TREND_BLOCK symbol={sym} "
                        f"expected={trend_decision.expected} "
                        f"actual={trend_decision.actual}",
                        heartbeat_sec=60,
                    )

                    # Русский комментарий:
                    # В PAPER-режиме разрешаем advisory-only проход через trend gate,
                    # чтобы накапливать live-статистику фактических PAPER-сделок.
                    trend_advisory_only = (
                        str(os.getenv("EXECUTION_MODE", "paper")).lower() == "paper"
                        and os.getenv("TREND_GATE_ADVISORY_ONLY", "0") == "1"
                    )
                    if trend_advisory_only:
                        print(
                            "PIPE_TREND_ADVISORY_CONTINUE",
                            f"symbol={sym}",
                            f"expected={trend_decision.expected}",
                            f"actual={trend_decision.actual}",
                            "paper_only=1",
                            flush=True,
                        )
                    else:
                        return

            # === EXTRA IMPULSE FILTER ===
            if (not is_exit_intent) and (not is_force_intent) and abs(st.get("ema_fast", price) - price) / price < float(os.getenv("IMPULSE_MIN","0.0003")) and regime.volatility != "high":
                print("PIPE_NO_IMPULSE_BLOCK", flush=True)

                # Русский комментарий:
                # В PAPER-режиме разрешаем advisory-only проход через impulse filter
                # для накопления live-статистики сделок.
                impulse_advisory_only = (
                    str(os.getenv("EXECUTION_MODE", "paper")).lower() == "paper"
                    and os.getenv("IMPULSE_FILTER_ADVISORY_ONLY", "0") == "1"
                )
                if impulse_advisory_only:
                    print(
                        "PIPE_IMPULSE_ADVISORY_CONTINUE",
                        f"symbol={sym}",
                        "paper_only=1",
                        flush=True,
                    )
                else:
                    return

            # === REMOVE DUPLICATE HARD FILTER (it caused over-blocking & loops) ===
            # (intentionally removed redundant conditions)

        except Exception as e:
            print(f"TREND_FILTER_ERROR {e}", flush=True)

        # =========================================================
        # === SIGNAL DEDUP (ANTI-DUPLICATE CORE FIX, WITH TTL)
        # =========================================================
        try:
            symbol = intent.get("symbol")
            side = intent.get("side")
            price = round(float(intent.get("price", 0.0)), 3)

            signal_key = f"{symbol}:{side}:{price}"
            now_ts = time.time()

            last_key = getattr(self, "_last_signal_key", None)
            last_ts = getattr(self, "_last_signal_ts", 0.0)

            dedup_ttl = float(os.getenv("SIGNAL_DEDUP_TTL", "2"))

            if last_key == signal_key and (now_ts - last_ts) < dedup_ttl:
                # duplicate suppressed silently (cooldown will handle)
                return

            self._last_signal_key = signal_key
            self._last_signal_ts = now_ts

        except Exception as e:
            print(f"PIPE_SIGNAL_KEY_ERROR {e}", flush=True)

        # =========================================================
        # === POSITION GUARD (STRICT, NO STACKING)
        # =========================================================
        self._restore_pm_position_from_projection_v1(str(sym))
        pos = self.pm.positions.get(sym)
        current_qty = float(getattr(pos, "qty", 0.0) or 0.0) if pos else 0.0
        avg_price = float(getattr(pos, "avg_price", 0.0) or 0.0) if pos else 0.0

        # === PYRAMIDING (LEVEL 2: add to winners only) ===
        if (not is_exit_intent) and current_qty != 0.0:
            side = intent.get("side")

            # позиция должна совпадать по направлению
            if (current_qty > 0 and side == "BUY") or (current_qty < 0 and side == "SELL"):

                # считаем текущую прибыль по реальной рыночной цене
                market_price = st.get("last") or price
                if current_qty > 0:
                    pnl_pct = (market_price - avg_price) / avg_price if avg_price else 0.0
                else:
                    pnl_pct = (avg_price - market_price) / avg_price if avg_price else 0.0

                # более гибкий порог для пирамидинга (более агрессивный для MOEX low-vol)
                threshold = float(os.getenv("PYRAMIDING_THRESHOLD", "0.0003"))  # 0.03% (ускорение)
                print(f"DEBUG_PYRAMID pnl={round(pnl_pct,6)} threshold={threshold} avg={avg_price} mkt={market_price}", flush=True)
                # добавляем только если уже есть прибыль
                if pnl_pct > threshold:
                    print(f"PIPE_PYRAMID_ADD pnl={round(pnl_pct,4)}", flush=True)

                    # уменьшаем размер добавки (без увеличения риска)
                    intent["qty"] = round(intent.get("qty", 0.0) * 0.5, 3)

                else:
                    print("PIPE_PYRAMID_WAIT not_ready", flush=True)
                    return
            else:
                print("PIPE_POSITION_BLOCK opposite_direction", flush=True)
                return

        # === REMOVE position exists guard (handled by pyramiding logic) ===
        # if pos and float(getattr(pos, "qty", 0.0)) != 0.0:
        #     print(f"PIPE_POSITION_BLOCK symbol={sym} qty={getattr(pos, 'qty', 0.0)}", flush=True)
        #     return

        # =========================================================
        # === TRADE GATES: COOLDOWN + TRADE LIMIT
        # =========================================================
        trade_gate = getattr(self, "trade_gate_service", None)
        if trade_gate is None:
            trade_gate = TradeGateService(
                base_cooldown_sec=float(os.getenv("TRADE_COOLDOWN_SEC", "45")),
                max_trades_per_hour=int(os.getenv("MAX_TRADES_PER_HOUR", "5")),
                max_trades_per_symbol=int(os.getenv("MAX_TRADES_PER_SYMBOL", "2")),
            )
            self.trade_gate_service = trade_gate

        cooldown_decision = trade_gate.cooldown_allows(
            symbol=sym,
            price=float(price or 0.0),
            atr=float(st.get("atr", 0.0) or 0.0),
        )
        if not cooldown_decision.allowed:
            self._log_dedup(
                f"PIPE_COOLDOWN_BLOCK:{sym}",
                f"PIPE_COOLDOWN_BLOCK symbol={sym} reason={cooldown_decision.reason}",
                heartbeat_sec=60,
            )
            return

        # === LOSS COOLDOWN CHECK ===
        if sym in self._cooldown_until:
            if time.time() < self._cooldown_until[sym]:
                print("PIPE_LOSS_COOLDOWN_BLOCK", flush=True)
                return

        limit_decision = trade_gate.trade_limit_allows(sym)
        if not limit_decision.allowed:
            if "global" in limit_decision.reason:
                print("PIPE_TRADE_LIMIT_BLOCK_GLOBAL", flush=True)
            else:
                print(f"PIPE_TRADE_LIMIT_BLOCK_SYMBOL {sym}", flush=True)
            return

        # Русский комментарий:
        # Лимит сделок здесь только проверяется.
        # Учет trade_limit выполняется только после успешного FILL.
        # =========================================================
        # === PORTFOLIO KILL-SWITCH (cumulative PnL / max drawdown)
        # =========================================================
        kill_ok, kill_reason = self._portfolio_kill_switch_allows()
        if not kill_ok:
            print(f"PIPE_PORTFOLIO_KILL_SWITCH_BLOCK {kill_reason}", flush=True)
            return

        # =========================================================
        # === RISK (PRODUCTION MODE)
        # =========================================================
        try:
            gate_side = self._extract_session_side_gate_side_v1(intent)
            if gate_side in {'BUY', 'SELL'}:
                try:
                    phase2_decision = self.runtime_edge_governance_soft_block_v1.decide(
                        symbol=str(sym),
                        side=str(gate_side),
                    )
                    print(
                        "PIPE_RUNTIME_EDGE_GOVERNANCE_PHASE2_DECISION",
                        f"symbol={phase2_decision.symbol}",
                        f"side={phase2_decision.side}",
                        f"hour_msk={phase2_decision.hour_msk}",
                        f"allowed={phase2_decision.allowed}",
                        f"action={phase2_decision.action}",
                        f"reason={phase2_decision.reason}",
                        f"session_action={phase2_decision.session_action}",
                        f"strict_reason={phase2_decision.strict_reason}",
                        f"decay_state={phase2_decision.decay_state}",
                        flush=True,
                    )

                    self._record_runtime_governance_live_accumulation_v1(
                        sym=sym,
                        gate_side=gate_side,
                        phase2_decision=phase2_decision,
                    )  # runtime_governance_live_accumulation_v1_call
                    if not phase2_decision.allowed:
                        print(
                            "PIPE_RUNTIME_EDGE_GOVERNANCE_PHASE2_SOFT_BLOCK",
                            f"symbol={phase2_decision.symbol}",
                            f"side={phase2_decision.side}",
                            f"reason={phase2_decision.reason}",
                            flush=True,
                        )

                        # Русский комментарий:
                        # В PAPER-режиме разрешаем advisory-only проход для накопления live-статистики.
                        # Governance решение сохраняется, но не останавливает PaperExecution.
                        phase2_advisory_only = (
                            str(os.getenv("EXECUTION_MODE", "paper")).lower() == "paper"
                            and os.getenv("RUNTIME_GOVERNANCE_PHASE2_ADVISORY_ONLY", "0") == "1"
                        )
                        if phase2_advisory_only:
                            print(
                                "PIPE_RUNTIME_EDGE_GOVERNANCE_PHASE2_ADVISORY_CONTINUE",
                                f"symbol={phase2_decision.symbol}",
                                f"side={phase2_decision.side}",
                                f"reason={phase2_decision.reason}",
                                "paper_only=1",
                                flush=True,
                            )
                        else:
                            return
                except Exception as exc:
                    print(
                        "PIPE_RUNTIME_EDGE_GOVERNANCE_PHASE2_FAILED_OPEN",
                        f"symbol={sym}",
                        f"side={gate_side}",
                        f"error={type(exc).__name__}:{exc}",
                        flush=True,
                    )

                if not self._check_session_side_execution_gate_v1(symbol=str(sym), side=gate_side):
                    # Русский комментарий: PAPER-only advisory bypass для накопления статистики BRN6,
                    # без влияния на real execution.
                    br_session_bypass = (
                        str(sym) == os.getenv("BR_SESSION_SIDE_GATE_BYPASS_SYMBOL", "BRN6@RTSX")
                        and str(os.getenv("EXECUTION_MODE", "paper")).lower() == "paper"
                        and os.getenv("ENABLE_BR_SESSION_SIDE_GATE_ADVISORY_V1", "0") == "1"
                    )

                    if br_session_bypass:
                        print(
                            "PIPE_BR_SESSION_SIDE_GATE_ADVISORY_CONTINUE",
                            f"symbol={sym}",
                            f"side={gate_side}",
                            "paper_only=1",
                            flush=True,
                        )
                    else:
                        return

                try:
                    strict_decision = self.edge_gate_strict_mode_v1.evaluate(
                        symbol=str(sym),
                        side=str(gate_side),
                    )
                    print(
                        "PIPE_EDGE_GATE_STRICT_MODE",
                        f"symbol={sym}",
                        f"side={gate_side}",
                        f"allowed={strict_decision.allowed}",
                        f"reason={strict_decision.reason}",
                        f"expectancy={strict_decision.expectancy_points}",
                        f"closed_trades={strict_decision.closed_trades}",
                        f"matched_symbol={strict_decision.matched_symbol}",
                        flush=True,
                    )
                    if not strict_decision.allowed:
                        ng_paper_bypass = (
                            str(sym).startswith("NG")
                            and self.runtime_config.get("EXECUTION_MODE", "paper").lower() == "paper"
                            and strict_decision.reason == "strict_mode_no_match"
                            and os.getenv("ENABLE_NG_PAPER_ACCUMULATION_BYPASS_V1", "0") == "1"
                        )

                        br_paper_bypass = (
                            str(sym) == os.getenv("BR_STRICT_EDGE_BYPASS_SYMBOL", "BRN6@RTSX")
                            and self.runtime_config.get("EXECUTION_MODE", "paper").lower() == "paper"
                            and os.getenv("ENABLE_BR_STRICT_EDGE_ADVISORY_V1", "0") == "1"
                        )

                        if ng_paper_bypass:
                            print("NG_PAPER_ACCUMULATION_BYPASS", f"symbol={sym}", f"side={gate_side}", f"reason={strict_decision.reason}", flush=True)
                        elif br_paper_bypass:
                            print("PIPE_BR_STRICT_EDGE_ADVISORY_CONTINUE", f"symbol={sym}", f"side={gate_side}", f"reason={strict_decision.reason}", "paper_only=1", flush=True)
                        else:
                            return
                except Exception as exc:
                    print(
                        "PIPE_EDGE_GATE_STRICT_MODE_FAILED_OPEN",
                        f"symbol={sym}",
                        f"side={gate_side}",
                        f"error={type(exc).__name__}:{exc}",
                        flush=True,
                    )

            decision = self.risk_router.route(
                RiskRouteInput(
                    symbol=sym,
                    intent=intent,
                    state=st,
                    label="PIPE_RISK",
                )
            )

            # === DEBUG RISK DECISION (CRITICAL VISIBILITY) ===
            try:
                print(f"PIPE_RISK_DECISION raw={decision}", flush=True)
                if hasattr(decision, "__dict__"):
                    print(f"PIPE_RISK_FIELDS {decision.__dict__}", flush=True)
            except Exception:
                pass

            approved = _decision_allowed(decision)

            # soft override for dev/sim
            if os.getenv("RISK_SOFT", "0") == "1":
                print("PIPE_RISK_FORCE_PASS", flush=True)
                approved = True

            if not approved:
                reject_reason = str(getattr(decision, 'reason', 'unknown'))
                print(
                    f"PIPE_RISK_REJECT reason={reject_reason} "
                    f"value={getattr(getattr(self.risk_router, 'last_context', None), 'trade_value', None)} exposure={getattr(getattr(self.risk_router, 'last_context', None), 'total_exposure', None)}",
                    flush=True,
                )
                self._audit_runtime_risk_event_v1(
                    symbol=str(sym),
                    intent=intent,
                    decision=decision,
                    severity="CRITICAL" if reject_reason in {"daily_loss_limit", "kill_switch", "portfolio_kill_switch"} else "WARNING",
                    reason=reject_reason,
                    state=st,
                    regime=regime,
                    price=price,
                )
                return


            print("PIPE_RISK_OK", flush=True)
            if str(sym).startswith("NG"):
                print(
                    "PIPE_NG_EXEC_TRACE_AFTER_RISK_OK",
                    f"symbol={sym}",
                    f"side={gate_side}",
                    flush=True,
                )

            # =========================================================
            # === CENTRALIZED PORTFOLIO RISK GATE
            # =========================================================
            try:
                gate = getattr(self, "portfolio_risk_gate", None)
                if gate is None:
                    gate = PortfolioRiskGate()
                    self.portfolio_risk_gate = gate

                if str(sym).startswith("NG"):
                    print(
                        "PIPE_NG_EXEC_TRACE_BEFORE_PORTFOLIO_GATE",
                        f"symbol={sym}",
                        flush=True,
                    )
                pm_ctx = self.pm.get_context()

                equity = float(getattr(pm_ctx, "portfolio_value", 0.0) or 0.0)
                total_exposure = float(getattr(pm_ctx, "total_exposure", 0.0) or 0.0)
                symbol_exposure = float(
                    getattr(pm_ctx, "current_symbol_exposure", 0.0) or 0.0
                )
                used_margin = float(getattr(pm_ctx, "used_margin", 0.0) or 0.0)
                daily_pnl = float(getattr(pm_ctx, "daily_realized_pnl", 0.0) or 0.0)

                peak = getattr(self, "_equity_peak", None)
                if peak is None:
                    peak = equity
                    self._equity_peak = equity
                if equity > peak:
                    peak = equity
                    self._equity_peak = equity

                if hasattr(gate, "evaluate"):
                    decision = gate.evaluate(
                        equity=equity,
                        total_exposure=total_exposure,
                        symbol_exposure=symbol_exposure,
                        used_margin=used_margin,
                        daily_pnl=daily_pnl,
                        peak_equity=peak,
                        current_equity=equity,
                        max_portfolio_heat=float(os.getenv("MAX_PORTFOLIO_HEAT", "0.30")),
                        max_symbol_heat=float(os.getenv("MAX_SYMBOL_HEAT", "0.10")),
                        max_margin_utilization=float(os.getenv("MAX_MARGIN_UTILIZATION", "0.65")),
                        max_daily_loss_pct=float(os.getenv("MAX_DAILY_LOSS_PCT", "0.02")),
                        max_drawdown_pct=float(os.getenv("MAX_DRAWDOWN_PCT", "0.03")),
                    )
                elif hasattr(gate, "check"):
                    decision = gate.check(symbol=str(sym))
                else:
                    decision = None
                    print("PIPE_PORTFOLIO_RISK_GATE_SKIP_NO_METHOD", flush=True)

                if decision is not None and not getattr(decision, "allowed", True):
                    print(
                        "PIPE_PORTFOLIO_RISK_BLOCK",
                        f"reason={getattr(decision, 'reason', None)}",
                        f"cluster={getattr(decision, 'cluster_name', None)}",
                        f"risk_state={getattr(decision, 'risk_state', None)}",
                        f"heat={getattr(decision, 'portfolio_heat', None)}",
                        f"symbol_heat={getattr(decision, 'symbol_heat', None)}",
                        f"margin={getattr(decision, 'margin_utilization', None)}",
                        f"daily_loss={getattr(decision, 'daily_loss_pct', None)}",
                        f"drawdown={getattr(decision, 'drawdown_pct', None)}",
                        flush=True,
                    )
                    self._kill_switch_active = True
                    return

                if decision is not None:
                    print(
                        "PIPE_PORTFOLIO_RISK_OK",
                        f"reason={getattr(decision, 'reason', None)}",
                        f"cluster={getattr(decision, 'cluster_name', None)}",
                        f"risk_state={getattr(decision, 'risk_state', None)}",
                        f"heat={getattr(decision, 'portfolio_heat', None)}",
                        f"symbol_heat={getattr(decision, 'symbol_heat', None)}",
                        f"margin={getattr(decision, 'margin_utilization', None)}",
                        flush=True,
                    )

            except Exception as e:
                print(f"PIPE_PORTFOLIO_RISK_ERROR {e}", flush=True)

            symbol_for_anti = str(intent.get("symbol") or "")
            side_for_anti = str(intent.get("side") or "")
            anti_ok, anti_reason = self._anti_reentry_allows(symbol_for_anti, side_for_anti)
            if not anti_ok:
                self._anti_reentry_blocked_count = int(getattr(self, "_anti_reentry_blocked_count", 0)) + 1
                print(f"PIPE_ANTI_REENTRY_BLOCK {anti_reason}", flush=True)
                return

            # =========================================================
            # === PORTFOLIO RISK (LEVEL 2: portfolio heat limit)
            # =========================================================
            try:
                pm_ctx = self.pm.get_context()

                total_exposure = float(getattr(pm_ctx, "total_exposure", 0.0) or 0.0)
                equity = float(getattr(pm_ctx, "portfolio_value", 0.0) or 0.0)

                if equity > 0:
                    heat = total_exposure / equity
                else:
                    heat = 0.0

                max_heat = float(os.getenv("MAX_PORTFOLIO_HEAT", "0.3"))  # 30% default

                if heat > max_heat:
                    print(f"PIPE_PORTFOLIO_HEAT_BLOCK heat={round(heat,3)}", flush=True)
                    return

                print(f"PIPE_PORTFOLIO_HEAT_OK heat={round(heat,3)}", flush=True)

            except Exception as e:
                print(f"PIPE_PORTFOLIO_HEAT_ERROR {e}", flush=True)

            # =========================================================
            # === SYMBOL RISK (LEVEL 2: ограничение на инструмент)
            # =========================================================
            try:
                symbol_exposure = float(getattr(pm_ctx, "current_symbol_exposure", 0.0) or 0.0)

                if equity > 0:
                    symbol_heat = symbol_exposure / equity
                else:
                    symbol_heat = 0.0

                max_symbol_heat = float(os.getenv("MAX_SYMBOL_HEAT", "0.1"))  # 10% default

                if symbol_heat > max_symbol_heat:
                    print(f"PIPE_SYMBOL_HEAT_BLOCK heat={round(symbol_heat,3)}", flush=True)
                    return

                print(f"PIPE_SYMBOL_HEAT_OK heat={round(symbol_heat,3)}", flush=True)

            except Exception as e:
                print(f"PIPE_SYMBOL_HEAT_ERROR {e}", flush=True)

            # =========================================================
            # === KILL SWITCH (LEVEL 2: защита капитала)
            # =========================================================
            try:
                pm_ctx = self.pm.get_context()

                equity = float(getattr(pm_ctx, "portfolio_value", 0.0) or 0.0)
                realized = float(getattr(pm_ctx, "daily_realized_pnl", 0.0) or 0.0)

                # === INIT PEAK EQUITY ===
                peak = getattr(self, "_equity_peak", None)
                if peak is None:
                    self._equity_peak = equity
                    peak = equity

                # === UPDATE PEAK ===
                if equity > peak:
                    self._equity_peak = equity
                    peak = equity

                # === DRAWDOWN ===
                dd = (equity - peak) / peak if peak > 0 else 0.0

                max_dd = float(os.getenv("MAX_DRAWDOWN", "-0.03"))  # -3%
                max_daily_loss = float(os.getenv("MAX_DAILY_LOSS", "-0.02"))  # -2%

                # === HARD LOCK (ONCE TRIGGERED) ===
                if getattr(self, "_kill_switch_active", False):
                    print("PIPE_KILL_SWITCH_ACTIVE", flush=True)
                    return

                if dd < max_dd:
                    print(f"PIPE_KILL_SWITCH_DD dd={round(dd, 4)}", flush=True)
                    self._kill_switch_active = True
                    return

                if realized < max_daily_loss * peak:
                    print(f"PIPE_KILL_SWITCH_DAILY pnl={round(realized, 2)}", flush=True)
                    self._kill_switch_active = True
                    return
                if realized < max_daily_loss * peak:
                    print(f"PIPE_KILL_SWITCH_DAILY pnl={round(realized,2)}", flush=True)
                    return

            except Exception as e:
                print(f"PIPE_KILL_SWITCH_ERROR {e}", flush=True)

            # === TEMP FIX: MIN TRADE SIZE FLOOR ===
            try:
                if ctx.trade_value < 10:  # слишком маленькие сделки режем/расширяем
                    print("PIPE_RISK_ADJUST small_trade -> force min size", flush=True)
                    intent["qty"] = max(1.0, float(intent.get("qty", 0)))
            except Exception:
                pass

        except Exception as e:
            print(f"PIPE_RISK_ERROR {e}", flush=True)
            return
        # =========================================================
        # === EXECUTION
        # =========================================================
        # === VALIDATION BEFORE EXECUTION (CRITICAL FIX) ===
        # === CORRELATION FILTER ===
        try:
            current_positions = getattr(self.pm, "positions", {}) or {}

            active_symbols = list(current_positions.keys())
            active_symbols = self._runtime_symbol_reload_if_due(active_symbols)

            def get_cluster(sym):
                base = sym.split("@")[0][:2]
                for k, v in CLUSTERS.items():
                    if base in v:
                        return k
                return None

            new_cluster = get_cluster(intent.get("symbol"))

            for s in active_symbols:
                existing_cluster = get_cluster(s)

                if existing_cluster and existing_cluster == new_cluster:
                    # Русский комментарий: research-only bypass для накопления PAPER-статистики
                    # по энерго-инструментам независимо от уже открытой позиции в кластере.
                    cluster_bypass_symbols = {
                        x.strip()
                        for x in os.getenv(
                            "PAPER_CLUSTER_BLOCK_BYPASS_SYMBOLS",
                            "NGN6@RTSX,BRN6@RTSX",
                        ).split(",")
                        if x.strip()
                    }
                    cluster_bypass_allowed = (
                        str(os.getenv("EXECUTION_MODE", "paper")).lower() == "paper"
                        and os.getenv("ENABLE_PAPER_CLUSTER_BLOCK_BYPASS_V1", "0") == "1"
                        and str(intent.get("symbol") or "") in cluster_bypass_symbols
                    )

                    if cluster_bypass_allowed:
                        print(
                            "PIPE_CLUSTER_BLOCK_ADVISORY_CONTINUE",
                            f"symbol={intent.get('symbol')}",
                            f"cluster={new_cluster}",
                            f"existing_symbol={s}",
                            "paper_only=1",
                            flush=True,
                        )
                        continue

                    print(f"PIPE_CLUSTER_BLOCK {new_cluster}", flush=True)
                    return

        except Exception:
            pass
        if intent.get("price") is None:
            px = st.get("last") or st.get("price") or st.get("bid") or st.get("ask")
            if px is not None:
                intent["price"] = float(px)
                print(f"DEBUG PRICE FIX BEFORE EXEC {intent['price']}", flush=True)
            else:
                print("PIPE_EXEC_BLOCK missing_price", flush=True)
                return
        if intent.get("qty") is None or float(intent.get("qty", 0)) <= 0:
            print("PIPE_EXEC_BLOCK invalid_qty", flush=True)
            return
        if not self._usd_paper_pilot_allows_intent_v1(intent):
            return

        if self._execute_routed_order_if_needed(intent, st):
            return

        if self.execution_mode in ("real_dry_run", "real"):
            real_result = self.execution_dispatcher.execute(intent=intent, market_state=st)
            print(
                f"PIPE_REAL_EXECUTION_RESULT mode={self.execution_mode} symbol={getattr(real_result, 'symbol', None)} "
                f"side={getattr(real_result, 'side', None)} qty={getattr(real_result, 'qty', None)} price={getattr(real_result, 'price', None)} "
                f"status={getattr(real_result, 'status', None)} order_id={getattr(real_result, 'order_id', None)} reason={getattr(real_result, 'reason', None)}",
                flush=True,
            )
            return

        if not self.runtime_config.get_bool("ENABLE_PAPER_FILLS", True):
            self._log_dedup("PIPE_PAPER_FILL_BLOCKED:main_execution", "PIPE_PAPER_FILL_BLOCKED source=main_execution")
            return

        # =========================================================
        self._inject_latest_smart_money_context(intent)
        self._inject_latest_institutional_flow_context(intent)
        self._resolve_execution_symbol_if_enabled(intent, st)

        if not self._institutional_execution_gate_if_enabled(intent):
            return

        if not self._adaptive_regime_filter_if_enabled(intent):
            return

        if not self._entry_confidence_gate_if_enabled(intent, st):
            return

        self._adaptive_position_size_if_enabled(intent, st)

        # === ENTRY GATE COORDINATOR
        # =========================================================
        if isinstance(intent, dict) and intent.get("intent_type") != "EXIT":
            try:
                gate = getattr(self, "entry_gate_coordinator", None)

                if gate is not None:
                    gate_decision = gate.allow_entry(
                        symbol=str(intent.get("symbol") or st.get("symbol") or ""),
                        strategy=str(intent.get("strategy") or (intent.get("features") or {}).get("strategy") or "default"),
                        strategy_side=str(intent.get("side") or ""),
                        expected_side=str(st.get("expected_side") or st.get("trend_side") or intent.get("side") or ""),
                        qty=float(intent.get("qty", 0.0) or 0.0),
                        price=float(intent.get("price") or st.get("last") or st.get("price") or 0.0),
                        atr=float(st.get("atr", 0.0) or 0.0),
                        regime=str(intent.get("regime") or (intent.get("features") or {}).get("regime_label") or "UNKNOWN"),
                    )

                    replay_accumulation_mode = (
                        self.runtime_config.get_bool("SIMULATE_MARKET", False)
                        and os.getenv("REPLAY_ACCUMULATION_MODE", "0") == "1"
                    )

                    if not gate_decision.allowed:
                        if replay_accumulation_mode and gate_decision.gate == "runtime_control":
                            self._log_dedup(
                                f"PIPE_ENTRY_GATE_BYPASS_REPLAY:{intent.get('symbol')}",
                                f"PIPE_ENTRY_GATE_BYPASS_REPLAY symbol={intent.get('symbol')} gate={gate_decision.gate} reason={gate_decision.reason}",
                                heartbeat_sec=60,
                            )
                        else:
                            self._log_dedup(
                                f"PIPE_ENTRY_GATE_BLOCK:{intent.get('symbol')}:{gate_decision.gate}",
                                f"PIPE_ENTRY_GATE_BLOCK symbol={intent.get('symbol')} gate={gate_decision.gate} reason={gate_decision.reason}",
                                heartbeat_sec=60,
                            )

                            # Русский комментарий:
                            # В PAPER-режиме разрешаем advisory-only проход через entry gate
                            # для накопления live-статистики сделок.
                            entry_gate_advisory_only = (
                                str(os.getenv("EXECUTION_MODE", "paper")).lower() == "paper"
                                and os.getenv("ENTRY_GATE_ADVISORY_ONLY", "0") == "1"
                            )
                            if entry_gate_advisory_only:
                                print(
                                    "PIPE_ENTRY_GATE_ADVISORY_CONTINUE",
                                    f"symbol={intent.get('symbol')}",
                                    f"gate={gate_decision.gate}",
                                    f"reason={gate_decision.reason}",
                                    "paper_only=1",
                                    flush=True,
                                )
                            else:
                                return

                    # Русский комментарий:
                    # В advisory-only PAPER режиме не даем entry gate занулить qty,
                    # иначе PaperExecution создает raw_fill qty=0.0 и fill отбрасывается.
                    entry_gate_advisory_only_qty = (
                        str(os.getenv("EXECUTION_MODE", "paper")).lower() == "paper"
                        and os.getenv("ENTRY_GATE_ADVISORY_ONLY", "0") == "1"
                        and not gate_decision.allowed
                        and float(gate_decision.qty or 0.0) <= 0.0
                    )

                    if entry_gate_advisory_only_qty:
                        print(
                            "PIPE_ENTRY_GATE_ADVISORY_KEEP_ORIGINAL_QTY",
                            f"symbol={intent.get('symbol')}",
                            f"gate={gate_decision.gate}",
                            f"reason={gate_decision.reason}",
                            f"original_qty={intent.get('qty')}",
                            f"gate_qty={gate_decision.qty}",
                            "paper_only=1",
                            flush=True,
                        )
                    elif not (
                        replay_accumulation_mode
                        and gate_decision.gate == "runtime_control"
                        and float(gate_decision.qty or 0.0) <= 0.0
                    ):
                        intent["qty"] = gate_decision.qty

                    intent.setdefault("features", {})
                    intent["features"]["entry_gate_reason"] = gate_decision.reason
                    intent["features"]["entry_gate"] = gate_decision.gate
                    intent["features"]["entry_gate_replay_bypass"] = (
                        replay_accumulation_mode
                        and gate_decision.gate == "runtime_control"
                    )

            except Exception as exc:
                print(f"PIPE_ENTRY_GATE_COORDINATOR_ERROR {type(exc).__name__}:{exc}", flush=True)
                return

        raw_fill = self.paper.execute(intent, st)

        # === NORMALIZE FILL (define raw_qty and side ONCE) ===
        raw_qty = float(getattr(raw_fill, "qty", intent.get("qty", 0.0)) or 0.0)

        if raw_qty < 0:
            side = "SELL"
        else:
            side = "BUY"

        exec_price = float(
            getattr(raw_fill, "price", None)
            or st.get("last")
            or st.get("price")
            or 0.0
        )

        print("DEBUG COMMISSION CALL OK", flush=True)

        if hasattr(self.fee_tax, "commission"):
            commission = self.fee_tax.commission(
                symbol=intent.get("symbol"),
                qty=abs(raw_qty),
                price=exec_price
            )
        elif hasattr(self.fee_tax, "calc_commission"):
            commission = self.fee_tax.calc_commission(
                symbol=intent.get("symbol"),
                qty=abs(raw_qty),
                price=exec_price
            )
        else:
            commission = 0.0

        fill = ExecutionFill(
            symbol=intent.get("symbol"),
            side=side,
            qty=abs(raw_qty),
            price=exec_price,
            commission=commission,
            fill_id=getattr(raw_fill, "fill_id", None),
        )

        # Русский комментарий: единый PAPER/REAL helper metadata для analytics lineage.
        FillMetadataFactory.attach(fill, intent=intent, market_state=st, raw_fill=raw_fill)

        # Русский комментарий: NG_SIGNAL_SOURCE_PROPAGATION_V2.
        # Сохраняем исходный intent по fill_id до публикации FILL.
        try:
            if not hasattr(self, "_fill_intent_payload_by_fill_id"):
                self._fill_intent_payload_by_fill_id = {}
            fill_key = str(getattr(fill, "fill_id", None) or "")
            if fill_key:
                self._fill_intent_payload_by_fill_id[fill_key] = dict(intent or {})
        except Exception as exc:
            print(f"PIPE_SIGNAL_SOURCE_CACHE_FAILED symbol={intent.get('symbol')} error={exc}", flush=True)

        # SAFETY: гарантируем корректный fill (также qty > 0)
        if not hasattr(fill, "side") or fill.side is None or fill.qty <= 0:
            LOG.error("FILL BUILD ERROR: invalid fill, intent=%s raw_fill=%s", intent, raw_fill)
            return

        print(
            f"PIPE_EXEC side={intent.get('side')} qty={intent.get('qty')}",
            flush=True,
        )
        print(f"PIPE_TRADE_EXEC symbol={intent.get('symbol')} side={intent.get('side')}", flush=True)

        self.bus.publish({"type": "FILL", "fill": fill})
        self._account_trade_after_fill_v1(intent.get("symbol"))

    def generate(self, state, regime=None):

        if regime is None:
            return None

        replay_accumulation_mode = (
            self.runtime_config.get_bool("SIMULATE_MARKET", False)
            and os.getenv("REPLAY_ACCUMULATION_MODE", "0") == "1"
        )

        # ✔ Правильная логика: используем только regime.tradable
        if not regime.tradable:
            if replay_accumulation_mode:
                print(
                    f"PIPE_SIGNAL_REPLAY_ACCUMULATION_BYPASS reason=regime_filter trend={regime.trend} vol={regime.volatility}",
                    flush=True,
                )
            else:
                print(
                    f"PIPE_SIGNAL_REJECT reason=regime_filter trend={regime.trend} vol={regime.volatility}",
                    flush=True,
                )
                return

        # 🚫 не торгуем низкую волу
        if regime.volatility == "low":
            if replay_accumulation_mode:
                print("PIPE_SIGNAL_REPLAY_ACCUMULATION_BYPASS reason=low_volatility", flush=True)
            else:
                return None

        # ✔ breakout только в тренде
        if regime.trend in ("up", "down"):
            return self._breakout_logic(state)

    def _update_position_lifecycle_on_fill_v1(self, event: dict) -> None:
        """Русский комментарий: синхронизирует position_lifecycle_state.remaining_qty по FILL."""
        try:
            database_url = os.getenv("DATABASE_URL", "")
            if not database_url:
                return

            fill = event.get("fill") if isinstance(event, dict) else event
            if fill is None:
                return

            symbol = str(getattr(fill, "symbol", "") or "")
            side = str(getattr(fill, "side", "") or "").upper()
            qty = float(getattr(fill, "qty", 0.0) or 0.0)

            if not symbol or qty <= 0 or side not in ("BUY", "SELL"):
                return

            delta = qty if side == "BUY" else -qty

            import psycopg
            from psycopg.rows import dict_row
            from psycopg.types.json import Jsonb

            with psycopg.connect(database_url, row_factory=dict_row) as conn:
                with conn.transaction():
                    row = conn.execute(
                        """
                        SELECT id, remaining_qty, raw
                        FROM position_lifecycle_state
                        WHERE symbol = %s
                        ORDER BY updated_at DESC NULLS LAST, created_at DESC
                        LIMIT 1
                        FOR UPDATE
                        """,
                        (symbol,),
                    ).fetchone()

                    if row:
                        old_qty = float(row["remaining_qty"] or 0.0)
                        new_qty = old_qty + delta
                        raw = dict(row["raw"] or {})
                        raw.update({
                            "source": "paper_pipeline_lifecycle_on_fill_v1",
                            "last_fill_side": side,
                            "last_fill_qty": qty,
                            "previous_remaining_qty": old_qty,
                        })

                        conn.execute(
                            """
                            UPDATE position_lifecycle_state
                            SET remaining_qty = %s,
                                initial_qty = COALESCE(initial_qty, %s),
                                raw = %s,
                                updated_at = now()
                            WHERE id = %s
                            """,
                            (new_qty, new_qty, Jsonb(raw), row["id"]),
                        )
                    else:
                        new_qty = delta
                        conn.execute(
                            """
                            INSERT INTO position_lifecycle_state
                                (symbol, strategy, remaining_qty, initial_qty, raw, created_at, updated_at)
                            VALUES
                                (%s, %s, %s, %s, %s, now(), now())
                            """,
                            (
                                symbol,
                                "default",
                                new_qty,
                                new_qty,
                                Jsonb({"source": "paper_pipeline_lifecycle_on_fill_v1"}),
                            ),
                        )

            if symbol.startswith("NG"):
                print(
                    f"PIPE_POSITION_LIFECYCLE_ON_FILL_UPDATED symbol={symbol} "
                    f"side={side} delta={delta} qty={new_qty}",
                    flush=True,
                )

        except Exception as exc:
            print(f"PIPE_POSITION_LIFECYCLE_ON_FILL_FAILED error={exc}", flush=True)


    def _restore_pm_position_from_projection_v1(self, symbol: str) -> bool:
        """Русский комментарий: восстанавливает qty в in-memory PositionManager из position_projection."""
        try:
            symbol = str(symbol or "")
            if not symbol:
                return False

            database_url = os.getenv("DATABASE_URL", "")
            if not database_url:
                return False

            import psycopg
            from psycopg.rows import dict_row

            with psycopg.connect(database_url, row_factory=dict_row) as conn:
                row = conn.execute(
                    """
                    SELECT NULLIF(state->>'qty', '')::double precision AS qty
                    FROM position_projection
                    WHERE symbol = %s
                    """,
                    (symbol,),
                ).fetchone()

            if not row:
                return False

            projection_qty = float(row["qty"] or 0.0)

            if not hasattr(self, "pm") or not hasattr(self.pm, "positions"):
                return False

            # Русский комментарий: positions — defaultdict(Position), поэтому get() не создаёт позицию.
            # Для restore используем индексный доступ, чтобы создать in-memory позицию при отсутствии.
            pos = self.pm.positions[symbol]
            pos.symbol = symbol

            current_qty = float(getattr(pos, "qty", 0.0) or 0.0)

            if abs(current_qty - projection_qty) < 1e-9:
                return False

            setattr(pos, "qty", projection_qty)

            if symbol.startswith("NG"):
                print(
                    f"PIPE_PM_RESTORED_FROM_PROJECTION symbol={symbol} "
                    f"old_qty={current_qty} projection_qty={projection_qty}",
                    flush=True,
                )

            return True

        except Exception as exc:
            print(f"PIPE_PM_RESTORE_FROM_PROJECTION_FAILED symbol={symbol} error={exc}", flush=True)
            return False


    def _update_position_projection_on_fill_v1(self, event: dict) -> None:
        """Русский комментарий: обновляет position_projection по каждому FILL-событию."""
        try:
            database_url = os.getenv("DATABASE_URL", "")
            if not database_url:
                return

            fill = event.get("fill") if isinstance(event, dict) else event
            if fill is None:
                return

            symbol = str(getattr(fill, "symbol", "") or "")
            side = str(getattr(fill, "side", "") or "").upper()
            qty = float(getattr(fill, "qty", 0.0) or 0.0)
            price = float(getattr(fill, "price", 0.0) or 0.0)
            fill_id = str(getattr(fill, "fill_id", "") or "")

            if not symbol or qty <= 0 or side not in ("BUY", "SELL"):
                return

            delta = qty if side == "BUY" else -qty

            import psycopg
            from psycopg.rows import dict_row
            from psycopg.types.json import Jsonb

            with psycopg.connect(database_url, row_factory=dict_row) as conn:
                with conn.transaction():
                    row = conn.execute(
                        """
                        SELECT state
                        FROM position_projection
                        WHERE symbol = %s
                        FOR UPDATE
                        """,
                        (symbol,),
                    ).fetchone()

                    state = dict(row["state"]) if row and isinstance(row.get("state"), dict) else {}
                    old_qty = float(
                        state.get("qty")
                        or state.get("net_qty")
                        or state.get("position_qty")
                        or 0.0
                    )
                    new_qty = old_qty + delta

                    state.update(
                        {
                            "symbol": symbol,
                            "qty": new_qty,
                            "net_qty": new_qty,
                            "last_fill_side": side,
                            "last_fill_qty": qty,
                            "last_fill_price": price,
                            "last_fill_id": fill_id,
                            "source": "paper_pipeline_fill_event_projection_v1",
                        }
                    )
                    state["fills_count_projected"] = int(state.get("fills_count_projected") or 0) + 1

                    conn.execute(
                        """
                        INSERT INTO position_projection (symbol, state, updated_at)
                        VALUES (%s, %s, now())
                        ON CONFLICT (symbol)
                        DO UPDATE SET
                            state = EXCLUDED.state,
                            updated_at = now()
                        """,
                        (symbol, Jsonb(state)),
                    )

            if symbol.startswith("NG"):
                print(
                    f"PIPE_POSITION_PROJECTION_UPDATED symbol={symbol} "
                    f"side={side} delta={delta} qty={new_qty}",
                    flush=True,
                )

        except Exception as exc:
            print(f"PIPE_POSITION_PROJECTION_UPDATE_FAILED error={exc}", flush=True)


    def _on_fill(self, event: dict):
        # Русский комментарий: POSITION_PROJECTION_ON_FILL_V1 — синхронизация projection по FILL.
        self._update_position_projection_on_fill_v1(event)

        # Русский комментарий: POSITION_LIFECYCLE_ON_FILL_V1 — синхронизация lifecycle по FILL.
        self._update_position_lifecycle_on_fill_v1(event)
        """
        Русский коммент: единая точка применения исполнений.
        Идемпотентность по fill_id держит PositionManager (если включена).
        """
        fill = event.get("fill") if isinstance(event, dict) else event
        # === TYPE GUARD: пропускаем не ExecutionFill ===
        if not isinstance(fill, ExecutionFill):
            # RAW PaperFill игнорируем молча (уже обработан на этапе execution)
            return
        if fill is None:
            return

        # === FIX: safe validation (NO MUTATION, NO NORMALIZATION) ===
        try:
            # === SAFE VALIDATION (NO MUTATION) ===
            raw_qty = float(getattr(fill, "qty", 0.0) or 0.0)
            price = float(getattr(fill, "price", 0.0) or 0.0)

            # просто проверяем корректность, НИЧЕГО НЕ МЕНЯЕМ
            if raw_qty == 0.0 or price == 0.0:
                LOG.warning("INVALID FILL (zero qty/price): %s (skipped)", fill)
                return

            if not hasattr(fill, "side") or fill.side not in ("BUY", "SELL"):
                LOG.warning("INVALID FILL SIDE: %s (skipped)", fill)
                return

        except Exception as e:
            LOG.error("FILL NORMALIZATION ERROR (SAFE SKIP): %s fill=%s", e, fill)
            return

        # SAFETY: проверка обязательных полей ПОСЛЕ валидации
        if fill.qty <= 0:
            LOG.warning("INVALID FILL AFTER VALIDATION: %s (skipped)", fill)
            return

        # === APPLY FILL WITH COMMISSION ===
        self.pm.apply_fill(fill)

        # === PnL CALC (REALIZED) ===
        try:
            self._restore_pm_position_from_projection_v1(str(getattr(fill, "symbol", "") or ""))
            pos = self.pm.positions.get(getattr(fill, "symbol", None))
            if pos:
                realized = getattr(pos, "realized_pnl", 0.0)
                tax = self.fee_tax.tax(realized)

                net_pnl = realized - tax

                # списываем налог из cash (если доступно)
                try:
                    if hasattr(self.pm, "cash"):
                        self.pm.cash -= tax
                except Exception:
                    pass

                print(
                    f"PIPE_NET_PNL net={net_pnl}",
                    flush=True,
                )

                print(
                    f"PIPE_TAX realized={realized} tax={tax}",
                    flush=True,
                )
                unrealized = getattr(pos, "unrealized_pnl", 0.0)

                print(
                    f"PIPE_PNL realized={realized} unrealized={unrealized} commission={getattr(fill, 'commission', 0.0)}",
                    flush=True,
                )

                # === EQUITY TRACKING ===
                try:
                    cash = float(getattr(self.pm, "cash", 0.0) or 0.0)
                    unrealized = float(getattr(pos, "unrealized_pnl", 0.0) or 0.0)

                    equity = cash + unrealized

                    # сохраняем историю equity
                    hist = getattr(self, "_equity_curve", None)
                    if hist is None:
                        self._equity_curve = []
                        hist = self._equity_curve

                    hist.append(equity)

                    # === DRAWDOWN ===
                    peak = max(hist)
                    drawdown = (equity - peak) / peak if peak > 0 else 0.0

                    print(
                        f"PIPE_EQUITY equity={round(equity,2)} dd={round(drawdown*100,2)}%",
                        flush=True,
                    )

                except Exception as e:
                    LOG.debug("EQUITY ERROR: %s", e)
        except Exception as e:
            LOG.debug("PNL CALC ERROR: %s", e)

        if str(getattr(fill, "side", "")).upper() == "BUY":
            self.trailing_exit.on_position_opened(
                getattr(fill, "symbol", None),
                float(getattr(fill, "price", 0.0) or 0.0),
            )
        elif str(getattr(fill, "side", "")).upper() == "SELL":
            self.trailing_exit.reset(getattr(fill, "symbol", None))

        # --- DIAG (safe) ---
        try:
            pm_ctx = self.pm.get_context()

            self._restore_pm_position_from_projection_v1(str(getattr(fill, "symbol", "") or ""))
            pos = self.pm.positions.get(getattr(fill, "symbol", None))
            qty_now = float(getattr(pos, "qty", 0.0) or 0.0) if pos is not None else 0.0
            avg_now = float(getattr(pos, "avg_price", 0.0) or 0.0) if pos is not None else 0.0
            cash_now = float(getattr(self.pm, "cash", 0.0) or 0.0)

            sym_exposure = abs(qty_now) * float(getattr(fill, "price", 0.0) or 0.0)

            print(
                f"PIPE_PM_CTX portfolio_value={getattr(pm_ctx, 'portfolio_value', None)} "
                f"total_exposure={getattr(pm_ctx, 'total_exposure', None)} "
                f"sym_exposure={sym_exposure} daily_realized_pnl={getattr(pm_ctx, 'daily_realized_pnl', None)} "
                f"qty={qty_now} avg={avg_now} cash={cash_now}",
                flush=True,
            )
            LOG.info(
                "PM_CTX portfolio_value=%s total_exposure=%s sym_exposure=%s daily_realized_pnl=%s qty=%s avg=%s cash=%s",
                getattr(pm_ctx, "portfolio_value", None),
                getattr(pm_ctx, "total_exposure", None),
                sym_exposure,
                getattr(pm_ctx, "daily_realized_pnl", None),
                qty_now,
                avg_now,
                cash_now,
            )
        except Exception as e:
            LOG.debug("PM_CTX DIAG ERROR: %s", e)

        fill_price = float(getattr(fill, "price", 0.0) or 0.0)
        if fill_price <= 0:
            print(
                f"PIPE_EXEC_REJECT_INVALID_PRICE symbol={getattr(fill, 'symbol', None)} "
                f"side={getattr(fill, 'side', None)} qty={getattr(fill, 'qty', None)} price={fill_price}",
                flush=True,
            )
            return

        print(
            f"PIPE_FILLED paper {getattr(fill, 'symbol', None)} "
            f"side={getattr(fill, 'side', None)} qty={getattr(fill, 'qty', None)} "
            f"price={getattr(fill, 'price', None)} id={getattr(fill, 'fill_id', None)}",
            flush=True,
        )

        # Русский комментарий:
        # Базовый payload должен существовать до любых обращений payload.get(...).
        payload = getattr(fill, "payload", None)
        if not isinstance(payload, dict):
            payload = {}
        payload.setdefault("symbol", getattr(fill, "symbol", None))
        payload.setdefault("side", getattr(fill, "side", None))
        payload.setdefault("qty", getattr(fill, "qty", None))
        payload.setdefault("price", getattr(fill, "price", None))
        payload.setdefault("fill_id", getattr(fill, "fill_id", None))
        self._notify_telegram_event(
            f"✅ FILL {getattr(fill, 'symbol', None)}\n"
            f"side={getattr(fill, 'side', None)} qty={getattr(fill, 'qty', None)}\n"
            f"price={getattr(fill, 'price', None)}\n"
            f"id={getattr(fill, 'fill_id', None)}"
        )
        self._mark_anti_reentry_entry(
            str(getattr(fill, "symbol", None) or payload.get("symbol") or ""),
            str(getattr(fill, "side", None) or payload.get("side") or ""),
        )
        # === TELEGRAM: единый сигнал входа ===
        try:
            trend = self._mkt.get(getattr(fill, "symbol", None), {}).get("regime_trend")
            vol = self._mkt.get(getattr(fill, "symbol", None), {}).get("regime_vol")

            # Русский комментарий: Telegram по сделкам/fill отключён; оставляем только сигналы вход/стоп/тейк.
            # Русский комментарий: Telegram fill/trade уведомление отключено.

        except Exception:
            pass
        LOG.info("FILLED paper %s qty=%s price=%s id=%s",
                 getattr(fill, "symbol", None),
                 getattr(fill, "qty", None),
                 getattr(fill, "price", None),
                 getattr(fill, "fill_id", None))

        # Русский комментарий: единый сервис сохраняет fill/trade и связывает signal_id.
        try:
            service = getattr(self, "fill_persistence_service", None)
            if service is not None:
                # Русский комментарий: протягиваем signal_id из intent в fill/payload до persistence.
                FillMetadataFactory.attach(fill, intent=payload, raw_fill=fill)

                # Русский комментарий: последний защитный слой metadata перед записью fill/trade.
                # Русский комментарий:
                # payload уже инициализирован выше перед первым использованием.
                # Здесь сохраняем его, а не пересоздаем пустой словарь.
                if not isinstance(payload, dict):
                    payload = {}

                fill_symbol = str(getattr(fill, "symbol", None) or payload.get("symbol") or "")
                fill_id = str(getattr(fill, "fill_id", None) or "")

                # Русский комментарий: NG_SIGNAL_SOURCE_PROPAGATION_V2.
                # Восстанавливаем исходный intent по fill_id до fallback signal_id.
                try:
                    cached_intent = getattr(self, "_fill_intent_payload_by_fill_id", {}).pop(fill_id, None)
                    if isinstance(cached_intent, dict):
                        for key, value in cached_intent.items():
                            if value is not None and key not in payload:
                                payload[key] = value

                        source_signal_id = (
                            cached_intent.get("signal_id")
                            or cached_intent.get("source_signal_id")
                            or cached_intent.get("id")
                        )
                        if source_signal_id:
                            payload["signal_id"] = str(source_signal_id)
                            payload["source_signal_id"] = str(source_signal_id)
                            payload["source"] = cached_intent.get("source") or "strategy_signal"

                            if fill_symbol.startswith("NG"):
                                print(
                                    f"PIPE_NG_SIGNAL_SOURCE_RESTORED symbol={fill_symbol} "
                                    f"fill_id={fill_id} signal_id={source_signal_id}",
                                    flush=True,
                                )
                except Exception as exc:
                    print(f"PIPE_SIGNAL_SOURCE_RESTORE_FAILED fill_id={fill_id} error={exc}", flush=True)

                # Русский комментарий: NG_SIGNAL_STRATEGY_NORMALIZATION_V1.
                # Если intent пришёл как UNKNOWN_STRATEGY, восстанавливаем стратегию из features.strategy.
                try:
                    features_for_strategy = payload.get("features") or {}
                    if not isinstance(features_for_strategy, dict):
                        features_for_strategy = {}

                    resolved_strategy = (
                        features_for_strategy.get("strategy")
                        or payload.get("strategy")
                        or self._strategy_name_for_symbol(fill_symbol)
                    )

                    if payload.get("strategy") in (None, "", "UNKNOWN_STRATEGY") and resolved_strategy:
                        payload["strategy"] = str(resolved_strategy)

                    sqs = payload.get("signal_quality_snapshot")
                    if isinstance(sqs, dict) and sqs.get("strategy") in (None, "", "UNKNOWN_STRATEGY"):
                        sqs["strategy"] = payload.get("strategy")

                    sid = str(payload.get("signal_id") or "")
                    if "UNKNOWN_STRATEGY" in sid and payload.get("strategy"):
                        fixed_sid = sid.replace("UNKNOWN_STRATEGY", str(payload["strategy"]))
                        payload["signal_id"] = fixed_sid
                        payload["source_signal_id"] = fixed_sid

                    if fill_symbol.startswith("NG") and payload.get("strategy") != "UNKNOWN_STRATEGY":
                        print(
                            f"PIPE_NG_SIGNAL_STRATEGY_NORMALIZED symbol={fill_symbol} "
                            f"strategy={payload.get('strategy')} signal_id={payload.get('signal_id')}",
                            flush=True,
                        )
                except Exception as exc:
                    print(f"PIPE_SIGNAL_STRATEGY_NORMALIZE_FAILED fill_id={fill_id} error={exc}", flush=True)

                # Русский комментарий: NG_SIGNAL_LINKAGE_V2.
                # Не пишем атрибуты в ExecutionFill напрямую: signal_id берём из payload/metadata,
                # иначе возможен конфликт с реализацией ExecutionFill.
                fill_metadata = getattr(fill, "metadata", None)
                if not isinstance(fill_metadata, dict):
                    fill_metadata = {}

                source_signal_id = (
                    payload.get("signal_id")
                    or payload.get("source_signal_id")
                    or fill_metadata.get("signal_id")
                    or fill_metadata.get("source_signal_id")
                )

                if source_signal_id:
                    payload["signal_id"] = str(source_signal_id)
                    payload["source_signal_id"] = str(source_signal_id)
                    payload.setdefault("source", "strategy_signal")
                else:
                    payload.setdefault("signal_id", f"fill-{fill_id}")
                    payload.setdefault("source", "paper_fill_fallback")

                payload.setdefault("strategy", payload.get("strategy") or self._strategy_name_for_symbol(fill_symbol))
                payload.setdefault("horizon", payload.get("horizon") or "INTRADAY")
                payload.setdefault("timeframe", payload.get("timeframe") or "LIVE")
                payload.setdefault("regime", payload.get("regime") or "UNKNOWN")

                features = payload.get("features") or {}
                if isinstance(features, dict):
                    payload.setdefault("adaptive_position_base_qty", features.get("adaptive_position_base_qty"))
                    payload.setdefault("adaptive_position_final_qty", features.get("adaptive_position_final_qty"))
                    payload.setdefault("adaptive_position_multiplier", features.get("adaptive_position_multiplier"))
                    payload.setdefault("adaptive_position_reason", features.get("adaptive_position_reason"))
                    payload.setdefault("adaptive_regime_action", features.get("adaptive_regime_action"))
                    payload.setdefault("adaptive_regime_multiplier", features.get("adaptive_regime_multiplier"))
                    payload.setdefault("adaptive_regime_reason", features.get("adaptive_regime_reason"))
                    payload.setdefault("institutional_flow_regime_ru", features.get("institutional_flow_regime_ru"))

                # Русский комментарий: добавляем contract identity в fallback payload.
                try:
                    from finam_core.contracts.contract_identity_resolver import ContractIdentityResolver
                    identity = ContractIdentityResolver.resolve(fill_symbol)
                    payload.setdefault("root_symbol", identity.root)
                    payload.setdefault("continuous_symbol", identity.continuous if identity.is_futures else fill_symbol)
                    payload.setdefault("futures_month_code", identity.month_code)
                    payload.setdefault("futures_year_code", identity.year_code)
                    payload.setdefault("venue", identity.venue)
                    payload.setdefault("is_futures", identity.is_futures)
                    payload.setdefault("confidence", payload.get("confidence") or 1.0)
                    payload.setdefault("attribution_version", "strategy_attribution_v1")
                except Exception as exc:
                    print(f"PIPE_CONTRACT_IDENTITY_ENRICH_FAILED symbol={fill_symbol} error={exc}", flush=True)

                # Русский комментарий: metadata replay campaign для связывания fills/trades/closed_trades с campaign.
                if os.getenv("REPLAY_CAMPAIGN_ID"):
                    payload.setdefault("replay_campaign_id", os.getenv("REPLAY_CAMPAIGN_ID"))
                    payload.setdefault("replay_id", os.getenv("REPLAY_ID"))
                    payload.setdefault("replay_symbol", os.getenv("REPLAY_SYMBOL"))
                    payload.setdefault("replay_timeframe", os.getenv("REPLAY_TIMEFRAME"))
                    payload.setdefault("replay_strategy", os.getenv("REPLAY_STRATEGY"))
                    payload.setdefault("dataset_source", "replay_campaign")

                payload = _edge_gate_enrich_payload_for_paper(
                    payload=payload,
                    signal_like=payload,
                )
                persist_result = service.persist_fill(fill, execution_type="paper", payload=payload)
                print(f"PIPE_FILL_PERSISTED result={persist_result} payload={payload}", flush=True)
            else:
                print("PIPE_FILL_PERSISTENCE_SKIP reason=service_not_configured", flush=True)
        except Exception as exc:
            LOG.warning("PIPE_FILL_PERSISTENCE_FAILED error=%s", exc)

        # === TELEGRAM: исполнение ===
        try:
            # Русский комментарий: Telegram по сделкам/fill отключён; оставляем только сигналы вход/стоп/тейк.
            # Русский комментарий: Telegram fill/trade уведомление отключено.
            pass
        except Exception:
            pass

        # exit-on-fill
        if not self._filled_once and os.getenv("EXIT_ON_FILL", "1") == "1":
            self._filled_once = True
            LOG.info("DONE: filled once, exiting")
            if self._done is not None:
                try:
                    self._done.set()
                except Exception:
                    pass

    def _risk_check_br_signal(self, br_signal, qty: float) -> tuple[bool, str]:
        """Русский комментарий: BR PAPER-сигнал проходит RiskEngine, но real orders не создаются."""
        if not hasattr(self, "risk") or self.risk is None:
            return True, "NO_RISK_ENGINE_ATTACHED_PAPER_ONLY"

        try:
            if hasattr(self.risk, "check_order"):
                decision = self.risk.check_order(
                    symbol=br_signal.symbol,
                    side=br_signal.side,
                    qty=qty,
                    price=br_signal.price,
                )
                accepted = bool(getattr(decision, "accepted", decision))
                reason = str(getattr(decision, "reason", "RISK_CHECK_ORDER"))
                return accepted, reason

            if hasattr(self.risk, "evaluate"):
                candidate = {
                    "symbol": br_signal.symbol,
                    "side": br_signal.side,
                    "qty": qty,
                    "price": br_signal.price,
                    "stop": br_signal.stop,
                    "take": br_signal.take,
                    "strategy": br_strategy,
                    "source": "paper_pipeline_closed_bar",
                }
                decision = self.risk.evaluate(candidate)
                accepted = bool(getattr(decision, "accepted", decision))
                reason = str(getattr(decision, "reason", "RISK_EVALUATE"))
                return accepted, reason

            return True, "RISK_ENGINE_NO_COMPATIBLE_METHOD_PAPER_ONLY"

        except Exception as exc:
            return False, f"RISK_EXCEPTION:{type(exc).__name__}:{exc}"

    def _log_br_risk_event(self, br_signal, qty: float, accepted: bool, reason: str) -> None:
        # Русский комментарий: replay и live могут передавать разные формы сигнала,
        # поэтому strategy берём из сигнала с безопасным fallback.
        br_strategy = (
            getattr(br_signal, "strategy", None)
            or getattr(br_signal, "strategy_name", None)
            or "BR_CONSERVATIVE_BREAKOUT"
        )
        """Русский комментарий: логируем результат risk gate без отправки реальных заявок."""
        if not hasattr(self, "pg_logger") or self.pg_logger is None:
            return

        payload = {
            "symbol": br_signal.symbol,
            "side": br_signal.side,
            "qty": qty,
            "price": br_signal.price,
            "stop": br_signal.stop,
            "take": br_signal.take,
            "strategy": br_strategy,
            "accepted": accepted,
            "reason": reason,
            "paper_only": True,
            "execution_mode": self.runtime_config.get("EXECUTION_MODE", "paper"),
        }

        try:
            if hasattr(self.pg_logger, "log_risk_event"):
                self.pg_logger.log_risk_event(
                    symbol=br_signal.symbol,
                    event="BR_PAPER_SIGNAL_RISK_ACCEPTED" if accepted else "BR_PAPER_SIGNAL_RISK_REJECTED",
                    severity="info" if accepted else "warning",
                    payload=payload,
                )
        except Exception:
            pass

    def _log_br_paper_fill(self, br_signal, qty: float, fill, paper_reason: str) -> None:
        # Русский комментарий: strategy нужна для корректной записи replay/paper fill в trades.
        br_symbol = str(getattr(br_signal, "symbol", "") or "")
        br_strategy = "BR_CONSERVATIVE_BREAKOUT"
        """Русский комментарий: PaperExecutionEngine возвращает PaperFill; здесь явно пишем его в trades."""
        if not hasattr(self, "pg_logger") or self.pg_logger is None:
            return
        if not hasattr(self.pg_logger, "log_trade"):
            return

        fill_qty = float(getattr(fill, "qty", qty) or qty)
        fill_price = float(getattr(fill, "price", br_signal.price) or br_signal.price)
        run_id = str(getattr(self, "run_id", "unknown"))
        fill_id_raw = str(getattr(fill, "fill_id", f"paper_br_{int(br_signal.ts.timestamp())}"))
        fill_id = f"{run_id}_{fill_id_raw}"

        try:
            from finam_core.contracts.continuous_contract_resolver import ContinuousContractResolver
            continuous_symbol = ContinuousContractResolver.resolve(br_signal.symbol)
        except Exception:
            continuous_symbol = br_signal.symbol

        from finam_core.analytics.regime_attribution import derive_regime_label

        trade_payload = {
            "symbol": br_signal.symbol,
            "side": br_signal.side,
            "qty": abs(fill_qty),
            "price": fill_price,
            "run_id": run_id,
            "paper_only": True,
            "execution_type": paper_reason,
            "strategy": br_strategy,
            "horizon": "INTRADAY",
            "timeframe": "M5",
            "source": "paper_pipeline_br",
            "regime": derive_regime_label({
                "reason": getattr(br_signal, "reason", None),
                "regime_direction": locals().get("regime_direction"),
                "regime_atr_pct": locals().get("regime_atr_pct"),
                "regime_strength": locals().get("regime_strength"),
            }),
            "regime_label": derive_regime_label({
                "reason": getattr(br_signal, "reason", None),
                "regime_direction": locals().get("regime_direction"),
                "regime_atr_pct": locals().get("regime_atr_pct"),
                "regime_strength": locals().get("regime_strength"),
            }),
            "reason": getattr(br_signal, "reason", None),
            "stop_loss": getattr(br_signal, "stop", None),
            "take_profit": getattr(br_signal, "take", None),
            "entry_price": getattr(br_signal, "price", None),
            "regime_direction": getattr(self.br_breakout, "regime_direction", None),
            "regime_atr_pct": getattr(self.br_breakout, "regime_atr_pct", None),
            "regime_strength": getattr(self.br_breakout, "regime_strength", None),
            "replay_campaign_id": os.getenv("REPLAY_CAMPAIGN_ID"),
            "replay_id": os.getenv("REPLAY_ID"),
            "replay_symbol": os.getenv("REPLAY_SYMBOL"),
            "replay_timeframe": os.getenv("REPLAY_TIMEFRAME"),
            "replay_strategy": os.getenv("REPLAY_STRATEGY"),
            "dataset_source": "replay_campaign" if os.getenv("REPLAY_CAMPAIGN_ID") else "runtime",
        }

        trade_payload = _edge_gate_enrich_payload_for_paper(
            payload=trade_payload,
            signal_like=trade_payload,
        )

        try:
            log_result = self.pg_logger.log_trade(
                symbol=br_signal.symbol,
                side=br_signal.side,
                qty=abs(fill_qty),
                price=fill_price,
                trade_id=fill_id,
                execution_type=paper_reason,
                run_id=run_id,
                strategy=trade_payload.get("strategy"),
                timeframe=trade_payload.get("timeframe"),
                continuous_symbol=trade_payload.get("continuous_symbol"),
                payload=trade_payload,
            )
            db_trade_id = log_result.get("id") if isinstance(log_result, dict) else None
            _save_trade_context_snapshot_for_paper_trade(
                trade_id=fill_id,
                db_trade_id=db_trade_id,
                trade_payload=trade_payload,
            )
        except TypeError:
            trade = {
                "symbol": br_signal.symbol,
                "side": br_signal.side,
                "qty": abs(fill_qty),
                "quantity": abs(fill_qty),
                "price": fill_price,
                "trade_id": fill_id,
                "execution_type": paper_reason,
                "run_id": run_id,
                "ts": br_signal.ts,
                "payload": trade_payload,
                "raw_json": trade_payload,
                "strategy": trade_payload.get("strategy"),
                "horizon": trade_payload.get("horizon"),
                "timeframe": trade_payload.get("timeframe"),
                "reason": trade_payload.get("reason"),
            }
            log_result = self.pg_logger.log_trade(trade)
            db_trade_id = log_result.get("id") if isinstance(log_result, dict) else None
            _save_trade_context_snapshot_for_paper_trade(
                trade_id=fill_id,
                db_trade_id=db_trade_id,
                trade_payload=trade_payload,
            )




    def _inject_latest_institutional_flow_context(self, intent: dict) -> None:
        """Русский комментарий: подтягивает latest institutional flow regime из PostgreSQL."""
        try:
            import os

            if os.getenv("ENABLE_INSTITUTIONAL_FLOW_CONTEXT", "1") != "1":
                return

            symbol = str(intent.get("symbol") or "")
            if not symbol:
                return

            lookup_symbols = [symbol]

            try:
                from finam_core.market.contract_identity import ContractIdentityResolver

                identity = ContractIdentityResolver().resolve(symbol)
                continuous_symbol = getattr(identity, "continuous_symbol", None)
                if continuous_symbol and continuous_symbol not in lookup_symbols:
                    lookup_symbols.append(str(continuous_symbol))
            except Exception:
                pass

            pg = getattr(self, "pg_logger", None)
            if pg is None:
                return

            sql = """
            select regime, bias, confidence
            from institutional_flow_regime_events
            where symbol = any(%s)
            order by ts desc
            limit 1
            """

            with pg._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (lookup_symbols,))
                    row = cur.fetchone()

            if not row:
                return

            regime, bias, confidence = row
            features = intent.setdefault("features", {})
            features["institutional_flow_regime"] = str(regime or "UNKNOWN")
            features["institutional_flow_bias"] = str(bias or "NEUTRAL")
            features["institutional_flow_confidence"] = float(confidence or 0.0)

        except Exception as exc:
            self._log_dedup(
                "PIPE_INSTITUTIONAL_FLOW_CONTEXT_ERROR",
                f"PIPE_INSTITUTIONAL_FLOW_CONTEXT_ERROR {type(exc).__name__}:{exc}",
                heartbeat_sec=300,
            )

    def _inject_latest_smart_money_context(self, intent: dict) -> None:
        """Русский комментарий: подтягивает latest smart_money_score из PostgreSQL."""
        try:
            import os

            if os.getenv("ENABLE_SMART_MONEY_CONTEXT", "1") != "1":
                return

            symbol = str(intent.get("symbol") or "")
            if not symbol:
                return

            lookup_symbols = [symbol]

            try:
                from finam_core.market.contract_identity import ContractIdentityResolver

                identity = ContractIdentityResolver().resolve(symbol)
                continuous_symbol = getattr(identity, "continuous_symbol", None)
                if continuous_symbol and continuous_symbol not in lookup_symbols:
                    lookup_symbols.append(str(continuous_symbol))
            except Exception:
                pass

            pg = getattr(self, "pg_logger", None)
            if pg is None:
                return

            sql = """
            select
                smart_money_score,
                smart_money_label
            from market_opportunity_metrics
            where symbol = %s
            order by calculated_at desc
            limit 1
            """

            with pg._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (symbol,))
                    row = cur.fetchone()

            if not row:
                return

            smart_money_score, smart_money_label = row

            features = intent.setdefault("features", {})

            features["smart_money_score"] = float(smart_money_score or 0.0)
            features["smart_money_label"] = str(
                smart_money_label or "NO_SMART_MONEY_DATA"
            )

        except Exception as exc:
            self._log_dedup(
                "PIPE_SMART_MONEY_CONTEXT_ERROR",
                f"PIPE_SMART_MONEY_CONTEXT_ERROR {type(exc).__name__}:{exc}",
                heartbeat_sec=300,
            )

    def _institutional_execution_gate_if_enabled(self, intent: dict) -> bool:
        """Русский комментарий: событийный institutional gate перед входом в сделку."""
        try:
            import os

            if os.getenv("ENABLE_INSTITUTIONAL_EXECUTION_GATE", "0") != "1":
                return True

            if not isinstance(intent, dict):
                return True

            if intent.get("intent_type") == "EXIT":
                return True

            features = intent.setdefault("features", {})
            symbol = str(intent.get("symbol") or "")
            strategy = str(features.get("strategy") or intent.get("strategy") or self._strategy_name_for_symbol(symbol))

            regime_ru = str(
                features.get("institutional_flow_regime_ru")
                or features.get("institutional_flow_regime")
                or "❔ Нет данных"
            )

            regime_map = {
                "ACCUMULATION": "🟢 Накопление",
                "DISTRIBUTION": "🔴 Распределение",
                "TREND_INITIATION": "🚀 Запуск тренда",
                "BREAKOUT_TRAP": "🪤 Ловушка пробоя",
                "INSTITUTIONAL_PARTICIPATION": "🏦 Активность крупного участника",
                "NORMAL_FLOW": "⚪ Обычная активность",
                "UNKNOWN": "❔ Нет данных",
            }
            regime_ru = regime_map.get(regime_ru, regime_ru)

            if symbol.startswith("BR"):
                instrument_group = "BR"
            elif symbol.startswith("NG"):
                instrument_group = "NG"
            elif symbol.startswith("USDRUB") or "USDRUB" in symbol:
                instrument_group = "USDRUB"
            else:
                instrument_group = "EQUITY"

            from finam_core.risk.market_event_calendar_repository import MarketEventCalendarRepository
            from finam_core.risk.institutional_execution_gate import InstitutionalExecutionGate

            event_repo = getattr(self, "market_event_calendar_repository", None)
            if event_repo is None:
                event_repo = MarketEventCalendarRepository(getattr(self, "pg_logger", None))
                self.market_event_calendar_repository = event_repo

            gate = getattr(self, "institutional_execution_gate", None)
            if gate is None:
                gate = InstitutionalExecutionGate()
                self.institutional_execution_gate = gate

            event_ctx = event_repo.load_context(instrument_group)

            decision = gate.evaluate(
                symbol=symbol,
                strategy=strategy,
                regime_ru=regime_ru,
                liquidity_score=float(features.get("liquidity_score", 0.0) or 0.0),
                churn_status=str(features.get("churn_status") or ""),
                has_cbr_event_today=event_ctx.has_cbr_event_today,
                has_inventory_event_today=event_ctx.has_inventory_event_today,
                minutes_to_event=event_ctx.minutes_to_event,
                is_rollover_window=bool(features.get("is_rollover_window", False)),
            )

            features["institutional_execution_action"] = decision.action
            features["institutional_execution_multiplier"] = decision.multiplier
            features["institutional_execution_reason"] = decision.reason
            features["market_event_type"] = event_ctx.event_type
            features["market_event_name"] = event_ctx.event_name
            features["market_event_severity"] = event_ctx.severity
            features["market_event_minutes_to_event"] = event_ctx.minutes_to_event

            print(
                f"PIPE_INSTITUTIONAL_EXECUTION_GATE "
                f"symbol={symbol} group={instrument_group} "
                f"event={event_ctx.event_type} minutes={event_ctx.minutes_to_event} "
                f"action={decision.action} allowed={decision.allowed} "
                f"multiplier={decision.multiplier} reason={decision.reason}",
                flush=True,
            )

            return bool(decision.allowed)

        except Exception as exc:
            self._log_dedup(
                "PIPE_INSTITUTIONAL_EXECUTION_GATE_ERROR",
                f"PIPE_INSTITUTIONAL_EXECUTION_GATE_ERROR {type(exc).__name__}:{exc}",
                heartbeat_sec=300,
            )
            return True

    def _adaptive_regime_filter_if_enabled(self, intent: dict) -> bool:
        """Русский комментарий: блокирует или снижает риск входа по исторической эффективности режима."""
        try:
            import os

            if os.getenv("ENABLE_ADAPTIVE_REGIME_FILTER", "0") != "1":
                return True

            if not isinstance(intent, dict):
                return True

            if intent.get("intent_type") == "EXIT":
                return True

            features = intent.setdefault("features", {})
            regime = str(
                features.get("institutional_flow_regime_ru")
                or features.get("institutional_flow_regime")
                or "❔ Нет данных"
            )

            # Русский комментарий: если режим пришёл техническим кодом, переводим в операционный русский label.
            regime_map = {
                "ACCUMULATION": "🟢 Накопление",
                "DISTRIBUTION": "🔴 Распределение",
                "TREND_INITIATION": "🚀 Запуск тренда",
                "BREAKOUT_TRAP": "🪤 Ловушка пробоя",
                "INSTITUTIONAL_PARTICIPATION": "🏦 Активность крупного участника",
                "NORMAL_FLOW": "⚪ Обычная активность",
                "UNKNOWN": "❔ Нет данных",
            }
            regime_ru = regime_map.get(regime, regime)

            if regime_ru == "❔ Нет данных":
                symbol = str(intent.get("symbol") or "")
                try:
                    with self.pg_logger._connect() as conn:
                        with conn.cursor() as cur:
                            cur.execute(
                                """
                                select regime
                                from institutional_flow_regime_events
                                where symbol = %s
                                order by ts desc
                                limit 1
                                """,
                                (symbol,),
                            )
                            row = cur.fetchone()

                    if row:
                        regime_ru = regime_map.get(str(row[0]), str(row[0]))
                        features["institutional_flow_regime"] = str(row[0])
                        features["institutional_flow_regime_ru"] = regime_ru
                except Exception:
                    regime_ru = "❔ Нет данных"

            from finam_core.risk.adaptive_regime_repository import AdaptiveRegimeRepository

            repo = getattr(self, "adaptive_regime_repository", None)
            if repo is None:
                repo = AdaptiveRegimeRepository(getattr(self, "pg_logger", None))
                self.adaptive_regime_repository = repo

            decision = repo.evaluate_regime(regime_ru, symbol=str(intent.get('symbol') or ''))

            features["adaptive_regime_action"] = decision.action
            features["adaptive_regime_multiplier"] = decision.multiplier
            features["adaptive_regime_reason"] = decision.reason
            features["institutional_flow_regime_ru"] = regime_ru

            print(
                f"PIPE_ADAPTIVE_REGIME_FILTER "
                f"symbol={intent.get('symbol')} "
                f"regime={regime_ru} "
                f"action={decision.action} "
                f"allowed={decision.allowed} "
                f"multiplier={decision.multiplier} "
                f"reason={decision.reason}",
                flush=True,
            )

            if not decision.allowed:
                return False

            return True

        except Exception as exc:
            self._log_dedup(
                "PIPE_ADAPTIVE_REGIME_FILTER_ERROR",
                f"PIPE_ADAPTIVE_REGIME_FILTER_ERROR {type(exc).__name__}:{exc}",
                heartbeat_sec=300,
            )
            return True

    def _resolve_execution_symbol_if_enabled(self, intent: dict, market_state: dict) -> None:
        """Русский комментарий: подменяет symbol на preferred execution contract перед Risk/Execution."""
        try:
            import os

            if os.getenv("ENABLE_EXECUTION_SYMBOL_RESOLVER", "0") != "1":
                return

            if not isinstance(intent, dict):
                return

            if intent.get("intent_type") == "EXIT":
                return

            symbol = str(intent.get("symbol") or market_state.get("symbol") or "")
            if not symbol:
                return

            from finam_core.execution.execution_symbol_resolver import ExecutionSymbolResolver

            resolver = getattr(self, "execution_symbol_resolver", None)
            if resolver is None:
                resolver = ExecutionSymbolResolver(getattr(self, "pg_logger", None))
                self.execution_symbol_resolver = resolver

            decision = resolver.resolve(symbol)

            if decision.execution_symbol == symbol:
                print(
                    f"PIPE_EXECUTION_SYMBOL_UNCHANGED "
                    f"requested={decision.requested_symbol} "
                    f"execution={decision.execution_symbol} "
                    f"continuous={decision.continuous_symbol} "
                    f"reason={decision.reason}",
                    flush=True,
                )
                return

            features = intent.setdefault("features", {})
            features["requested_symbol"] = decision.requested_symbol
            features["execution_symbol"] = decision.execution_symbol
            features["continuous_symbol"] = decision.continuous_symbol
            features["execution_symbol_reason"] = decision.reason

            intent["requested_symbol"] = decision.requested_symbol
            intent["symbol"] = decision.execution_symbol
            market_state["requested_symbol"] = decision.requested_symbol
            market_state["symbol"] = decision.execution_symbol

            print(
                f"PIPE_EXECUTION_SYMBOL_RESOLVED "
                f"requested={decision.requested_symbol} "
                f"execution={decision.execution_symbol} "
                f"continuous={decision.continuous_symbol} "
                f"reason={decision.reason}",
                flush=True,
            )

        except Exception as exc:
            self._log_dedup(
                "PIPE_EXECUTION_SYMBOL_RESOLVER_ERROR",
                f"PIPE_EXECUTION_SYMBOL_RESOLVER_ERROR {type(exc).__name__}:{exc}",
                heartbeat_sec=300,
            )

    def _adaptive_position_size_if_enabled(self, intent: dict, market_state: dict) -> None:
        """Русский комментарий: адаптивно меняет qty после confidence gate и до RiskStack."""
        try:
            import os

            if os.getenv("ENABLE_ADAPTIVE_POSITION_SIZER", "0") != "1":
                return

            if not isinstance(intent, dict):
                return

            if intent.get("intent_type") == "EXIT":
                return

            from finam_core.risk.adaptive_position_sizer import AdaptivePositionSizer

            features = intent.setdefault("features", {})

            base_qty = float(intent.get("qty") or intent.get("quantity") or 0.0)
            if base_qty <= 0:
                return

            sizer = getattr(self, "adaptive_position_sizer", None)
            if sizer is None:
                sizer = AdaptivePositionSizer(
                    min_multiplier=float(os.getenv("ADAPTIVE_POSITION_MIN_MULTIPLIER", "0.25")),
                    max_multiplier=float(os.getenv("ADAPTIVE_POSITION_MAX_MULTIPLIER", "1.50")),
                )
                self.adaptive_position_sizer = sizer

            decision = sizer.size(
                base_qty=base_qty,
                confidence=float(features.get("entry_confidence", 0.5)),
                institutional_flow_regime=str(features.get("institutional_flow_regime") or "NORMAL_FLOW"),
                institutional_flow_bias=str(features.get("institutional_flow_bias") or "NEUTRAL"),
                smart_money_score=float(features.get("smart_money_score", 0.0)),
                volatility_quality=float(features.get("volatility_quality", 0.5)),
                portfolio_heat=float(market_state.get("portfolio_heat", 0.0) or features.get("portfolio_heat", 0.0) or 0.0),
            )

            regime_multiplier = float(features.get("adaptive_regime_multiplier", 1.0) or 1.0)
            if regime_multiplier < 1.0:
                adjusted_qty = round(decision.final_qty * regime_multiplier, 6)
                features["adaptive_regime_adjusted_qty"] = adjusted_qty
                features["adaptive_regime_original_qty"] = decision.final_qty
                decision = type(decision)(
                    base_qty=decision.base_qty,
                    final_qty=adjusted_qty,
                    multiplier=round(decision.multiplier * regime_multiplier, 6),
                    confidence_multiplier=decision.confidence_multiplier,
                    institutional_multiplier=decision.institutional_multiplier,
                    volatility_multiplier=decision.volatility_multiplier,
                    heat_multiplier=decision.heat_multiplier,
                    reason=decision.reason + f";adaptive_regime_multiplier={regime_multiplier};adaptive_regime_adjusted_qty={adjusted_qty}",
                )

            intent["qty"] = decision.final_qty
            intent["quantity"] = decision.final_qty

            features["adaptive_position_base_qty"] = decision.base_qty
            features["adaptive_position_final_qty"] = decision.final_qty
            features["adaptive_position_multiplier"] = decision.multiplier
            features["adaptive_position_reason"] = decision.reason

            print(
                f"PIPE_ADAPTIVE_POSITION_SIZE symbol={intent.get('symbol')} "
                f"base_qty={decision.base_qty} final_qty={decision.final_qty} "
                f"multiplier={decision.multiplier}",
                flush=True,
            )

        except Exception as exc:
            self._log_dedup(
                "PIPE_ADAPTIVE_POSITION_SIZE_ERROR",
                f"PIPE_ADAPTIVE_POSITION_SIZE_ERROR {type(exc).__name__}:{exc}",
                heartbeat_sec=300,
            )

    def _entry_confidence_gate_if_enabled(self, intent: dict, market_state: dict) -> bool:
        """Русский комментарий: confirmation gate перед Risk/Execution для новых входов."""
        try:
            import os

            if os.getenv("ENABLE_ENTRY_CONFIDENCE_GATE", "0") != "1":
                return True

            if not isinstance(intent, dict):
                return True

            if intent.get("intent_type") == "EXIT":
                return True

            from finam_core.strategy.entry_confidence_gate import EntryConfidenceGate

            gate = getattr(self, "entry_confidence_gate", None)
            if gate is None:
                gate = EntryConfidenceGate(
                    min_confidence=float(os.getenv("ENTRY_CONFIDENCE_MIN", "0.55")),
                )
                self.entry_confidence_gate = gate

            decision = gate.evaluate(intent=intent, market_state=market_state)

            symbol = str(intent.get("symbol") or market_state.get("symbol") or "")

            if not decision.accepted:
                self._log_dedup(
                    f"PIPE_ENTRY_CONFIDENCE_REJECT:{symbol}",
                    f"PIPE_ENTRY_CONFIDENCE_REJECT symbol={symbol} confidence={decision.confidence} reason={decision.reason}",
                    heartbeat_sec=float(os.getenv("ENTRY_CONFIDENCE_LOG_SEC", "60")),
                )
                return False

            print(
                f"PIPE_ENTRY_CONFIDENCE_ACCEPT symbol={symbol} "
                f"confidence={decision.confidence} institutional_confirmed={decision.institutional_confirmed}",
                flush=True,
            )

            intent.setdefault("features", {})["entry_confidence"] = decision.confidence
            intent.setdefault("features", {})["institutional_confirmed"] = decision.institutional_confirmed
            intent.setdefault("features", {})["entry_confidence_reason"] = decision.reason

            return True

        except Exception as exc:
            self._log_dedup(
                "PIPE_ENTRY_CONFIDENCE_ERROR",
                f"PIPE_ENTRY_CONFIDENCE_ERROR {type(exc).__name__}:{exc}",
                heartbeat_sec=300,
            )
            return True

    def _runtime_symbol_reload_if_due(self, current_symbols: list[str]) -> list[str]:
        """Русский комментарий: периодически перечитывает runtime-universe из dynamic_watchlist."""
        try:
            import time
            import os

            enabled = os.getenv("ENABLE_RUNTIME_SYMBOL_RELOAD", "0") == "1"
            if not enabled:
                return current_symbols

            interval_sec = float(os.getenv("RUNTIME_SYMBOL_RELOAD_SEC", "300"))
            now_ts = time.time()
            last_ts = float(getattr(self, "_runtime_symbol_reload_last_ts", 0.0) or 0.0)

            if now_ts - last_ts < interval_sec:
                return current_symbols

            self._runtime_symbol_reload_last_ts = now_ts

            from finam_core.data.runtime_symbol_reload_service import RuntimeSymbolReloadService
            from finam_core.strategy.strategy_factory import StrategyFactory

            svc = getattr(self, "runtime_symbol_reload_service", None)
            if svc is None:
                svc = RuntimeSymbolReloadService(
                    getattr(self, "pg_logger", None),
                    limit=int(os.getenv("RUNTIME_SYMBOL_RELOAD_LIMIT", "10")),
                )
                self.runtime_symbol_reload_service = svc

            decision = svc.decide(current_symbols)

            self._log_dedup(
                "PIPE_RUNTIME_SYMBOL_RELOAD",
                "PIPE_RUNTIME_SYMBOL_RELOAD "
                f"active={','.join(decision.active_symbols)} "
                f"added={','.join(decision.added_symbols)} "
                f"removed={','.join(decision.removed_symbols)}",
                heartbeat_sec=float(os.getenv("RUNTIME_SYMBOL_RELOAD_LOG_SEC", "60")),
            )

            if not hasattr(self, "strategy_by_symbol") or self.strategy_by_symbol is None:
                self.strategy_by_symbol = {}

            for dynamic_symbol in decision.added_symbols:
                if dynamic_symbol not in self.strategy_by_symbol:
                    strategy_name = self._strategy_name_for_symbol(dynamic_symbol)
                    self.strategy_by_symbol[dynamic_symbol] = StrategyFactory.create(
                        dynamic_symbol,
                        strategy_name=strategy_name,
                    )
                    print(
                        f"PIPE_RUNTIME_SYMBOL_STRATEGY_CREATED symbol={dynamic_symbol} strategy={strategy_name}",
                        flush=True,
                    )

            # Русский комментарий: удаляем runtime strategy/state только если по символу нет открытой позиции.
            for stale_symbol in decision.removed_symbols:
                try:
                    position_qty = 0.0
                    try:
                        positions = getattr(getattr(self, "position_manager", None), "positions", {}) or {}
                        position = positions.get(stale_symbol)
                        position_qty = float(getattr(position, "qty", 0.0) or 0.0)
                    except Exception:
                        position_qty = 0.0

                    if abs(position_qty) > 0:
                        print(
                            f"PIPE_RUNTIME_SYMBOL_EVICT_SKIPPED_OPEN_POSITION symbol={stale_symbol} qty={position_qty}",
                            flush=True,
                        )
                        continue

                    if hasattr(self, "strategy_by_symbol") and self.strategy_by_symbol is not None:
                        self.strategy_by_symbol.pop(stale_symbol, None)

                    if hasattr(self, "state") and isinstance(self.state, dict):
                        self.state.pop(stale_symbol, None)

                    if hasattr(self, "_ng_strategy_by_symbol") and self._ng_strategy_by_symbol is not None:
                        self._ng_strategy_by_symbol.pop(stale_symbol, None)

                    print(
                        f"PIPE_RUNTIME_SYMBOL_EVICT symbol={stale_symbol}",
                        flush=True,
                    )

                except Exception as evict_exc:
                    self._log_dedup(
                        f"PIPE_RUNTIME_SYMBOL_EVICT_ERROR:{stale_symbol}",
                        f"PIPE_RUNTIME_SYMBOL_EVICT_ERROR symbol={stale_symbol} error={type(evict_exc).__name__}:{evict_exc}",
                        heartbeat_sec=300,
                    )

            # Русский комментарий: runtime MarketData resubscribe без restart pipeline.
            self._runtime_active_symbols = decision.active_symbols

            try:
                marketdata = getattr(self, "marketdata", None)

                if marketdata is not None and hasattr(marketdata, "ensure_subscribed"):
                    marketdata.ensure_subscribed(decision.active_symbols)

                    self._log_dedup(
                        "PIPE_RUNTIME_MD_RESUBSCRIBE",
                        "PIPE_RUNTIME_MD_RESUBSCRIBE "
                        f"symbols={','.join(decision.active_symbols)}",
                        heartbeat_sec=float(os.getenv("RUNTIME_MD_RESUBSCRIBE_LOG_SEC", "60")),
                    )

            except Exception as md_exc:
                self._log_dedup(
                    "PIPE_RUNTIME_MD_RESUBSCRIBE_ERROR",
                    f"PIPE_RUNTIME_MD_RESUBSCRIBE_ERROR {type(md_exc).__name__}:{md_exc}",
                    heartbeat_sec=300,
                )

            return decision.active_symbols

        except Exception as exc:
            self._log_dedup(
                "PIPE_RUNTIME_SYMBOL_RELOAD_ERROR",
                f"PIPE_RUNTIME_SYMBOL_RELOAD_ERROR {type(exc).__name__}:{exc}",
                heartbeat_sec=300,
            )
            return current_symbols


    def _log_breakout_detected_dedup_v1(self, symbol: str, side: str, level, ttl_sec: float | None = None) -> None:
        """Русский комментарий: подавляет повторный лог одного и того же breakout-кандидата."""
        import os
        import time

        try:
            ttl = float(ttl_sec if ttl_sec is not None else os.getenv("PIPE_BREAKOUT_DEDUP_TTL_SEC", "900"))
        except Exception:
            ttl = 900.0

        try:
            normalized_level = round(float(level), 6)
        except Exception:
            normalized_level = str(level)

        # Русский комментарий:
        # v2: dedup по instrument+side, потому что breakout level может "ползти"
        # на каждом тике и создавать шум без нового торгового смысла.
        key = f"{symbol}:{str(side).upper()}"

        cache = getattr(self, "_breakout_detected_log_cache_v1", None)
        if cache is None:
            cache = {}
            self._breakout_detected_log_cache_v1 = cache

        now_ts = time.time()
        last_ts = float(cache.get(key, 0.0) or 0.0)

        if last_ts and (now_ts - last_ts) < ttl:
            return

        cache[key] = now_ts

        print(
            "PIPE_BREAKOUT_DETECTED",
            str(side).upper(),
            f"symbol={symbol}",
            f"level={level}",
            flush=True,
        )


    def _save_pre_signal_block_audit_v1(
        self,
        *,
        symbol: str,
        block_type: str,
        block_reason: str,
        strategy: str | None = None,
        timeframe: str | None = None,
        price=None,
        atr=None,
        atr_pct=None,
        threshold=None,
        compression_ratio=None,
        regime: str | None = None,
        trend: str | None = None,
        volatility: str | None = None,
        payload: dict | None = None,
    ) -> None:
        """Русский комментарий: сохраняет pre-signal блокировки без влияния на execution."""
        try:
            audit = getattr(self, "runtime_guard_pre_signal_block_audit_v1", None)
            if audit is None:
                from finam_core.analytics.runtime_guard_pre_signal_block_audit_v1 import (
                    RuntimeGuardPreSignalBlockAuditV1,
                )

                audit = RuntimeGuardPreSignalBlockAuditV1()
                audit.migrate()
                setattr(self, "runtime_guard_pre_signal_block_audit_v1", audit)

            audit.save(
                symbol=symbol,
                strategy=strategy,
                timeframe=timeframe,
                block_type=block_type,
                block_reason=block_reason,
                price=price,
                atr=atr,
                atr_pct=atr_pct,
                threshold=threshold,
                compression_ratio=compression_ratio,
                regime=regime,
                trend=trend,
                volatility=volatility,
                payload=payload or {},
            )
        except Exception as exc:
            print(f"RUNTIME_GUARD_PRE_SIGNAL_BLOCK_AUDIT_FAILED error={exc}", flush=True)

    def _strategy_name_for_symbol(self, symbol: str) -> str:
        """Русский комментарий: возвращает имя стратегии с учётом dynamic_watchlist."""
        try:
            from finam_core.strategy.dynamic_strategy_resolver import DynamicStrategyResolver

            resolver = getattr(self, "dynamic_strategy_resolver", None)
            if resolver is None:
                resolver = DynamicStrategyResolver(getattr(self, "pg_logger", None))
                self.dynamic_strategy_resolver = resolver

            return str(resolver.strategy_for_symbol(symbol))

        except Exception as exc:
            self._log_dedup(
                f"PIPE_DYNAMIC_STRATEGY_RESOLVER_ERROR:{symbol}",
                f"PIPE_DYNAMIC_STRATEGY_RESOLVER_ERROR symbol={symbol} error={type(exc).__name__}:{exc}",
                heartbeat_sec=300,
            )

            try:
                from finam_core.strategy.symbol_strategy_map import SYMBOL_STRATEGY_MAP, DEFAULT_STRATEGY
                return str(SYMBOL_STRATEGY_MAP.get(symbol, DEFAULT_STRATEGY))
            except Exception:
                return "default"

    def _runtime_active_universe_allows_paper(self, symbol: str, strategy: str = "default") -> tuple[bool, str]:
        """Русский комментарий: запрещает paper-entry, если инструмент не включён runtime allocator-ом."""
        try:
            import os

            if os.getenv("ENABLE_RUNTIME_ACTIVE_UNIVERSE_GATE", "0") != "1":
                return True, "runtime_active_universe_gate_disabled"

            pg_logger = getattr(self, "pg_logger", None)
            if pg_logger is None:
                return True, "runtime_active_universe_no_pg_logger"

            with pg_logger._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        select strategy, regime, score, priority
                        from runtime_active_universe
                        where symbol = %s
                          and is_enabled = true
                        limit 1
                        """,
                        (symbol,),
                    )
                    row = cur.fetchone()

            if not row:
                return False, f"runtime_active_universe_not_enabled:symbol={symbol}"

            active_strategy, active_regime, active_score, active_priority = row
            return (
                True,
                f"runtime_active_universe_ok:symbol={symbol}:strategy={active_strategy}:regime={active_regime}:score={active_score}:priority={active_priority}",
            )

        except Exception as exc:
            self._log_dedup(
                "PIPE_RUNTIME_ACTIVE_UNIVERSE_GATE_ERROR",
                f"PIPE_RUNTIME_ACTIVE_UNIVERSE_GATE_ERROR {type(exc).__name__}:{exc}",
                heartbeat_sec=300,
            )
            return True, f"runtime_active_universe_error_soft:{type(exc).__name__}:{exc}"


    def _strategy_runtime_control_allows_paper(self, symbol: str, qty: float, strategy: str = "default") -> tuple[bool, float, str]:
        """Русский комментарий: thin wrapper; логика runtime-control вынесена в StrategyRuntimeControlService."""
        service = getattr(self, "strategy_runtime_control_service", None)
        if service is None:
            service = StrategyRuntimeControlService(getattr(self, "pg_logger", None))
            self.strategy_runtime_control_service = service
        return service.allow_paper(symbol=symbol, qty=qty, strategy=strategy)

    def _br_total_open_abs_position(self) -> float:
        """Русский комментарий: сумма абсолютных открытых PAPER-позиций по BR replay/paper."""
        positions = getattr(self, "_br_replay_positions", None) or {}
        return float(sum(abs(float(qty or 0.0)) for qty in positions.values()))

    def _paper_orders_count_for_portfolio_guard(self) -> int:
        """Русский комментарий: глобальное количество paper orders в текущем run."""
        shared = getattr(self, "portfolio_guard_state", None)
        if isinstance(shared, dict):
            return int(shared.get("paper_orders_total", 0) or 0)

        paper = getattr(self, "paper", None)
        return int(getattr(paper, "orders_total", 0) or 0)

    def _portfolio_guard_allows_br(self) -> tuple[bool, str]:
        """Русский комментарий: портфельный gate перед paper execution."""
        guard = getattr(self, "portfolio_guard", None)
        if guard is None:
            guard = PortfolioGuard()
            self.portfolio_guard = guard

        return guard.is_allowed(
            total_open_abs_position=self._br_total_open_abs_position(),
            paper_orders_count=self._paper_orders_count_for_portfolio_guard(),
        )

    def _br_symbol_state(self, symbol: str) -> dict:
        """Русский комментарий: PAPER-состояние PnL по символу для drawdown guard."""
        states = getattr(self, "_br_symbol_pnl_state", None)
        if states is None:
            states = {}
            self._br_symbol_pnl_state = states
        if symbol not in states:
            states[symbol] = {
                "qty": 0.0,
                "avg_price": 0.0,
                "realized_pnl": 0.0,
                "peak_realized_pnl": 0.0,
                "drawdown": 0.0,
            }
        return states[symbol]

    def _br_symbol_drawdown(self, symbol: str) -> float:
        state = self._br_symbol_state(symbol)
        return float(state.get("drawdown", 0.0) or 0.0)


    def _br_symbol_loss_streak(self, symbol: str) -> int:
        state = self._br_symbol_state(symbol)
        return int(state.get("loss_streak", 0) or 0)

    def _br_symbol_pause_left(self, symbol: str) -> int:
        state = self._br_symbol_state(symbol)
        return int(state.get("loss_streak_pause_left", 0) or 0)

    def _decrement_br_symbol_pause(self, symbol: str) -> None:
        state = self._br_symbol_state(symbol)
        pause_left = int(state.get("loss_streak_pause_left", 0) or 0)
        if pause_left > 0:
            state["loss_streak_pause_left"] = pause_left - 1

    def _symbol_loss_streak_allows_br(self, br_signal) -> tuple[bool, str]:
        """Русский комментарий: временно блокируем сигнал после серии убыточных закрытий."""
        guard = getattr(self, "symbol_loss_streak_guard", None)
        if guard is None:
            guard = SymbolLossStreakGuard()
            self.symbol_loss_streak_guard = guard

        symbol = br_signal.symbol
        loss_streak = self._br_symbol_loss_streak(symbol)
        pause_left = self._br_symbol_pause_left(symbol)

        allowed, reason = guard.is_allowed(symbol, loss_streak, pause_left)
        if not allowed:
            self._decrement_br_symbol_pause(symbol)

        return allowed, reason

    def _symbol_drawdown_allows_br(self, br_signal) -> tuple[bool, str]:
        """Русский комментарий: блокируем новый paper-сигнал при превышении просадки по символу."""
        guard = getattr(self, "symbol_drawdown_guard", None)
        if guard is None:
            guard = SymbolDrawdownGuard()
            self.symbol_drawdown_guard = guard
        current_drawdown = self._br_symbol_drawdown(br_signal.symbol)
        return guard.is_allowed(br_signal.symbol, current_drawdown)

    def _update_br_symbol_pnl_after_fill(self, symbol: str, side: str, qty: float, price: float) -> None:
        """Русский комментарий: обновляем realized PnL и drawdown после успешного paper-fill."""
        state = self._br_symbol_state(symbol)
        current_qty = float(state.get("qty", 0.0) or 0.0)
        avg_price = float(state.get("avg_price", 0.0) or 0.0)
        realized = float(state.get("realized_pnl", 0.0) or 0.0)

        signed = abs(float(qty)) if side.upper() == "BUY" else -abs(float(qty))

        if current_qty == 0 or (current_qty > 0 and signed > 0) or (current_qty < 0 and signed < 0):
            new_qty = current_qty + signed
            if new_qty != 0:
                state["avg_price"] = ((abs(current_qty) * avg_price) + (abs(signed) * price)) / abs(new_qty)
            state["qty"] = new_qty
        else:
            closing_qty = min(abs(current_qty), abs(signed))
            if current_qty > 0:
                pnl = (price - avg_price) * closing_qty
            else:
                pnl = (avg_price - price) * closing_qty

            realized += pnl

            if pnl < 0:
                state["loss_streak"] = int(state.get("loss_streak", 0) or 0) + 1
            elif pnl > 0:
                state["loss_streak"] = 0

            guard = getattr(self, "symbol_loss_streak_guard", None)
            if guard is None:
                guard = SymbolLossStreakGuard()
                self.symbol_loss_streak_guard = guard

            loss_limit = int(guard.loss_limit_for(symbol))
            pause_bars = int(guard.pause_bars_for(symbol))

            if loss_limit > 0 and pause_bars > 0 and int(state.get("loss_streak", 0) or 0) >= loss_limit:
                state["loss_streak_pause_left"] = pause_bars
                state["loss_streak"] = 0

            remaining_qty = current_qty + signed

            if remaining_qty == 0:
                state["qty"] = 0.0
                state["avg_price"] = 0.0
            elif (current_qty > 0 and remaining_qty > 0) or (current_qty < 0 and remaining_qty < 0):
                state["qty"] = remaining_qty
            else:
                state["qty"] = remaining_qty
                state["avg_price"] = price

        state["realized_pnl"] = realized
        state["peak_realized_pnl"] = max(float(state.get("peak_realized_pnl", 0.0) or 0.0), realized)
        state["drawdown"] = realized - float(state.get("peak_realized_pnl", 0.0) or 0.0)

    def _current_br_regime(self) -> str:
        """Русский комментарий: текущий режим из M15-состояния BR-стратегии."""
        br = getattr(self, "br_breakout", None)
        if br is None:
            return "unknown"

        direction = int(getattr(br, "regime_direction", 0) or 0)
        atr_pct = float(getattr(br, "regime_atr_pct", 0.0) or 0.0)

        if direction > 0:
            trend = "up"
        elif direction < 0:
            trend = "down"
        else:
            trend = "flat"

        if atr_pct < 0.0005:
            vol = "low_vol"
        elif atr_pct > 0.003:
            vol = "high_vol"
        else:
            vol = "normal_vol"

        return f"{trend}_{vol}"

    def _regime_policy_allows_br(self, br_signal) -> tuple[bool, str]:
        # Русский комментарий: режим только для replay-проверки записи paper trades; в production не включать.
        if os.getenv("REPLAY_DISABLE_BR_REGIME", "0") == "1":
            return True, "REPLAY_BR_REGIME_DISABLED"
        """Русский комментарий: блокируем не бары, а уже сформированный сигнал перед PaperExecution."""
        policy = getattr(self, "regime_policy", None)
        if policy is None:
            policy = RegimePolicy()
            self.regime_policy = policy

        regime = self._current_br_regime()
        allowed, reason = policy.is_allowed(br_signal.symbol, regime)
        return allowed, f"{reason};regime={regime}"

    def _max_abs_position_for_br(self, symbol: str) -> float:
        """Русский комментарий: лимит позиции берём через adapter; при недоступности Финама работает .env fallback."""
        adapter = getattr(self, "finam_limits_adapter", None)
        if adapter is None:
            adapter = FinamLimitsAdapter()
            self.finam_limits_adapter = adapter
        return float(adapter.get_symbol_limit(symbol).max_abs_position)

    def _current_replay_position_for_br(self, symbol: str) -> float:
        """Русский комментарий: текущая PAPER/replay позиция внутри pipeline."""
        positions = getattr(self, "_br_replay_positions", None)
        if positions is None:
            positions = {}
            self._br_replay_positions = positions
        return float(positions.get(symbol, 0.0))

    def _apply_replay_position_for_br(self, symbol: str, side: str, qty: float) -> None:
        """Русский комментарий: обновляем PAPER/replay позицию после успешного paper-fill."""
        positions = getattr(self, "_br_replay_positions", None)
        if positions is None:
            positions = {}
            self._br_replay_positions = positions
        signed = qty if side.upper() == "BUY" else -qty
        positions[symbol] = float(positions.get(symbol, 0.0)) + signed

        # Русский комментарий: синхронизируем глобальное состояние PortfolioGuard между symbol pipelines.
        shared = getattr(self, "portfolio_guard_state", None)
        if isinstance(shared, dict):
            positions = shared.setdefault("positions", {})
            positions[symbol] = float(self._current_replay_position_for_br(symbol))


    def _position_limit_allows_br(self, br_signal, qty: float) -> tuple[bool, str]:
        """Русский комментарий: не разрешаем наращивать позицию сверх лимита; сокращение разрешаем."""
        symbol = br_signal.symbol
        side = br_signal.side.upper()
        current_pos = self._current_replay_position_for_br(symbol)
        limit = self._max_abs_position_for_br(symbol)
        signed = qty if side == "BUY" else -qty
        new_pos = current_pos + signed

        if abs(new_pos) <= limit:
            return True, f"POSITION_LIMIT_OK current={current_pos} new={new_pos} limit={limit}"

        if abs(new_pos) < abs(current_pos):
            return True, f"POSITION_REDUCE_ALLOWED current={current_pos} new={new_pos} limit={limit}"

        return False, f"MAX_POSITION_LIMIT current={current_pos} requested={signed} new={new_pos} limit={limit}"

    def _log_br_event(self, event_type: str, symbol: str, payload: dict) -> None:
        """Русский комментарий: безопасно логирует BR regime/confirmation события."""
        try:
            data = dict(payload or {})
            data["event_type"] = event_type
            data["symbol"] = symbol
            data["source"] = "br_regime_confirmation"

            if (
                hasattr(self, "pg_logger")
                and self.pg_logger is not None
                and hasattr(self.pg_logger, "log_risk_event")
            ):
                self.pg_logger.log_risk_event(
                    symbol=symbol,
                    event=event_type,
                    payload=data,
                )
        except Exception as exc:
            print(
                f"PIPE_BR_EVENT_LOG_ERROR type={event_type} symbol={symbol} error={exc}",
                flush=True,
            )


    def _check_br_confirmation(self, symbol: str, side: str, price: float) -> bool:
        """Русский комментарий: подтверждение слабого BR breakout удержанием уровня."""
        pending = self._br_confirm_pending.get(symbol)
        if not pending:
            return False

        level = float(pending.get("level") or 0.0)
        ticks = int(pending.get("ticks") or 0)
        expected_side = str(pending.get("side") or "")

        if expected_side and expected_side != side:
            self._br_confirm_pending.pop(symbol, None)
            print(
                f"PIPE_BR_CONFIRM_REJECT symbol={symbol} side={side} reason=side_changed",
                flush=True,
            )
            self._log_br_event(
                "BR_CONFIRM_REJECT",
                symbol,
                {"side": side, "reason": "side_changed", "price": price, "level": level, "ticks": ticks},
            )
            return False

        if side == "BUY":
            ok = price >= level
        elif side == "SELL":
            ok = price <= level
        else:
            ok = False

        if not ok:
            self._br_confirm_pending.pop(symbol, None)
            print(
                f"PIPE_BR_CONFIRM_REJECT symbol={symbol} side={side} price={price} level={level}",
                flush=True,
            )
            self._log_br_event(
                "BR_CONFIRM_REJECT",
                symbol,
                {"side": side, "reason": "level_lost", "price": price, "level": level, "ticks": ticks},
            )
            return False

        ticks += 1
        pending["ticks"] = ticks

        required_ticks = int(pending.get("required_ticks") or 3)
        if ticks >= required_ticks:
            self._br_confirm_pending.pop(symbol, None)
            print(
                f"PIPE_BR_CONFIRM_OK symbol={symbol} side={side} ticks={ticks}",
                flush=True,
            )
            self._log_br_event(
                "BR_CONFIRM_OK",
                symbol,
                {"side": side, "price": price, "level": level, "ticks": ticks},
            )
            return True

        print(
            f"PIPE_BR_CONFIRM_WAIT symbol={symbol} side={side} ticks={ticks} level={level} price={price}",
            flush=True,
        )
        self._log_br_event(
            "BR_CONFIRM_WAIT",
            symbol,
            {"side": side, "price": price, "level": level, "ticks": ticks},
        )
        return False


    def _append_br_volume_bar(self, symbol: str, price: float, volume: float | None = None) -> list[dict]:
        """Русский комментарий: хранит компактный BR volume buffer по символу."""
        buffers = getattr(self, "_br_volume_bars_by_symbol", None)
        if buffers is None:
            buffers = {}
            self._br_volume_bars_by_symbol = buffers

        buf = buffers.setdefault(symbol, [])
        buf.append({
            "close": float(price),
            "volume": float(volume or 0.0),
        })

        max_len = int(os.getenv("BR_VOLUME_BUFFER_MAX", "200"))
        if len(buf) > max_len:
            del buf[:-max_len]

        return buf


    def _br_regime_allows_signal(self, br_signal):
        """Русский комментарий: BR regime layer возвращает решение допуска сигнала."""
        features = getattr(br_signal, "features", {}) or {}

        price = float(getattr(br_signal, "price", 0.0) or 0.0)
        atr_pct = float(features.get("atr_pct", 0.0) or 0.0)
        slope_m5 = float(features.get("slope_m5", 0.0) or 0.0)
        slope_m15 = float(features.get("slope_m15", 0.0) or 0.0)
        compression_ratio = float(features.get("compression_ratio", 0.0) or 0.0)

        # Русский комментарий: replay-бар не всегда содержит feature payload.
        # В этом случае используем уже прогретое состояние BR-стратегии,
        # иначе BRRegimeLayer получает atr_pct=0 и ошибочно блокирует сигнал как invalid_atr.
        br_state = getattr(self, "br_breakout", None)
        if br_state is not None:
            if atr_pct <= 0:
                atr_pct = float(getattr(br_state, "regime_atr_pct", 0.0) or 0.0)
                features["atr_pct"] = atr_pct

            if slope_m15 == 0.0:
                direction = int(getattr(br_state, "regime_direction", 0) or 0)
                strength = float(getattr(br_state, "regime_strength", 0.0) or 0.0)
                slope_m15 = strength * direction

            if slope_m5 == 0.0:
                slope_m5 = slope_m15

            if compression_ratio <= 0.0:
                compression_ratio = 1.0
        atr_short = float(features.get("atr_short", 0.0) or 0.0)
        atr_long = float(features.get("atr_long", 0.0) or 0.0)

        vol_layer = getattr(self, "br_volatility_intelligence", None)
        if vol_layer is None:
            from finam_core.strategy.br_regime_layer import BRVolatilityIntelligence
            vol_layer = BRVolatilityIntelligence()
            self.br_volatility_intelligence = vol_layer

        volatility_profile = None
        if price > 0 and atr_short > 0 and atr_long > 0:
            volatility_profile = vol_layer.evaluate(
                atr_short=atr_short,
                atr_long=atr_long,
                price=price,
            )

        layer = getattr(self, "br_regime_layer", None)
        if layer is None:
            from finam_core.strategy.br_regime_layer import BRRegimeLayer
            layer = BRRegimeLayer()
            self.br_regime_layer = layer

        decision = layer.evaluate(
            atr_pct=atr_pct,
            slope_m5=slope_m5,
            slope_m15=slope_m15,
            compression_ratio=compression_ratio,
            signal_side=str(getattr(br_signal, "side", "") or ""),
            price=price,
            atr_short=atr_short,
            atr_long=atr_long,
            volatility_profile=volatility_profile,
        )

        # Русский комментарий: replay-only bypass для проверки записи paper trades в БД; в production не включать.
        if os.getenv("REPLAY_DISABLE_BR_REGIME", "0") == "1":
            from dataclasses import replace

            decision = replace(
                decision,
                allowed=True,
                reason="REPLAY_BR_REGIME_DISABLED",
                size_multiplier=1.0,
            )

        print(
            f"PIPE_BR_REGIME_DECISION symbol={getattr(br_signal, 'symbol', None)} "
            f"side={getattr(br_signal, 'side', None)} allowed={decision.allowed} "
            f"regime={decision.regime} reason={decision.reason} size_mult={decision.size_multiplier} "
            f"confirm_ticks={getattr(decision, 'confirmation_ticks', 3)} "
            f"breakout_k={getattr(decision, 'breakout_k', 1.0)} "
            f"rel_volume={features.get('rel_volume')} "
            f"volume_confirmed={features.get('volume_confirmed')}",
            flush=True,
        )

        self._log_br_event(
            "BR_REGIME_DECISION",
            str(getattr(br_signal, "symbol", "") or ""),
            {
                "side": str(getattr(br_signal, "side", "") or ""),
                "allowed": bool(decision.allowed),
                "regime": decision.regime,
                "reason": decision.reason,
                "size_multiplier": float(decision.size_multiplier),
                "confirmation_required": bool(getattr(decision, "confirmation_required", False)),
                "confirmation_ticks": int(getattr(decision, "confirmation_ticks", 3)),
                "breakout_k": float(getattr(decision, "breakout_k", 1.0)),
                "volatility_regime": getattr(volatility_profile, "volatility_regime", None),
                "volatility_reason": getattr(volatility_profile, "reason", None),
                "rel_volume": float(features.get("rel_volume", 0.0) or 0.0),
                "volume_confirmed": bool(features.get("volume_confirmed", False)),
                "volume_reason": features.get("volume_reason"),
            },
        )
        return decision

    def _runtime_override_gate_allows_paper_signal(self, br_signal, qty: float, strategy: str) -> tuple[bool, float, str]:
        """Русский комментарий: применяет runtime_regime_overrides перед PaperExecution."""
        database_url = os.getenv("DATABASE_URL", "")
        if not database_url:
            return True, float(qty), "runtime_override_no_database_url"

        symbol = str(getattr(br_signal, "symbol", "") or "")
        payload = getattr(br_signal, "payload", None) or getattr(br_signal, "features", None) or {}
        if not isinstance(payload, dict):
            payload = {}

        timeframe = str(
            getattr(br_signal, "timeframe", "")
            or payload.get("timeframe")
            or payload.get("regime")
            or payload.get("market_regime")
            or ""
        ).upper()

        if not timeframe:
            if symbol.startswith("NG"):
                timeframe = "M1"
            elif symbol.startswith("BR"):
                timeframe = "M5"
            else:
                timeframe = "LIVE"

        root_symbol = symbol
        if symbol.startswith("BR"):
            root_symbol = "BR"
        elif symbol.startswith("NG"):
            root_symbol = "NG"
        elif symbol.startswith("USDRUB"):
            root_symbol = "USDRUB"
        elif symbol.startswith("CNY"):
            root_symbol = "CNY"

        # Русский комментарий: для NG M1 используем точное имя стратегии из runtime override layer.
        if symbol.startswith("NG") and timeframe == "M1":
            strategy = "NG_CONSERVATIVE_BREAKOUT_M1"

        try:
            override = RuntimeRegimeOverrideRepository(database_url).get_override(
                strategy=strategy,
                root_symbol=root_symbol,
                regime=timeframe,
            )
            gate = apply_runtime_override_gate(
                requested_quantity=float(qty),
                execution_mode="paper",
                override=override,
            )
        except Exception as exc:
            print(
                "RUNTIME_OVERRIDE_GATE_ERROR "
                f"symbol={symbol} strategy={strategy} regime={timeframe} "
                f"type={type(exc).__name__} error={exc}",
                flush=True,
            )
            return True, float(qty), "runtime_override_error_fail_open"

        if not gate.allowed:
            print(
                "RUNTIME_OVERRIDE_GATE_BLOCK "
                f"symbol={symbol} strategy={strategy} regime={timeframe} "
                f"reason={gate.reason}",
                flush=True,
            )
            return False, 0.0, gate.reason

        if float(gate.adjusted_quantity) != float(qty):
            print(
                "RUNTIME_OVERRIDE_GATE_ADJUST "
                f"symbol={symbol} strategy={strategy} regime={timeframe} "
                f"qty={qty} adjusted_qty={gate.adjusted_quantity} "
                f"risk_multiplier={gate.risk_multiplier} "
                f"profile={gate.stop_take_profile} reason={gate.reason}",
                flush=True,
            )

        return True, float(gate.adjusted_quantity), gate.reason

    def _execute_br_signal_in_paper(self, br_signal, qty: float) -> tuple[bool, str]:
        # Русский комментарий: strategy нужна внутри метода для order payload и replay trade metadata.
        br_symbol = str(getattr(br_signal, "symbol", "") or "")
        br_strategy = self._strategy_name_for_symbol(br_symbol)
        """Русский комментарий: исполняем risk_accepted BR-сигнал только через PAPER-движок, без real orders."""
        if self.runtime_config.get("EXECUTION_MODE", "paper").lower() != "paper":
            return False, "SKIPPED_NOT_PAPER_MODE"

        if not hasattr(self, "paper") or self.paper is None:
            return False, "NO_PAPER_EXECUTION_ENGINE_ATTACHED"

        # br_long_shadow_pipeline_hook_v1_call:
        # Русский комментарий: BR LONG после отрицательной clean-statistics
        # не отправляем в PaperExecution, но в shadow-режиме пишем сигнал в PostgreSQL.
        if not _br_long_shadow_pipeline_hook_v1(
            symbol=br_symbol,
            side=str(getattr(br_signal, "side", "") or ""),
            strategy=br_strategy,
            signal_id=str(getattr(br_signal, "signal_id", "") or "") or None,
            price=getattr(br_signal, "price", None),
            quantity=qty,
        ):
            return False, "BR_LONG_SHADOW_BLOCK"

        # br_short_shadow_pipeline_hook_v1_call:
        # Русский комментарий: BR short пока только shadow. Исполнение не меняем.
        _br_short_shadow_pipeline_hook_v1(
            symbol=br_symbol,
            side=str(getattr(br_signal, "side", "") or ""),
            strategy=br_strategy,
            current_position=self._current_replay_position_for_br(br_symbol),
            signal_id=str(getattr(br_signal, "signal_id", "") or "") or None,
            price=getattr(br_signal, "price", None),
            quantity=qty,
        )

        # Русский комментарий:
        # Runtime-фильтр BR short-only ставим непосредственно в BR execution path.
        # Это надёжнее общего raw_intent gate, потому что здесь уже есть br_signal и br_strategy.
        if (
            os.getenv("BR_SHORT_ONLY_ENABLED", "1") == "1"
            and br_strategy == "BR_CONSERVATIVE_BREAKOUT"
            and str(getattr(br_signal, "side", "")).upper() == "BUY"
        ):
            now_ts = time.time()
            log_every_sec = float(os.getenv("PIPE_BR_SHORT_ONLY_LOG_EVERY_SEC", "120"))

            if (
                now_ts
                - float(getattr(self, "_last_br_short_only_execution_log_ts", 0.0) or 0.0)
            ) >= log_every_sec:
                self._last_br_short_only_execution_log_ts = now_ts
                print(
                    "PIPE_BR_SHORT_ONLY_BLOCK",
                    f"symbol={getattr(br_signal, 'symbol', None)}",
                    f"strategy={br_strategy}",
                    f"side={getattr(br_signal, 'side', None)}",
                    f"price={getattr(br_signal, 'price', None)}",
                    flush=True,
                )

            return False, "BR_SHORT_ONLY_BLOCK_BUY"

        regime_allowed, regime_reason = self._regime_policy_allows_br(br_signal)
        if not regime_allowed:
            return False, regime_reason

        # Русский комментарий: дополнительный regime-фильтр для Brent перед PaperExecution.
        br_regime = self._br_regime_allows_signal(br_signal)

        if getattr(br_regime, "confirmation_required", False):
            symbol = str(getattr(br_signal, "symbol", "") or "")
            side = str(getattr(br_signal, "side", "") or "")
            price = float(getattr(br_signal, "price", 0.0) or 0.0)
            pending = self._br_confirm_pending.get(symbol)

            if pending is None:
                self._br_confirm_pending[symbol] = {
                    "side": side,
                    "level": price,
                    "ticks": 0,
                    "required_ticks": int(getattr(br_regime, "confirmation_ticks", 3)),
                }
                print(
                    f"PIPE_BR_CONFIRM_PENDING symbol={symbol} side={side} level={price}",
                    flush=True,
                )
                self._log_br_event(
                    "BR_CONFIRM_PENDING",
                    symbol,
                    {"side": side, "level": price, "ticks": 0},
                )
                return False, "BR_CONFIRM_PENDING"

            if not self._check_br_confirmation(symbol, side, price):
                return False, "BR_CONFIRM_WAIT"

        if not br_regime.allowed:
            print(
                f"PIPE_BR_REGIME_BLOCK symbol={br_signal.symbol} side={br_signal.side} "
                f"regime={br_regime.regime} reason={br_regime.reason}",
                flush=True,
            )
            return False, f"BR_REGIME_BLOCK:{br_regime.reason}"

        if br_regime.size_multiplier <= 0:
            return False, "BR_REGIME_BLOCK:invalid_size_multiplier"

        qty = float(qty) * float(br_regime.size_multiplier)

        drawdown_allowed, drawdown_reason = self._symbol_drawdown_allows_br(br_signal)
        if not drawdown_allowed:
            return False, drawdown_reason

        loss_streak_allowed, loss_streak_reason = self._symbol_loss_streak_allows_br(br_signal)
        if not loss_streak_allowed:
            return False, loss_streak_reason

        portfolio_allowed, portfolio_reason = self._portfolio_guard_allows_br()
        if not portfolio_allowed:
            return False, portfolio_reason

        allowed, limit_reason = self._position_limit_allows_br(br_signal, qty)
        if not allowed:
            return False, limit_reason

        br_symbol = str(getattr(br_signal, "symbol", "") or "")
        br_strategy = self._strategy_name_for_symbol(br_symbol)
        active_universe_allowed, active_universe_reason = self._runtime_active_universe_allows_paper(
            symbol=br_symbol,
            strategy=br_strategy,
        )
        if not active_universe_allowed:
            print(
                f"PIPE_ENTRY_GATE_BLOCK symbol={br_symbol} gate=runtime_active_universe reason={active_universe_reason}",
                flush=True,
            )
            return False, active_universe_reason
        print(
            f"PIPE_RUNTIME_ACTIVE_UNIVERSE_OK symbol={br_symbol} reason={active_universe_reason}",
            flush=True,
        )

        # Русский комментарий: исторический replay должен проверять стратегию без runtime governance,
        # иначе старое состояние strategy_runtime_control блокирует генерацию paper-сделок для исследования.
        if os.getenv("REPLAY_DISABLE_RUNTIME_CONTROL", "0") == "1":
            runtime_allowed, runtime_qty, runtime_reason = True, qty, "REPLAY_RUNTIME_CONTROL_DISABLED"
        else:
            runtime_allowed, runtime_qty, runtime_reason = self._strategy_runtime_control_allows_paper(
                br_signal.symbol,
                qty,
                strategy=br_strategy,
            )

        replay_accumulation_mode = (
            self.runtime_config.get_bool("SIMULATE_MARKET", False)
            and os.getenv("REPLAY_ACCUMULATION_MODE", "0") == "1"
        )

        if not runtime_allowed:
            if replay_accumulation_mode:
                self._log_dedup(
                    f"PIPE_RUNTIME_CONTROL_BYPASS_REPLAY:{br_signal.symbol}",
                    f"PIPE_RUNTIME_CONTROL_BYPASS_REPLAY symbol={br_signal.symbol} reason={runtime_reason}",
                    heartbeat_sec=300,
                )
            else:
                self._log_dedup(
                    f"PIPE_RUNTIME_CONTROL_BLOCK:{br_signal.symbol}",
                    f"PIPE_RUNTIME_CONTROL_BLOCK symbol={br_signal.symbol} reason={runtime_reason}",
                    heartbeat_sec=300,
                )
                return False, runtime_reason

        qty = runtime_qty

        # Русский комментарий: в replay/smoke режиме runtime override не должен блокировать paper execution,
        # иначе невозможно проверить replay, trade logging и explainability snapshots.
        if (
            os.getenv("REPLAY_DISABLE_RUNTIME_CONTROL", "0") == "1"
            or os.getenv("RUNTIME_OVERRIDE_GATE_ENABLED", "1") == "0"
        ):
            runtime_override_allowed = True
            runtime_override_qty = qty
            runtime_override_reason = "runtime_override_bypassed_for_replay"
        else:
            runtime_override_allowed, runtime_override_qty, runtime_override_reason = self._runtime_override_gate_allows_paper_signal(
                br_signal=br_signal,
                qty=qty,
                strategy=br_strategy,
            )
        if not runtime_override_allowed:
            return False, runtime_override_reason

        qty = runtime_override_qty

        # Русский комментарий: защитный слой Brent против flip-flop входов.
        # Работает только в runtime, чтобы не ломать исторические replay/исследования.
        if os.getenv("REPLAY_DISABLE_RUNTIME_CONTROL", "0") != "1":
            from finam_core.risk.br_signal_stability_guard import BrSignalStabilityGuard

            if not hasattr(self, "br_signal_stability_guard"):
                self.br_signal_stability_guard = BrSignalStabilityGuard(
                    cooldown_minutes=int(os.getenv("BR_SIGNAL_STABILITY_COOLDOWN_MIN", "20"))
                )

            br_features = getattr(br_signal, "features", {}) or {}
            if not isinstance(br_features, dict):
                br_features = {}

            h1_bias = (
                br_features.get("h1_bias")
                or br_features.get("h1_trend")
                or getattr(br_signal, "h1_bias", None)
                or getattr(self.br_breakout, "h1_bias", None)
                or getattr(self.br_breakout, "h1_trend", None)
                or "unknown"
            )

            stability_decision = self.br_signal_stability_guard.decide(
                symbol=str(getattr(br_signal, "symbol", "") or ""),
                side=str(getattr(br_signal, "side", "") or ""),
                signal_ts=getattr(br_signal, "ts", None),
                h1_bias=str(h1_bias or "unknown"),
            )

            if not stability_decision.allowed:
                print(
                    "PIPE_BR_STABILITY_BLOCK",
                    f"symbol={getattr(br_signal, 'symbol', None)}",
                    f"side={getattr(br_signal, 'side', None)}",
                    f"h1_bias={stability_decision.h1_bias}",
                    f"last_side={stability_decision.last_side}",
                    f"cooldown_active={stability_decision.cooldown_active}",
                    f"reason={stability_decision.reason}",
                    flush=True,
                )
                return False, f"BR_STABILITY_BLOCK:{stability_decision.reason}"

            print(
                "PIPE_BR_STABILITY_OK",
                f"symbol={getattr(br_signal, 'symbol', None)}",
                f"side={getattr(br_signal, 'side', None)}",
                f"h1_bias={stability_decision.h1_bias}",
                f"reason={stability_decision.reason}",
                flush=True,
            )

        order = {
            "symbol": br_signal.symbol,
            "side": br_signal.side,
            "qty": qty,
            "price": br_signal.price,
            "stop": br_signal.stop,
            "take": br_signal.take,
            "strategy": br_strategy,
            "source": "paper_pipeline_closed_bar",
            "paper_only": True,
        }

        try:
            fill = None
            paper_reason = "PAPER_ENGINE_NO_COMPATIBLE_METHOD"

            if hasattr(self.paper, "execute"):
                if not self.runtime_config.get_bool("ENABLE_PAPER_FILLS", True):
                    self._log_dedup("PIPE_PAPER_FILL_BLOCKED:br_paper_signal", "PIPE_PAPER_FILL_BLOCKED source=br_paper_signal")
                    return False, "PAPER_FILLS_DISABLED"
                fill = self.paper.execute(
                    order,
                    market_state={
                        "price": br_signal.price,
                        "last": br_signal.price,
                        "timestamp": br_signal.ts.timestamp(),
                    },
                )
                paper_reason = "PAPER_EXECUTE_ORDER_DICT"

            elif hasattr(self.paper, "execute_order"):
                fill = self.paper.execute_order(order)
                paper_reason = "PAPER_EXECUTE_ORDER_DICT"

            elif hasattr(self.paper, "submit_order"):
                fill = self.paper.submit_order(order)
                paper_reason = "PAPER_SUBMIT_ORDER_DICT"

            elif hasattr(self.paper, "fill_market_order"):
                fill = self.paper.fill_market_order(
                    symbol=br_signal.symbol,
                    side=br_signal.side,
                    qty=qty,
                    price=br_signal.price,
                )
                paper_reason = "PAPER_FILL_MARKET_ORDER"

            if fill is not None:
                self._log_br_paper_fill(
                    br_signal=br_signal,
                    qty=qty,
                    fill=fill,
                    paper_reason=paper_reason,
                )
                self._apply_replay_position_for_br(br_signal.symbol, br_signal.side, qty)

                # Русский комментарий: глобальный счётчик исполненных paper orders для PortfolioGuard.
                shared = getattr(self, "portfolio_guard_state", None)
                if isinstance(shared, dict):
                    shared["paper_orders_total"] = int(shared.get("paper_orders_total", 0) or 0) + 1
                self._update_br_symbol_pnl_after_fill(
                    symbol=br_signal.symbol,
                    side=br_signal.side,
                    qty=qty,
                    price=float(getattr(fill, "price", 0.0) or 0.0),
                )
                return True, paper_reason

            if hasattr(self.pg_logger, "log_trade"):
                # Русский комментарий: fallback должен передавать объект trade, потому что storage.log_trade ожидает один аргумент.
                class _PaperTrade:
                    pass

                trade = _PaperTrade()
                trade.symbol = br_signal.symbol
                trade.side = br_signal.side
                trade.quantity = qty
                trade.qty = qty
                trade.price = br_signal.price
                trade.commission = 0.0
                trade.fill_id = f"paper_br_{int(br_signal.ts.timestamp())}"
                trade.origin = "paper_pipeline_fallback"
                trade.trade_source = "paper"

                self.pg_logger.log_trade(trade)
                return True, "PAPER_TRADE_LOG_FALLBACK"

            return False, "PAPER_ENGINE_NO_COMPATIBLE_METHOD"

        except Exception as exc:
            print(f"PIPE_BR_PAPER_EXEC_ERROR type={type(exc).__name__} error={exc}", flush=True)
            return False, f"PAPER_EXCEPTION:{type(exc).__name__}:{exc}"



    def _usd_paper_pilot_profile_v1(self, *, side: str, hour_msk: int) -> tuple[int, float | None]:
        """
        Русский комментарий:
        Возвращает профиль USD_CONTINUOUS + side + hour_msk для PAPER-пилота USD.
        Используется только как фильтр перед PaperExecution.
        """
        import os
        import time

        cache_ttl = float(os.getenv("USD_PAPER_PILOT_PROFILE_CACHE_TTL_SEC", "300"))
        cache = getattr(self, "_usd_paper_pilot_profile_cache_v1", None)
        if cache is None:
            cache = {}
            self._usd_paper_pilot_profile_cache_v1 = cache

        key = (str(side).upper(), int(hour_msk))
        now = time.time()
        cached = cache.get(key)
        if cached and now - float(cached.get("ts", 0.0)) <= cache_ttl:
            return int(cached.get("profile_trades") or 0), cached.get("profile_expectancy")

        sql = """
        with bars as (
            select
                symbol,
                ts,
                close,
                high,
                low,
                extract(hour from ts + interval '3 hours')::int as hour_msk,
                max(high) over (
                    partition by symbol order by ts rows between %(lookback)s preceding and 1 preceding
                ) as prev_high,
                min(low) over (
                    partition by symbol order by ts rows between %(lookback)s preceding and 1 preceding
                ) as prev_low,
                lead(close, %(horizon)s) over (
                    partition by symbol order by ts
                ) as future_close
            from market_bars
            where timeframe = %(timeframe)s
              and symbol = 'USDRUBF@RTSX'
        ),
        signals as (
            select
                hour_msk,
                close as entry_close,
                future_close,
                case
                    when prev_high is not null and close > prev_high then 'BUY'
                    when prev_low is not null and close < prev_low then 'SELL'
                    else null
                end as side
            from bars
        ),
        outcomes as (
            select
                side,
                hour_msk,
                case
                    when side = 'BUY' then future_close - entry_close
                    when side = 'SELL' then entry_close - future_close
                    else null
                end as pnl_points
            from signals
            where side is not null
              and future_close is not null
        )
        select
            count(*)::int as profile_trades,
            avg(pnl_points)::float as profile_expectancy
        from outcomes
        where side = %(side)s
          and hour_msk = %(hour_msk)s;
        """

        try:
            import psycopg
            from psycopg.rows import dict_row
            from finam_core.analytics.statistics_repository import build_psycopg_url

            params = {
                "side": str(side).upper(),
                "hour_msk": int(hour_msk),
                "timeframe": os.getenv("USD_PAPER_PILOT_PROFILE_TIMEFRAME", "M5"),
                "lookback": int(os.getenv("USD_PAPER_PILOT_LOOKBACK", "20")),
                "horizon": int(os.getenv("USD_PAPER_PILOT_HORIZON", "24")),
            }

            with psycopg.connect(build_psycopg_url(), row_factory=dict_row) as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, params)
                    row = dict(cur.fetchone() or {})

            profile_trades = int(row.get("profile_trades") or 0)
            profile_expectancy = row.get("profile_expectancy")

            cache[key] = {
                "ts": now,
                "profile_trades": profile_trades,
                "profile_expectancy": profile_expectancy,
            }

            return profile_trades, profile_expectancy

        except Exception as exc:
            print(
                "USD_PAPER_GOVERNANCE_PROFILE_ERROR",
                f"side={side}",
                f"hour_msk={hour_msk}",
                f"error={type(exc).__name__}:{exc}",
                flush=True,
            )
            return 0, None

    def _usd_paper_pilot_allows_intent_v1(self, intent: dict) -> bool:
        """
        Русский комментарий:
        PAPER-only gate для USD BUY pilot.
        Если gate выключен, поведение пайплайна не меняется.
        """
        import os

        if os.getenv("ENABLE_USD_PAPER_PILOT_GATE_V1", "0") != "1":
            return True

        symbol = str(intent.get("symbol") or "")
        if symbol != "USDRUBF@RTSX":
            return True

        side = str(intent.get("side") or intent.get("direction") or intent.get("action") or "").upper()

        try:
            ts = intent.get("ts")
            if hasattr(ts, "hour"):
                hour_msk = int((ts.hour + 3) % 24)
            else:
                from datetime import datetime
                hour_msk = int((datetime.utcnow().hour + 3) % 24)
        except Exception:
            hour_msk = -1

        profile_trades, profile_expectancy = self._usd_paper_pilot_profile_v1(
            side=side,
            hour_msk=hour_msk,
        )

        try:
            from finam_core.governance.usd_continuous_profile_gate_v1 import UsdContinuousProfileGateV1

            gate = UsdContinuousProfileGateV1(
                min_profile_trades=int(os.getenv("USD_PAPER_PILOT_MIN_PROFILE_TRADES", "20")),
                min_expectancy=float(os.getenv("USD_PAPER_PILOT_MIN_EXPECTANCY", "0.0")),
            )
            decision = gate.decide(
                symbol=symbol,
                side=side,
                hour_msk=hour_msk,
                profile_trades=profile_trades,
                profile_expectancy=profile_expectancy,
            )
        except Exception as exc:
            print(
                "USD_PAPER_GOVERNANCE_GATE_ERROR",
                f"symbol={symbol}",
                f"side={side}",
                f"hour_msk={hour_msk}",
                f"error={type(exc).__name__}:{exc}",
                flush=True,
            )
            return False

        label = "USD_PAPER_GOVERNANCE_ALLOWED" if decision.allowed else "USD_PAPER_GOVERNANCE_BLOCKED"
        print(
            label,
            f"symbol={decision.symbol}",
            f"side={decision.side}",
            f"hour_msk={decision.hour_msk}",
            "profile=USD_CONTINUOUS_SIDE_HOUR",
            f"profile_trades={decision.profile_trades}",
            f"profile_expectancy={decision.profile_expectancy}",
            f"reason={decision.reason}",
            "paper_only=1",
            flush=True,
        )

        return bool(decision.allowed)


    def _ng_paper_pilot_profile_v1(self, *, side: str, hour_msk: int) -> tuple[int, float | None]:
        """
        Русский комментарий:
        Возвращает профиль NG_CONTINUOUS + side + hour_msk для PAPER-пилота NG.
        Используется только как фильтр перед PaperExecution, не влияет на real execution.
        """
        import os
        import time

        cache_ttl = float(os.getenv("NG_PAPER_PILOT_PROFILE_CACHE_TTL_SEC", "300"))
        cache = getattr(self, "_ng_paper_pilot_profile_cache_v1", None)
        if cache is None:
            cache = {}
            self._ng_paper_pilot_profile_cache_v1 = cache

        key = (str(side).upper(), int(hour_msk))
        now = time.time()
        cached = cache.get(key)
        if cached and now - float(cached.get("ts", 0.0)) <= cache_ttl:
            return int(cached.get("profile_trades") or 0), cached.get("profile_expectancy")

        sql = """
        with bars as (
            select
                symbol,
                ts,
                close,
                high,
                low,
                extract(hour from ts + interval '3 hours')::int as hour_msk,
                max(high) over (
                    partition by symbol
                    order by ts
                    rows between %(lookback)s preceding and 1 preceding
                ) as prev_high,
                min(low) over (
                    partition by symbol
                    order by ts
                    rows between %(lookback)s preceding and 1 preceding
                ) as prev_low,
                lead(close, %(horizon)s) over (
                    partition by symbol
                    order by ts
                ) as future_close
            from market_bars
            where timeframe = %(timeframe)s
              and symbol like 'NG%%@RTSX'
        ),
        signals as (
            select
                symbol,
                ts,
                hour_msk,
                close as entry_close,
                future_close,
                case
                    when prev_high is not null and close > prev_high then 'BUY'
                    when prev_low is not null and close < prev_low then 'SELL'
                    else null
                end as side
            from bars
        ),
        outcomes as (
            select
                side,
                hour_msk,
                case
                    when side = 'BUY' then future_close - entry_close
                    when side = 'SELL' then entry_close - future_close
                    else null
                end as pnl_points
            from signals
            where side is not null
              and future_close is not null
        )
        select
            count(*)::int as profile_trades,
            avg(pnl_points)::float as profile_expectancy
        from outcomes
        where side = %(side)s
          and hour_msk = %(hour_msk)s;
        """

        try:
            import psycopg
            from psycopg.rows import dict_row
            from finam_core.analytics.statistics_repository import build_psycopg_url

            params = {
                "side": str(side).upper(),
                "hour_msk": int(hour_msk),
                "timeframe": os.getenv("NG_PAPER_PILOT_PROFILE_TIMEFRAME", "M5"),
                "lookback": int(os.getenv("NG_PAPER_PILOT_LOOKBACK", "20")),
                "horizon": int(os.getenv("NG_PAPER_PILOT_HORIZON", "24")),
            }

            with psycopg.connect(build_psycopg_url(), row_factory=dict_row) as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, params)
                    row = dict(cur.fetchone() or {})

            profile_trades = int(row.get("profile_trades") or 0)
            profile_expectancy = row.get("profile_expectancy")

            cache[key] = {
                "ts": now,
                "profile_trades": profile_trades,
                "profile_expectancy": profile_expectancy,
            }

            return profile_trades, profile_expectancy

        except Exception as exc:
            print(
                "NG_PAPER_GOVERNANCE_PROFILE_ERROR",
                f"side={side}",
                f"hour_msk={hour_msk}",
                f"error={type(exc).__name__}:{exc}",
                flush=True,
            )
            return 0, None

    def _ng_paper_pilot_allows_signal_v1(self, ng_signal) -> bool:
        """
        Русский комментарий:
        PAPER-only gate для NG BUY pilot.
        Если gate выключен, поведение пайплайна не меняется.
        """
        import os

        if os.getenv("ENABLE_NG_PAPER_PILOT_GATE_V1", "0") != "1":
            return True

        symbol = str(getattr(ng_signal, "symbol", ""))
        side = str(getattr(ng_signal, "side", "")).upper()

        try:
            ts = getattr(ng_signal, "ts", None)
            hour_msk = int((ts.hour + 3) % 24) if ts is not None else -1
        except Exception:
            hour_msk = -1

        profile_trades, profile_expectancy = self._ng_paper_pilot_profile_v1(
            side=side,
            hour_msk=hour_msk,
        )

        try:
            from finam_core.governance.ng_continuous_profile_gate_v1 import NgContinuousProfileGateV1

            gate = NgContinuousProfileGateV1(
                min_profile_trades=int(os.getenv("NG_PAPER_PILOT_MIN_PROFILE_TRADES", "20")),
                min_expectancy=float(os.getenv("NG_PAPER_PILOT_MIN_EXPECTANCY", "0.0")),
            )
            decision = gate.decide(
                symbol=symbol,
                side=side,
                hour_msk=hour_msk,
                profile_trades=profile_trades,
                profile_expectancy=profile_expectancy,
            )
        except Exception as exc:
            print(
                "NG_PAPER_GOVERNANCE_GATE_ERROR",
                f"symbol={symbol}",
                f"side={side}",
                f"hour_msk={hour_msk}",
                f"error={type(exc).__name__}:{exc}",
                flush=True,
            )
            return False

        label = "NG_PAPER_GOVERNANCE_ALLOWED" if decision.allowed else "NG_PAPER_GOVERNANCE_BLOCKED"
        print(
            label,
            f"symbol={decision.symbol}",
            f"side={decision.side}",
            f"hour_msk={decision.hour_msk}",
            f"profile=NG_CONTINUOUS_SIDE_HOUR",
            f"profile_trades={decision.profile_trades}",
            f"profile_expectancy={decision.profile_expectancy}",
            f"reason={decision.reason}",
            "paper_only=1",
            flush=True,
        )

        return bool(decision.allowed)


    def _process_ng_m1_closed_bar_for_paper_signal(self, bar) -> None:
        """Русский комментарий: обработка закрытых M1 баров NG для live paper runtime."""
        if not (self.ng_m1_breakout_enabled and self.ng_m1_breakout is not None):
            return

        if bar.symbol != self.ng_m1_breakout_symbol:
            return

        timeframe = str(bar.timeframe).upper()
        if timeframe != "M1":
            return

        ng_signal = self.ng_m1_breakout.on_signal_bar(
            ts=bar.ts,
            open_=float(bar.open),
            high=float(bar.high),
            low=float(bar.low),
            close=float(bar.close_price),
            volume=float(bar.volume or 0.0),
        )

        if ng_signal is None:
            return

        if not self._ng_paper_pilot_allows_signal_v1(ng_signal):
            return

        qty = float(os.getenv("NG_M1_BREAKOUT_QTY", "1"))

        # Русский комментарий: обычная NG-стратегия допускается к RiskEngine только через Selection Layer.
        ng_payload = getattr(ng_signal, "payload", None) or getattr(ng_signal, "features", None) or {}
        if isinstance(ng_payload, dict):
            ng_regime = str(ng_payload.get("regime") or ng_payload.get("market_regime") or "unknown")
        else:
            ng_regime = str(getattr(ng_signal, "regime", "unknown") or "unknown")

        if not _selection_gate_allowed(
            self,
            strategy="NG_CONSERVATIVE_BREAKOUT",
            symbol=str(getattr(ng_signal, "symbol", "")),
            regime=ng_regime,
        ):
            self._log_br_risk_event(
                br_signal=ng_signal,
                qty=qty,
                accepted=False,
                reason="selection_gate_rejected",
            )
            return

        risk_accepted, risk_reason = self._risk_check_br_signal(ng_signal, qty)
        signal_status = "risk_accepted" if risk_accepted else "risk_rejected"

        self._log_br_risk_event(
            br_signal=ng_signal,
            qty=qty,
            accepted=risk_accepted,
            reason=risk_reason,
        )

        if not risk_accepted:
            return

        paper_executed, paper_reason = self._execute_br_signal_in_paper(
            br_signal=ng_signal,
            qty=qty,
        )

        payload = {
            "price": ng_signal.price,
            "stop": ng_signal.stop,
            "take": ng_signal.take,
            "reason": ng_signal.reason,
            "ts": ng_signal.ts.isoformat(),
            "execution_mode": self.runtime_config.get("EXECUTION_MODE", "paper"),
            "paper_only": True,
            "source": "paper_pipeline_ng_m1_closed_bar",
            "risk_accepted": risk_accepted,
            "risk_reason": risk_reason,
            "paper_executed": paper_executed,
            "paper_reason": paper_reason,
            "run_id": getattr(self, "run_id", "unknown"),
        }

        try:
            self.pg_logger.log_signal(
                symbol=ng_signal.symbol,
                strategy=self._strategy_name_for_symbol(ng_signal.symbol),
                side=ng_signal.side,
                qty=qty,
                status=signal_status,
                payload=payload,
            )
        except Exception as exc:
            print(
                f"PIPE_NG_M1_SIGNAL_LOG_ERROR type={type(exc).__name__} error={exc}",
                flush=True,
            )

    def _process_br_closed_bar_for_paper_signal(self, bar) -> None:
        # Русский комментарий: единое имя BR-стратегии для live/replay логов, risk events и paper fills.
        br_strategy = "BR_CONSERVATIVE_BREAKOUT"
        """Русский комментарий: единая обработка закрытых M5/M15 баров BR для live и historical replay."""
        if not (self.br_breakout_enabled and self.br_breakout is not None):
            return
        if bar.symbol != self.br_breakout_symbol:
            return

        timeframe = str(bar.timeframe).upper()

        if timeframe == "M15":
            self.br_breakout.on_regime_bar(
                ts=bar.ts,
                open_=float(bar.open),
                high=float(bar.high),
                low=float(bar.low),
                close=float(bar.close_price),
                volume=float(bar.volume or 0.0),
            )
            return

        if timeframe != "M5":
            return

        br_signal = self.br_breakout.on_signal_bar(
            ts=bar.ts,
            open_=float(bar.open),
            high=float(bar.high),
            low=float(bar.low),
            close=float(bar.close_price),
            volume=float(bar.volume or 0.0),
        )

        if br_signal is None:
            return

        current_params = getattr(self.br_breakout, "current_params", None)
        qty = float(os.getenv("BR_BREAKOUT_QTY", "1"))
        risk_accepted, risk_reason = self._risk_check_br_signal(br_signal, qty)
        signal_status = "risk_accepted" if risk_accepted else "risk_rejected"

        payload = {
            "price": br_signal.price,
            "stop": br_signal.stop,
            "take": br_signal.take,
            "reason": br_signal.reason,
            "ts": br_signal.ts.isoformat(),
            "execution_mode": self.runtime_config.get("EXECUTION_MODE", "paper"),
            "paper_only": True,
            "source": "paper_pipeline_closed_bar",
            "risk_accepted": risk_accepted,
            "risk_reason": risk_reason,
            "online_mode": getattr(current_params, "mode", None),
            "online_allow_trade": getattr(current_params, "allow_trade", None),
            "online_reason": getattr(current_params, "reason", None),
            "selected_window": getattr(current_params, "breakout_window", None),
            "selected_stop_atr": getattr(current_params, "stop_atr", None),
            "selected_take_atr": getattr(current_params, "take_atr", None),
            "regime_direction": getattr(self.br_breakout, "regime_direction", None),
            "regime_atr_pct": getattr(self.br_breakout, "regime_atr_pct", None),
            "regime_strength": getattr(self.br_breakout, "regime_strength", None),
            "regime_rsi": getattr(self.br_breakout, "regime_rsi", None),
            "regime_rsi_state": getattr(self.br_breakout, "regime_rsi_state", None),
            "rsi_filter_passed": getattr(self.br_breakout, "rsi_filter_passed", None),
            "rsi_filter_reason": getattr(self.br_breakout, "rsi_filter_reason", None),
        }


        self._log_br_risk_event(br_signal=br_signal, qty=qty, accepted=risk_accepted, reason=risk_reason)

        if not risk_accepted:
            return

        paper_executed, paper_reason = self._execute_br_signal_in_paper(br_signal=br_signal, qty=qty)
        payload["paper_executed"] = paper_executed
        payload["paper_reason"] = paper_reason
        payload["symbol_drawdown"] = self._br_symbol_drawdown(br_signal.symbol)
        payload["loss_streak"] = self._br_symbol_loss_streak(br_signal.symbol)
        payload["loss_streak_pause_left"] = self._br_symbol_pause_left(br_signal.symbol)
        payload["portfolio_open_abs_position"] = self._br_total_open_abs_position()
        payload["portfolio_paper_orders_count"] = self._paper_orders_count_for_portfolio_guard()
        payload["run_id"] = getattr(self, "run_id", "unknown")
        payload = _edge_gate_enrich_payload_for_paper(
            payload=payload,
            signal_like=br_signal,
        )

        # Русский комментарий: разделяем причины отказа execution-gate для replay-аналитики.
        if not paper_executed:
            reason_text = str(paper_reason or "")
            if reason_text.startswith("MAX_POSITION_LIMIT"):
                self._br_position_limit_rejected = int(getattr(self, "_br_position_limit_rejected", 0)) + 1
            elif "REGIME_" in reason_text:
                self._br_regime_policy_rejected = int(getattr(self, "_br_regime_policy_rejected", 0)) + 1
            elif reason_text.startswith("SYMBOL_DRAWDOWN_LIMIT"):
                self._br_symbol_drawdown_rejected = int(getattr(self, "_br_symbol_drawdown_rejected", 0)) + 1
            elif reason_text.startswith("LOSS_STREAK_PAUSE_ACTIVE"):
                self._br_loss_streak_rejected = int(getattr(self, "_br_loss_streak_rejected", 0)) + 1
            elif reason_text.startswith("PORTFOLIO_"):
                self._br_portfolio_guard_rejected = int(getattr(self, "_br_portfolio_guard_rejected", 0)) + 1
            else:
                self._br_other_execution_rejected = int(getattr(self, "_br_other_execution_rejected", 0)) + 1

        self.pg_logger.log_signal(
            symbol=br_signal.symbol,
            strategy=br_strategy,
            side=br_signal.side,
            qty=qty,
            status=signal_status,
            payload=payload,
        )

        try:
            # Русский комментарий: Telegram trade/fill уведомление отключено.
            pass
        except Exception:
            pass
    def _breakout_level_bucket_for_symbol(self, symbol: str) -> float:
        """Русский комментарий: шаг округления breakout-уровня для дедупликации близких цен."""
        import os
        safe_key = str(symbol).replace("@", "_").replace(".", "_").replace("-", "_").upper()
        raw = os.getenv(
            f"BREAKOUT_LEVEL_BUCKET_{safe_key}",
            os.getenv("BREAKOUT_LEVEL_BUCKET_DEFAULT", "0"),
        )
        return float(raw or 0.0)


    def _build_runtime_governance_explainability_payload_v2(self, phase2_decision) -> dict:
        """Русский комментарий: формирует русскоязычное объяснение решения Runtime Governance."""
        try:
            action = str(getattr(phase2_decision, "action", "") or "").upper()
            allowed = bool(getattr(phase2_decision, "allowed", False))
            reason = str(getattr(phase2_decision, "reason", "") or "")
            session_action = str(getattr(phase2_decision, "session_action", "") or "")
            strict_reason = str(getattr(phase2_decision, "strict_reason", "") or "")
            decay_state = str(getattr(phase2_decision, "decay_state", "") or "")

            expectancy = getattr(phase2_decision, "expectancy_points", None)
            closed_trades = getattr(phase2_decision, "closed_trades", None)

            решение = "РАЗРЕШЕНО" if allowed else "ЗАБЛОКИРОВАНО"

            основание = "прочее_основание"
            if allowed or action == "ALLOW":
                if expectancy is not None and float(expectancy) > 0:
                    основание = "положительное_матожидание"
                else:
                    основание = "разрешено_по_правилам_governance"
            elif reason == "session_side_gate_block":
                if expectancy is not None and float(expectancy) < 0:
                    основание = "отрицательное_матожидание"
                else:
                    основание = "сессионная_блокировка"
            elif reason == "strict_gate_block":
                if strict_reason == "strict_mode_no_match":
                    основание = "недостаточно_подтвержденного_преимущества"
                else:
                    основание = "строгий_фильтр_governance"

            try:
                closed_trades_int = int(closed_trades or 0)
            except Exception:
                closed_trades_int = 0

            if closed_trades_int >= 100:
                статус_выборки = "устойчивая_выборка"
            elif closed_trades_int >= 30:
                статус_выборки = "достаточная_выборка"
            elif closed_trades_int >= 10:
                статус_выборки = "ранняя_выборка"
            elif closed_trades_int > 0:
                статус_выборки = "малая_выборка"
            else:
                статус_выборки = "нет_выборки"

            if closed_trades_int >= 100:
                уровень_уверенности = "высокая"
            elif closed_trades_int >= 30:
                уровень_уверенности = "средняя"
            elif closed_trades_int >= 10:
                уровень_уверенности = "низкая"
            else:
                уровень_уверенности = "очень_низкая"

            try:
                expectancy_float = float(expectancy) if expectancy is not None else None
            except Exception:
                expectancy_float = None

            if expectancy_float is None:
                сила_преимущества = "не_оценено"
            elif expectancy_float < 0:
                сила_преимущества = "отрицательное"
            elif expectancy_float >= 0.10:
                сила_преимущества = "сильное"
            elif expectancy_float >= 0.03:
                сила_преимущества = "умеренное"
            elif expectancy_float > 0:
                сила_преимущества = "слабое"
            else:
                сила_преимущества = "нейтральное"

            if основание == "положительное_матожидание":
                причина_понятно = "Исторически это окно показывает положительный результат."
            elif основание == "отрицательное_матожидание":
                причина_понятно = "Исторически это окно показывает отрицательный результат."
            elif основание == "недостаточно_подтвержденного_преимущества":
                причина_понятно = "Недостаточно статистики для подтверждения преимущества."
            elif основание == "сессионная_блокировка":
                причина_понятно = "Сессионный фильтр запрещает вход в этом окне."
            elif основание == "строгий_фильтр_governance":
                причина_понятно = "Строгий фильтр Governance не подтвердил качество сигнала."
            else:
                причина_понятно = "Решение принято по правилам Runtime Governance."

            вердикт = "ВХОД РАЗРЕШЕН" if allowed else "ВХОД ЗАПРЕЩЕН"

            if reason == "session_side_gate_block":
                источник_решения = "Сессионная статистика по направлению сделки"
            elif reason == "strict_gate_block":
                источник_решения = "Строгий фильтр Runtime Governance"
            elif allowed or action == "ALLOW":
                источник_решения = "Runtime Governance: подтвержденное преимущество"
            else:
                источник_решения = "Runtime Governance"

            предполагаемый_результат = expectancy_float

            if allowed:
                человеческое_объяснение = (
                    f"{вердикт}. {причина_понятно} "
                    f"Основание: {closed_trades_int} закрытых сделок, "
                    f"матожидание {expectancy_float if expectancy_float is not None else 'не рассчитано'} пункта. "
                    f"Уровень доверия: {уровень_уверенности}."
                )
            elif expectancy_float is not None and expectancy_float < 0:
                человеческое_объяснение = (
                    f"{вердикт}. {причина_понятно} "
                    f"Без блокировки ожидаемый результат составлял бы около {expectancy_float:.6f} пункта. "
                    f"Governance заблокировал вход, чтобы не брать статистически отрицательное окно. "
                    f"Основание: {closed_trades_int} закрытых сделок. "
                    f"Уровень доверия: {уровень_уверенности}."
                )
            else:
                человеческое_объяснение = (
                    f"{вердикт}. {причина_понятно} "
                    f"Подтвержденного положительного преимущества пока нет. "
                    f"Уровень доверия: {уровень_уверенности}."
                )

            return {
                "версия_объяснения": "runtime_governance_explainability_payload_v2",
                "вердикт": вердикт,
                "решение": решение,
                "основание_решения": основание,
                "причина": причина_понятно,
                "человеческое_объяснение": человеческое_объяснение,
                "уровень_доверия": уровень_уверенности,
                "уровень_уверенности": уровень_уверенности,
                "сила_преимущества": сила_преимущества,
                "источник_решения": источник_решения,
                "предполагаемый_результат_без_блокировки": предполагаемый_результат,
                "статус_выборки": статус_выборки,
                "описание": человеческое_объяснение,
                "доказательства": {
                    "закрытых_сделок": closed_trades,
                    "матожидание_пункты": expectancy,
                    "статус_выборки": статус_выборки,
                    "уровень_доверия": уровень_уверенности,
                    "сила_преимущества": сила_преимущества,
                },
                "технические_поля": {
                    "reason": reason,
                    "session_action": session_action,
                    "strict_reason": strict_reason,
                    "decay_state": decay_state,
                },
            }
        except Exception as exc:
            return {
                "версия_объяснения": "runtime_governance_explainability_payload_v2",
                "решение": "НЕ_ОПРЕДЕЛЕНО",
                "основание_решения": "ошибка_формирования_объяснения",
                "статус_выборки": "не_определено",
                "описание": f"Ошибка формирования объяснения Runtime Governance: {type(exc).__name__}:{exc}",
            }


    def _record_runtime_governance_live_accumulation_v1(
        self,
        *,
        sym,
        gate_side,
        phase2_decision,
    ) -> None:
        """
        Русский комментарий:
        Безопасная запись фактического Phase2 governance-решения.
        Ошибка записи в PostgreSQL не должна ломать торговый поток.
        """
        try:
            self.runtime_governance_live_accumulator_v1.append(
                RuntimeGovernanceLiveDecisionV1(
                    symbol=str(sym),
                    side=str(gate_side),
                    hour_msk=int(getattr(phase2_decision, "hour_msk", -1)),
                    allowed=bool(getattr(phase2_decision, "allowed", False)),
                    action=str(getattr(phase2_decision, "action", "UNKNOWN")),
                    reason=str(getattr(phase2_decision, "reason", "UNKNOWN")),
                    session_action=getattr(phase2_decision, "session_action", None),
                    strict_reason=getattr(phase2_decision, "strict_reason", None),
                    decay_state=getattr(phase2_decision, "decay_state", None),
                    expectancy_points=getattr(phase2_decision, "expectancy_points", None),
                    closed_trades=getattr(phase2_decision, "closed_trades", None),
                    raw_json={
                        "source": "paper_pipeline_phase2_runtime",
                        "pipeline": "paper_pipeline",
                        "hook": "runtime_governance_live_accumulation_v1",
                        "explainability": self._build_runtime_governance_explainability_payload_v2(phase2_decision),
                    },
                )
            )
        except Exception as exc:
            print(
                "PIPE_RUNTIME_EDGE_GOVERNANCE_LIVE_ACCUMULATION_FAILED_OPEN",
                f"symbol={sym}",
                f"side={gate_side}",
                f"error={exc}",
                flush=True,
            )

    def _extract_session_side_gate_side_v1(self, intent) -> str:
        """
        Русский комментарий:
        Унифицированное извлечение стороны сделки из dict/dataclass intent.
        """
        try:
            if isinstance(intent, dict):
                for key in ("side", "direction", "action"):
                    value = intent.get(key)
                    if value:
                        return str(value).upper().strip()

            for key in ("side", "direction", "action"):
                value = getattr(intent, key, None)
                if value:
                    return str(value).upper().strip()
        except Exception:
            pass

        return ""


    def _check_session_side_execution_gate_v1(
        self,
        *,
        symbol: str,
        side: str,
    ) -> bool:
        """
        Русский комментарий:
        Мягкий runtime-фильтр по side/session/hour edge.
        Блокирует только явные BLOCK-окна. UNKNOWN/INSUFFICIENT пока fail-open.
        """
        try:
            gate = getattr(self, "_session_side_execution_gate_v1", None)
            if gate is None:
                gate = SessionSideExecutionGateV1()
                self._session_side_execution_gate_v1 = gate

            decision = gate.decide(symbol=str(symbol), side=str(side))

            print(
                "PIPE_SESSION_SIDE_GATE_DECISION",
                f"symbol={decision.symbol}",
                f"side={decision.side}",
                f"hour_msk={decision.hour_msk}",
                f"session={decision.session_name}",
                f"action={decision.action}",
                f"allowed={decision.allowed}",
                f"reason={decision.reason}",
                f"matched_symbol={decision.matched_symbol}",
                f"expectancy={decision.expectancy_points}",
                f"closed_trades={decision.closed_trades}",
                flush=True,
            )

            try:
                audit = getattr(self, "_session_side_gate_runtime_audit_v1", None)
                if audit is None:
                    audit = SessionSideGateRuntimeAuditV1()
                    self._session_side_gate_runtime_audit_v1 = audit

                audit.save(
                    decision=decision,
                    source="paper_pipeline",
                    raw={
                        "hook": "session_side_gate_runtime_audit_v1",
                        "gate_version": "session_side_execution_gate_v1",
                    },
                )

                print(
                    "PIPE_SESSION_SIDE_GATE_AUDIT_OK",
                    f"symbol={decision.symbol}",
                    f"side={decision.side}",
                    f"action={decision.action}",
                    flush=True,
                )

            except Exception as audit_exc:
                print(
                    "PIPE_SESSION_SIDE_GATE_AUDIT_FAILED",
                    f"symbol={decision.symbol}",
                    f"side={decision.side}",
                    f"error={type(audit_exc).__name__}:{audit_exc}",
                    flush=True,
                )

            if not decision.allowed:
                print(
                    "PIPE_SESSION_SIDE_GATE_BLOCK",
                    f"symbol={decision.symbol}",
                    f"side={decision.side}",
                    f"hour_msk={decision.hour_msk}",
                    f"reason={decision.reason}",
                    flush=True,
                )
                return False

            return True

        except Exception as exc:
            print(
                "PIPE_SESSION_SIDE_GATE_FAILED_OPEN",
                f"symbol={symbol}",
                f"side={side}",
                f"error={type(exc).__name__}:{exc}",
                flush=True,
            )
            return True



    def _audit_runtime_risk_event_v1(
        self,
        *,
        symbol: str,
        intent,
        decision,
        severity: str,
        reason: str,
        state=None,
        regime=None,
        price=None,
    ) -> None:
        """
        Русский комментарий:
        Side-effect only audit/notification hook для runtime risk decisions.
        Не меняет approved/rejected result и не влияет на execution flow.
        """
        try:
            bridge = getattr(self, "_risk_notification_bridge_v1", None)
            if bridge is None:
                bridge = RiskNotificationBridgeV1()
                self._risk_notification_bridge_v1 = bridge

            strategy_name = "UNKNOWN"
            try:
                strategy_name = str(self._strategy_name_for_symbol(str(symbol)))
            except Exception:
                strategy_name = str(getattr(intent, "strategy", None) or "UNKNOWN")

            timeframe = "M5"
            try:
                timeframe = str(getattr(self, "timeframe", None) or getattr(intent, "timeframe", None) or "M5")
            except Exception:
                timeframe = "M5"

            value = None
            exposure = None
            try:
                ctx = getattr(self.risk_router, "last_context", None)
                value = getattr(ctx, "trade_value", None)
                exposure = getattr(ctx, "total_exposure", None)
            except Exception:
                pass

            bridge.dispatch_risk_event(
                RiskNotificationInputV1(
                    symbol=str(symbol),
                    strategy=str(strategy_name),
                    timeframe=str(timeframe),
                    decision=str(getattr(decision, "decision", None) or "REJECT"),
                    reason=str(reason or getattr(decision, "reason", None) or "runtime_risk_event"),
                    severity=str(severity),
                    value=float(value) if value is not None else None,
                    exposure=float(exposure) if exposure is not None else None,
                    risk_limit=None,
                    raw={
                        "source": "paper_pipeline",
                        "hook": "wire_runtime_risk_events_to_audit_v1",
                        "decision_repr": repr(decision),
                        "regime": str(getattr(regime, "type", None) or getattr(regime, "regime", None) or "UNKNOWN_REGIME"),
                        "trend": str(getattr(regime, "trend", None) or ""),
                        "volatility": str(getattr(regime, "volatility", None) or ""),
                        "atr": float(getattr(regime, "atr", 0.0) or 0.0),
                        "atr_pct": float((state or {}).get("atr_pct", 0.0) or 0.0) if isinstance(state, dict) else 0.0,
                        "price": float(price or 0.0),
                        "tradable": bool(getattr(regime, "tradable", False)),
                    },
                )
            )

            print(
                "PIPE_RUNTIME_RISK_EVENT_AUDIT_OK",
                f"symbol={symbol}",
                f"severity={severity}",
                f"reason={reason}",
                flush=True,
            )

        except Exception as exc:
            print(
                "PIPE_RUNTIME_RISK_EVENT_AUDIT_FAILED",
                f"symbol={symbol}",
                f"error={type(exc).__name__}:{exc}",
                flush=True,
            )


    def _breakout_bucketed_level(self, symbol: str, level: float) -> float:
        """Русский комментарий: приводит уровень к bucket, если bucket включён."""
        bucket = self._breakout_level_bucket_for_symbol(symbol)
        value = float(level)
        if bucket <= 0:
            return round(value, 4)
        return round(round(value / bucket) * bucket, 4)



def log_exit_policy_advisory(
    *,
    database_url: str,
    symbol: str,
    strategy: str,
    timeframe: str,
) -> None:
    """
    Русский комментарий:
    Advisory-only лог выбранного exit policy.

    Важно:
    - не меняет stop/take;
    - не отправляет заявки;
    - не влияет на RiskEngine;
    - только пишет диагностический лог.
    """

    try:
        advisor = RuntimeExitPolicyAdvisor(database_url)
        advice = advisor.get_advice(
            symbol=symbol,
            strategy=strategy,
            timeframe=timeframe,
        )

        if advice is None:
            print(
                "EXIT_POLICY_ADVISORY_EMPTY "
                f"symbol={symbol} "
                f"strategy={strategy} "
                f"timeframe={timeframe}",
                flush=True,
            )
            return

        print(
            "EXIT_POLICY_ADVISORY_APPLIED "
            f"symbol={advice.symbol} "
            f"strategy={advice.strategy} "
            f"timeframe={advice.timeframe} "
            f"policy={advice.policy} "
            f"take_distance={advice.take_distance} "
            f"stop_distance={advice.stop_distance} "
            f"profit_factor={advice.profit_factor} "
            f"net_pnl={advice.net_pnl} "
            f"max_drawdown={advice.max_drawdown} "
            f"winrate={advice.winrate}",
            flush=True,
        )

    except Exception as exc:
        print(
            "EXIT_POLICY_ADVISORY_ERROR "
            f"symbol={symbol} "
            f"strategy={strategy} "
            f"timeframe={timeframe} "
            f"error={type(exc).__name__}:{exc}",
            flush=True,
        )



def log_incremental_exit_advice(
    *,
    symbol: str,
    strategy: str,
    timeframe: str,
    side: str,
    entry_price: float,
    current_price: float,
    qty: float,
    take_distance: float,
    stop_distance: float,
) -> None:
    """
    Русский комментарий:
    Incremental Exit Intelligence в режиме advisory-only.
    Не меняет заявки, RiskEngine, stop/take и execution.
    """

    try:
        advice = build_incremental_exit_advice(
            IncrementalExitInput(
                symbol=symbol,
                strategy=strategy,
                timeframe=timeframe,
                side=side,
                entry_price=entry_price,
                current_price=current_price,
                qty=qty,
                take_distance=take_distance,
                stop_distance=stop_distance,
            )
        )

        print(
            "INCREMENTAL_EXIT_ADVICE "
            f"symbol={advice.symbol} "
            f"strategy={advice.strategy} "
            f"timeframe={advice.timeframe} "
            f"side={advice.side} "
            f"entry={entry_price} "
            f"current={current_price} "
            f"take_price={advice.take_price} "
            f"stop_price={advice.stop_price} "
            f"distance_to_take={advice.distance_to_take} "
            f"distance_to_stop={advice.distance_to_stop} "
            f"action={advice.action} "
            f"reason={advice.reason}",
            flush=True,
        )

    except Exception as exc:
        print(
            "INCREMENTAL_EXIT_ADVICE_ERROR "
            f"symbol={symbol} "
            f"error={type(exc).__name__}:{exc}",
            flush=True,
        )



def log_portfolio_heat_advisory(*, database_url: str) -> None:
    """
    Русский комментарий:
    Portfolio Heat advisory-only лог.
    Не меняет RiskStack, execution, заявки и позиции.
    """

    try:
        advisor = RuntimePortfolioHeatAdvisor(database_url)
        advice = advisor.get_latest_advice()

        if advice is None:
            print("PORTFOLIO_HEAT_ADVISORY_EMPTY", flush=True)
            return

        print(
            "PORTFOLIO_HEAT_ADVISORY_APPLIED "
            f"status={advice.status} "
            f"heat={advice.heat} "
            f"risk_multiplier={advice.risk_multiplier} "
            f"allow_new_entries={advice.allow_new_entries} "
            f"reason={advice.reason}",
            flush=True,
        )

    except Exception as exc:
        print(
            "PORTFOLIO_HEAT_ADVISORY_ERROR "
            f"error={type(exc).__name__}:{exc}",
            flush=True,
        )



def log_portfolio_governance_advisory(
    *,
    database_url: str,
    symbol: str,
    strategy: str,
    timeframe: str,
) -> None:
    """
    Русский комментарий:
    Единый Portfolio Governance advisory-log.
    Не меняет RiskStack, execution, заявки и позиции.
    """

    try:
        advisor = PortfolioGovernanceAdvisor(database_url)
        decision = advisor.build(
            symbol=symbol,
            strategy=strategy,
            timeframe=timeframe,
        )

        print(
            "PORTFOLIO_GOVERNANCE_ADVISORY_APPLIED "
            f"symbol={decision.symbol} "
            f"strategy={decision.strategy} "
            f"timeframe={timeframe} "
            f"heat_status={decision.portfolio_heat_status} "
            f"portfolio_risk_multiplier={decision.portfolio_risk_multiplier} "
            f"exit_policy={decision.exit_policy} "
            f"allow_new_entries={decision.allow_new_entries} "
            f"mode={decision.governance_mode}",
            flush=True,
        )

        repo = PortfolioGovernanceRepository(database_url)
        repo.migrate()
        repo.save(timeframe=timeframe, decision=decision)

        print(
            "PORTFOLIO_GOVERNANCE_EVENT_SAVED "
            f"symbol={decision.symbol} "
            f"strategy={decision.strategy} "
            f"timeframe={timeframe} "
            f"mode={decision.governance_mode}",
            flush=True,
        )

    except Exception as exc:
        print(
            "PORTFOLIO_GOVERNANCE_ADVISORY_ERROR "
            f"symbol={symbol} "
            f"strategy={strategy} "
            f"timeframe={timeframe} "
            f"error={type(exc).__name__}:{exc}",
            flush=True,
        )



def log_runtime_governance_decision(
    *,
    database_url: str,
    symbol: str,
    strategy: str,
    timeframe: str,
) -> None:
    """
    Русский комментарий:
    Runtime Governance Coordinator v2 startup-log.
    Только advisory/log. Не меняет execution, RiskStack и заявки.
    """

    try:
        coordinator = RuntimeGovernanceCoordinatorV2(database_url)
        decision = coordinator.decide(
            symbol=symbol,
            strategy=strategy,
            timeframe=timeframe,
        )

        print(
            "RUNTIME_GOVERNANCE_DECISION "
            f"symbol={decision.symbol} "
            f"strategy={decision.strategy} "
            f"timeframe={decision.timeframe} "
            f"mode={decision.mode} "
            f"heat_status={decision.heat_status} "
            f"risk_multiplier={decision.risk_multiplier} "
            f"allow_new_entries={decision.allow_new_entries} "
            f"allow_execution={decision.allow_execution} "
            f"watch_only={decision.watch_only} "
            f"lifecycle_action={decision.lifecycle_action} "
            f"lifecycle_severity={decision.lifecycle_severity} "
            f"reason={decision.reason}",
            flush=True,
        )

    except Exception as exc:
        print(
            "RUNTIME_GOVERNANCE_DECISION_ERROR "
            f"symbol={symbol} "
            f"strategy={strategy} "
            f"timeframe={timeframe} "
            f"error={type(exc).__name__}:{exc}",
            flush=True,
        )


_RUNTIME_GUARD_READER_V1 = None
_RUNTIME_GUARD_STATE_V1 = None
_GUARD_CLASSIFICATION_STATE_V1 = {}
_GUARD_SHADOW_ACCUMULATOR_V1 = None



def _load_guard_classification_state_v1() -> None:
    global _GUARD_CLASSIFICATION_STATE_V1
    try:
        reader = GuardCandidateClassificationReader()
        _GUARD_CLASSIFICATION_STATE_V1 = reader.load_all()

        block_ready = sum(1 for x in _GUARD_CLASSIFICATION_STATE_V1.values() if x.classification == "BLOCK_READY")
        research_only = sum(1 for x in _GUARD_CLASSIFICATION_STATE_V1.values() if x.classification == "RESEARCH_ONLY")
        keep_watch = sum(1 for x in _GUARD_CLASSIFICATION_STATE_V1.values() if x.classification == "KEEP_WATCH")

        print(
            "PIPE_GUARD_CLASSIFICATION_STATE_LOADED "
            f"rows={len(_GUARD_CLASSIFICATION_STATE_V1)} "
            f"block_ready={block_ready} "
            f"research_only={research_only} "
            f"keep_watch={keep_watch}",
            flush=True,
        )
    except Exception as exc:
        _GUARD_CLASSIFICATION_STATE_V1 = {}
        print(
            "PIPE_GUARD_CLASSIFICATION_STATE_LOAD_FAILED "
            f"error={type(exc).__name__}:{exc}",
            flush=True,
        )


def _guard_classification_advisory_v1(
    *,
    symbol: str,
    strategy: str,
    timeframe: str,
    side: str,
    session_bucket: str,
) -> None:
    normalized_side = str(side or "").upper()
    if normalized_side not in ("LONG", "SHORT"):
        return

    key = (
        str(symbol or ""),
        str(strategy or ""),
        str(timeframe or ""),
        normalized_side,
        str(session_bucket or "UNKNOWN"),
    )

    item = _GUARD_CLASSIFICATION_STATE_V1.get(key)
    if item is None:
        print(
            "PIPE_GUARD_CLASSIFICATION_ADVISORY_NOT_FOUND "
            f"symbol={key[0]} strategy={key[1]} timeframe={key[2]} "
            f"side={key[3]} session={key[4]} advisory_only=1",
            flush=True,
        )
        return

    print(
        "PIPE_GUARD_CLASSIFICATION_ADVISORY "
        f"symbol={item.symbol} strategy={item.strategy} timeframe={item.timeframe} "
        f"side={item.side} session={item.session_bucket} "
        f"classification={item.classification} reason={item.reason} "
        f"trades={item.total_trades} expectancy={item.expectancy:.8f} "
        f"stop_rate={item.stop_rate:.4f} advisory_only=1",
        flush=True,
    )

    # guard_execution_gate_shadow_v1:
    # Только считаем потенциальную блокировку. Торговое решение не меняем.
    if item.classification == "BLOCK_READY":
        print(
            "PIPE_GUARD_EXECUTION_GATE_SHADOW "
            f"symbol={item.symbol} strategy={item.strategy} timeframe={item.timeframe} "
            f"side={item.side} session={item.session_bucket} "
            f"classification={item.classification} reason={item.reason} "
            f"would_block=1 actual_block=0 advisory_only=1",
            flush=True,
        )

        # guard_shadow_accumulation_v1:
        # Пишем shadow-событие в PostgreSQL. Торговое решение не меняем.
        try:
            global _GUARD_SHADOW_ACCUMULATOR_V1
            if _GUARD_SHADOW_ACCUMULATOR_V1 is None:
                _GUARD_SHADOW_ACCUMULATOR_V1 = GuardShadowAccumulator()

            _GUARD_SHADOW_ACCUMULATOR_V1.record(
                GuardShadowEvent(
                    symbol=item.symbol,
                    strategy=item.strategy,
                    timeframe=item.timeframe,
                    side=item.side,
                    session_bucket=item.session_bucket,
                    classification=item.classification,
                    reason=item.reason,
                    would_block=True,
                    actual_block=False,
                    advisory_only=True,
                    signal_id=None,
                )
            )

            print(
                "PIPE_GUARD_SHADOW_ACCUMULATION_RECORDED "
                f"symbol={item.symbol} strategy={item.strategy} timeframe={item.timeframe} "
                f"side={item.side} session={item.session_bucket} classification={item.classification}",
                flush=True,
            )
        except Exception as exc:
            print(
                "PIPE_GUARD_SHADOW_ACCUMULATION_FAILED "
                f"symbol={item.symbol} strategy={item.strategy} "
                f"error={type(exc).__name__}:{exc}",
                flush=True,
            )

def _runtime_guard_advisory_v1(symbol: str, strategy: str, timeframe: str, side: str, session_bucket: str) -> None:
    """Только advisory-лог. Не блокирует pipeline и не меняет торговое решение."""
    global _RUNTIME_GUARD_READER_V1, _RUNTIME_GUARD_STATE_V1

    try:
        if _RUNTIME_GUARD_READER_V1 is None:
            _RUNTIME_GUARD_READER_V1 = RuntimeGuardReader()
        # classification_state_loaded_inside_runtime_guard_v1
        if not _GUARD_CLASSIFICATION_STATE_V1:
            _load_guard_classification_state_v1()


        if _RUNTIME_GUARD_STATE_V1 is None:
            _RUNTIME_GUARD_STATE_V1 = _RUNTIME_GUARD_READER_V1.load_active_guards()
            block = sum(1 for g in _RUNTIME_GUARD_STATE_V1.values() if g.decision == "BLOCK_STOP_DOMINATED")
            watch = sum(1 for g in _RUNTIME_GUARD_STATE_V1.values() if g.decision == "WATCH_NEGATIVE_TOTAL")
            allow = sum(1 for g in _RUNTIME_GUARD_STATE_V1.values() if g.decision == "ALLOW_WATCH")
            print(
                f"PIPE_RUNTIME_GUARD_STATE_LOADED rows={len(_RUNTIME_GUARD_STATE_V1)} "
                f"block={block} watch={watch} allow={allow}",
                flush=True,
            )

        normalized_side = str(side or "").upper()
        if normalized_side not in ("LONG", "SHORT"):
            return

        key = (
            str(symbol or ""),
            str(strategy or ""),
            str(timeframe or ""),
            normalized_side,
            str(session_bucket or "UNKNOWN"),
        )
        guard = _RUNTIME_GUARD_STATE_V1.get(key)

        if guard is None:
            print(
                f"PIPE_RUNTIME_GUARD_ADVISORY symbol={symbol} strategy={strategy} "
                f"timeframe={timeframe} side={side} session={session_bucket} "
                f"decision=NO_GUARD reason=no_matching_guard_state advisory_only=1",
                flush=True,
            )
            # regime_guard_shadow_live_smoke_v1_call_no_guard
            _emit_regime_guard_live_match_pipeline_advisory_v1(symbol)
            return

        print(
            f"PIPE_RUNTIME_GUARD_ADVISORY symbol={symbol} strategy={strategy} "
            f"timeframe={timeframe} side={side} session={session_bucket} "
            f"decision={guard.decision} reason={guard.reason} "
            f"total_trades={guard.total_trades} stop_trades={guard.stop_trades} "
            f"stop_net_pnl={guard.stop_net_pnl:.8f} take_trades={guard.take_trades} "
            f"take_net_pnl={guard.take_net_pnl:.8f} advisory_only=1",
            flush=True,
        )

        # regime_guard_shadow_live_smoke_v1_call
        _emit_regime_guard_live_match_pipeline_advisory_v1(symbol)


    except Exception as exc:
        print(f"PIPE_RUNTIME_GUARD_ADVISORY_FAILED error={type(exc).__name__}:{exc} advisory_only=1", flush=True)


# regime_guard_advisory_v1:
# Только advisory-телеметрия. Торговое решение не меняется.
def _emit_regime_guard_advisory_v1(symbol: str, side: str = "UNKNOWN") -> None:
    try:
        from finam_core.governance.regime_guard_candidate_reader import RegimeGuardCandidateReader

        reader = RegimeGuardCandidateReader()
        rows = reader.load()

        # v1 использует только уже материализованные кандидаты.
        # Точное сопоставление live regime_key будет добавлено следующим слоем,
        # после стабилизации live regime snapshot.
        block_count = sum(1 for x in rows.values() if x.classification == "BLOCK_CANDIDATE")

        print(
            "PIPE_REGIME_GUARD_ADVISORY "
            f"symbol={symbol} side={side} "
            f"candidates={len(rows)} block_candidates={block_count} "
            "would_block=0 actual_block=0 advisory_only=1 "
            "reason=reader_loaded_no_live_regime_key_yet",
            flush=True,
        )
    except Exception as exc:
        print(
            "PIPE_REGIME_GUARD_ADVISORY_FAILED "
            f"symbol={symbol} side={side} error={type(exc).__name__}:{exc}",
            flush=True,
        )

# regime_guard_live_match_pipeline_advisory_v1:
# Advisory-only. Торговое решение не меняется.
def _emit_regime_guard_live_match_pipeline_advisory_v1(symbol: str = "UNKNOWN") -> None:
    try:
        from finam_core.governance.regime_guard_advisory_service import RegimeGuardAdvisoryService

        decision = RegimeGuardAdvisoryService().evaluate()
        pf = decision.profit_factor
        pf_text = "None" if pf is None else f"{pf:.8f}"

        print(
            "PIPE_REGIME_GUARD_ADVISORY "
            f"symbol={symbol} scope={decision.scope} "
            f"regime_key={decision.regime_key} matched={int(decision.matched)} "
            f"classification={decision.classification} reason={decision.reason} "
            f"trades={decision.trades} expectancy={decision.expectancy:.8f} "
            f"profit_factor={pf_text} "
            f"would_block={int(decision.would_block)} actual_block=0 advisory_only=1",
            flush=True,
        )

        try:
            from finam_core.governance.regime_guard_shadow_accumulator import RegimeGuardShadowAccumulator

            RegimeGuardShadowAccumulator().record(
                symbol=symbol,
                signal_id=None,
                strategy=None,
                regime_key=decision.regime_key,
                classification=decision.classification,
                would_block=decision.would_block,
                reason=decision.reason,
            )

            print(
                "PIPE_REGIME_GUARD_SHADOW_ACCUMULATION_OK "
                f"symbol={symbol} regime_key={decision.regime_key} "
                f"classification={decision.classification} "
                f"would_block={int(decision.would_block)} actual_block=0 advisory_only=1",
                flush=True,
            )
        except Exception as shadow_exc:
            print(
                "PIPE_REGIME_GUARD_SHADOW_ACCUMULATION_FAILED "
                f"symbol={symbol} error={type(shadow_exc).__name__}:{shadow_exc}",
                flush=True,
            )
    except Exception as exc:
        print(
            "PIPE_REGIME_GUARD_ADVISORY_FAILED "
            f"symbol={symbol} error={type(exc).__name__}:{exc}",
            flush=True,
        )


# br_short_shadow_pipeline_hook_v1:
# Русский комментарий: ленивые singleton-объекты для shadow-policy BR short.
_BR_SHORT_SHADOW_POLICY_V1 = None
_BR_SHORT_SHADOW_ACCUMULATOR_V1 = None


def _br_short_shadow_pipeline_hook_v1(
    *,
    symbol: str,
    side: str,
    strategy: str = "UNKNOWN",
    current_position: float = 0.0,
    signal_id: str | None = None,
    price=None,
    quantity=None,
) -> bool:
    """Русский комментарий: BR short shadow-hook.

    Ничего не блокирует и не исполняет.
    Только печатает, был бы SELL-сигнал кандидатом на OPEN_SHORT при flat/short позиции.
    """
    global _BR_SHORT_SHADOW_POLICY_V1, _BR_SHORT_SHADOW_ACCUMULATOR_V1

    try:
        if _BR_SHORT_SHADOW_POLICY_V1 is None:
            _BR_SHORT_SHADOW_POLICY_V1 = BrShortShadowPolicyV1()

        decision = _BR_SHORT_SHADOW_POLICY_V1.evaluate(
            symbol=symbol,
            side=side,
            strategy=strategy,
            current_position=float(current_position or 0.0),
        )

        print(
            "PIPE_BR_SHORT_SHADOW_POLICY_V1 "
            f"symbol={symbol} side={side} strategy={strategy} "
            f"position={float(current_position or 0.0)} "
            f"allowed={int(decision.allowed)} "
            f"shadow_logged={int(decision.shadow_logged)} "
            f"reason={decision.reason} "
            f"signal_id={signal_id or ''} price={price} qty={quantity}",
            flush=True,
        )

        if decision.shadow_logged:
            from decimal import Decimal

            if _BR_SHORT_SHADOW_ACCUMULATOR_V1 is None:
                _BR_SHORT_SHADOW_ACCUMULATOR_V1 = BrShortShadowAccumulatorV1()

            def _to_decimal(value):
                if value is None:
                    return None
                try:
                    return Decimal(str(value))
                except Exception:
                    return None

            _BR_SHORT_SHADOW_ACCUMULATOR_V1.record(
                BrShortShadowEventV1(
                    symbol=symbol,
                    side=side,
                    strategy=strategy,
                    signal_id=signal_id,
                    mode="shadow",
                    allowed=bool(decision.allowed),
                    shadow_logged=bool(decision.shadow_logged),
                    reason=decision.reason,
                    current_position=_to_decimal(current_position),
                    price=_to_decimal(price),
                    quantity=_to_decimal(quantity),
                    payload={
                        "source": "br_short_shadow_pipeline_hook_v1",
                        "runtime_changed": 0,
                    },
                )
            )

            print(
                "PIPE_BR_SHORT_SHADOW_ACCUMULATION_OK "
                f"symbol={symbol} side={side} strategy={strategy} "
                f"signal_id={signal_id or ''} reason={decision.reason}",
                flush=True,
            )

        return True
    except Exception as exc:
        print(
            "PIPE_BR_SHORT_SHADOW_POLICY_V1_ERROR "
            f"symbol={symbol} side={side} strategy={strategy} "
            f"type={type(exc).__name__} error={exc}",
            flush=True,
        )
        return True


# br_long_shadow_pipeline_hook_v1:
# Ленивые singleton-объекты, чтобы не создавать соединение на каждый сигнал.
_BR_LONG_GOVERNANCE_V1 = None
_BR_LONG_SHADOW_ACCUMULATOR_V1 = None


def _br_long_shadow_pipeline_hook_v1(
    *,
    symbol: str,
    side: str,
    strategy: str = "UNKNOWN",
    signal_id: str | None = None,
    price=None,
    quantity=None,
) -> bool:
    """Возвращает True, если сигнал можно пропустить дальше.

    Для BR LONG в shadow/disabled режиме возвращает False.
    Runtime/execution для остальных сигналов не меняет.
    """
    global _BR_LONG_GOVERNANCE_V1, _BR_LONG_SHADOW_ACCUMULATOR_V1

    try:
        import os
        from decimal import Decimal

        if _BR_LONG_GOVERNANCE_V1 is None:
            _BR_LONG_GOVERNANCE_V1 = BrLongGovernanceV1(
                mode=os.getenv("BR_LONG_MODE", "shadow")
            )

        decision = _BR_LONG_GOVERNANCE_V1.evaluate(symbol=symbol, side=side)

        print(
            "PIPE_BR_LONG_GOVERNANCE_V1 "
            f"symbol={decision.symbol} side={decision.side} mode={decision.mode} "
            f"allowed={int(decision.allowed)} shadow_logged={int(decision.shadow_logged)} "
            f"reason={decision.reason}",
            flush=True,
        )

        if decision.shadow_logged:
            if _BR_LONG_SHADOW_ACCUMULATOR_V1 is None:
                _BR_LONG_SHADOW_ACCUMULATOR_V1 = BrLongShadowAccumulatorV1()

            def _to_decimal(value):
                if value is None:
                    return None
                try:
                    return Decimal(str(value))
                except Exception:
                    return None

            _BR_LONG_SHADOW_ACCUMULATOR_V1.record(
                BrLongShadowEventV1(
                    symbol=decision.symbol,
                    side=decision.side,
                    strategy=str(strategy or "UNKNOWN"),
                    signal_id=signal_id,
                    price=_to_decimal(price),
                    quantity=_to_decimal(quantity),
                    mode=decision.mode,
                    allowed=decision.allowed,
                    shadow_logged=decision.shadow_logged,
                    reason=decision.reason,
                )
            )

            print(
                "PIPE_BR_LONG_SHADOW_ACCUMULATION_OK "
                f"symbol={decision.symbol} side={decision.side} "
                f"strategy={strategy} signal_id={signal_id} "
                f"allowed={int(decision.allowed)} shadow_logged=1",
                flush=True,
            )

        return bool(decision.allowed)

    except Exception as exc:
        # Fail-open: governance не должен ломать общий pipeline.
        print(
            "PIPE_BR_LONG_SHADOW_PIPELINE_HOOK_FAILED "
            f"symbol={symbol} side={side} error={type(exc).__name__}:{exc} "
            "fail_open=1",
            flush=True,
        )
        return True

