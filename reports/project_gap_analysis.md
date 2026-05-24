# Finam_Core Project Gap Analysis

## Git
feature/exit-alpha-v1
dfde6b9 config: migrate market data runtime flags
?? scripts/audit_project_gap_analysis.sh

## Top-level structure
src/finam_core
src/finam_core/accounting
src/finam_core/accounting/__pycache__
src/finam_core/adapters
src/finam_core/adapters/grpc
src/finam_core/adapters/__pycache__
src/finam_core/adapters/rest
src/finam_core/ai
src/finam_core/ai/__pycache__
src/finam_core/alpha
src/finam_core/alpha/__pycache__
src/finam_core/analytics
src/finam_core/analytics/__pycache__
src/finam_core/app
src/finam_core/app/__pycache__
src/finam_core/auth
src/finam_core/auth/__pycache__
src/finam_core/backtest
src/finam_core/clients
src/finam_core/config
src/finam_core/config/__pycache__
src/finam_core/contracts
src/finam_core/contracts/__pycache__
src/finam_core/control
src/finam_core/control/__pycache__
src/finam_core/core
src/finam_core/core/events
src/finam_core/core/pipeline
src/finam_core/core/__pycache__
src/finam_core/data
src/finam_core/data/__pycache__
src/finam_core/domain
src/finam_core/domain/__pycache__
src/finam_core/domain/regime
src/finam_core/domain/risk
src/finam_core/domain/session
src/finam_core/engine
src/finam_core/engine/__pycache__
src/finam_core/events
src/finam_core/events/__pycache__
src/finam_core/execution
src/finam_core/execution/__pycache__
src/finam_core/features
src/finam_core/features/__pycache__
src/finam_core/futures
src/finam_core/futures/__pycache__
src/finam_core/gateway
src/finam_core/gateway/__pycache__
src/finam_core/infra
src/finam_core/infra/brokers
src/finam_core/infra/finam
src/finam_core/infra/__pycache__
src/finam_core/ingestion
src/finam_core/ingestion/__pycache__
src/finam_core/instruments
src/finam_core/manual
src/finam_core/manual/__pycache__
src/finam_core/market
src/finam_core/market/__pycache__
src/finam_core/metrics
src/finam_core/notifications
src/finam_core/notifications/__pycache__
src/finam_core/oms
src/finam_core/oms/__pycache__
src/finam_core/orderflow
src/finam_core/orderflow/__pycache__
src/finam_core/pipeline
src/finam_core/pipelines
src/finam_core/pipelines/__pycache__
src/finam_core/portfolio
src/finam_core/portfolio/__pycache__
src/finam_core/projections
src/finam_core/projections/__pycache__
src/finam_core/__pycache__
src/finam_core/reconciliation
src/finam_core/reconciliation/__pycache__
src/finam_core/recovery
src/finam_core/recovery/__pycache__
src/finam_core/regime
src/finam_core/regime/__pycache__
src/finam_core/replay
src/finam_core/replay/__pycache__
src/finam_core/research
src/finam_core/research/__pycache__
src/finam_core/risk
src/finam_core/risk/__pycache__
src/finam_core/risk/rules
src/finam_core/runtime
src/finam_core/runtime/__pycache__
src/finam_core/scripts
src/finam_core/session
src/finam_core/session/__pycache__
src/finam_core/signals
src/finam_core/signals/__pycache__
src/finam_core/simulation
src/finam_core/storage
src/finam_core/storage/__pycache__
src/finam_core/strategy
src/finam_core/strategy/br
src/finam_core/strategy/equities
src/finam_core/strategy/filters
src/finam_core/strategy/futures
src/finam_core/strategy/fx
src/finam_core/strategy/ng
src/finam_core/strategy/__pycache__
src/finam_core/utils

## Runtime / Risk / Execution modules
src/finam_core/execution/asset_execution_policy.py
src/finam_core/execution/auto_breakeven_manager.py
src/finam_core/execution/broker_capabilities_gate.py
src/finam_core/execution/broker_event_idempotency.py
src/finam_core/execution/broker_reconciliation.py
src/finam_core/execution/cancel_replace_stop_manager.py
src/finam_core/execution/client_order_id_factory.py
src/finam_core/execution/duplicate_fill_protection.py
src/finam_core/execution/entry_point_selector.py
src/finam_core/execution/execution_decision_layer.py
src/finam_core/execution/execution_dispatcher.py
src/finam_core/execution/execution_engine.py
src/finam_core/execution/execution_fill.py
src/finam_core/execution/execution_gateway.py
src/finam_core/execution/execution_intent_fsm.py
src/finam_core/execution/execution_intent_router.py
src/finam_core/execution/execution_intent_transition_service.py
src/finam_core/execution/execution_lifecycle_determinism.py
src/finam_core/execution/execution_report_listener.py
src/finam_core/execution/execution_state_transition_logger.py
src/finam_core/execution/execution_symbol_resolver.py
src/finam_core/execution/exit_lifecycle_manager.py
src/finam_core/execution/fill_event_router.py
src/finam_core/execution/fill_metadata_factory.py
src/finam_core/execution/fill_persistence_service.py
src/finam_core/execution/finam_execution_engine.py
src/finam_core/execution/finam_order_client_adapter.py
src/finam_core/execution/finam_order_identity_extraction.py
src/finam_core/execution/finam_order_status_adapter.py
src/finam_core/execution/__init__.py
src/finam_core/execution/managed_position_service.py
src/finam_core/execution/oco_order_manager.py
src/finam_core/execution/oms_dispatch_guard.py
src/finam_core/execution/oms.py
src/finam_core/execution/open_orders_sync.py
src/finam_core/execution/order_ack_logger.py
src/finam_core/execution/order_ack.py
src/finam_core/execution/order_manager.py
src/finam_core/execution/order_model.py
src/finam_core/execution/order.py
src/finam_core/execution/order_router.py
src/finam_core/execution/order_state_machine.py
src/finam_core/execution/paper_engine.py
src/finam_core/execution/partial_close_engine.py
src/finam_core/execution/position_lifecycle_reconcile_event_repository.py
src/finam_core/execution/position_lifecycle_reconciler.py
src/finam_core/execution/position_lifecycle_self_healer.py
src/finam_core/execution/position_lifecycle_service.py
src/finam_core/execution/position_lifecycle_state_repository.py
src/finam_core/execution/position_order_tracker.py
src/finam_core/execution/position_registry.py
src/finam_core/execution/profit_lock_engine.py
src/finam_core/execution/profit_lock_event_repository.py
src/finam_core/execution/protection_level_calculator.py
src/finam_core/execution/protective_duplicate_gate.py
src/finam_core/execution/protective_order_link.py
src/finam_core/execution/protective_order_link_repository.py
src/finam_core/execution/__pycache__/auto_breakeven_manager.cpython-313.pyc
src/finam_core/execution/__pycache__/broker_capabilities_gate.cpython-313.pyc
src/finam_core/execution/__pycache__/broker_event_idempotency.cpython-313.pyc
src/finam_core/execution/__pycache__/broker_reconciliation.cpython-313.pyc
src/finam_core/execution/__pycache__/cancel_replace_stop_manager.cpython-313.pyc
src/finam_core/execution/__pycache__/client_order_id_factory.cpython-313.pyc
src/finam_core/execution/__pycache__/duplicate_fill_protection.cpython-313.pyc
src/finam_core/execution/__pycache__/entry_point_selector.cpython-313.pyc
src/finam_core/execution/__pycache__/execution_decision_layer.cpython-313.pyc
src/finam_core/execution/__pycache__/execution_dispatcher.cpython-313.pyc
src/finam_core/execution/__pycache__/execution_engine.cpython-313.pyc
src/finam_core/execution/__pycache__/execution_fill.cpython-313.pyc
src/finam_core/execution/__pycache__/execution_gateway.cpython-313.pyc
src/finam_core/execution/__pycache__/execution_intent_fsm.cpython-313.pyc
src/finam_core/execution/__pycache__/execution_intent_router.cpython-313.pyc
src/finam_core/execution/__pycache__/execution_intent_transition_service.cpython-313.pyc
src/finam_core/execution/__pycache__/execution_lifecycle_determinism.cpython-313.pyc
src/finam_core/execution/__pycache__/execution_state_transition_logger.cpython-313.pyc
src/finam_core/execution/__pycache__/execution_symbol_resolver.cpython-313.pyc
src/finam_core/execution/__pycache__/exit_lifecycle_manager.cpython-313.pyc
src/finam_core/execution/__pycache__/fill_event_router.cpython-313.pyc
src/finam_core/execution/__pycache__/fill_metadata_factory.cpython-313.pyc
src/finam_core/execution/__pycache__/fill_persistence_service.cpython-313.pyc
src/finam_core/execution/__pycache__/finam_execution_engine.cpython-313.pyc
src/finam_core/execution/__pycache__/finam_order_client_adapter.cpython-313.pyc
src/finam_core/execution/__pycache__/finam_order_identity_extraction.cpython-313.pyc
src/finam_core/execution/__pycache__/finam_order_status_adapter.cpython-313.pyc
src/finam_core/execution/__pycache__/__init__.cpython-313.pyc
src/finam_core/execution/__pycache__/managed_position_service.cpython-313.pyc
src/finam_core/execution/__pycache__/oco_order_manager.cpython-313.pyc
src/finam_core/execution/__pycache__/oms_dispatch_guard.cpython-313.pyc
src/finam_core/execution/__pycache__/open_orders_sync.cpython-313.pyc
src/finam_core/execution/__pycache__/order_ack.cpython-313.pyc
src/finam_core/execution/__pycache__/order_ack_logger.cpython-313.pyc
src/finam_core/execution/__pycache__/order_router.cpython-313.pyc
src/finam_core/execution/__pycache__/order_state_machine.cpython-313.pyc
src/finam_core/execution/__pycache__/paper_engine.cpython-313.pyc
src/finam_core/execution/__pycache__/partial_close_engine.cpython-313.pyc
src/finam_core/execution/__pycache__/position_lifecycle_reconcile_event_repository.cpython-313.pyc
src/finam_core/execution/__pycache__/position_lifecycle_reconciler.cpython-313.pyc
src/finam_core/execution/__pycache__/position_lifecycle_self_healer.cpython-313.pyc
src/finam_core/execution/__pycache__/position_lifecycle_service.cpython-313.pyc
src/finam_core/execution/__pycache__/position_lifecycle_state_repository.cpython-313.pyc
src/finam_core/execution/__pycache__/position_order_tracker.cpython-313.pyc
src/finam_core/execution/__pycache__/position_registry.cpython-313.pyc
src/finam_core/execution/__pycache__/profit_lock_engine.cpython-313.pyc
src/finam_core/execution/__pycache__/profit_lock_event_repository.cpython-313.pyc
src/finam_core/execution/__pycache__/protection_level_calculator.cpython-313.pyc
src/finam_core/execution/__pycache__/protective_duplicate_gate.cpython-313.pyc
src/finam_core/execution/__pycache__/protective_order_link.cpython-313.pyc
src/finam_core/execution/__pycache__/protective_order_link_repository.cpython-313.pyc
src/finam_core/execution/__pycache__/real_buy_execution_adapter.cpython-313.pyc
src/finam_core/execution/__pycache__/real_execution.cpython-313.pyc
src/finam_core/execution/__pycache__/real_execution_safety.cpython-313.pyc
src/finam_core/execution/__pycache__/real_order_state_synchronizer.cpython-313.pyc
src/finam_core/execution/__pycache__/real_protective_lifecycle.cpython-313.pyc
src/finam_core/execution/__pycache__/real_sell_execution_adapter.cpython-313.pyc
src/finam_core/execution/__pycache__/stop_replacement_engine.cpython-313.pyc
src/finam_core/execution/__pycache__/strategy_runtime_gate.cpython-313.pyc
src/finam_core/execution/__pycache__/take_profit_engine.cpython-313.pyc
src/finam_core/execution/__pycache__/take_profit_event_repository.cpython-313.pyc
src/finam_core/execution/__pycache__/trade_management_service.cpython-313.pyc
src/finam_core/execution/__pycache__/trailing_exit_policy.cpython-313.pyc
src/finam_core/execution/__pycache__/trailing_order_event_repository.cpython-313.pyc
src/finam_core/execution/__pycache__/trailing_order_manager.cpython-313.pyc
src/finam_core/execution/real_buy_execution_adapter.py
src/finam_core/execution/real_execution_engine.py
src/finam_core/execution/real_execution.py
src/finam_core/execution/real_execution_safety.py
src/finam_core/execution/real_order_state_synchronizer.py
src/finam_core/execution/real_protective_lifecycle.py
src/finam_core/execution/real_sell_execution_adapter.py
src/finam_core/execution/slippage_model.py
src/finam_core/execution/stop_replacement_engine.py
src/finam_core/execution/strategy_runtime_gate.py
src/finam_core/execution/take_profit_engine.py
src/finam_core/execution/take_profit_event_repository.py
src/finam_core/execution/trade_management_service.py
src/finam_core/execution/trading_engine.py
src/finam_core/execution/trailing_exit_policy.py
src/finam_core/execution/trailing_order_event_repository.py
src/finam_core/execution/trailing_order_manager.py
src/finam_core/pipelines/__init__.py
src/finam_core/pipelines/paper_pipeline.py
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633
src/finam_core/pipelines/pipeline_kernel.py
src/finam_core/pipelines/pipeline_orchestrator.py
src/finam_core/pipelines/__pycache__/__init__.cpython-313.pyc
src/finam_core/pipelines/__pycache__/paper_pipeline.cpython-313.pyc
src/finam_core/pipelines/__pycache__/pipeline_kernel.cpython-313.pyc
src/finam_core/pipelines/__pycache__/pipeline_orchestrator.cpython-313.pyc
src/finam_core/pipelines/__pycache__/quote_normalizer.cpython-313.pyc
src/finam_core/pipelines/quote_normalizer.py
src/finam_core/risk/adaptive_position_sizer.py
src/finam_core/risk/adaptive_regime_filter.py
src/finam_core/risk/adaptive_regime_repository.py
src/finam_core/risk/base_rule.py
src/finam_core/risk/context_builders.py
src/finam_core/risk/context.py
src/finam_core/risk/contract_adapter.py
src/finam_core/risk/correlation_risk.py
src/finam_core/risk/daily_risk_tracker.py
src/finam_core/risk/DrawdownRule.py
src/finam_core/risk/finam_limits_adapter.py
src/finam_core/risk/__init__.py
src/finam_core/risk/institutional_execution_gate.py
src/finam_core/risk/kill_switch.py
src/finam_core/risk/live_atr.py
src/finam_core/risk/margin_calculator.py
src/finam_core/risk/market_event_calendar_repository.py
src/finam_core/risk/MaxGrossExposureRule.py
src/finam_core/risk/MaxPositionPctRule.py
src/finam_core/risk/models.py
src/finam_core/risk/persistent_kill_switch.py
src/finam_core/risk/portfolio_heat.py
src/finam_core/risk/portfolio_risk_gate.py
src/finam_core/risk/position_cap.py
src/finam_core/risk/position_sizer.py
src/finam_core/risk/pre_trade_risk_engine.py
src/finam_core/risk/pre_trade_risk.py
src/finam_core/risk/__pycache__/adaptive_position_sizer.cpython-313.pyc
src/finam_core/risk/__pycache__/adaptive_regime_filter.cpython-313.pyc
src/finam_core/risk/__pycache__/adaptive_regime_repository.cpython-313.pyc
src/finam_core/risk/__pycache__/context_builders.cpython-313.pyc
src/finam_core/risk/__pycache__/correlation_risk.cpython-313.pyc
src/finam_core/risk/__pycache__/DrawdownRule.cpython-313.pyc
src/finam_core/risk/__pycache__/finam_limits_adapter.cpython-313.pyc
src/finam_core/risk/__pycache__/__init__.cpython-313.pyc
src/finam_core/risk/__pycache__/institutional_execution_gate.cpython-313.pyc
src/finam_core/risk/__pycache__/kill_switch.cpython-313.pyc
src/finam_core/risk/__pycache__/live_atr.cpython-313.pyc
src/finam_core/risk/__pycache__/market_event_calendar_repository.cpython-313.pyc
src/finam_core/risk/__pycache__/MaxGrossExposureRule.cpython-313.pyc
src/finam_core/risk/__pycache__/MaxPositionPctRule.cpython-313.pyc
src/finam_core/risk/__pycache__/persistent_kill_switch.cpython-313.pyc
src/finam_core/risk/__pycache__/portfolio_heat.cpython-313.pyc
src/finam_core/risk/__pycache__/portfolio_risk_gate.cpython-313.pyc
src/finam_core/risk/__pycache__/real_stock_safety_gate.cpython-313.pyc
src/finam_core/risk/__pycache__/regime_policy.cpython-313.pyc
src/finam_core/risk/__pycache__/risk_engine.cpython-313.pyc
src/finam_core/risk/__pycache__/risk_router.cpython-313.pyc
src/finam_core/risk/__pycache__/runtime_override_gate.cpython-313.pyc
src/finam_core/risk/__pycache__/sl_tp_cooldown.cpython-313.pyc
src/finam_core/risk/__pycache__/trailing_exit.cpython-313.pyc
src/finam_core/risk/__pycache__/unified_decision.cpython-313.pyc
src/finam_core/risk/__pycache__/volatility_risk.cpython-313.pyc
src/finam_core/risk/real_stock_safety_gate.py
src/finam_core/risk/regime_layer.py
src/finam_core/risk/regime_policy.py
src/finam_core/risk/risk_config.py
src/finam_core/risk/risk_engine.py
src/finam_core/risk/risk.py
src/finam_core/risk/risk_router.py
src/finam_core/risk/rules/core_rules.py
src/finam_core/risk/rules/__init__.py
src/finam_core/risk/rules.py
src/finam_core/risk/runtime_override_gate.py
src/finam_core/risk/session.py
src/finam_core/risk/sizing_engine.py
src/finam_core/risk/sl_tp_cooldown.py
src/finam_core/risk/trailing_exit.py
src/finam_core/risk/unified_decision.py
src/finam_core/risk/volatility_risk.py
src/finam_core/risk/volatility_sizer.py
src/finam_core/runtime/active_policy_reader.py
src/finam_core/runtime/adaptive_capital_allocator_v2.py
src/finam_core/runtime/adaptive_portfolio_allocator.py
src/finam_core/runtime/broker_reconciliation_engine.py
src/finam_core/runtime/capital_growth_daily_loss_guard.py
src/finam_core/runtime/capital_growth_mode.py
src/finam_core/runtime/capital_growth_portfolio_governor.py
src/finam_core/runtime/capital_growth_profile.py
src/finam_core/runtime/capital_growth_telegram_digest.py
src/finam_core/runtime/context_runtime_filter.py
src/finam_core/runtime/entry_gate_coordinator.py
src/finam_core/runtime/exit_policy_advisor.py
src/finam_core/runtime/__init__.py
src/finam_core/runtime/institutional_trade_quality_score.py
src/finam_core/runtime/intermarket_selection_modifier.py
src/finam_core/runtime/net_trade_evaluator.py
src/finam_core/runtime/ng_live_runtime_state_machine.py
src/finam_core/runtime/portfolio_aware_signal_filter.py
src/finam_core/runtime/portfolio_execution_planner.py
src/finam_core/runtime/portfolio_governance_advisor.py
src/finam_core/runtime/portfolio_governance_repository.py
src/finam_core/runtime/portfolio_heat_advisor.py
src/finam_core/runtime/portfolio_heat_risk_gate.py
src/finam_core/runtime/portfolio_reconciliation_engine.py
src/finam_core/runtime/__pycache__/active_policy_reader.cpython-313.pyc
src/finam_core/runtime/__pycache__/adaptive_capital_allocator_v2.cpython-313.pyc
src/finam_core/runtime/__pycache__/adaptive_portfolio_allocator.cpython-313.pyc
src/finam_core/runtime/__pycache__/autonomous_portfolio_brain.cpython-313.pyc
src/finam_core/runtime/__pycache__/broker_reconciliation_engine.cpython-313.pyc
src/finam_core/runtime/__pycache__/capital_growth_daily_loss_guard.cpython-313.pyc
src/finam_core/runtime/__pycache__/capital_growth_mode.cpython-313.pyc
src/finam_core/runtime/__pycache__/capital_growth_portfolio_governor.cpython-313.pyc
src/finam_core/runtime/__pycache__/capital_growth_profile.cpython-313.pyc
src/finam_core/runtime/__pycache__/capital_growth_regime_allocator.cpython-313.pyc
src/finam_core/runtime/__pycache__/capital_growth_telegram_digest.cpython-313.pyc
src/finam_core/runtime/__pycache__/context_runtime_filter.cpython-313.pyc
src/finam_core/runtime/__pycache__/entry_gate_coordinator.cpython-313.pyc
src/finam_core/runtime/__pycache__/exit_policy_advisor.cpython-313.pyc
src/finam_core/runtime/__pycache__/__init__.cpython-313.pyc
src/finam_core/runtime/__pycache__/institutional_trade_quality_score.cpython-313.pyc
src/finam_core/runtime/__pycache__/intermarket_selection_modifier.cpython-313.pyc
src/finam_core/runtime/__pycache__/net_trade_evaluator.cpython-313.pyc
src/finam_core/runtime/__pycache__/ng_live_runtime_state_machine.cpython-313.pyc
src/finam_core/runtime/__pycache__/portfolio_aware_signal_filter.cpython-313.pyc
src/finam_core/runtime/__pycache__/portfolio_execution_planner.cpython-313.pyc
src/finam_core/runtime/__pycache__/portfolio_governance_advisor.cpython-313.pyc
src/finam_core/runtime/__pycache__/portfolio_governance_repository.cpython-313.pyc
src/finam_core/runtime/__pycache__/portfolio_heat_advisor.cpython-313.pyc
src/finam_core/runtime/__pycache__/portfolio_heat_risk_gate.cpython-313.pyc
src/finam_core/runtime/__pycache__/portfolio_reconciliation_engine.cpython-313.pyc
src/finam_core/runtime/__pycache__/regime_matrix_modifier.cpython-313.pyc
src/finam_core/runtime/__pycache__/regime_runtime_control_service.cpython-313.pyc
src/finam_core/runtime/__pycache__/regime_runtime_override.cpython-313.pyc
src/finam_core/runtime/__pycache__/regime_runtime_override_repository.cpython-313.pyc
src/finam_core/runtime/__pycache__/risk_per_trade_sizing.cpython-313.pyc
src/finam_core/runtime/__pycache__/runtime_active_strategy_provider.cpython-313.pyc
src/finam_core/runtime/__pycache__/runtime_adaptive_risk.cpython-313.pyc
src/finam_core/runtime/__pycache__/runtime_allocator_decision_logger.cpython-313.pyc
src/finam_core/runtime/__pycache__/runtime_capital_allocator.cpython-313.pyc
src/finam_core/runtime/__pycache__/runtime_decision_digest.cpython-313.pyc
src/finam_core/runtime/__pycache__/runtime_execution_engine.cpython-313.pyc
src/finam_core/runtime/__pycache__/runtime_execution_sizer.cpython-313.pyc
src/finam_core/runtime/__pycache__/runtime_governance_coordinator.cpython-313.pyc
src/finam_core/runtime/__pycache__/runtime_governance_coordinator_v2.cpython-313.pyc
src/finam_core/runtime/__pycache__/runtime_governance_engine.cpython-313.pyc
src/finam_core/runtime/__pycache__/runtime_governance_telemetry.cpython-313.pyc
src/finam_core/runtime/__pycache__/runtime_policy_mode_resolver.cpython-313.pyc
src/finam_core/runtime/__pycache__/runtime_rebalance_cycle.cpython-313.pyc
src/finam_core/runtime/__pycache__/runtime_state.cpython-313.pyc
src/finam_core/runtime/__pycache__/runtime_state_gate.cpython-313.pyc
src/finam_core/runtime/__pycache__/runtime_strategy_cooldown_builder.cpython-313.pyc
src/finam_core/runtime/__pycache__/runtime_strategy_cooldown_provider.cpython-313.pyc
src/finam_core/runtime/__pycache__/runtime_strategy_gate_provider.cpython-313.pyc
src/finam_core/runtime/__pycache__/runtime_strategy_selection_provider.cpython-313.pyc
src/finam_core/runtime/__pycache__/runtime_strategy_selection_repository.cpython-313.pyc
src/finam_core/runtime/__pycache__/runtime_strategy_selector.cpython-313.pyc
src/finam_core/runtime/__pycache__/runtime_subprocess_worker.cpython-313.pyc
src/finam_core/runtime/__pycache__/runtime_telemetry.cpython-313.pyc
src/finam_core/runtime/__pycache__/runtime_universe_allocator.cpython-313.pyc
src/finam_core/runtime/__pycache__/runtime_universe_rotation_logger.cpython-313.pyc
src/finam_core/runtime/__pycache__/signal_lifecycle_engine.cpython-313.pyc
src/finam_core/runtime/__pycache__/signal_probability_estimator.cpython-313.pyc
src/finam_core/runtime/__pycache__/strategy_lifecycle_repository.cpython-313.pyc
src/finam_core/runtime/__pycache__/strategy_lifecycle_state_machine.cpython-313.pyc
src/finam_core/runtime/__pycache__/strategy_promotion_engine_repository.cpython-313.pyc
src/finam_core/runtime/__pycache__/strategy_promotion_engine_v1.cpython-313.pyc
src/finam_core/runtime/__pycache__/strategy_promotion_feed.cpython-313.pyc
src/finam_core/runtime/__pycache__/strategy_promotion_feed_repository.cpython-313.pyc
src/finam_core/runtime/__pycache__/strategy_runtime_control_service.cpython-313.pyc
src/finam_core/runtime/__pycache__/trade_gate_service.cpython-313.pyc
src/finam_core/runtime/__pycache__/trend_gate_service.cpython-313.pyc
src/finam_core/runtime/regime_matrix_modifier.py
src/finam_core/runtime/regime_runtime_control_service.py
src/finam_core/runtime/regime_runtime_override.py
src/finam_core/runtime/regime_runtime_override_repository.py
src/finam_core/runtime/risk_per_trade_sizing.py
src/finam_core/runtime/runtime_active_strategy_provider.py
src/finam_core/runtime/runtime_adaptive_risk.py
src/finam_core/runtime/runtime_allocator_decision_logger.py
src/finam_core/runtime/runtime_capital_allocator.py
src/finam_core/runtime/runtime_decision_digest.py
src/finam_core/runtime/runtime_execution_engine.py
src/finam_core/runtime/runtime_execution_sizer.py
src/finam_core/runtime/runtime_governance_coordinator.py
src/finam_core/runtime/runtime_governance_coordinator_v2.py
src/finam_core/runtime/runtime_governance_engine.py
src/finam_core/runtime/runtime_governance_telemetry.py
src/finam_core/runtime/runtime_policy_mode_resolver.py
src/finam_core/runtime/runtime_rebalance_cycle.py
src/finam_core/runtime/runtime_state_gate.py
src/finam_core/runtime/runtime_state.py
src/finam_core/runtime/runtime_strategy_cooldown_builder.py
src/finam_core/runtime/runtime_strategy_cooldown_provider.py
src/finam_core/runtime/runtime_strategy_gate_provider.py
src/finam_core/runtime/runtime_strategy_selection_provider.py
src/finam_core/runtime/runtime_strategy_selection_repository.py
src/finam_core/runtime/runtime_strategy_selector.py
src/finam_core/runtime/runtime_subprocess_worker.py
src/finam_core/runtime/runtime_telemetry.py
src/finam_core/runtime/runtime_universe_allocator.py
src/finam_core/runtime/runtime_universe_rotation_logger.py
src/finam_core/runtime/signal_lifecycle_engine.py
src/finam_core/runtime/signal_probability_estimator.py
src/finam_core/runtime/strategy_lifecycle_repository.py
src/finam_core/runtime/strategy_lifecycle_state_machine.py
src/finam_core/runtime/strategy_promotion_engine_repository.py
src/finam_core/runtime/strategy_promotion_engine_v1.py
src/finam_core/runtime/strategy_promotion_feed.py
src/finam_core/runtime/strategy_promotion_feed_repository.py
src/finam_core/runtime/strategy_runtime_control_service.py
src/finam_core/runtime/trade_gate_service.py
src/finam_core/runtime/trend_gate_service.py

## PostgreSQL tables declared in code
scripts/audit_project_gap_analysis.sh:24:  grep -R --exclude-dir='__pycache__' "CREATE TABLE IF NOT EXISTS" -n src scripts | sort
scripts/audit_project_inventory.sh:9:grep -R --exclude-dir='__pycache__' "CREATE TABLE IF NOT EXISTS" -n src scripts | sort \
scripts/create_closed_trades_table.sh:5:CREATE TABLE IF NOT EXISTS closed_trades (
scripts/create_manual_broker_position_snapshots.sh:5:CREATE TABLE IF NOT EXISTS manual_broker_position_snapshots (
scripts/create_order_events.sql:1:CREATE TABLE IF NOT EXISTS order_events (
scripts/create_position_intents.sql:12:CREATE TABLE IF NOT EXISTS position_intent_history (
scripts/create_position_intents.sql:1:CREATE TABLE IF NOT EXISTS position_intents (
scripts/create_position_lifecycle_reconcile_events.sh:5:CREATE TABLE IF NOT EXISTS position_lifecycle_reconcile_events (
scripts/create_position_lifecycle_state_table.sh:8:CREATE TABLE IF NOT EXISTS position_lifecycle_state (
scripts/create_profit_lock_events.sh:5:CREATE TABLE IF NOT EXISTS profit_lock_events (
scripts/create_runtime_alert_dedup.sh:5:CREATE TABLE IF NOT EXISTS runtime_alert_dedup (
scripts/create_signal_tables.sh:40:CREATE TABLE IF NOT EXISTS signal_fills (
scripts/create_signal_tables.sh:57:CREATE TABLE IF NOT EXISTS closed_trades (
scripts/create_signal_tables.sh:5:CREATE TABLE IF NOT EXISTS signals (
scripts/create_strategy_performance_history.sh:5:CREATE TABLE IF NOT EXISTS strategy_performance_history (
scripts/create_strategy_runtime_control.sh:5:CREATE TABLE IF NOT EXISTS strategy_runtime_control (
scripts/create_take_profit_events.sh:5:CREATE TABLE IF NOT EXISTS take_profit_events (
scripts/create_trailing_order_events.sh:5:CREATE TABLE IF NOT EXISTS trailing_order_events (
scripts/migrate_ai_sentiment_events.sh:13:CREATE TABLE IF NOT EXISTS ai_sentiment_events (
scripts/migrate_closed_trades_v1.sh:5:CREATE TABLE IF NOT EXISTS closed_trades (
scripts/migrate_feature_snapshots_v1.sh:5:CREATE TABLE IF NOT EXISTS feature_snapshots (
scripts/migrate_intermarket_regime_v1.sh:5:CREATE TABLE IF NOT EXISTS intermarket_regime_snapshots (
scripts/migrate_regime_runtime_overrides_v3.sh:5:CREATE TABLE IF NOT EXISTS runtime_regime_overrides (
scripts/migrate_research_layer_v1.sh:5:CREATE TABLE IF NOT EXISTS strategy_research_results (
scripts/migrate_runtime_config_v1.sh:5:CREATE TABLE IF NOT EXISTS runtime_config (
scripts/migrate_runtime_strategy_scores_v1.sh:5:CREATE TABLE IF NOT EXISTS runtime_strategy_scores (
scripts/migrate_selection_layer_v1.sh:5:CREATE TABLE IF NOT EXISTS strategy_selection_state (
scripts/migrate_strategy_regime_matrix_v1.sh:5:CREATE TABLE IF NOT EXISTS strategy_regime_matrix (
scripts/migrate_strategy_regime_performance_v1.sh:5:CREATE TABLE IF NOT EXISTS strategy_regime_performance (
scripts/test_broker_order_snapshot_store.sh:9:grep -q "CREATE TABLE IF NOT EXISTS broker_order_snapshots" sql/20260511_broker_order_snapshots.sql
scripts/test_order_ack_logger.sh:9:grep -q "CREATE TABLE IF NOT EXISTS order_acks" sql/20260511_order_acks.sql
scripts/test_order_reconciliation_logger.sh:10:grep -q "CREATE TABLE IF NOT EXISTS order_reconciliation_issues" sql/20260511_order_reconciliation_runs.sql
scripts/test_order_reconciliation_logger.sh:9:grep -q "CREATE TABLE IF NOT EXISTS order_reconciliation_runs" sql/20260511_order_reconciliation_runs.sql
scripts/test_protective_order_link.sh:10:grep -q "CREATE TABLE IF NOT EXISTS protective_order_links" sql/20260511_protective_order_links.sql
src/finam_core/analytics/closed_trade_reconstruction_v2_repository.py:23:        CREATE TABLE IF NOT EXISTS closed_trade_chains_v2 (
src/finam_core/analytics/exit_optimization_repository.py:16:        CREATE TABLE IF NOT EXISTS analytics_exit_optimization (
src/finam_core/analytics/exit_policy_repository.py:17:        CREATE TABLE IF NOT EXISTS analytics_exit_policy_simulation (
src/finam_core/analytics/exit_policy_selector.py:11:        CREATE TABLE IF NOT EXISTS analytics_exit_policy_selected (
src/finam_core/analytics/intrabar_repository.py:21:        CREATE TABLE IF NOT EXISTS analytics_intrabar_trade_quality (
src/finam_core/analytics/regime_snapshot_repository.py:20:        CREATE TABLE IF NOT EXISTS regime_snapshots (
src/finam_core/analytics/research_pipeline_run_log.py:23:        CREATE TABLE IF NOT EXISTS research_pipeline_runs (
src/finam_core/analytics/research_pipeline_run_log.py:35:        CREATE TABLE IF NOT EXISTS research_pipeline_step_events (
src/finam_core/analytics/statistics_repository.py:206:        CREATE TABLE IF NOT EXISTS analytics_equity_curve (
src/finam_core/analytics/statistics_repository.py:281:        CREATE TABLE IF NOT EXISTS analytics_drawdown_summary (
src/finam_core/analytics/statistics_repository.py:317:        CREATE TABLE IF NOT EXISTS analytics_trade_quality (
src/finam_core/analytics/statistics_repository.py:41:        CREATE TABLE IF NOT EXISTS analytics_trade_statistics (
src/finam_core/analytics/strategy_ranking_v2_repository.py:18:        CREATE TABLE IF NOT EXISTS strategy_ranking_v2 (
src/finam_core/analytics/strategy_statistics_v2_repository.py:18:        CREATE TABLE IF NOT EXISTS strategy_statistics_v2 (
src/finam_core/analytics/trade_attribution_v2_repository.py:22:        CREATE TABLE IF NOT EXISTS trade_attribution_v2 (
src/finam_core/analytics/trade_context_snapshot_repository.py:28:        CREATE TABLE IF NOT EXISTS trade_context_snapshots (
src/finam_core/analytics/trade_exit_policy_repository.py:20:        CREATE TABLE IF NOT EXISTS trade_exit_policy_context (
src/finam_core/analytics/trade_fill_quality_audit_repository.py:18:        CREATE TABLE IF NOT EXISTS trade_fill_quality_audit (
src/finam_core/analytics/trade_risk_context_repository.py:20:        CREATE TABLE IF NOT EXISTS trade_risk_context (
src/finam_core/data/instrument_reference_seed.py:34:                CREATE TABLE IF NOT EXISTS instrument_reference (
src/finam_core/manual/broker_manual_trade_sync.py:18:        CREATE TABLE IF NOT EXISTS manual_trade_journal (
src/finam_core/manual/manual_trade_journal.py:39:        CREATE TABLE IF NOT EXISTS manual_trade_journal (
src/finam_core/notifications/telegram_alert_deduplication.py:28:        CREATE TABLE IF NOT EXISTS telegram_alert_state (
src/finam_core/pipelines/paper_pipeline.py:894:                        CREATE TABLE IF NOT EXISTS portfolio_pnl_events (
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:614:                        CREATE TABLE IF NOT EXISTS portfolio_pnl_events (
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:617:                        CREATE TABLE IF NOT EXISTS portfolio_pnl_events (
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:622:                        CREATE TABLE IF NOT EXISTS portfolio_pnl_events (
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:628:                        CREATE TABLE IF NOT EXISTS portfolio_pnl_events (
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:614:                        CREATE TABLE IF NOT EXISTS portfolio_pnl_events (
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:614:                        CREATE TABLE IF NOT EXISTS portfolio_pnl_events (
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:614:                        CREATE TABLE IF NOT EXISTS portfolio_pnl_events (
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:614:                        CREATE TABLE IF NOT EXISTS portfolio_pnl_events (
src/finam_core/portfolio/lifecycle_stale_position_repository.py:16:        CREATE TABLE IF NOT EXISTS lifecycle_stale_position_advice_events (
src/finam_core/portfolio/portfolio_heat_repository.py:20:        CREATE TABLE IF NOT EXISTS portfolio_heat_events (
src/finam_core/portfolio/position_state_reconciliation_repository.py:25:        CREATE TABLE IF NOT EXISTS position_state_reconciliation_events (
src/finam_core/research/futures_context_normalizer.py:20:        CREATE TABLE IF NOT EXISTS futures_context_snapshots (
src/finam_core/research/futures_contract_universe_repository.py:15:        CREATE TABLE IF NOT EXISTS futures_contract_universe (
src/finam_core/research/futures_mtf_regime_aggregator.py:37:        CREATE TABLE IF NOT EXISTS futures_mtf_regime (
src/finam_core/research/futures_regime_governance_repository.py:19:        CREATE TABLE IF NOT EXISTS futures_regime_governance (
src/finam_core/research/research_runtime_state_repository.py:19:        CREATE TABLE IF NOT EXISTS research_runtime_state (
src/finam_core/research/research_runtime_state_repository.py:31:        CREATE TABLE IF NOT EXISTS research_runtime_cycle_log (
src/finam_core/runtime/portfolio_governance_repository.py:19:        CREATE TABLE IF NOT EXISTS portfolio_governance_events (
src/finam_core/runtime/runtime_strategy_selection_repository.py:34:        CREATE TABLE IF NOT EXISTS runtime_strategy_selection (
src/finam_core/runtime/strategy_lifecycle_repository.py:14:        CREATE TABLE IF NOT EXISTS strategy_lifecycle_state (
src/finam_core/runtime/strategy_promotion_engine_repository.py:18:        CREATE TABLE IF NOT EXISTS strategy_promotion_decisions (
src/finam_core/runtime/strategy_promotion_feed_repository.py:14:        CREATE TABLE IF NOT EXISTS strategy_promotion_runtime_feed (
src/finam_core/storage/bars_sqlite_storage.py:85:            CREATE TABLE IF NOT EXISTS bars (
src/finam_core/storage/managed_position_repository.py:26:        CREATE TABLE IF NOT EXISTS managed_positions (
src/finam_core/storage/migrations.sql:111:CREATE TABLE IF NOT EXISTS fills (
src/finam_core/storage/migrations.sql:133:CREATE TABLE IF NOT EXISTS positions (
src/finam_core/storage/migrations.sql:144:CREATE TABLE IF NOT EXISTS positions_history (
src/finam_core/storage/migrations.sql:161:CREATE TABLE IF NOT EXISTS portfolio_snapshots (
src/finam_core/storage/migrations.sql:177:CREATE TABLE IF NOT EXISTS risk_events (
src/finam_core/storage/migrations.sql:17:CREATE TABLE IF NOT EXISTS market_data (
src/finam_core/storage/migrations.sql:196:CREATE TABLE IF NOT EXISTS engine_metrics (
src/finam_core/storage/migrations.sql:209:CREATE TABLE IF NOT EXISTS model_registry (
src/finam_core/storage/migrations.sql:222:CREATE TABLE IF NOT EXISTS inference_log (
src/finam_core/storage/migrations.sql:238:CREATE TABLE IF NOT EXISTS trades (
src/finam_core/storage/migrations.sql:253:CREATE TABLE IF NOT EXISTS transactions (
src/finam_core/storage/migrations.sql:262:CREATE TABLE IF NOT EXISTS stream_snapshots (
src/finam_core/storage/migrations.sql:281:CREATE TABLE IF NOT EXISTS events (
src/finam_core/storage/migrations.sql:37:CREATE TABLE IF NOT EXISTS market_ticks (
src/finam_core/storage/migrations.sql:51:CREATE TABLE IF NOT EXISTS signals (
src/finam_core/storage/migrations.sql:71:CREATE TABLE IF NOT EXISTS signal_features (
src/finam_core/storage/migrations.sql:86:CREATE TABLE IF NOT EXISTS orders (
src/finam_core/storage/real_position_snapshot_repository.py:23:        CREATE TABLE IF NOT EXISTS real_position_snapshots (
src/finam_core/storage/sqlite_storage.py:15:            CREATE TABLE IF NOT EXISTS fills (
src/scripts/backfill_futures_market_bars.py:54:                CREATE TABLE IF NOT EXISTS market_bars (
src/scripts/backtest_runner.py:60:        CREATE TABLE IF NOT EXISTS backtest_runs (
src/scripts/backtest_runner.py:87:        CREATE TABLE IF NOT EXISTS backtest_trades (
src/scripts/build_best_exit_alpha_policy.py:23:                CREATE TABLE IF NOT EXISTS strategy_best_exit_alpha_policy (
src/scripts/build_exit_alpha_policy.py:14:                CREATE TABLE IF NOT EXISTS strategy_exit_alpha_policy (
src/scripts/build_futures_session_analytics.py:18:                CREATE TABLE IF NOT EXISTS futures_session_trade_analytics (
src/scripts/build_market_bar_coverage_audit.py:38:                CREATE TABLE IF NOT EXISTS strategy_market_bar_coverage (
src/scripts/build_market_radar_candidates.py:126:                CREATE TABLE IF NOT EXISTS market_radar_candidates (
src/scripts/build_ng_active_edge_resolver.py:18:                CREATE TABLE IF NOT EXISTS ng_active_edge_state (
src/scripts/build_ng_live_runtime_state.py:22:                CREATE TABLE IF NOT EXISTS ng_live_runtime_state (
src/scripts/build_ng_m1_runtime_policy.py:22:                CREATE TABLE IF NOT EXISTS ng_m1_runtime_policy (
src/scripts/build_ng_m1_session_regime_matrix.py:24:                CREATE TABLE IF NOT EXISTS ng_m1_session_regime_matrix (
src/scripts/build_ng_regime_v2_analytics.py:25:                CREATE TABLE IF NOT EXISTS ng_regime_v2_trade_analytics (
src/scripts/build_ng_runtime_telemetry.py:18:                CREATE TABLE IF NOT EXISTS ng_runtime_telemetry (
src/scripts/build_portfolio_risk_state.py:32:                CREATE TABLE IF NOT EXISTS portfolio_risk_state (
src/scripts/build_runtime_governance_decisions.py:23:                CREATE TABLE IF NOT EXISTS runtime_governance_decisions (
src/scripts/build_trade_timestamp_normalizer.py:46:                CREATE TABLE IF NOT EXISTS trade_timestamp_normalization_audit (
src/scripts/collect_runtime_observations.py:12:                CREATE TABLE IF NOT EXISTS runtime_observations (
src/scripts/find_market_bar_gaps.py:36:                CREATE TABLE IF NOT EXISTS market_bar_gaps (
src/scripts/ingestion/backfill_finam_futures_market_bars.py:50:                CREATE TABLE IF NOT EXISTS market_bars (
src/scripts/replay_exit_alpha_policy_bar_by_bar.py:33:                CREATE TABLE IF NOT EXISTS strategy_exit_alpha_bar_replay (
src/scripts/replay_exit_alpha_policy.py:14:                CREATE TABLE IF NOT EXISTS strategy_exit_alpha_replay (
src/scripts/replay_ng_conservative_breakout_m1.py:41:        CREATE TABLE IF NOT EXISTS trades (
src/scripts/replay/replay_ng_conservative_breakout.py:41:        CREATE TABLE IF NOT EXISTS trades (
src/scripts/research/build_ng_regime_analytics.py:30:                CREATE TABLE IF NOT EXISTS ng_regime_trade_analytics (
src/scripts/research/build_ng_runtime_regime_policy.py:19:                CREATE TABLE IF NOT EXISTS ng_runtime_regime_policy (
src/scripts/research/build_ng_runtime_regime_policy_v2.py:22:                CREATE TABLE IF NOT EXISTS ng_runtime_regime_policy_v2 (
src/scripts/research/build_ng_session_regime_matrix.py:24:                CREATE TABLE IF NOT EXISTS ng_session_regime_matrix (
src/scripts/research/build_strategy_event_risk_context.py:22:                CREATE TABLE IF NOT EXISTS market_event_calendar (
src/scripts/research/build_strategy_event_risk_context.py:35:                CREATE TABLE IF NOT EXISTS strategy_event_risk_context (
src/scripts/research/materialize_market_event_templates.py:16:                CREATE TABLE IF NOT EXISTS market_event_templates (
src/scripts/run_exit_alpha_parameter_grid.py:34:                CREATE TABLE IF NOT EXISTS strategy_exit_alpha_grid_results (
src/scripts/runtime/build_runtime_capital_allocator.py:23:                CREATE TABLE IF NOT EXISTS runtime_capital_allocator (
src/scripts/runtime/build_runtime_rolling_strategy_stats.py:20:                CREATE TABLE IF NOT EXISTS runtime_rolling_strategy_stats (
src/scripts/runtime/build_session_runtime_policy.py:19:                CREATE TABLE IF NOT EXISTS session_runtime_policy (
src/scripts/sync_best_exit_alpha_to_radar.py:12:                CREATE TABLE IF NOT EXISTS strategy_exit_alpha_radar (
src/scripts/sync_runtime_active_universe_from_strategy_selection.py:9:    CREATE TABLE IF NOT EXISTS runtime_active_universe (
src/storage/migrations.sql:111:CREATE TABLE IF NOT EXISTS fills (
src/storage/migrations.sql:133:CREATE TABLE IF NOT EXISTS positions (
src/storage/migrations.sql:144:CREATE TABLE IF NOT EXISTS positions_history (
src/storage/migrations.sql:161:CREATE TABLE IF NOT EXISTS portfolio_snapshots (
src/storage/migrations.sql:177:CREATE TABLE IF NOT EXISTS risk_events (
src/storage/migrations.sql:17:CREATE TABLE IF NOT EXISTS market_data (
src/storage/migrations.sql:196:CREATE TABLE IF NOT EXISTS engine_metrics (
src/storage/migrations.sql:209:CREATE TABLE IF NOT EXISTS model_registry (
src/storage/migrations.sql:222:CREATE TABLE IF NOT EXISTS inference_log (
src/storage/migrations.sql:238:CREATE TABLE IF NOT EXISTS trades (
src/storage/migrations.sql:253:CREATE TABLE IF NOT EXISTS transactions (
src/storage/migrations.sql:262:CREATE TABLE IF NOT EXISTS stream_snapshots (
src/storage/migrations.sql:281:CREATE TABLE IF NOT EXISTS events (
src/storage/migrations.sql:37:CREATE TABLE IF NOT EXISTS market_ticks (
src/storage/migrations.sql:51:CREATE TABLE IF NOT EXISTS signals (
src/storage/migrations.sql:71:CREATE TABLE IF NOT EXISTS signal_features (
src/storage/migrations.sql:86:CREATE TABLE IF NOT EXISTS orders (
src/storage/sqlite_storage.py:15:            CREATE TABLE IF NOT EXISTS fills (

## Repositories
src/finam_core/accounting/position_manager.py:57:        self.snapshot_repo = SnapshotRepository()
src/finam_core/adapters/grpc/orders_client.py:58:        self.protective_link_repository = ProtectiveOrderLinkRepository()
src/finam_core/ai/sentiment_event_repository.py:13:class SentimentEventRepository:
src/finam_core/ai/sentiment_feature_provider.py:45:        self.repository = repository or SentimentEventRepository()
src/finam_core/ai/telegram_bot_news_ingest.py:54:        self.repository = SentimentEventRepository()
src/finam_core/ai/telethon_news_ingest.py:87:        self.repository = SentimentEventRepository()
src/finam_core/analytics/closed_trade_reconstruction_v2_repository.py:12:class ClosedTradeReconstructionV2Repository:
src/finam_core/analytics/closed_trade_repository.py:12:class ClosedTradeRepository:
src/finam_core/analytics/exit_optimization_repository.py:13:class ExitOptimizationRepository(StatisticsRepository):
src/finam_core/analytics/exit_policy_repository.py:14:class ExitPolicySimulationRepository(StatisticsRepository):
src/finam_core/analytics/exit_policy_selector.py:8:class ExitPolicySelector(StatisticsRepository):
src/finam_core/analytics/fee_calculator.py:21:        self.repository = repository or FeeProfileRepository()
src/finam_core/analytics/intrabar_repository.py:18:class IntrabarAnalyticsRepository(StatisticsRepository):
src/finam_core/analytics/regime_snapshot_repository.py:8:class RegimeSnapshotRepository:
src/finam_core/analytics/signal_repository.py:19:class SignalRepository:
src/finam_core/analytics/statistics_repository.py:35:class StatisticsRepository:
src/finam_core/analytics/strategy_ranking_v2_repository.py:12:class StrategyRankingV2Repository:
src/finam_core/analytics/strategy_statistics_v2_repository.py:12:class StrategyStatisticsV2Repository:
src/finam_core/analytics/trade_attribution_v2_repository.py:11:class TradeAttributionV2Repository:
src/finam_core/analytics/trade_context_snapshot_repository.py:16:class TradeContextSnapshotRepository:
src/finam_core/analytics/trade_exit_policy_repository.py:8:class TradeExitPolicyRepository:
src/finam_core/analytics/trade_fill_quality_audit_repository.py:12:class TradeFillQualityAuditRepository:
src/finam_core/analytics/trade_risk_context_repository.py:8:class TradeRiskContextRepository:
src/finam_core/data/radar_persistence_repository.py:10:class RadarPersistenceRepository:
src/finam_core/data/repository.py:1:class MarketBarRepository:
src/finam_core/execution/managed_position_service.py:15:        self.repository = repository or ManagedPositionRepository()
src/finam_core/execution/position_lifecycle_reconcile_event_repository.py:10:class PositionLifecycleReconcileEventRepository:
src/finam_core/execution/position_lifecycle_state_repository.py:10:class PositionLifecycleStateRepository:
src/finam_core/execution/profit_lock_event_repository.py:10:class ProfitLockEventRepository:
src/finam_core/execution/protective_duplicate_gate.py:19:        self.repository = repository or ProtectiveOrderLinkRepository()
src/finam_core/execution/protective_order_link_repository.py:16:class ProtectiveOrderLinkRepository:
src/finam_core/execution/take_profit_event_repository.py:10:class TakeProfitEventRepository:
src/finam_core/execution/trailing_order_event_repository.py:10:class TrailingOrderEventRepository:
src/finam_core/instruments/instrument_spec_registry.py:36:        self.repository = repository or InstrumentSpecRepository()
src/finam_core/orderflow/smart_money_feature_repository.py:9:class SmartMoneyFeatureRepository:
src/finam_core/pipelines/paper_pipeline.py:2716:                repo = SmartMoneyFeatureRepository(getattr(self, "pg_logger", None))
src/finam_core/pipelines/paper_pipeline.py:311:                link_repository=ProtectiveOrderLinkRepository(),
src/finam_core/pipelines/paper_pipeline.py:319:        self.position_lifecycle_state_repository = PositionLifecycleStateRepository()
src/finam_core/pipelines/paper_pipeline.py:321:        self.position_lifecycle_reconcile_event_repository = PositionLifecycleReconcileEventRepository()
src/finam_core/pipelines/paper_pipeline.py:325:        self.take_profit_event_repository = TakeProfitEventRepository()
src/finam_core/pipelines/paper_pipeline.py:326:        self.profit_lock_event_repository = ProfitLockEventRepository()
src/finam_core/pipelines/paper_pipeline.py:345:        self.trailing_order_event_repository = TrailingOrderEventRepository()
src/finam_core/pipelines/paper_pipeline.py:367:        self.position_intent_repo = PositionIntentRepository(
src/finam_core/pipelines/paper_pipeline.py:427:                self.signal_repository = SignalRepository(conn)
src/finam_core/pipelines/paper_pipeline.py:4935:                event_repo = MarketEventCalendarRepository(getattr(self, "pg_logger", None))
src/finam_core/pipelines/paper_pipeline.py:5045:                repo = AdaptiveRegimeRepository(getattr(self, "pg_logger", None))
src/finam_core/pipelines/paper_pipeline.py:5958:            override = RuntimeRegimeOverrideRepository(database_url).get_override(
src/finam_core/pipelines/paper_pipeline.py:6636:        repo = PortfolioGovernanceRepository(database_url)
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:227:        self.position_intent_repo = PositionIntentRepository(
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:239:            self.signal_repository = SignalRepository(self.pg_logger.conn)
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:208:        self.trailing_order_event_repository = TrailingOrderEventRepository()
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:230:        self.position_intent_repo = PositionIntentRepository(
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:242:            self.signal_repository = SignalRepository(self.pg_logger.conn)
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:213:        self.trailing_order_event_repository = TrailingOrderEventRepository()
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:235:        self.position_intent_repo = PositionIntentRepository(
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:247:            self.signal_repository = SignalRepository(self.pg_logger.conn)
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:216:        self.take_profit_event_repository = TakeProfitEventRepository()
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:217:        self.profit_lock_event_repository = ProfitLockEventRepository()
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:219:        self.trailing_order_event_repository = TrailingOrderEventRepository()
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:241:        self.position_intent_repo = PositionIntentRepository(
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:253:            self.signal_repository = SignalRepository(self.pg_logger.conn)
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:227:        self.position_intent_repo = PositionIntentRepository(
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:239:            self.signal_repository = SignalRepository(self.pg_logger.conn)
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:227:        self.position_intent_repo = PositionIntentRepository(
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:239:            self.signal_repository = SignalRepository(self.pg_logger.conn)
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:227:        self.position_intent_repo = PositionIntentRepository(
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:239:            self.signal_repository = SignalRepository(self.pg_logger.conn)
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:227:        self.position_intent_repo = PositionIntentRepository(
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:239:            self.signal_repository = SignalRepository(self.pg_logger.conn)
src/finam_core/portfolio/lifecycle_stale_position_repository.py:10:class LifecycleStalePositionRepository:
src/finam_core/portfolio/portfolio_heat_repository.py:8:class PortfolioHeatRepository:
src/finam_core/portfolio/portfolio_intelligence_repository.py:12:class PortfolioIntelligenceRepository:
src/finam_core/portfolio/position_intent_repository.py:28:class PositionIntentRepository:
src/finam_core/portfolio/position_state_reconciliation_repository.py:14:class PositionStateReconciliationRepository:
src/finam_core/reconciliation/manual_position_snapshot_repository.py:11:class ManualPositionSnapshotRepository:
src/finam_core/reconciliation/order_ack_repository.py:14:class OrderAckRepository:
src/finam_core/reconciliation/protective_order_recovery_check.py:21:        self.repository = repository or ProtectiveOrderLinkRepository()
src/finam_core/recovery/recovery_orchestrator.py:16:class _EmptyRepository:
src/finam_core/recovery/recovery_orchestrator.py:27:        self.repository = _EmptyRepository()
src/finam_core/research/futures_contract_universe_repository.py:7:class FuturesContractUniverseRepository:
src/finam_core/research/futures_regime_engine.py:123:        repo = RegimeSnapshotRepository(self.dsn)
src/finam_core/research/futures_regime_governance_repository.py:7:class FuturesRegimeGovernanceRepository:
src/finam_core/research/policy_decision_repository.py:7:class PolicyDecisionRepository:
src/finam_core/research/policy_impact_repository.py:7:class PolicyImpactRepository:
src/finam_core/research/regime_policy_repository.py:10:class RegimePolicyRepository:
src/finam_core/research/research_repository.py:19:class ResearchRepository:
src/finam_core/research/research_runner.py:29:    repo = ResearchRepository()
src/finam_core/research/research_runtime_state_repository.py:8:class ResearchRuntimeStateRepository:
src/finam_core/research/research_runtime_supervisor.py:37:        self.repository = repository or ResearchRuntimeStateRepository()
src/finam_core/risk/adaptive_regime_repository.py:55:class AdaptiveRegimeRepository:
src/finam_core/risk/margin_calculator.py:24:        self.repository = repository or MarginRequirementRepository()
src/finam_core/risk/market_event_calendar_repository.py:17:class MarketEventCalendarRepository:
src/finam_core/runtime/portfolio_governance_repository.py:8:class PortfolioGovernanceRepository:
src/finam_core/runtime/regime_runtime_override_repository.py:22:class RuntimeRegimeOverrideRepository:
src/finam_core/runtime/runtime_strategy_selection_repository.py:22:class RuntimeStrategySelectionRepository:
src/finam_core/runtime/strategy_lifecycle_repository.py:8:class StrategyLifecycleRepository:
src/finam_core/runtime/strategy_promotion_engine_repository.py:12:class StrategyPromotionEngineRepository:
src/finam_core/runtime/strategy_promotion_feed_repository.py:8:class StrategyPromotionFeedRepository:
src/finam_core/scripts/test_ingest_bars.py:142:    sync_repo = MarketSyncRepository(storage)
src/finam_core/scripts/test_ingest_bars.py:42:sync_repo = MarketSyncRepository(storage)
src/finam_core/scripts/test_ingest_bars.py:43:repo = MarketBarRepository(storage)
src/finam_core/scripts/test_ingest_bars.py:68:sync_repo = MarketSyncRepository(storage)
src/finam_core/simulation/signal_trade_runtime.py:32:        self.trade_repo = VirtualSignalTradeRepository()
src/finam_core/storage/daily_risk_repository.py:9:class DailyRiskRepository:
src/finam_core/storage/dynamic_watchlist_repository.py:8:class DynamicWatchlistRepository:
src/finam_core/storage/fee_profile_repository.py:11:class FeeProfileRepository:
src/finam_core/storage/instrument_spec_repository.py:10:class InstrumentSpecRepository:
src/finam_core/storage/managed_position_repository.py:12:class ManagedPositionRepository:
src/finam_core/storage/margin_requirement_repository.py:11:class MarginRequirementRepository:
src/finam_core/storage/market_bar_repository.py:6:class MarketBarRepository:
src/finam_core/storage/market_sync_repository.py:7:class MarketSyncRepository:
src/finam_core/storage/real_position_snapshot_repository.py:9:class RealPositionSnapshotRepository:
src/finam_core/storage/snapshot_repository.py:13:class SnapshotRepository:
src/finam_core/storage/virtual_signal_trade_repository.py:10:class VirtualSignalTradeRepository:
src/scripts/build_closed_trade_reconstruction_v2.py:22:    audit_repo = TradeFillQualityAuditRepository(database_url)
src/scripts/build_closed_trade_reconstruction_v2.py:41:    repo = ClosedTradeReconstructionV2Repository(database_url)
src/scripts/build_futures_regime_governance.py:9:    repo = FuturesRegimeGovernanceRepository()
src/scripts/build_lifecycle_stale_position_advice.py:73:        repo = LifecycleStalePositionRepository(database_url)
src/scripts/build_portfolio_governance_event.py:31:        repo = PortfolioGovernanceRepository(database_url)
src/scripts/build_portfolio_heat.py:21:    repo = PortfolioIntelligenceRepository(database_url)
src/scripts/build_portfolio_heat.py:29:        heat_repo = PortfolioHeatRepository(database_url)
src/scripts/build_portfolio_intelligence_snapshot.py:17:    repo = PortfolioIntelligenceRepository(build_psycopg_url())
src/scripts/build_position_state_reconciliation.py:18:    repo = PositionStateReconciliationRepository(build_psycopg_url())
src/scripts/build_regime_risk_policy.py:111:            saved = RegimePolicyRepository(conn).save_policy(
src/scripts/build_regime_snapshots.py:21:    repo = RegimeSnapshotRepository()
src/scripts/build_replay_closed_trades.py:48:        saved = ClosedTradeRepository(conn).save_closed_trades(closed, trade_source="paper")
src/scripts/build_strategy_lifecycle_state.py:73:        repo = StrategyLifecycleRepository(database_url)
src/scripts/build_strategy_promotion_engine_v1.py:20:    repo = StrategyPromotionEngineRepository(build_psycopg_url())
src/scripts/build_strategy_promotion_feed.py:62:        feed_repo = StrategyPromotionFeedRepository(build_psycopg_url())
src/scripts/build_strategy_ranking_v2.py:17:    repo = StrategyRankingV2Repository(build_psycopg_url())
src/scripts/build_strategy_statistics_v2.py:18:    repo = StrategyStatisticsV2Repository(build_psycopg_url())
src/scripts/build_trade_attribution_v2.py:19:    repo = TradeAttributionV2Repository(build_psycopg_url())
src/scripts/build_trade_context_snapshots.py:19:    repo = TradeContextSnapshotRepository(build_psycopg_url())
src/scripts/build_trade_exit_policy_context.py:18:    repo = TradeExitPolicyRepository()
src/scripts/build_trade_fill_quality_audit.py:19:    repo = TradeFillQualityAuditRepository(build_psycopg_url())
src/scripts/build_trade_risk_context.py:18:    repo = TradeRiskContextRepository()
src/scripts/close_virtual_futures_trade.py:18:    repo = VirtualSignalTradeRepository()
src/scripts/place_protective_for_filled_entries.py:165:                ProtectiveOrderLinkRepository().mark_manual_protection_required(
src/scripts/reconcile_order_acks.py:64:    acks = OrderAckRepository().list_recent(limit=limit)
src/scripts/resolve_futures_active_contracts.py:17:    repo = FuturesContractUniverseRepository()
src/scripts/rotate_active_policy.py:120:        saved = PolicyDecisionRepository(conn).save_decision(
src/scripts/run_closed_trade_report.py:101:    repo = ClosedTradeRepository(conn)
src/scripts/run_daily_risk_check.py:12:    repo = DailyRiskRepository()
src/scripts/run_manual_trade_reconciliation.py:77:    repo = ManualPositionSnapshotRepository(conn)
src/scripts/run_market_radar.py:276:    persistence = RadarPersistenceRepository().load_persistence(hours=4)
src/scripts/run_market_radar.py:287:        watchlist_saved = DynamicWatchlistRepository().replace_watchlist(clean_rows[: args.top_n])
src/scripts/run_research_runtime_supervisor.py:19:    repo = FuturesContractUniverseRepository()
src/scripts/runtime/build_runtime_strategy_selection.py:53:    repo = RuntimeStrategySelectionRepository()
src/scripts/save_policy_decision.py:96:        saved = PolicyDecisionRepository(conn).save_decision(
src/scripts/save_policy_impact_report.py:63:        saved = PolicyImpactRepository(conn).save(
src/scripts/seed_futures_contract_universe.py:9:    repo = FuturesContractUniverseRepository()
src/scripts/seed_futures_regime_snapshots.py:19:    regime_repo = RegimeSnapshotRepository()
src/scripts/send_watchlist_telegram.py:9:    repo = DynamicWatchlistRepository()
src/scripts/sync_finam_real_positions.py:24:    saved = RealPositionSnapshotRepository().save_positions(positions)
src/scripts/test_ingest_bars.py:142:    sync_repo = MarketSyncRepository(storage)
src/scripts/test_ingest_bars.py:42:sync_repo = MarketSyncRepository(storage)
src/scripts/test_ingest_bars.py:43:repo = MarketBarRepository(storage)
src/scripts/test_ingest_bars.py:68:sync_repo = MarketSyncRepository(storage)

## RuntimeConfig usage
scripts/audit_project_gap_analysis.sh:31:  echo "## RuntimeConfig usage"
scripts/audit_project_gap_analysis.sh:32:  grep -R --exclude-dir='__pycache__' "RuntimeConfig\|runtime_config.get" -n src scripts | sort
scripts/test_marketdata_runtime_config_v1.sh:11:grep -R -q "RuntimeConfig" \
scripts/test_marketdata_runtime_config_v1.sh:15:grep -R -q 'runtime_config.get_float("MD_RECONNECT_INITIAL_SEC"' src
scripts/test_marketdata_runtime_config_v1.sh:16:grep -R -q 'runtime_config.get_float("MD_RECONNECT_MAX_SEC"' src
scripts/test_marketdata_runtime_config_v1.sh:17:grep -R -q 'runtime_config.get_float("MD_FIRST_QUOTE_GRACE_SEC"' src
scripts/test_marketdata_runtime_config_v1.sh:18:grep -R -q 'runtime_config.get("MD_WATCHDOG_MODE"' src
scripts/test_marketdata_runtime_config_v1.sh:19:grep -R -q 'runtime_config.get_bool("MD_DEBUG"' src
scripts/test_orders_client_runtime_config_safety.sh:10:grep -q "RuntimeConfig" src/finam_core/adapters/grpc/orders_client.py
scripts/test_orders_client_runtime_config_safety.sh:11:grep -q 'runtime_config.get("FINAM_TOKEN"' src/finam_core/adapters/grpc/orders_client.py
scripts/test_orders_client_runtime_config_safety.sh:12:grep -q 'runtime_config.get("FINAM_ACCOUNT_ID"' src/finam_core/adapters/grpc/orders_client.py
scripts/test_orders_client_runtime_config_safety.sh:13:grep -q 'runtime_config.get("FINAM_GRPC_ENDPOINT"' src/finam_core/adapters/grpc/orders_client.py
scripts/test_orders_client_runtime_config_safety.sh:14:grep -q 'runtime_config.get_bool("REAL_EXECUTION_ENABLED"' src/finam_core/adapters/grpc/orders_client.py
scripts/test_orders_client_runtime_config_safety.sh:15:grep -q 'runtime_config.get_bool("REAL_ORDER_CONFIRM"' src/finam_core/adapters/grpc/orders_client.py
scripts/test_paper_pipeline_runtime_config_v1.sh:10:grep -q "RuntimeConfig" \
scripts/test_paper_pipeline_runtime_config_v1.sh:13:grep -q 'runtime_config.get("EXECUTION_MODE"' \
scripts/test_paper_pipeline_runtime_config_v1.sh:16:grep -q 'runtime_config.get_bool("ENABLE_PAPER_FILLS"' \
scripts/test_paper_pipeline_runtime_config_v1.sh:19:grep -q 'runtime_config.get_bool("SIMULATE_MARKET"' \
scripts/test_runtime_config_v1.sh:10:from finam_core.config.runtime_config import RuntimeConfig
scripts/test_runtime_config_v1.sh:13:cfg = RuntimeConfig(database_url="")
scripts/test_runtime_config_v1.sh:23:grep -q "class RuntimeConfig" src/finam_core/config/runtime_config.py
src/finam_core/adapters/grpc/market_data.py:209:                    if self.runtime_config.get_bool("MD_DEBUG", False) and (now - self._wd_last_warn_ts) >= self._wd_warn_every_sec:
src/finam_core/adapters/grpc/market_data.py:20:from finam_core.config.runtime_config import RuntimeConfig
src/finam_core/adapters/grpc/market_data.py:257:                if self.runtime_config.get_bool("MD_DEBUG", False):
src/finam_core/adapters/grpc/market_data.py:269:                if self.runtime_config.get_bool("MD_DEBUG", False):
src/finam_core/adapters/grpc/market_data.py:318:            if self.runtime_config.get_bool("MD_DEBUG", False):
src/finam_core/adapters/grpc/market_data.py:327:            if self.runtime_config.get_bool("MD_DEBUG", False):
src/finam_core/adapters/grpc/market_data.py:366:                if self.runtime_config.get_bool("MD_DEBUG", False):
src/finam_core/adapters/grpc/market_data.py:369:                if self.runtime_config.get_bool("MD_DEBUG", False):
src/finam_core/adapters/grpc/market_data.py:49:        self.first_quote_grace_sec = float(self.runtime_config.get_float("MD_FIRST_QUOTE_GRACE_SEC", 60.0))
src/finam_core/adapters/grpc/market_data.py:54:        self.watchdog_mode = self.runtime_config.get("MD_WATCHDOG_MODE", "soft").strip().lower()
src/finam_core/adapters/grpc/market_data.py:80:        self.reconnect_initial_sec = float(self.runtime_config.get_float("MD_RECONNECT_INITIAL_SEC", 0.5))
src/finam_core/adapters/grpc/market_data.py:81:        self.reconnect_max_sec = float(self.runtime_config.get_float("MD_RECONNECT_MAX_SEC", 30.0))
src/finam_core/adapters/grpc/orders_client.py:45:        self.runtime_config = RuntimeConfig()
src/finam_core/adapters/grpc/orders_client.py:474:        if not self.runtime_config.get_bool("REAL_EXECUTION_ENABLED", False) or not self.runtime_config.get_bool("REAL_ORDER_CONFIRM", False):
src/finam_core/adapters/grpc/orders_client.py:47:            self.runtime_config.get("FINAM_ACCOUNT_ID")
src/finam_core/adapters/grpc/orders_client.py:48:            or self.runtime_config.get("ACCOUNT_ID")
src/finam_core/adapters/grpc/orders_client.py:49:            or self.runtime_config.get("FINAM_ACCOUNT")
src/finam_core/adapters/grpc/orders_client.py:514:        if not self.runtime_config.get_bool("REAL_EXECUTION_ENABLED", False) or not self.runtime_config.get_bool("REAL_ORDER_CONFIRM", False):
src/finam_core/adapters/grpc/orders_client.py:52:        self.token = self.runtime_config.get("FINAM_TOKEN", "").strip()
src/finam_core/adapters/grpc/orders_client.py:54:        self.endpoint = self.runtime_config.get("FINAM_GRPC_ENDPOINT", "api.finam.ru:443").strip()
src/finam_core/adapters/grpc/orders_client.py:592:        if not self.runtime_config.get_bool("REAL_EXECUTION_ENABLED", False) or not self.runtime_config.get_bool("REAL_ORDER_CONFIRM", False):
src/finam_core/adapters/grpc/orders_client.py:679:        if not self.runtime_config.get_bool("REAL_ORDER_CONFIRM", False):
src/finam_core/adapters/grpc/orders_client.py:7:from finam_core.config.runtime_config import RuntimeConfig
src/finam_core/config/runtime_config.py:10:class RuntimeConfigValue:
src/finam_core/config/runtime_config.py:17:class RuntimeConfig:
src/finam_core/config/runtime_config.py:22:        self._cache: dict[str, RuntimeConfigValue] = {}
src/finam_core/config/runtime_config.py:52:    def _get_from_db(self, key: str) -> RuntimeConfigValue | None:
src/finam_core/config/runtime_config.py:77:        item = RuntimeConfigValue(
src/finam_core/pipelines/paper_pipeline.py:265:        self.execution_mode = self.runtime_config.get("EXECUTION_MODE", "paper").strip().lower()
src/finam_core/pipelines/paper_pipeline.py:2846:            if os.getenv("SESSION_OVERRIDE", "0") == "1" or self.runtime_config.get_bool("SIMULATE_MARKET", False):
src/finam_core/pipelines/paper_pipeline.py:28:from finam_core.config.runtime_config import RuntimeConfig
src/finam_core/pipelines/paper_pipeline.py:2981:                if not self.runtime_config.get_bool("ENABLE_PAPER_FILLS", True):
src/finam_core/pipelines/paper_pipeline.py:3083:        if self.runtime_config.get_bool("SIMULATE_MARKET", False):
src/finam_core/pipelines/paper_pipeline.py:3256:                self.runtime_config.get_bool("SIMULATE_MARKET", False)
src/finam_core/pipelines/paper_pipeline.py:339:        self.runtime_config = RuntimeConfig()
src/finam_core/pipelines/paper_pipeline.py:3613:                if os.getenv("SESSION_OVERRIDE", "0") == "1" or self.runtime_config.get_bool("SIMULATE_MARKET", False):
src/finam_core/pipelines/paper_pipeline.py:3764:            if self.runtime_config.get("EXECUTION_MODE", "paper").lower() == "real":
src/finam_core/pipelines/paper_pipeline.py:4199:        if not self.runtime_config.get_bool("ENABLE_PAPER_FILLS", True):
src/finam_core/pipelines/paper_pipeline.py:4238:                        self.runtime_config.get_bool("SIMULATE_MARKET", False)
src/finam_core/pipelines/paper_pipeline.py:4341:            self.runtime_config.get_bool("SIMULATE_MARKET", False)
src/finam_core/pipelines/paper_pipeline.py:4684:            "execution_mode": self.runtime_config.get("EXECUTION_MODE", "paper"),
src/finam_core/pipelines/paper_pipeline.py:534:            self.runtime_config.get("EXECUTION_MODE", "paper").lower() == "paper"
src/finam_core/pipelines/paper_pipeline.py:542:            self.runtime_config.get("EXECUTION_MODE", "paper").lower() == "paper"
src/finam_core/pipelines/paper_pipeline.py:6000:        if self.runtime_config.get("EXECUTION_MODE", "paper").lower() != "paper":
src/finam_core/pipelines/paper_pipeline.py:6093:            self.runtime_config.get_bool("SIMULATE_MARKET", False)
src/finam_core/pipelines/paper_pipeline.py:6141:                if not self.runtime_config.get_bool("ENABLE_PAPER_FILLS", True):
src/finam_core/pipelines/paper_pipeline.py:6288:            "execution_mode": self.runtime_config.get("EXECUTION_MODE", "paper"),
src/finam_core/pipelines/paper_pipeline.py:6359:            "execution_mode": self.runtime_config.get("EXECUTION_MODE", "paper"),
src/scripts/run_market_pipeline.py:173:    p.add_argument("--md-first-quote-grace-sec", type=float, default=runtime_config.get_float("MD_FIRST_QUOTE_GRACE_SEC", 60.0))
src/scripts/run_market_pipeline.py:17:from finam_core.config.runtime_config import RuntimeConfig
src/scripts/run_market_pipeline.py:183:    p.add_argument("--debug", action="store_true", default=runtime_config.get_bool("MD_DEBUG", False))
src/scripts/run_market_pipeline.py:52:runtime_config = RuntimeConfig()
src/scripts/run_market_pipeline.py:92:    parser.add_argument("--md-first-quote-grace-sec", type=float, default=runtime_config.get_float("MD_FIRST_QUOTE_GRACE_SEC", 60.0))
src/scripts/run_market_pipeline.py:98:    parser.add_argument("--debug", action="store_true", default=runtime_config.get_bool("MD_DEBUG", False))

## Direct os.getenv still present
scripts/analytics_refresh_batch.sh:17:top_n = int(os.getenv("TOP_N", "5"))
scripts/analytics_refresh_batch.sh:20:timeframe = os.getenv("TIMEFRAME", "M5")
scripts/audit_project_gap_analysis.sh:35:  echo "## Direct os.getenv still present"
scripts/audit_project_gap_analysis.sh:36:  grep -R --exclude-dir='__pycache__' "os.getenv" -n src scripts | sort
scripts/audit_project_inventory.sh:12:grep -R --exclude-dir='__pycache__' "os.getenv\|os.environ" -n src scripts \
scripts/audit_project_inventory.sh:16:grep -R --exclude-dir='__pycache__' "os.getenv\|os.environ" -n scripts/test_* src/scripts/test_* 2>/dev/null \
scripts/check_ai_env.sh:16:    v = os.getenv(name, "")
scripts/check_ai_env.sh:30:dsn = os.getenv("DATABASE_URL")
scripts/check_ai_env.sh:46:token = os.getenv("TG_AI_TOKEN")
scripts/manage_position_intents.py:19:    database_url = os.getenv("DATABASE_URL", "").strip()
scripts/manual_brm6_buy_stop_dry_run.py:12:assert os.getenv("EXECUTION_MODE") == "real_dry_run", "EXECUTION_MODE must be real_dry_run"
scripts/manual_brm6_buy_stop_dry_run.py:13:assert os.getenv("REAL_ORDER_CONFIRM") == "0", "REAL_ORDER_CONFIRM must be 0 for safe dry-run"
scripts/test_engine_coordinator_execution_route_runtime.sh:47:assert os.getenv("ENABLE_ENGINE_COORDINATOR_EXECUTION_ROUTE") == "1"
scripts/test_engine_coordinator_on_quote_runtime.sh:28:assert os.getenv("ENABLE_ENGINE_COORDINATOR_ON_QUOTE") == "1"
scripts/test_marketdata_runtime_config_v1.sh:21:if grep -R -q 'os.getenv("MD_RECONNECT_INITIAL_SEC"' src/finam_core; then
scripts/test_marketdata_runtime_config_v1.sh:26:if grep -R -q 'os.getenv("MD_RECONNECT_MAX_SEC"' src/finam_core; then
scripts/test_marketdata_runtime_config_v1.sh:31:if grep -R -q 'os.getenv("MD_FIRST_QUOTE_GRACE_SEC"' src/finam_core; then
scripts/test_marketdata_runtime_config_v1.sh:36:if grep -R -q 'os.getenv("MD_WATCHDOG_MODE"' src/finam_core; then
scripts/test_marketdata_runtime_config_v1.sh:41:if grep -R -q 'os.getenv("MD_DEBUG"' src/finam_core; then
scripts/test_orders_client_runtime_config_safety.sh:17:if grep -q 'os.getenv("REAL_EXECUTION_ENABLED"' src/finam_core/adapters/grpc/orders_client.py; then
scripts/test_orders_client_runtime_config_safety.sh:22:if grep -q 'os.getenv("REAL_ORDER_CONFIRM"' src/finam_core/adapters/grpc/orders_client.py; then
scripts/test_paper_pipeline_runtime_config_v1.sh:22:if grep -q 'os.getenv("EXECUTION_MODE"' \
scripts/test_paper_pipeline_runtime_config_v1.sh:28:if grep -q 'os.getenv("ENABLE_PAPER_FILLS"' \
scripts/test_paper_pipeline_runtime_config_v1.sh:34:if grep -q 'os.getenv("SIMULATE_MARKET"' \
scripts/test_pipeline_trade_gate_extraction.sh:22:assert "max_trades_per_hour = int(os.getenv" not in main_region
src/app/bootstrap.py:14:    token=os.getenv("TG_TOKEN"),
src/app/bootstrap.py:15:    chat_id=os.getenv("TG_CHAT_ID"),
src/app/main.py:27:    print("POSTGRES_DSN:", "SET" if os.getenv("POSTGRES_DSN") else "MISSING")
src/app/main.py:28:    token = os.getenv("FINAM_TOKEN")
src/app/main.py:35:    dsn = os.getenv("POSTGRES_DSN")
src/app/main.py:43:    mode = os.getenv("MODE", Settings.MODE)
src/config/settings.py:19:    MODE = os.getenv("MODE", "SIM")
src/config/settings.py:22:    INITIAL_CASH = float(os.getenv("INITIAL_CASH", 100_000))
src/config/settings.py:30:    MAX_POSITION = int(os.getenv("MAX_POSITION", 10))
src/config/settings.py:33:    MAX_EXPOSURE = float(os.getenv("MAX_EXPOSURE", 100_000))
src/config/settings.py:36:    DEFAULT_SLIPPAGE = float(os.getenv("DEFAULT_SLIPPAGE", 0.0))
src/config/settings.py:45:        float(os.getenv("MAX_DAILY_LOSS_PCT"))
src/config/settings.py:46:        if os.getenv("MAX_DAILY_LOSS_PCT") is not None
src/config/settings.py:53:        float(os.getenv("MAX_DRAWDOWN_PCT"))
src/config/settings.py:54:        if os.getenv("MAX_DRAWDOWN_PCT") is not None
src/config/settings.py:61:        float(os.getenv("MAX_POSITION_PCT"))
src/config/settings.py:62:        if os.getenv("MAX_POSITION_PCT") is not None
src/config/settings.py:69:        float(os.getenv("MAX_GROSS_EXPOSURE_PCT"))
src/config/settings.py:70:        if os.getenv("MAX_GROSS_EXPOSURE_PCT") is not None
src/config/settings.py:77:        float(os.getenv("MAX_PORTFOLIO_HEAT"))
src/config/settings.py:78:        if os.getenv("MAX_PORTFOLIO_HEAT") is not None
src/config/settings.py:84:    CORRELATION_THRESHOLD = float(os.getenv("CORRELATION_THRESHOLD", 0.8))
src/finam_core/accounting/fees.py:25:        self.broker_rate = float(os.getenv("BROKER_FEE_RATE", "0.0"))
src/finam_core/accounting/fees.py:26:        self.exchange_rate = float(os.getenv("EXCHANGE_FEE_RATE", "0.0"))
src/finam_core/accounting/fees.py:27:        self.min_broker_fee = float(os.getenv("MIN_BROKER_FEE", "0.0"))
src/finam_core/accounting/fees.py:28:        self.tax_rate = float(os.getenv("TAX_RESERVE_RATE", "0.13"))
src/finam_core/adapters/grpc/market_data.py:411:        time.sleep(float(os.getenv("MD_BAR_POLL_SEC", "0.5")))
src/finam_core/adapters/grpc/market_data.py:62:        self._wd_warn_every_sec = float(os.getenv("MD_WATCHDOG_WARN_EVERY_SEC", "3600"))  # 1 час
src/finam_core/adapters/grpc/market_data.py:73:        if os.getenv("SIMULATE_MARKET", "0") == "1":
src/finam_core/adapters/grpc/market_data.py:86:        ka_time_ms = int(os.getenv("MD_GRPC_KEEPALIVE_TIME_MS", "30000"))
src/finam_core/adapters/grpc/market_data.py:87:        ka_timeout_ms = int(os.getenv("MD_GRPC_KEEPALIVE_TIMEOUT_MS", "10000"))
src/finam_core/adapters/grpc/orders_client.py:125:        value = os.getenv("REAL_ORDER_VALID_BEFORE", "end_of_day").strip().lower()
src/finam_core/adapters/grpc/orders_client.py:443:                timeout=float(os.getenv("FINAM_SUBSCRIBE_ORDERS_TIMEOUT_SEC", "30")),
src/finam_core/adapters/grpc/orders_client.py:446:            limit = int(max_events or int(os.getenv("FINAM_SUBSCRIBE_ORDERS_MAX_EVENTS", "1")))
src/finam_core/adapters/grpc/orders_client.py:457:            heartbeat = float(os.getenv("SUBSCRIBE_ORDERS_ERROR_HEARTBEAT_SEC", "300"))
src/finam_core/adapters/grpc/orders_client.py:458:            cooldown = float(os.getenv("SUBSCRIBE_ORDERS_ERROR_COOLDOWN_SEC", "60"))
src/finam_core/adapters/grpc/orders_client.py:486:                timeout=float(os.getenv("FINAM_CANCEL_ORDER_TIMEOUT_SEC", "10")),
src/finam_core/adapters/grpc/orders_client.py:537:                timeout=float(os.getenv("FINAM_PLACE_STOP_TIMEOUT_SEC", "10")),
src/finam_core/adapters/grpc/orders_client.py:614:                timeout=float(os.getenv("FINAM_PLACE_LIMIT_TIMEOUT_SEC", "10")),
src/finam_core/adapters/grpc/orders_client.py:764:                timeout=float(os.getenv("FINAM_OPEN_ORDERS_TIMEOUT_SEC", "10")),
src/finam_core/adapters/grpc/orders_client.py:812:            if os.getenv("FINAM_OPEN_ORDERS_DEBUG", "0") == "1":
src/finam_core/ai/sentiment_event_repository.py:25:        database_url = os.getenv("DATABASE_URL", "").strip()
src/finam_core/ai/sentiment_event_repository.py:29:        db_name = os.getenv("POSTGRES_DB") or os.getenv("DB_BASE", "finam_core")
src/finam_core/ai/sentiment_event_repository.py:30:        db_user = os.getenv("POSTGRES_USER", "finam")
src/finam_core/ai/sentiment_event_repository.py:31:        db_password = os.getenv("POSTGRES_PASSWORD", "")
src/finam_core/ai/sentiment_event_repository.py:32:        db_host = os.getenv("POSTGRES_HOST", "localhost")
src/finam_core/ai/sentiment_event_repository.py:33:        db_port = os.getenv("POSTGRES_PORT", "5432")
src/finam_core/ai/telegram_bot_news_ingest.py:46:            os.getenv("TG_AI_TOKEN")
src/finam_core/ai/telegram_bot_news_ingest.py:47:            or os.getenv("TG_BOT_TOKEN")
src/finam_core/ai/telethon_news_ingest.py:34:    proxy_url = (os.getenv("TG_MTPROTO_PROXY") or os.getenv("TG_PROXY") or "").strip()
src/finam_core/ai/telethon_news_ingest.py:73:        api_id = os.getenv("TG_API_ID", "").strip()
src/finam_core/ai/telethon_news_ingest.py:74:        api_hash = os.getenv("TG_API_HASH", "").strip()
src/finam_core/ai/telethon_news_ingest.py:75:        channels = os.getenv("TG_CHANNELS", "").strip()
src/finam_core/analytics/closed_trade_repository.py:52:                                "replay_campaign_id": os.getenv("REPLAY_CAMPAIGN_ID"),
src/finam_core/analytics/closed_trade_repository.py:53:                                "replay_id": os.getenv("REPLAY_ID"),
src/finam_core/analytics/closed_trade_repository.py:54:                                "replay_symbol": os.getenv("REPLAY_SYMBOL"),
src/finam_core/analytics/closed_trade_repository.py:55:                                "replay_timeframe": os.getenv("REPLAY_TIMEFRAME"),
src/finam_core/analytics/closed_trade_repository.py:56:                                "replay_strategy": os.getenv("REPLAY_STRATEGY"),
src/finam_core/analytics/closed_trade_repository.py:57:                                "dataset_source": "replay_campaign" if os.getenv("REPLAY_CAMPAIGN_ID") else "runtime",
src/finam_core/analytics/statistics_repository.py:17:    database_url = os.getenv("DATABASE_URL")
src/finam_core/analytics/statistics_repository.py:27:        f"postgresql://{os.getenv('DB_USER', 'finam')}:"
src/finam_core/analytics/statistics_repository.py:28:        f"{os.getenv('DB_PASSWORD', '')}@"
src/finam_core/analytics/statistics_repository.py:29:        f"{os.getenv('DB_HOST', 'localhost')}:"
src/finam_core/analytics/statistics_repository.py:30:        f"{os.getenv('DB_PORT', '5432')}/"
src/finam_core/analytics/statistics_repository.py:31:        f"{os.getenv('DB_NAME', 'finam_core')}"
src/finam_core/auth/token_manager.py:31:        self.secret = (secret or os.getenv("FINAM_SECRET") or "").strip()
src/finam_core/auth/token_manager.py:35:        self.host = (host or os.getenv("FINAM_API_HOST") or "api.finam.ru:443").strip()
src/finam_core/auth/token_manager.py:37:        self.ttl_sec = int(os.getenv("FINAM_TOKEN_TTL_SEC", "600"))
src/finam_core/auth/token_manager.py:38:        self.timeout_sec = float(os.getenv("FINAM_AUTH_TIMEOUT_SEC", "10"))
src/finam_core/auth/token_manager.py:39:        self.retries = int(os.getenv("FINAM_AUTH_RETRIES", "3"))
src/finam_core/auth/token_manager.py:52:        ka_time_ms = int(os.getenv("FINAM_GRPC_KEEPALIVE_TIME_MS", "30000"))
src/finam_core/auth/token_manager.py:53:        ka_timeout_ms = int(os.getenv("FINAM_GRPC_KEEPALIVE_TIMEOUT_MS", "10000"))
src/finam_core/config/runtime_config.py:21:        self.database_url = database_url or os.getenv("DATABASE_URL", "")
src/finam_core/config/settings.py:10:    EXECUTION_ENABLED = os.getenv("EXECUTION_ENABLED", "0")
src/finam_core/config/settings.py:11:    FINAM_TOKEN = os.getenv("FINAM_TOKEN", os.getenv("FINAM_SECRET", ""))
src/finam_core/config/settings.py:12:    FINAM_ACCOUNT_ID = os.getenv("FINAM_ACCOUNT_ID", "")
src/finam_core/config/settings.py:13:    SYMBOL = os.getenv("SYMBOL", "SBER@MISX")
src/finam_core/config/settings.py:14:    SYMBOLS = [x.strip() for x in os.getenv("SYMBOLS", SYMBOL).split(",") if x.strip()]
src/finam_core/config/settings.py:24:    MODE = os.getenv("MODE", "SIM")
src/finam_core/config/settings.py:27:    INITIAL_CASH = float(os.getenv("INITIAL_CASH", 100_000))
src/finam_core/config/settings.py:35:    MAX_POSITION = int(os.getenv("MAX_POSITION", 10))
src/finam_core/config/settings.py:38:    MAX_EXPOSURE = float(os.getenv("MAX_EXPOSURE", 100_000))
src/finam_core/config/settings.py:41:    DEFAULT_SLIPPAGE = float(os.getenv("DEFAULT_SLIPPAGE", 0.0))
src/finam_core/config/settings.py:50:        float(os.getenv("MAX_DAILY_LOSS_PCT"))
src/finam_core/config/settings.py:51:        if os.getenv("MAX_DAILY_LOSS_PCT") is not None
src/finam_core/config/settings.py:58:        float(os.getenv("MAX_DRAWDOWN_PCT"))
src/finam_core/config/settings.py:59:        if os.getenv("MAX_DRAWDOWN_PCT") is not None
src/finam_core/config/settings.py:66:        float(os.getenv("MAX_POSITION_PCT"))
src/finam_core/config/settings.py:67:        if os.getenv("MAX_POSITION_PCT") is not None
src/finam_core/config/settings.py:74:        float(os.getenv("MAX_GROSS_EXPOSURE_PCT"))
src/finam_core/config/settings.py:75:        if os.getenv("MAX_GROSS_EXPOSURE_PCT") is not None
src/finam_core/config/settings.py:82:        float(os.getenv("MAX_PORTFOLIO_HEAT"))
src/finam_core/config/settings.py:83:        if os.getenv("MAX_PORTFOLIO_HEAT") is not None
src/finam_core/config/settings.py:89:    CORRELATION_THRESHOLD = float(os.getenv("CORRELATION_THRESHOLD", 0.8))
src/finam_core/contracts/contract_resolver.py:23:                active_symbol=os.getenv("BR_CONTRACT", "BRM6@RTSX"),
src/finam_core/contracts/contract_resolver.py:24:                next_symbol=os.getenv("BR_NEXT_CONTRACT", "BRN6@RTSX"),
src/finam_core/contracts/contract_resolver.py:28:                active_symbol=os.getenv("NG_CONTRACT", "NGK6@RTSX"),
src/finam_core/contracts/contract_resolver.py:29:                next_symbol=os.getenv("NG_NEXT_CONTRACT", "NGN6@RTSX"),
src/finam_core/contracts/contract_resolver.py:33:                active_symbol=os.getenv("USDRUB_CONTRACT", "USDRUBF@RTSX"),
src/finam_core/contracts/contract_resolver.py:34:                next_symbol=os.getenv("USDRUB_NEXT_CONTRACT", ""),
src/finam_core/control/adaptive_strategy_controller.py:87:                cooldown_hours = float(os.getenv("BLOCKED_STRATEGY_COOLDOWN_HOURS", "6"))
src/finam_core/data/instrument_reference_seed.py:27:    database_url = os.getenv("DATABASE_URL", "").strip()
src/finam_core/data/radar_persistence_repository.py:14:        self.dsn = dsn or os.getenv(
src/finam_core/domain/risk/risk_factory.py:32:    max_total_raw = float(os.getenv("RISK_MAX_GROSS_EXPOSURE_PCT", str(cfg.max_total_exposure)))
src/finam_core/domain/risk/risk_factory.py:33:    max_symbol_raw = float(os.getenv("RISK_MAX_POSITION_PCT", str(cfg.max_symbol_exposure)))
src/finam_core/domain/risk/risk_factory.py:38:    if os.getenv("RISK_DEBUG") == "1" and not _PRINTED_FACTORY_DEBUG:
src/finam_core/domain/risk/risk_factory.py:47:    max_total = float(os.getenv("RISK_MAX_GROSS_EXPOSURE_PCT", str(cfg.max_total_exposure)))
src/finam_core/domain/risk/risk_factory.py:48:    max_symbol = float(os.getenv("RISK_MAX_POSITION_PCT", str(cfg.max_symbol_exposure)))
src/finam_core/domain/risk/rules/exposure_rule.py:70:        if os.getenv("RISK_DEBUG") == "1":
src/finam_core/engine/coordinator_flags.py:11:        return os.getenv(name, "0") == "1"
src/finam_core/engine/restart_recovery_coordinator.py:35:        if os.getenv("ENABLE_RESTART_RECOVERY", "0") != "1":
src/finam_core/events/dead_letter_auto_replay_worker.py:31:        self.database_url = database_url or os.getenv("DATABASE_URL")
src/finam_core/events/dead_letter_auto_replay_worker.py:37:            interval_sec if interval_sec is not None else os.getenv("DLQ_REPLAY_WORKER_INTERVAL_SEC", "60")
src/finam_core/events/dead_letter_auto_replay_worker.py:40:            limit if limit is not None else os.getenv("DLQ_REPLAY_WORKER_LIMIT", "10")
src/finam_core/events/dead_letter_replay_service.py:33:        self.database_url = database_url or os.getenv("DATABASE_URL")
src/finam_core/events/dead_letter_service.py:28:        self.database_url = database_url or os.getenv("DATABASE_URL")
src/finam_core/events/event_store.py:28:        self.database_url = database_url or os.getenv("DATABASE_URL")
src/finam_core/events/event_store_reader.py:24:        self.database_url = database_url or os.getenv("DATABASE_URL")
src/finam_core/execution/asset_execution_policy.py:34:        if os.getenv("REAL_TRADING_ENABLED", "0") != "1":
src/finam_core/execution/asset_execution_policy.py:37:        if os.path.exists(os.getenv("KILL_SWITCH_FILE", "/opt/finam-core/KILL_SWITCH")):
src/finam_core/execution/asset_execution_policy.py:41:            if os.getenv("REAL_STOCK_TRADING_ENABLED", "0") != "1":
src/finam_core/execution/asset_execution_policy.py:46:                for x in os.getenv("REAL_STOCK_ALLOWLIST", "").split(",")
src/finam_core/execution/execution_dispatcher.py:154:        mode = os.getenv("EXECUTION_MODE", "paper").strip().lower()
src/finam_core/execution/execution_dispatcher.py:233:                    or os.getenv("PORTFOLIO_EQUITY", "0")
src/finam_core/execution/execution_dispatcher.py:238:                    or os.getenv("USED_MARGIN", "0")
src/finam_core/execution/execution_dispatcher.py:441:        mode = os.getenv("EXECUTION_MODE", "paper").strip().lower()
src/finam_core/execution/exit_lifecycle_manager.py:103:            if now_ts - last_intent_block_ts >= float(os.getenv("POSITION_INTENT_BLOCK_LOG_INTERVAL_SEC", "300")):
src/finam_core/execution/exit_lifecycle_manager.py:116:            if now_ts - last_no_avg_ts >= float(os.getenv("EXIT_NO_AVG_LOG_INTERVAL_SEC", "300")):
src/finam_core/execution/exit_lifecycle_manager.py:43:        if os.getenv("ENABLE_BROKER_POSITION_APPLY_TO_PM", "0") == "1" and abs(broker_qty) > 1e-9:
src/finam_core/execution/exit_lifecycle_manager.py:76:        should_log_exit_check = now_ts - last_log_ts >= float(os.getenv(interval_key, default_interval))
src/finam_core/execution/exit_lifecycle_manager.py:79:            abs(float(qty or 0.0)) > 1e-9 or os.getenv("EXIT_ENGINE_DEBUG", "0") == "1"
src/finam_core/execution/oco_order_manager.py:16:    category = os.getenv("BROKER_CATEGORY", "KNUR").strip().upper()
src/finam_core/execution/order_ack_logger.py:17:        self.database_url = (database_url or os.getenv("DATABASE_URL") or "").strip()
src/finam_core/execution/order_ack_logger.py:18:        self.enabled = os.getenv("ORDER_ACK_LOGGER_ENABLED", "1") == "1"
src/finam_core/execution/position_lifecycle_reconcile_event_repository.py:14:        self.database_url = os.getenv("DATABASE_URL", "").strip()
src/finam_core/execution/position_lifecycle_reconcile_event_repository.py:16:            db_host = os.getenv("DB_HOST", "127.0.0.1")
src/finam_core/execution/position_lifecycle_reconcile_event_repository.py:17:            db_port = os.getenv("DB_PORT", "5432")
src/finam_core/execution/position_lifecycle_reconcile_event_repository.py:18:            db_name = os.getenv("DB_NAME", "finam_core")
src/finam_core/execution/position_lifecycle_reconcile_event_repository.py:19:            db_user = os.getenv("DB_USER", "finam")
src/finam_core/execution/position_lifecycle_reconcile_event_repository.py:20:            db_password = os.getenv("DB_PASSWORD", "finam")
src/finam_core/execution/position_lifecycle_service.py:104:        if os.getenv("ENABLE_TRAILING_ORDER_MANAGER", "0") != "1":
src/finam_core/execution/position_lifecycle_service.py:107:        if os.getenv("ENABLE_POSITION_INTENT_GATE", "0") == "1":
src/finam_core/execution/position_lifecycle_service.py:113:                if now_ts - last_ts >= float(os.getenv("POSITION_INTENT_TRAILING_BLOCK_LOG_INTERVAL_SEC", "300")):
src/finam_core/execution/position_lifecycle_service.py:122:        dry_run = os.getenv("TRAILING_ORDER_DRY_RUN", "1") == "1"
src/finam_core/execution/position_lifecycle_service.py:39:        if os.getenv("ENABLE_TAKE_PROFIT_ENGINE", "0") != "1":
src/finam_core/execution/position_lifecycle_service.py:53:                    * (1.0 - float(os.getenv("TAKE_PROFIT_DEFAULT_STOP_PCT", "0.01")))
src/finam_core/execution/position_lifecycle_state_repository.py:23:        self.database_url = database_url or os.getenv("DATABASE_URL")
src/finam_core/execution/profit_lock_event_repository.py:14:        self.database_url = os.getenv("DATABASE_URL", "").strip()
src/finam_core/execution/profit_lock_event_repository.py:16:            db_host = os.getenv("DB_HOST", "127.0.0.1")
src/finam_core/execution/profit_lock_event_repository.py:17:            db_port = os.getenv("DB_PORT", "5432")
src/finam_core/execution/profit_lock_event_repository.py:18:            db_name = os.getenv("DB_NAME", "finam_core")
src/finam_core/execution/profit_lock_event_repository.py:19:            db_user = os.getenv("DB_USER", "finam")
src/finam_core/execution/profit_lock_event_repository.py:20:            db_password = os.getenv("DB_PASSWORD", "finam")
src/finam_core/execution/protective_order_link_repository.py:18:        self.database_url = (database_url or os.getenv("DATABASE_URL") or "").strip()
src/finam_core/execution/protective_order_link_repository.py:19:        self.enabled = os.getenv("PROTECTIVE_ORDER_LINKS_ENABLED", "1") == "1"
src/finam_core/execution/real_execution.py:17:    category = os.getenv("BROKER_CATEGORY", "KNUR").strip().upper()
src/finam_core/execution/real_execution.py:185:        if os.getenv("ENABLE_REAL_EXECUTION_SAFETY_GATE", "0") == "1":
src/finam_core/execution/real_execution.py:186:            allowlist_raw = os.getenv("REAL_EXECUTION_SYMBOL_ALLOWLIST", "").strip()
src/finam_core/execution/real_execution.py:199:            max_qty = float(os.getenv("REAL_EXECUTION_MAX_QTY", "1"))
src/finam_core/execution/real_execution.py:214:        if os.getenv("REAL_EXECUTION_ENABLED", "0") != "1":
src/finam_core/execution/real_execution.py:230:        if os.getenv("REAL_ORDER_CONFIRM", "0") != "1":
src/finam_core/execution/real_execution.py:73:        self.mode = os.getenv("EXECUTION_MODE", "paper").strip().lower()
src/finam_core/execution/real_execution.py:80:        if os.getenv("ENABLE_ORDER_EVENT_STORE", "0") == "1":
src/finam_core/execution/real_execution_safety.py:26:        self.execution_enabled = os.getenv("EXECUTION_ENABLED", "0") == "1"
src/finam_core/execution/real_execution_safety.py:27:        self.real_trading_enabled = os.getenv("REAL_TRADING_ENABLED", "0") == "1"
src/finam_core/execution/real_execution_safety.py:28:        self.real_stocks_only = os.getenv("REAL_STOCKS_ONLY", "1") == "1"
src/finam_core/execution/real_execution_safety.py:29:        self.allowed_symbols_raw = os.getenv("REAL_ALLOWED_SYMBOLS", "").strip()
src/finam_core/execution/real_execution_safety.py:35:        self.max_qty = float(os.getenv("REAL_MAX_QTY", "1"))
src/finam_core/execution/real_execution_safety.py:36:        self.duplicate_ttl_sec = float(os.getenv("REAL_DUPLICATE_TTL_SEC", "30"))
src/finam_core/execution/real_execution_safety.py:37:        self.position_mismatch_check_enabled = os.getenv("POSITION_MISMATCH_HARD_BLOCK", "1") == "1"
src/finam_core/execution/real_execution_safety.py:51:        mode = (execution_mode or os.getenv("EXECUTION_MODE", "paper")).strip().lower()
src/finam_core/execution/real_protective_lifecycle.py:29:            os.getenv("REAL_PROTECTIVE_LIFECYCLE_ENABLED", "0") == "1"
src/finam_core/execution/real_protective_lifecycle.py:30:            and os.getenv("TRAILING_ORDER_DRY_RUN", "1") == "0"
src/finam_core/execution/take_profit_event_repository.py:14:        self.database_url = os.getenv("DATABASE_URL", "").strip()
src/finam_core/execution/take_profit_event_repository.py:16:            db_host = os.getenv("DB_HOST", "127.0.0.1")
src/finam_core/execution/take_profit_event_repository.py:17:            db_port = os.getenv("DB_PORT", "5432")
src/finam_core/execution/take_profit_event_repository.py:18:            db_name = os.getenv("DB_NAME", "finam_core")
src/finam_core/execution/take_profit_event_repository.py:19:            db_user = os.getenv("DB_USER", "finam")
src/finam_core/execution/take_profit_event_repository.py:20:            db_password = os.getenv("DB_PASSWORD", "finam")
src/finam_core/execution/trade_management_service.py:20:        self.enabled = os.getenv("TRADE_MANAGEMENT_ENABLED", "1") == "1"
src/finam_core/execution/trade_management_service.py:21:        self.live_replace = os.getenv("STOP_REPLACE_LIVE", "0") == "1"
src/finam_core/execution/trailing_order_event_repository.py:14:        self.database_url = os.getenv("DATABASE_URL", "").strip()
src/finam_core/execution/trailing_order_event_repository.py:16:            db_host = os.getenv("DB_HOST", "127.0.0.1")
src/finam_core/execution/trailing_order_event_repository.py:17:            db_port = os.getenv("DB_PORT", "5432")
src/finam_core/execution/trailing_order_event_repository.py:18:            db_name = os.getenv("DB_NAME", "finam_core")
src/finam_core/execution/trailing_order_event_repository.py:19:            db_user = os.getenv("DB_USER", "finam")
src/finam_core/execution/trailing_order_event_repository.py:20:            db_password = os.getenv("DB_PASSWORD", "finam")
src/finam_core/futures/futures_access_gate.py:24:            os.getenv("FUTURES_REAL_ALLOWED_FROM", "2026-07-01")
src/finam_core/futures/futures_access_gate.py:58:        if os.getenv("ENABLE_REAL_FUTURES_TRADING", "0") != "1":
src/finam_core/futures/futures_margin_guard.py:32:        self.max_utilization = float(os.getenv("FUTURES_MAX_MARGIN_UTILIZATION", "0.50"))
src/finam_core/futures/futures_margin_guard.py:42:        if os.getenv(env_key):
src/finam_core/futures/futures_margin_guard.py:43:            return float(os.getenv(env_key, "0"))
src/finam_core/futures/futures_margin_guard.py:49:        return float(os.getenv("FUTURES_DEFAULT_MARGIN_PER_CONTRACT", "10000"))
src/finam_core/infra/brokers/finam_rest.py:36:        base_url = os.getenv("FINAM_REST_BASE", "https://tradeapi.finam.ru").rstrip("/")
src/finam_core/infra/brokers/finam_rest.py:37:        token = os.getenv("FINAM_TOKEN", "").strip()
src/finam_core/infra/brokers/finam_rest.py:40:        timeout = float(os.getenv("FINAM_TIMEOUT", "15"))
src/finam_core/infra/finam/client.py:92:        self.execution_enabled = os.getenv("EXECUTION_ENABLED", "0") == "1"
src/finam_core/infra/finam/client.py:93:        self.mode = os.getenv("MODE", "REAL").upper()
src/finam_core/infra/finam/client.py:94:        self.api_token = os.getenv("FINAM_TOKEN")
src/finam_core/infra/finam/client.py:95:        self.account_id = os.getenv("FINAM_ACCOUNT_ID")
src/finam_core/ingestion/history_loader.py:29:        self.dsn = dsn or os.getenv("DATABASE_URL") or (
src/finam_core/ingestion/history_loader.py:30:            f"postgresql://{os.getenv('DB_USER','finam')}:{os.getenv('DB_PASSWORD','finam')}"
src/finam_core/ingestion/history_loader.py:31:            f"@{os.getenv('DB_HOST','127.0.0.1')}:{os.getenv('DB_PORT','5432')}/{os.getenv('DB_NAME','finam')}"
src/finam_core/ingestion/live_bars_feed.py:14:        self.host = host or os.getenv("FINAM_GRPC_HOST") or os.getenv("FINAM_API_HOST")
src/finam_core/ingestion/live_bars_feed.py:19:            or os.getenv("FINAM_JWT")
src/finam_core/ingestion/live_bars_feed.py:20:            or os.getenv("FINAM_TOKEN")
src/finam_core/ingestion/live_bars_feed.py:21:            or os.getenv("JWT")
src/finam_core/instruments/contract_specs.py:23:            "BR": ContractSpec("BR", 0.01, float(os.getenv("FUTURES_SPEC_BR_STEP_VALUE", "10")), "RUB"),
src/finam_core/instruments/contract_specs.py:24:            "SI": ContractSpec("SI", 1.0, float(os.getenv("FUTURES_SPEC_SI_STEP_VALUE", "1")), "RUB"),
src/finam_core/instruments/contract_specs.py:25:            "NG": ContractSpec("NG", 0.001, float(os.getenv("FUTURES_SPEC_NG_STEP_VALUE", "1")), "RUB"),
src/finam_core/instruments/contract_specs.py:26:            "RI": ContractSpec("RI", 10.0, float(os.getenv("FUTURES_SPEC_RI_STEP_VALUE", "10")), "RUB"),
src/finam_core/instruments/contract_specs.py:27:            "MX": ContractSpec("MX", 0.25, float(os.getenv("FUTURES_SPEC_MX_STEP_VALUE", "1")), "RUB"),
src/finam_core/instruments/contract_specs.py:30:        raw = os.getenv("FUTURES_CONTRACT_SPECS_JSON", "").strip()
src/finam_core/instruments/finam_instrument_sync.py:19:        self.page_limit = int(os.getenv("MOEX_INSTRUMENT_PAGE_LIMIT", "100"))
src/finam_core/instruments/finam_instrument_sync.py:20:        self.max_pages = int(os.getenv("MOEX_INSTRUMENT_MAX_PAGES", "80"))
src/finam_core/instruments/finam_instrument_sync.py:21:        self.request_timeout_sec = float(os.getenv("MOEX_INSTRUMENT_TIMEOUT_SEC", "10"))
src/finam_core/instruments/finam_instrument_sync.py:22:        self.sleep_sec = float(os.getenv("MOEX_INSTRUMENT_SLEEP_SEC", "0.05"))
src/finam_core/notifications/telegram_notifier.py:24:env_path = os.getenv("FINAM_ENV_FILE", "/opt/finam-core/deploy/env/.env")
src/finam_core/notifications/telegram_notifier.py:33:        self.token = (os.getenv("TG_TOKEN") or os.getenv("TG_BOT_TOKEN") or "").strip()
src/finam_core/notifications/telegram_notifier.py:34:        self.chat_id = os.getenv("TG_CHAT_ID", "").strip()
src/finam_core/notifications/telegram_notifier.py:35:        self.proxy = os.getenv("TG_PROXY")
src/finam_core/notifications/telegram_notifier.py:37:        self.enabled = os.getenv("ENABLE_TELEGRAM_NOTIFIER", "0") == "1"
src/finam_core/notifications/telegram_notifier.py:43:        self._min_interval = float(os.getenv("TG_MIN_INTERVAL", "0.5"))
src/finam_core/notifications/telegram_signal_dispatcher.py:47:        token = os.getenv(self.token_env, "").strip()
src/finam_core/notifications/telegram_signal_dispatcher.py:48:        chat_id = os.getenv(route.target_env, "").strip()
src/finam_core/notifications/trade_signal_notifier.py:23:            os.getenv("ENABLE_TRADE_SIGNAL_ALERTS", "0") == "1"
src/finam_core/notifications/trade_signal_notifier.py:27:            os.getenv("TRADE_TG_BOT_TOKEN", "").strip()
src/finam_core/notifications/trade_signal_notifier.py:31:            os.getenv("TRADE_TG_CHAT_ID", "").strip()
src/finam_core/notifications/trade_signal_notifier.py:35:            os.getenv("TRADE_TG_PROXY", "").strip()
src/finam_core/oms/order_journal.py:33:        self.database_url = database_url or os.getenv("DATABASE_URL")
src/finam_core/pipelines/paper_pipeline.py:1020:        if os.getenv("BROKER_POSITION_HARD_GATE_USE_BROKER_AS_LOCAL", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py:1047:        if os.getenv("ENABLE_BROKER_POSITION_HARD_GATE", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py:1050:        tolerance = float(os.getenv("BROKER_POSITION_HARD_GATE_QTY_TOLERANCE", "1e-9"))
src/finam_core/pipelines/paper_pipeline.py:1081:        if os.getenv("ENABLE_BROKER_PROTECTION_GATE", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py:1121:        if os.getenv("ENABLE_BROKER_POSITION_HARD_GATE", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py:1177:        if os.getenv("ENABLE_OCO_ORDER_MANAGER", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py:1214:        if os.getenv("ENABLE_SUBSCRIBE_ORDERS_LISTENER", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py:1222:        poll_interval = float(os.getenv("SUBSCRIBE_ORDERS_POLL_INTERVAL_SEC", "15"))
src/finam_core/pipelines/paper_pipeline.py:122:PIPE_DEBUG = os.getenv("PIPE_DEBUG", "0") == "1"
src/finam_core/pipelines/paper_pipeline.py:1230:            max_events = int(os.getenv("SUBSCRIBE_ORDERS_MAX_EVENTS_PER_POLL", "1"))
src/finam_core/pipelines/paper_pipeline.py:1240:                heartbeat = float(os.getenv("SUBSCRIBE_ORDERS_APPLIED_HEARTBEAT_SEC", "300"))
src/finam_core/pipelines/paper_pipeline.py:1253:                    heartbeat_sec=float(os.getenv("SUBSCRIBE_ORDERS_ERROR_HEARTBEAT_SEC", "300")),
src/finam_core/pipelines/paper_pipeline.py:1262:        if os.getenv("ENABLE_BROKER_OPEN_ORDERS_SYNC", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py:1265:        interval_sec = float(os.getenv("BROKER_OPEN_ORDERS_SYNC_INTERVAL_SEC", "30"))
src/finam_core/pipelines/paper_pipeline.py:1497:        pct = float(os.getenv("EXIT_FALLBACK_ATR_PCT", "0.003"))
src/finam_core/pipelines/paper_pipeline.py:1509:        if os.getenv("ENABLE_POSITION_LIFECYCLE_SELF_HEALING", "1") != "1":
src/finam_core/pipelines/paper_pipeline.py:1578:        if os.getenv("ENABLE_POSITION_LIFECYCLE_RECONCILIATION", "1") != "1":
src/finam_core/pipelines/paper_pipeline.py:1732:        if os.getenv("ENABLE_PARTIAL_CLOSE_ENGINE", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py:1740:            base_stop = float(stop_price or (entry_price * (1.0 - float(os.getenv("PARTIAL_CLOSE_DEFAULT_STOP_PCT", "0.01")))))
src/finam_core/pipelines/paper_pipeline.py:1788:        if os.getenv("ENABLE_TAKE_PROFIT_ENGINE", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py:1796:            base_stop = float(stop_price or (entry_price * (1.0 - float(os.getenv("TAKE_PROFIT_DEFAULT_STOP_PCT", "0.01")))))
src/finam_core/pipelines/paper_pipeline.py:1853:        if os.getenv("ENABLE_PROFIT_LOCK_ENGINE", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py:1861:            base_stop = float(stop_price or (entry_price * (1.0 - float(os.getenv("PROFIT_LOCK_DEFAULT_STOP_PCT", "0.01")))))
src/finam_core/pipelines/paper_pipeline.py:1918:        if os.getenv("ENABLE_TRAILING_ORDER_MANAGER", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py:1921:        if os.getenv("ENABLE_POSITION_INTENT_GATE", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py:1927:                if now_ts - last_ts >= float(os.getenv("POSITION_INTENT_TRAILING_BLOCK_LOG_INTERVAL_SEC", "300")):
src/finam_core/pipelines/paper_pipeline.py:1936:        dry_run = os.getenv("TRAILING_ORDER_DRY_RUN", "1") == "1"
src/finam_core/pipelines/paper_pipeline.py:2018:        if os.getenv("ENABLE_POSITION_ORDER_TRACKER", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py:2051:        if os.getenv("ENABLE_POSITION_INTENT_GATE", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py:2066:        if os.getenv("ENABLE_BROKER_RECONCILIATION_GATE", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py:2079:            allow_repair=os.getenv("ALLOW_PORTFOLIO_REPAIR", "0") == "1",
src/finam_core/pipelines/paper_pipeline.py:2138:        if os.getenv("ENABLE_POSITION_INTENT_GATE", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py:2186:        if os.getenv("ENABLE_BROKER_POSITION_APPLY_TO_PM", "0") == "1" and abs(broker_qty) > 1e-9:
src/finam_core/pipelines/paper_pipeline.py:2223:        should_log_exit_check = now_ts - last_log_ts >= float(os.getenv(interval_key, default_interval))
src/finam_core/pipelines/paper_pipeline.py:2226:            abs(float(qty or 0.0)) > 1e-9 or os.getenv("EXIT_ENGINE_DEBUG", "0") == "1"
src/finam_core/pipelines/paper_pipeline.py:2250:            if now_ts - last_intent_block_ts >= float(os.getenv("POSITION_INTENT_BLOCK_LOG_INTERVAL_SEC", "300")):
src/finam_core/pipelines/paper_pipeline.py:2263:            if now_ts - last_no_avg_ts >= float(os.getenv("EXIT_NO_AVG_LOG_INTERVAL_SEC", "300")):
src/finam_core/pipelines/paper_pipeline.py:2463:        hb = float(heartbeat_sec if heartbeat_sec is not None else os.getenv("PIPE_DEDUP_LOG_HEARTBEAT_SEC", "300"))
src/finam_core/pipelines/paper_pipeline.py:2481:        if os.getenv("ENABLE_EXECUTION_DECISION_LAYER", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py:2559:        if os.getenv("ENABLE_ORDER_ROUTER", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py:2611:        if os.getenv("ENABLE_EXECUTION_DISPATCHER", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py:2631:        if os.getenv("ENABLE_EXECUTION_DISPATCHER_LIVE_ROUTE", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py:2637:        allowlist_raw = os.getenv("EXECUTION_DISPATCHER_LIVE_SYMBOL_ALLOWLIST", "BRM6@RTSX")
src/finam_core/pipelines/paper_pipeline.py:2643:        max_qty = float(os.getenv("EXECUTION_DISPATCHER_LIVE_MAX_QTY", "1"))
src/finam_core/pipelines/paper_pipeline.py:2689:            if os.getenv("ENABLE_SMART_MONEY_FEATURES", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py:2692:            threshold = float(os.getenv("SMART_MONEY_MIN_SCORE", "0.45"))
src/finam_core/pipelines/paper_pipeline.py:2693:            min_interval = float(os.getenv("SMART_MONEY_SAVE_INTERVAL_SEC", "60"))
src/finam_core/pipelines/paper_pipeline.py:2710:                    window=int(os.getenv("SMART_MONEY_WINDOW", "20")),
src/finam_core/pipelines/paper_pipeline.py:2813:        if os.getenv("SESSION_OVERRIDE", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py:2817:                heartbeat_sec=float(os.getenv("SESSION_OVERRIDE_LOG_SEC", "30")),
src/finam_core/pipelines/paper_pipeline.py:2846:            if os.getenv("SESSION_OVERRIDE", "0") == "1" or self.runtime_config.get_bool("SIMULATE_MARKET", False):
src/finam_core/pipelines/paper_pipeline.py:2850:                    heartbeat_sec=float(os.getenv("SESSION_BYPASS_LOG_SEC", "60")),
src/finam_core/pipelines/paper_pipeline.py:2871:                if os.getenv("FINAM_CORE_FEED") == "sim":
src/finam_core/pipelines/paper_pipeline.py:2875:                        heartbeat_sec=float(os.getenv("SESSION_OVERRIDE_LOG_SEC", "30")),
src/finam_core/pipelines/paper_pipeline.py:2881:                        heartbeat_sec=float(os.getenv("SESSION_BLOCK_LOG_SEC", "300")),
src/finam_core/pipelines/paper_pipeline.py:2916:                os.getenv("ENABLE_BROKER_POSITION_APPLY_TO_PM", "0") != "1"
src/finam_core/pipelines/paper_pipeline.py:293:        self._quote_log_every = float(os.getenv("QUOTE_LOG_EVERY", "0"))  # 0 = выключено
src/finam_core/pipelines/paper_pipeline.py:297:            trail_abs=float(os.getenv("TRAILING_ORDER_TRAIL_ABS", "0.40")),
src/finam_core/pipelines/paper_pipeline.py:298:            min_replace_step=float(os.getenv("TRAILING_ORDER_MIN_REPLACE_STEP", "0.10")),
src/finam_core/pipelines/paper_pipeline.py:3032:        force_signal_mode = os.getenv("FORCE_ONCE_BUY", "0") == "1"
src/finam_core/pipelines/paper_pipeline.py:306:            os.getenv("REAL_PROTECTIVE_LIFECYCLE_ENABLED", "0") == "1"
src/finam_core/pipelines/paper_pipeline.py:307:            and os.getenv("TRAILING_ORDER_DRY_RUN", "1") == "0"
src/finam_core/pipelines/paper_pipeline.py:3234:            log_every_sec = float(os.getenv("PIPE_REGIME_LOG_EVERY_SEC", "60"))
src/finam_core/pipelines/paper_pipeline.py:3257:                and os.getenv("REPLAY_ACCUMULATION_MODE", "0") == "1"
src/finam_core/pipelines/paper_pipeline.py:3260:            if (not is_exit_intent) and (not is_force_intent) and atr_pct < float(os.getenv("ATR_MIN_PCT","0.002")):
src/finam_core/pipelines/paper_pipeline.py:3265:                        heartbeat_sec=float(os.getenv("PIPE_VOL_LOW_BLOCK_LOG_EVERY_SEC", "60")),
src/finam_core/pipelines/paper_pipeline.py:3270:                    log_every_sec = float(os.getenv("PIPE_VOL_LOW_BLOCK_LOG_EVERY_SEC", "60"))
src/finam_core/pipelines/paper_pipeline.py:3285:                if trend_strength < float(os.getenv("TREND_STRENGTH_MIN","0.0003")) and regime.volatility != "high":  # ключевой параметр
src/finam_core/pipelines/paper_pipeline.py:3389:            breakout_ttl = float(os.getenv("BREAKOUT_DEDUP_TTL", "30"))
src/finam_core/pipelines/paper_pipeline.py:3412:            breakout_ttl = float(os.getenv("BREAKOUT_DEDUP_TTL", "30"))
src/finam_core/pipelines/paper_pipeline.py:359:            qty_tolerance=float(os.getenv("BROKER_RECONCILIATION_QTY_TOLERANCE", "1e-9"))
src/finam_core/pipelines/paper_pipeline.py:3613:                if os.getenv("SESSION_OVERRIDE", "0") == "1" or self.runtime_config.get_bool("SIMULATE_MARKET", False):
src/finam_core/pipelines/paper_pipeline.py:3617:                        heartbeat_sec=float(os.getenv("SESSION_OVERRIDE_LOG_SEC", "30")),
src/finam_core/pipelines/paper_pipeline.py:3623:                        heartbeat_sec=float(os.getenv("SESSION_BLOCK_LOG_SEC", "300")),
src/finam_core/pipelines/paper_pipeline.py:3634:        override = os.getenv("OVERRIDE_MODE", "0") == "1"
src/finam_core/pipelines/paper_pipeline.py:363:            qty_tolerance=float(os.getenv("BROKER_RECONCILIATION_QTY_TOLERANCE", "1e-9"))
src/finam_core/pipelines/paper_pipeline.py:368:            ttl_sec=float(os.getenv("POSITION_INTENT_CACHE_TTL_SEC", "60"))
src/finam_core/pipelines/paper_pipeline.py:3726:                        heartbeat_sec=float(os.getenv("POSITION_INTENT_BLOCK_HEARTBEAT_SEC", "300")),
src/finam_core/pipelines/paper_pipeline.py:372:            ttl_sec=float(os.getenv("EXIT_STATE_TTL_SEC", "30"))
src/finam_core/pipelines/paper_pipeline.py:3799:            if (not is_exit_intent) and (not is_force_intent) and abs(st.get("ema_fast", price) - price) / price < float(os.getenv("IMPULSE_MIN","0.0003")) and regime.volatility != "high":
src/finam_core/pipelines/paper_pipeline.py:3823:            dedup_ttl = float(os.getenv("SIGNAL_DEDUP_TTL", "2"))
src/finam_core/pipelines/paper_pipeline.py:382:                base_cooldown_sec=float(os.getenv("TRADE_COOLDOWN_SEC", "45")),
src/finam_core/pipelines/paper_pipeline.py:383:                max_trades_per_hour=int(os.getenv("MAX_TRADES_PER_HOUR", "5")),
src/finam_core/pipelines/paper_pipeline.py:384:                max_trades_per_symbol=int(os.getenv("MAX_TRADES_PER_SYMBOL", "2")),
src/finam_core/pipelines/paper_pipeline.py:3857:                threshold = float(os.getenv("PYRAMIDING_THRESHOLD", "0.0003"))  # 0.03% (ускорение)
src/finam_core/pipelines/paper_pipeline.py:3884:                base_cooldown_sec=float(os.getenv("TRADE_COOLDOWN_SEC", "45")),
src/finam_core/pipelines/paper_pipeline.py:3885:                max_trades_per_hour=int(os.getenv("MAX_TRADES_PER_HOUR", "5")),
src/finam_core/pipelines/paper_pipeline.py:3886:                max_trades_per_symbol=int(os.getenv("MAX_TRADES_PER_SYMBOL", "2")),
src/finam_core/pipelines/paper_pipeline.py:3951:            if os.getenv("RISK_SOFT", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py:4001:                    max_portfolio_heat=float(os.getenv("MAX_PORTFOLIO_HEAT", "0.30")),
src/finam_core/pipelines/paper_pipeline.py:4002:                    max_symbol_heat=float(os.getenv("MAX_SYMBOL_HEAT", "0.10")),
src/finam_core/pipelines/paper_pipeline.py:4003:                    max_margin_utilization=float(os.getenv("MAX_MARGIN_UTILIZATION", "0.65")),
src/finam_core/pipelines/paper_pipeline.py:4004:                    max_daily_loss_pct=float(os.getenv("MAX_DAILY_LOSS_PCT", "0.02")),
src/finam_core/pipelines/paper_pipeline.py:4005:                    max_drawdown_pct=float(os.getenv("MAX_DRAWDOWN_PCT", "0.03")),
src/finam_core/pipelines/paper_pipeline.py:403:            base_cooldown_sec=float(os.getenv("TRADE_COOLDOWN_SEC", "45")),
src/finam_core/pipelines/paper_pipeline.py:404:            max_trades_per_hour=int(os.getenv("MAX_TRADES_PER_HOUR", "5")),
src/finam_core/pipelines/paper_pipeline.py:4055:                max_heat = float(os.getenv("MAX_PORTFOLIO_HEAT", "0.3"))  # 30% default
src/finam_core/pipelines/paper_pipeline.py:405:            max_trades_per_symbol=int(os.getenv("MAX_TRADES_PER_SYMBOL", "2")),
src/finam_core/pipelines/paper_pipeline.py:4077:                max_symbol_heat = float(os.getenv("MAX_SYMBOL_HEAT", "0.1"))  # 10% default
src/finam_core/pipelines/paper_pipeline.py:4111:                max_dd = float(os.getenv("MAX_DRAWDOWN", "-0.03"))  # -3%
src/finam_core/pipelines/paper_pipeline.py:4112:                max_daily_loss = float(os.getenv("MAX_DAILY_LOSS", "-0.02"))  # -2%
src/finam_core/pipelines/paper_pipeline.py:416:            base_cooldown_sec=float(os.getenv("TRADE_COOLDOWN_SEC", "45")),
src/finam_core/pipelines/paper_pipeline.py:417:            max_trades_per_hour=int(os.getenv("MAX_TRADES_PER_HOUR", "5")),
src/finam_core/pipelines/paper_pipeline.py:418:            max_trades_per_symbol=int(os.getenv("MAX_TRADES_PER_SYMBOL", "2")),
src/finam_core/pipelines/paper_pipeline.py:4239:                        and os.getenv("REPLAY_ACCUMULATION_MODE", "0") == "1"
src/finam_core/pipelines/paper_pipeline.py:4342:            and os.getenv("REPLAY_ACCUMULATION_MODE", "0") == "1"
src/finam_core/pipelines/paper_pipeline.py:452:            tick_size=float(os.getenv("ENTRY_TICK_SIZE", "0.01")),
src/finam_core/pipelines/paper_pipeline.py:453:            stop_atr_mult=float(os.getenv("ENTRY_STOP_ATR_MULT", "1.5")),
src/finam_core/pipelines/paper_pipeline.py:454:            take_atr_mult=float(os.getenv("ENTRY_TAKE_ATR_MULT", "2.0")),
src/finam_core/pipelines/paper_pipeline.py:4597:                if os.getenv("REPLAY_CAMPAIGN_ID"):
src/finam_core/pipelines/paper_pipeline.py:4598:                    payload.setdefault("replay_campaign_id", os.getenv("REPLAY_CAMPAIGN_ID"))
src/finam_core/pipelines/paper_pipeline.py:4599:                    payload.setdefault("replay_id", os.getenv("REPLAY_ID"))
src/finam_core/pipelines/paper_pipeline.py:4600:                    payload.setdefault("replay_symbol", os.getenv("REPLAY_SYMBOL"))
src/finam_core/pipelines/paper_pipeline.py:4601:                    payload.setdefault("replay_timeframe", os.getenv("REPLAY_TIMEFRAME"))
src/finam_core/pipelines/paper_pipeline.py:4602:                    payload.setdefault("replay_strategy", os.getenv("REPLAY_STRATEGY"))
src/finam_core/pipelines/paper_pipeline.py:4621:        if not self._filled_once and os.getenv("EXIT_ON_FILL", "1") == "1":
src/finam_core/pipelines/paper_pipeline.py:4725:            "replay_campaign_id": os.getenv("REPLAY_CAMPAIGN_ID"),
src/finam_core/pipelines/paper_pipeline.py:4726:            "replay_id": os.getenv("REPLAY_ID"),
src/finam_core/pipelines/paper_pipeline.py:4727:            "replay_symbol": os.getenv("REPLAY_SYMBOL"),
src/finam_core/pipelines/paper_pipeline.py:4728:            "replay_timeframe": os.getenv("REPLAY_TIMEFRAME"),
src/finam_core/pipelines/paper_pipeline.py:4729:            "replay_strategy": os.getenv("REPLAY_STRATEGY"),
src/finam_core/pipelines/paper_pipeline.py:4730:            "dataset_source": "replay_campaign" if os.getenv("REPLAY_CAMPAIGN_ID") else "runtime",
src/finam_core/pipelines/paper_pipeline.py:4772:            if os.getenv("ENABLE_INSTITUTIONAL_FLOW_CONTEXT", "1") != "1":
src/finam_core/pipelines/paper_pipeline.py:480:            lookback=int(os.getenv("BR_VOLUME_LOOKBACK", "20")),
src/finam_core/pipelines/paper_pipeline.py:481:            confirm_ratio=float(os.getenv("BR_VOLUME_CONFIRM_RATIO", "1.5")),
src/finam_core/pipelines/paper_pipeline.py:4829:            if os.getenv("ENABLE_SMART_MONEY_CONTEXT", "1") != "1":
src/finam_core/pipelines/paper_pipeline.py:4891:            if os.getenv("ENABLE_INSTITUTIONAL_EXECUTION_GATE", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py:4989:            if os.getenv("ENABLE_ADAPTIVE_REGIME_FILTER", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py:5084:            if os.getenv("ENABLE_EXECUTION_SYMBOL_RESOLVER", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py:5149:            if os.getenv("ENABLE_ADAPTIVE_POSITION_SIZER", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py:5169:                    min_multiplier=float(os.getenv("ADAPTIVE_POSITION_MIN_MULTIPLIER", "0.25")),
src/finam_core/pipelines/paper_pipeline.py:5170:                    max_multiplier=float(os.getenv("ADAPTIVE_POSITION_MAX_MULTIPLIER", "1.50")),
src/finam_core/pipelines/paper_pipeline.py:521:            os.getenv("INCREMENTAL_EXIT_ADVICE_EVERY_SEC", "60")
src/finam_core/pipelines/paper_pipeline.py:5227:            if os.getenv("ENABLE_ENTRY_CONFIDENCE_GATE", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py:5241:                    min_confidence=float(os.getenv("ENTRY_CONFIDENCE_MIN", "0.55")),
src/finam_core/pipelines/paper_pipeline.py:5253:                    heartbeat_sec=float(os.getenv("ENTRY_CONFIDENCE_LOG_SEC", "60")),
src/finam_core/pipelines/paper_pipeline.py:5283:            enabled = os.getenv("ENABLE_RUNTIME_SYMBOL_RELOAD", "0") == "1"
src/finam_core/pipelines/paper_pipeline.py:5287:            interval_sec = float(os.getenv("RUNTIME_SYMBOL_RELOAD_SEC", "300"))
src/finam_core/pipelines/paper_pipeline.py:529:            os.getenv("INCREMENTAL_EXIT_ADVICE_EVERY_SEC", "60")
src/finam_core/pipelines/paper_pipeline.py:5303:                    limit=int(os.getenv("RUNTIME_SYMBOL_RELOAD_LIMIT", "10")),
src/finam_core/pipelines/paper_pipeline.py:5315:                heartbeat_sec=float(os.getenv("RUNTIME_SYMBOL_RELOAD_LOG_SEC", "60")),
src/finam_core/pipelines/paper_pipeline.py:535:            and os.getenv("ENABLE_BR_CONSERVATIVE_BREAKOUT", "0") == "1"
src/finam_core/pipelines/paper_pipeline.py:537:        self.br_breakout_symbol = os.getenv("BR_BREAKOUT_SYMBOL", "BRM6@RTSX")
src/finam_core/pipelines/paper_pipeline.py:5385:                        heartbeat_sec=float(os.getenv("RUNTIME_MD_RESUBSCRIBE_LOG_SEC", "60")),
src/finam_core/pipelines/paper_pipeline.py:5435:            if os.getenv("ENABLE_RUNTIME_ACTIVE_UNIVERSE_GATE", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py:543:            and os.getenv("ENABLE_NG_CONSERVATIVE_BREAKOUT_M1", "0") == "1"
src/finam_core/pipelines/paper_pipeline.py:545:        self.ng_m1_breakout_symbol = os.getenv("NG_M1_BREAKOUT_SYMBOL", "NGM6@RTSX")
src/finam_core/pipelines/paper_pipeline.py:556:            database_url=os.getenv('DATABASE_URL') or os.getenv('POSTGRES_DSN') or '',
src/finam_core/pipelines/paper_pipeline.py:559:            timeframe=os.getenv("BR_BREAKOUT_TIMEFRAME", "M5").strip().upper(),
src/finam_core/pipelines/paper_pipeline.py:563:            database_url=os.getenv("DATABASE_URL") or os.getenv("POSTGRES_DSN") or "",
src/finam_core/pipelines/paper_pipeline.py:5651:        if os.getenv("REPLAY_DISABLE_BR_REGIME", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py:567:            database_url=os.getenv("DATABASE_URL") or os.getenv("POSTGRES_DSN") or "",
src/finam_core/pipelines/paper_pipeline.py:570:                os.getenv("DATABASE_URL") or os.getenv("POSTGRES_DSN") or ""
src/finam_core/pipelines/paper_pipeline.py:572:            timeframe=os.getenv("BR_BREAKOUT_TIMEFRAME", "M5").strip().upper(),
src/finam_core/pipelines/paper_pipeline.py:576:            database_url=os.getenv("DATABASE_URL") or os.getenv("POSTGRES_DSN") or "",
src/finam_core/pipelines/paper_pipeline.py:579:                os.getenv("DATABASE_URL") or os.getenv("POSTGRES_DSN") or ""
src/finam_core/pipelines/paper_pipeline.py:581:            timeframe=os.getenv("BR_BREAKOUT_TIMEFRAME", "M5").strip().upper(),
src/finam_core/pipelines/paper_pipeline.py:5822:        max_len = int(os.getenv("BR_VOLUME_BUFFER_MAX", "200"))
src/finam_core/pipelines/paper_pipeline.py:5874:        if os.getenv("REPLAY_DISABLE_BR_REGIME", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py:5918:        database_url = os.getenv("DATABASE_URL", "")
src/finam_core/pipelines/paper_pipeline.py:592:        self.regime_enabled = os.getenv("REGIME_ENABLE", "1") == "1"
src/finam_core/pipelines/paper_pipeline.py:595:        self.regime_min_atr_pct = float(os.getenv("REGIME_MIN_ATR_PCT", "0.001"))
src/finam_core/pipelines/paper_pipeline.py:596:        self.regime_trend_mode = os.getenv("REGIME_TREND_MODE", "ema")  # ema / simple
src/finam_core/pipelines/paper_pipeline.py:6094:            and os.getenv("REPLAY_ACCUMULATION_MODE", "0") == "1"
src/finam_core/pipelines/paper_pipeline.py:6241:        qty = float(os.getenv("NG_M1_BREAKOUT_QTY", "1"))
src/finam_core/pipelines/paper_pipeline.py:6349:        qty = float(os.getenv("BR_BREAKOUT_QTY", "1"))
src/finam_core/pipelines/paper_pipeline.py:6429:        raw = os.getenv(
src/finam_core/pipelines/paper_pipeline.py:6431:            os.getenv("BREAKOUT_LEVEL_BUCKET_DEFAULT", "0"),
src/finam_core/pipelines/paper_pipeline.py:674:        raw = os.getenv(
src/finam_core/pipelines/paper_pipeline.py:676:            os.getenv("ENTRY_COOLDOWN_SEC_DEFAULT", "60"),
src/finam_core/pipelines/paper_pipeline.py:720:        raw_interval = os.getenv("LOG_THROTTLE_SEC", "30")
src/finam_core/pipelines/paper_pipeline.py:743:        if os.getenv("LOG_DUPLICATE_SIGNAL", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py:799:        max_loss = float(os.getenv("PORTFOLIO_MAX_CUMULATIVE_LOSS", "0") or 0.0)
src/finam_core/pipelines/paper_pipeline.py:803:        dd_limit = float(os.getenv("PORTFOLIO_MAX_DRAWDOWN", "0") or 0.0)
src/finam_core/pipelines/paper_pipeline.py:812:        explicit = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_DSN")
src/finam_core/pipelines/paper_pipeline.py:816:        host = os.getenv("PGHOST", "127.0.0.1")
src/finam_core/pipelines/paper_pipeline.py:817:        port = os.getenv("PGPORT", "5432")
src/finam_core/pipelines/paper_pipeline.py:818:        db = os.getenv("PGDATABASE", "finam")
src/finam_core/pipelines/paper_pipeline.py:819:        user = os.getenv("PGUSER", "finam")
src/finam_core/pipelines/paper_pipeline.py:820:        password = os.getenv("PGPASSWORD", "finam")
src/finam_core/pipelines/paper_pipeline.py:937:        if os.getenv("ENABLE_BROKER_POSITION_SYNC", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py:941:        interval = float(os.getenv("BROKER_POSITION_SYNC_INTERVAL_SEC", "30"))
src/finam_core/pipelines/paper_pipeline.py:952:            account_id = os.getenv("FINAM_ACCOUNT_ID", "").strip()
src/finam_core/pipelines/paper_pipeline.py:958:            endpoint = os.getenv("FINAM_GRPC_ENDPOINT", "api.finam.ru:443").strip()
src/finam_core/pipelines/paper_pipeline.py:966:                timeout=float(os.getenv("BROKER_POSITION_SYNC_TIMEOUT_SEC", "10")),
src/finam_core/pipelines/paper_pipeline.py:998:            heartbeat_sec = float(os.getenv("BROKER_POSITION_SYNC_LOG_HEARTBEAT_SEC", "300"))
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:1190:        pct = float(os.getenv("EXIT_FALLBACK_ATR_PCT", "0.003"))
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:1196:        if os.getenv("ENABLE_TRAILING_ORDER_MANAGER", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:1199:        if os.getenv("ENABLE_POSITION_INTENT_GATE", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:1205:                if now_ts - last_ts >= float(os.getenv("POSITION_INTENT_TRAILING_BLOCK_LOG_INTERVAL_SEC", "300")):
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:1214:        dry_run = os.getenv("TRAILING_ORDER_DRY_RUN", "1") == "1"
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:1252:        if os.getenv("ENABLE_POSITION_ORDER_TRACKER", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:1285:        if os.getenv("ENABLE_POSITION_INTENT_GATE", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:1300:        if os.getenv("ENABLE_BROKER_RECONCILIATION_GATE", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:1313:            allow_repair=os.getenv("ALLOW_PORTFOLIO_REPAIR", "0") == "1",
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:1372:        if os.getenv("ENABLE_POSITION_INTENT_GATE", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:1420:        if os.getenv("ENABLE_BROKER_POSITION_APPLY_TO_PM", "0") == "1" and abs(broker_qty) > 1e-9:
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:1443:        should_log_exit_check = now_ts - last_log_ts >= float(os.getenv(interval_key, default_interval))
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:1446:            abs(float(qty or 0.0)) > 1e-9 or os.getenv("EXIT_ENGINE_DEBUG", "0") == "1"
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:1472:            if now_ts - last_intent_block_ts >= float(os.getenv("POSITION_INTENT_BLOCK_LOG_INTERVAL_SEC", "300")):
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:1485:            if now_ts - last_no_avg_ts >= float(os.getenv("EXIT_NO_AVG_LOG_INTERVAL_SEC", "300")):
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:1583:        if os.getenv("ENABLE_RESTART_RECOVERY", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:1677:        hb = float(heartbeat_sec if heartbeat_sec is not None else os.getenv("PIPE_DEDUP_LOG_HEARTBEAT_SEC", "300"))
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:1695:        if os.getenv("ENABLE_EXECUTION_DECISION_LAYER", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:170:        self.execution_mode = os.getenv("EXECUTION_MODE", "paper").strip().lower()
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:1773:        if os.getenv("ENABLE_ORDER_ROUTER", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:1811:        if os.getenv("ENABLE_EXECUTION_DISPATCHER", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:1831:        if os.getenv("ENABLE_EXECUTION_DISPATCHER_LIVE_ROUTE", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:1837:        allowlist_raw = os.getenv("EXECUTION_DISPATCHER_LIVE_SYMBOL_ALLOWLIST", "BRM6@RTSX")
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:1843:        max_qty = float(os.getenv("EXECUTION_DISPATCHER_LIVE_MAX_QTY", "1"))
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:1923:        if os.getenv("SESSION_OVERRIDE", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:1927:                heartbeat_sec=float(os.getenv("SESSION_OVERRIDE_LOG_SEC", "30")),
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:1949:            if os.getenv("SESSION_OVERRIDE", "0") == "1" or os.getenv("SIMULATE_MARKET", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:1986:                os.getenv("ENABLE_BROKER_POSITION_APPLY_TO_PM", "0") != "1"
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:198:        self._quote_log_every = float(os.getenv("QUOTE_LOG_EVERY", "0"))  # 0 = выключено
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:202:            trail_abs=float(os.getenv("TRAILING_ORDER_TRAIL_ABS", "0.40")),
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:203:            min_replace_step=float(os.getenv("TRAILING_ORDER_MIN_REPLACE_STEP", "0.10")),
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:2050:                if os.getenv("ENABLE_PAPER_FILLS", "1") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:2097:        force_signal_mode = os.getenv("FORCE_ONCE_BUY", "0") == "1"
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:2148:        if os.getenv("SIMULATE_MARKET", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:219:            qty_tolerance=float(os.getenv("BROKER_RECONCILIATION_QTY_TOLERANCE", "1e-9"))
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:223:            qty_tolerance=float(os.getenv("BROKER_RECONCILIATION_QTY_TOLERANCE", "1e-9"))
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:228:            ttl_sec=float(os.getenv("POSITION_INTENT_CACHE_TTL_SEC", "60"))
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:2299:            log_every_sec = float(os.getenv("PIPE_REGIME_LOG_EVERY_SEC", "60"))
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:2320:            if (not is_exit_intent) and (not is_force_intent) and atr_pct < float(os.getenv("ATR_MIN_PCT","0.002")):
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:2323:                log_every_sec = float(os.getenv("PIPE_VOL_LOW_BLOCK_LOG_EVERY_SEC", "60"))
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:232:            ttl_sec=float(os.getenv("EXIT_STATE_TTL_SEC", "30"))
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:2338:                if trend_strength < float(os.getenv("TREND_STRENGTH_MIN","0.0003")) and regime.volatility != "high":  # ключевой параметр
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:2435:            breakout_ttl = float(os.getenv("BREAKOUT_DEDUP_TTL", "30"))
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:2458:            breakout_ttl = float(os.getenv("BREAKOUT_DEDUP_TTL", "30"))
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:254:            tick_size=float(os.getenv("ENTRY_TICK_SIZE", "0.01")),
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:255:            stop_atr_mult=float(os.getenv("ENTRY_STOP_ATR_MULT", "1.5")),
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:256:            take_atr_mult=float(os.getenv("ENTRY_TAKE_ATR_MULT", "2.0")),
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:2627:                if os.getenv("SESSION_OVERRIDE", "0") == "1" or os.getenv("SIMULATE_MARKET", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:2631:                        heartbeat_sec=float(os.getenv("SESSION_OVERRIDE_LOG_SEC", "30")),
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:2644:        override = os.getenv("OVERRIDE_MODE", "0") == "1"
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:2736:                        heartbeat_sec=float(os.getenv("POSITION_INTENT_BLOCK_HEARTBEAT_SEC", "300")),
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:274:            lookback=int(os.getenv("BR_VOLUME_LOOKBACK", "20")),
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:275:            confirm_ratio=float(os.getenv("BR_VOLUME_CONFIRM_RATIO", "1.5")),
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:2774:            if os.getenv("EXECUTION_MODE", "paper").lower() == "real":
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:2789:            if (not is_exit_intent) and (not is_force_intent) and abs(st.get("ema_fast", price) - price) / price < float(os.getenv("IMPULSE_MIN","0.0003")) and regime.volatility != "high":
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:2816:            dedup_ttl = float(os.getenv("SIGNAL_DEDUP_TTL", "2"))
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:2850:                threshold = float(os.getenv("PYRAMIDING_THRESHOLD", "0.0003"))  # 0.03% (ускорение)
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:2877:        base_cooldown = float(os.getenv("TRADE_COOLDOWN_SEC", "45"))
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:2909:            max_trades_per_hour = int(os.getenv("MAX_TRADES_PER_HOUR", "5"))
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:2910:            max_trades_per_symbol = int(os.getenv("MAX_TRADES_PER_SYMBOL", "2"))
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:2980:            if os.getenv("RISK_SOFT", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:299:            os.getenv("EXECUTION_MODE", "paper").lower() == "paper"
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:300:            and os.getenv("ENABLE_BR_CONSERVATIVE_BREAKOUT", "0") == "1"
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:302:        self.br_breakout_symbol = os.getenv("BR_BREAKOUT_SYMBOL", "BRM6@RTSX")
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:3030:                    max_portfolio_heat=float(os.getenv("MAX_PORTFOLIO_HEAT", "0.30")),
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:3031:                    max_symbol_heat=float(os.getenv("MAX_SYMBOL_HEAT", "0.10")),
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:3032:                    max_margin_utilization=float(os.getenv("MAX_MARGIN_UTILIZATION", "0.65")),
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:3033:                    max_daily_loss_pct=float(os.getenv("MAX_DAILY_LOSS_PCT", "0.02")),
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:3034:                    max_drawdown_pct=float(os.getenv("MAX_DRAWDOWN_PCT", "0.03")),
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:3084:                max_heat = float(os.getenv("MAX_PORTFOLIO_HEAT", "0.3"))  # 30% default
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:3106:                max_symbol_heat = float(os.getenv("MAX_SYMBOL_HEAT", "0.1"))  # 10% default
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:313:        self.regime_enabled = os.getenv("REGIME_ENABLE", "1") == "1"
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:3140:                max_dd = float(os.getenv("MAX_DRAWDOWN", "-0.03"))  # -3%
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:3141:                max_daily_loss = float(os.getenv("MAX_DAILY_LOSS", "-0.02"))  # -2%
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:316:        self.regime_min_atr_pct = float(os.getenv("REGIME_MIN_ATR_PCT", "0.001"))
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:317:        self.regime_trend_mode = os.getenv("REGIME_TREND_MODE", "ema")  # ema / simple
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:3227:        if os.getenv("ENABLE_PAPER_FILLS", "1") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:3530:        if not self._filled_once and os.getenv("EXIT_ON_FILL", "1") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:3593:            "execution_mode": os.getenv("EXECUTION_MODE", "paper"),
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:3878:        if os.getenv("REPLAY_DISABLE_BR_REGIME", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:394:        raw = os.getenv(
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:396:            os.getenv("ENTRY_COOLDOWN_SEC_DEFAULT", "60"),
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:4049:        max_len = int(os.getenv("BR_VOLUME_BUFFER_MAX", "200"))
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:4101:        if os.getenv("REPLAY_DISABLE_BR_REGIME", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:4145:        if os.getenv("EXECUTION_MODE", "paper").lower() != "paper":
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:4247:                if os.getenv("ENABLE_PAPER_FILLS", "1") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:4359:        qty = float(os.getenv("BR_BREAKOUT_QTY", "1"))
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:4369:            "execution_mode": os.getenv("EXECUTION_MODE", "paper"),
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:440:        raw_interval = os.getenv("LOG_THROTTLE_SEC", "30")
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:4439:        raw = os.getenv(
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:4441:            os.getenv("BREAKOUT_LEVEL_BUCKET_DEFAULT", "0"),
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:463:        if os.getenv("LOG_DUPLICATE_SIGNAL", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:519:        max_loss = float(os.getenv("PORTFOLIO_MAX_CUMULATIVE_LOSS", "0") or 0.0)
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:523:        dd_limit = float(os.getenv("PORTFOLIO_MAX_DRAWDOWN", "0") or 0.0)
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:532:        explicit = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_DSN")
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:536:        host = os.getenv("PGHOST", "127.0.0.1")
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:537:        port = os.getenv("PGPORT", "5432")
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:538:        db = os.getenv("PGDATABASE", "finam")
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:539:        user = os.getenv("PGUSER", "finam")
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:540:        password = os.getenv("PGPASSWORD", "finam")
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:657:        if os.getenv("ENABLE_BROKER_POSITION_SYNC", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:661:        interval = float(os.getenv("BROKER_POSITION_SYNC_INTERVAL_SEC", "30"))
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:672:            account_id = os.getenv("FINAM_ACCOUNT_ID", "").strip()
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:678:            endpoint = os.getenv("FINAM_GRPC_ENDPOINT", "api.finam.ru:443").strip()
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:67:PIPE_DEBUG = os.getenv("PIPE_DEBUG", "0") == "1"
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:686:                timeout=float(os.getenv("BROKER_POSITION_SYNC_TIMEOUT_SEC", "10")),
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:718:            heartbeat_sec = float(os.getenv("BROKER_POSITION_SYNC_LOG_HEARTBEAT_SEC", "300"))
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:740:        if os.getenv("BROKER_POSITION_HARD_GATE_USE_BROKER_AS_LOCAL", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:767:        if os.getenv("ENABLE_BROKER_POSITION_HARD_GATE", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:770:        tolerance = float(os.getenv("BROKER_POSITION_HARD_GATE_QTY_TOLERANCE", "1e-9"))
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:801:        if os.getenv("ENABLE_BROKER_PROTECTION_GATE", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:841:        if os.getenv("ENABLE_BROKER_POSITION_HARD_GATE", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:897:        if os.getenv("ENABLE_OCO_ORDER_MANAGER", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:934:        if os.getenv("ENABLE_SUBSCRIBE_ORDERS_LISTENER", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:942:        poll_interval = float(os.getenv("SUBSCRIBE_ORDERS_POLL_INTERVAL_SEC", "15"))
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:950:            max_events = int(os.getenv("SUBSCRIBE_ORDERS_MAX_EVENTS_PER_POLL", "1"))
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:960:                heartbeat = float(os.getenv("SUBSCRIBE_ORDERS_APPLIED_HEARTBEAT_SEC", "300"))
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:973:                    heartbeat_sec=float(os.getenv("SUBSCRIBE_ORDERS_ERROR_HEARTBEAT_SEC", "300")),
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:982:        if os.getenv("ENABLE_BROKER_OPEN_ORDERS_SYNC", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_log_dedup_20260514_103819:985:        interval_sec = float(os.getenv("BROKER_OPEN_ORDERS_SYNC_INTERVAL_SEC", "30"))
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:1220:        pct = float(os.getenv("EXIT_FALLBACK_ATR_PCT", "0.003"))
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:1226:        if os.getenv("ENABLE_TRAILING_ORDER_MANAGER", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:1229:        if os.getenv("ENABLE_POSITION_INTENT_GATE", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:1235:                if now_ts - last_ts >= float(os.getenv("POSITION_INTENT_TRAILING_BLOCK_LOG_INTERVAL_SEC", "300")):
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:1244:        dry_run = os.getenv("TRAILING_ORDER_DRY_RUN", "1") == "1"
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:1297:        if os.getenv("ENABLE_POSITION_ORDER_TRACKER", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:1330:        if os.getenv("ENABLE_POSITION_INTENT_GATE", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:1345:        if os.getenv("ENABLE_BROKER_RECONCILIATION_GATE", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:1358:            allow_repair=os.getenv("ALLOW_PORTFOLIO_REPAIR", "0") == "1",
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:1417:        if os.getenv("ENABLE_POSITION_INTENT_GATE", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:1465:        if os.getenv("ENABLE_BROKER_POSITION_APPLY_TO_PM", "0") == "1" and abs(broker_qty) > 1e-9:
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:1488:        should_log_exit_check = now_ts - last_log_ts >= float(os.getenv(interval_key, default_interval))
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:1491:            abs(float(qty or 0.0)) > 1e-9 or os.getenv("EXIT_ENGINE_DEBUG", "0") == "1"
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:1517:            if now_ts - last_intent_block_ts >= float(os.getenv("POSITION_INTENT_BLOCK_LOG_INTERVAL_SEC", "300")):
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:1530:            if now_ts - last_no_avg_ts >= float(os.getenv("EXIT_NO_AVG_LOG_INTERVAL_SEC", "300")):
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:1641:        if os.getenv("ENABLE_RESTART_RECOVERY", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:172:        self.execution_mode = os.getenv("EXECUTION_MODE", "paper").strip().lower()
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:1735:        hb = float(heartbeat_sec if heartbeat_sec is not None else os.getenv("PIPE_DEDUP_LOG_HEARTBEAT_SEC", "300"))
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:1753:        if os.getenv("ENABLE_EXECUTION_DECISION_LAYER", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:1831:        if os.getenv("ENABLE_ORDER_ROUTER", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:1869:        if os.getenv("ENABLE_EXECUTION_DISPATCHER", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:1889:        if os.getenv("ENABLE_EXECUTION_DISPATCHER_LIVE_ROUTE", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:1895:        allowlist_raw = os.getenv("EXECUTION_DISPATCHER_LIVE_SYMBOL_ALLOWLIST", "BRM6@RTSX")
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:1901:        max_qty = float(os.getenv("EXECUTION_DISPATCHER_LIVE_MAX_QTY", "1"))
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:1981:        if os.getenv("SESSION_OVERRIDE", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:1985:                heartbeat_sec=float(os.getenv("SESSION_OVERRIDE_LOG_SEC", "30")),
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:2007:            if os.getenv("SESSION_OVERRIDE", "0") == "1" or os.getenv("SIMULATE_MARKET", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:200:        self._quote_log_every = float(os.getenv("QUOTE_LOG_EVERY", "0"))  # 0 = выключено
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:2044:                os.getenv("ENABLE_BROKER_POSITION_APPLY_TO_PM", "0") != "1"
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:204:            trail_abs=float(os.getenv("TRAILING_ORDER_TRAIL_ABS", "0.40")),
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:205:            min_replace_step=float(os.getenv("TRAILING_ORDER_MIN_REPLACE_STEP", "0.10")),
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:2108:                if os.getenv("ENABLE_PAPER_FILLS", "1") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:2155:        force_signal_mode = os.getenv("FORCE_ONCE_BUY", "0") == "1"
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:2206:        if os.getenv("SIMULATE_MARKET", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:222:            qty_tolerance=float(os.getenv("BROKER_RECONCILIATION_QTY_TOLERANCE", "1e-9"))
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:226:            qty_tolerance=float(os.getenv("BROKER_RECONCILIATION_QTY_TOLERANCE", "1e-9"))
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:231:            ttl_sec=float(os.getenv("POSITION_INTENT_CACHE_TTL_SEC", "60"))
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:2357:            log_every_sec = float(os.getenv("PIPE_REGIME_LOG_EVERY_SEC", "60"))
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:235:            ttl_sec=float(os.getenv("EXIT_STATE_TTL_SEC", "30"))
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:2378:            if (not is_exit_intent) and (not is_force_intent) and atr_pct < float(os.getenv("ATR_MIN_PCT","0.002")):
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:2381:                log_every_sec = float(os.getenv("PIPE_VOL_LOW_BLOCK_LOG_EVERY_SEC", "60"))
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:2396:                if trend_strength < float(os.getenv("TREND_STRENGTH_MIN","0.0003")) and regime.volatility != "high":  # ключевой параметр
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:2499:            breakout_ttl = float(os.getenv("BREAKOUT_DEDUP_TTL", "30"))
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:2522:            breakout_ttl = float(os.getenv("BREAKOUT_DEDUP_TTL", "30"))
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:257:            tick_size=float(os.getenv("ENTRY_TICK_SIZE", "0.01")),
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:258:            stop_atr_mult=float(os.getenv("ENTRY_STOP_ATR_MULT", "1.5")),
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:259:            take_atr_mult=float(os.getenv("ENTRY_TAKE_ATR_MULT", "2.0")),
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:2691:                if os.getenv("SESSION_OVERRIDE", "0") == "1" or os.getenv("SIMULATE_MARKET", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:2695:                        heartbeat_sec=float(os.getenv("SESSION_OVERRIDE_LOG_SEC", "30")),
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:2708:        override = os.getenv("OVERRIDE_MODE", "0") == "1"
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:277:            lookback=int(os.getenv("BR_VOLUME_LOOKBACK", "20")),
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:278:            confirm_ratio=float(os.getenv("BR_VOLUME_CONFIRM_RATIO", "1.5")),
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:2800:                        heartbeat_sec=float(os.getenv("POSITION_INTENT_BLOCK_HEARTBEAT_SEC", "300")),
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:2838:            if os.getenv("EXECUTION_MODE", "paper").lower() == "real":
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:2853:            if (not is_exit_intent) and (not is_force_intent) and abs(st.get("ema_fast", price) - price) / price < float(os.getenv("IMPULSE_MIN","0.0003")) and regime.volatility != "high":
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:2880:            dedup_ttl = float(os.getenv("SIGNAL_DEDUP_TTL", "2"))
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:2914:                threshold = float(os.getenv("PYRAMIDING_THRESHOLD", "0.0003"))  # 0.03% (ускорение)
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:2941:        base_cooldown = float(os.getenv("TRADE_COOLDOWN_SEC", "45"))
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:2973:            max_trades_per_hour = int(os.getenv("MAX_TRADES_PER_HOUR", "5"))
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:2974:            max_trades_per_symbol = int(os.getenv("MAX_TRADES_PER_SYMBOL", "2"))
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:302:            os.getenv("EXECUTION_MODE", "paper").lower() == "paper"
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:303:            and os.getenv("ENABLE_BR_CONSERVATIVE_BREAKOUT", "0") == "1"
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:3044:            if os.getenv("RISK_SOFT", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:305:        self.br_breakout_symbol = os.getenv("BR_BREAKOUT_SYMBOL", "BRM6@RTSX")
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:3094:                    max_portfolio_heat=float(os.getenv("MAX_PORTFOLIO_HEAT", "0.30")),
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:3095:                    max_symbol_heat=float(os.getenv("MAX_SYMBOL_HEAT", "0.10")),
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:3096:                    max_margin_utilization=float(os.getenv("MAX_MARGIN_UTILIZATION", "0.65")),
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:3097:                    max_daily_loss_pct=float(os.getenv("MAX_DAILY_LOSS_PCT", "0.02")),
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:3098:                    max_drawdown_pct=float(os.getenv("MAX_DRAWDOWN_PCT", "0.03")),
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:3148:                max_heat = float(os.getenv("MAX_PORTFOLIO_HEAT", "0.3"))  # 30% default
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:316:        self.regime_enabled = os.getenv("REGIME_ENABLE", "1") == "1"
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:3170:                max_symbol_heat = float(os.getenv("MAX_SYMBOL_HEAT", "0.1"))  # 10% default
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:319:        self.regime_min_atr_pct = float(os.getenv("REGIME_MIN_ATR_PCT", "0.001"))
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:3204:                max_dd = float(os.getenv("MAX_DRAWDOWN", "-0.03"))  # -3%
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:3205:                max_daily_loss = float(os.getenv("MAX_DAILY_LOSS", "-0.02"))  # -2%
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:320:        self.regime_trend_mode = os.getenv("REGIME_TREND_MODE", "ema")  # ema / simple
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:3291:        if os.getenv("ENABLE_PAPER_FILLS", "1") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:3628:        if not self._filled_once and os.getenv("EXIT_ON_FILL", "1") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:3691:            "execution_mode": os.getenv("EXECUTION_MODE", "paper"),
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:397:        raw = os.getenv(
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:3991:        if os.getenv("REPLAY_DISABLE_BR_REGIME", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:399:            os.getenv("ENTRY_COOLDOWN_SEC_DEFAULT", "60"),
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:4162:        max_len = int(os.getenv("BR_VOLUME_BUFFER_MAX", "200"))
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:4214:        if os.getenv("REPLAY_DISABLE_BR_REGIME", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:4258:        if os.getenv("EXECUTION_MODE", "paper").lower() != "paper":
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:4360:                if os.getenv("ENABLE_PAPER_FILLS", "1") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:443:        raw_interval = os.getenv("LOG_THROTTLE_SEC", "30")
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:4472:        qty = float(os.getenv("BR_BREAKOUT_QTY", "1"))
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:4482:            "execution_mode": os.getenv("EXECUTION_MODE", "paper"),
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:4552:        raw = os.getenv(
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:4554:            os.getenv("BREAKOUT_LEVEL_BUCKET_DEFAULT", "0"),
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:466:        if os.getenv("LOG_DUPLICATE_SIGNAL", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:522:        max_loss = float(os.getenv("PORTFOLIO_MAX_CUMULATIVE_LOSS", "0") or 0.0)
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:526:        dd_limit = float(os.getenv("PORTFOLIO_MAX_DRAWDOWN", "0") or 0.0)
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:535:        explicit = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_DSN")
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:539:        host = os.getenv("PGHOST", "127.0.0.1")
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:540:        port = os.getenv("PGPORT", "5432")
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:541:        db = os.getenv("PGDATABASE", "finam")
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:542:        user = os.getenv("PGUSER", "finam")
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:543:        password = os.getenv("PGPASSWORD", "finam")
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:660:        if os.getenv("ENABLE_BROKER_POSITION_SYNC", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:664:        interval = float(os.getenv("BROKER_POSITION_SYNC_INTERVAL_SEC", "30"))
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:675:            account_id = os.getenv("FINAM_ACCOUNT_ID", "").strip()
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:681:            endpoint = os.getenv("FINAM_GRPC_ENDPOINT", "api.finam.ru:443").strip()
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:689:                timeout=float(os.getenv("BROKER_POSITION_SYNC_TIMEOUT_SEC", "10")),
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:69:PIPE_DEBUG = os.getenv("PIPE_DEBUG", "0") == "1"
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:721:            heartbeat_sec = float(os.getenv("BROKER_POSITION_SYNC_LOG_HEARTBEAT_SEC", "300"))
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:743:        if os.getenv("BROKER_POSITION_HARD_GATE_USE_BROKER_AS_LOCAL", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:770:        if os.getenv("ENABLE_BROKER_POSITION_HARD_GATE", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:773:        tolerance = float(os.getenv("BROKER_POSITION_HARD_GATE_QTY_TOLERANCE", "1e-9"))
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:804:        if os.getenv("ENABLE_BROKER_PROTECTION_GATE", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:844:        if os.getenv("ENABLE_BROKER_POSITION_HARD_GATE", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:900:        if os.getenv("ENABLE_OCO_ORDER_MANAGER", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:937:        if os.getenv("ENABLE_SUBSCRIBE_ORDERS_LISTENER", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:945:        poll_interval = float(os.getenv("SUBSCRIBE_ORDERS_POLL_INTERVAL_SEC", "15"))
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:953:            max_events = int(os.getenv("SUBSCRIBE_ORDERS_MAX_EVENTS_PER_POLL", "1"))
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:963:                heartbeat = float(os.getenv("SUBSCRIBE_ORDERS_APPLIED_HEARTBEAT_SEC", "300"))
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:976:                    heartbeat_sec=float(os.getenv("SUBSCRIBE_ORDERS_ERROR_HEARTBEAT_SEC", "300")),
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:985:        if os.getenv("ENABLE_BROKER_OPEN_ORDERS_SYNC", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125318:988:        interval_sec = float(os.getenv("BROKER_OPEN_ORDERS_SYNC_INTERVAL_SEC", "30"))
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:1225:        pct = float(os.getenv("EXIT_FALLBACK_ATR_PCT", "0.003"))
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:1238:        if os.getenv("ENABLE_PROFIT_LOCK_ENGINE", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:1246:            base_stop = float(stop_price or (entry_price * (1.0 - float(os.getenv("PROFIT_LOCK_DEFAULT_STOP_PCT", "0.01")))))
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:1277:        if os.getenv("ENABLE_TRAILING_ORDER_MANAGER", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:1280:        if os.getenv("ENABLE_POSITION_INTENT_GATE", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:1286:                if now_ts - last_ts >= float(os.getenv("POSITION_INTENT_TRAILING_BLOCK_LOG_INTERVAL_SEC", "300")):
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:1295:        dry_run = os.getenv("TRAILING_ORDER_DRY_RUN", "1") == "1"
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:1348:        if os.getenv("ENABLE_POSITION_ORDER_TRACKER", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:1381:        if os.getenv("ENABLE_POSITION_INTENT_GATE", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:1396:        if os.getenv("ENABLE_BROKER_RECONCILIATION_GATE", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:1409:            allow_repair=os.getenv("ALLOW_PORTFOLIO_REPAIR", "0") == "1",
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:1468:        if os.getenv("ENABLE_POSITION_INTENT_GATE", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:1516:        if os.getenv("ENABLE_BROKER_POSITION_APPLY_TO_PM", "0") == "1" and abs(broker_qty) > 1e-9:
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:1539:        should_log_exit_check = now_ts - last_log_ts >= float(os.getenv(interval_key, default_interval))
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:1542:            abs(float(qty or 0.0)) > 1e-9 or os.getenv("EXIT_ENGINE_DEBUG", "0") == "1"
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:1576:            if now_ts - last_intent_block_ts >= float(os.getenv("POSITION_INTENT_BLOCK_LOG_INTERVAL_SEC", "300")):
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:1589:            if now_ts - last_no_avg_ts >= float(os.getenv("EXIT_NO_AVG_LOG_INTERVAL_SEC", "300")):
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:1700:        if os.getenv("ENABLE_RESTART_RECOVERY", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:173:        self.execution_mode = os.getenv("EXECUTION_MODE", "paper").strip().lower()
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:1794:        hb = float(heartbeat_sec if heartbeat_sec is not None else os.getenv("PIPE_DEDUP_LOG_HEARTBEAT_SEC", "300"))
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:1812:        if os.getenv("ENABLE_EXECUTION_DECISION_LAYER", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:1890:        if os.getenv("ENABLE_ORDER_ROUTER", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:1928:        if os.getenv("ENABLE_EXECUTION_DISPATCHER", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:1948:        if os.getenv("ENABLE_EXECUTION_DISPATCHER_LIVE_ROUTE", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:1954:        allowlist_raw = os.getenv("EXECUTION_DISPATCHER_LIVE_SYMBOL_ALLOWLIST", "BRM6@RTSX")
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:1960:        max_qty = float(os.getenv("EXECUTION_DISPATCHER_LIVE_MAX_QTY", "1"))
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:201:        self._quote_log_every = float(os.getenv("QUOTE_LOG_EVERY", "0"))  # 0 = выключено
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:2040:        if os.getenv("SESSION_OVERRIDE", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:2044:                heartbeat_sec=float(os.getenv("SESSION_OVERRIDE_LOG_SEC", "30")),
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:205:            trail_abs=float(os.getenv("TRAILING_ORDER_TRAIL_ABS", "0.40")),
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:2066:            if os.getenv("SESSION_OVERRIDE", "0") == "1" or os.getenv("SIMULATE_MARKET", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:206:            min_replace_step=float(os.getenv("TRAILING_ORDER_MIN_REPLACE_STEP", "0.10")),
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:2103:                os.getenv("ENABLE_BROKER_POSITION_APPLY_TO_PM", "0") != "1"
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:2167:                if os.getenv("ENABLE_PAPER_FILLS", "1") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:2214:        force_signal_mode = os.getenv("FORCE_ONCE_BUY", "0") == "1"
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:2265:        if os.getenv("SIMULATE_MARKET", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:227:            qty_tolerance=float(os.getenv("BROKER_RECONCILIATION_QTY_TOLERANCE", "1e-9"))
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:231:            qty_tolerance=float(os.getenv("BROKER_RECONCILIATION_QTY_TOLERANCE", "1e-9"))
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:236:            ttl_sec=float(os.getenv("POSITION_INTENT_CACHE_TTL_SEC", "60"))
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:240:            ttl_sec=float(os.getenv("EXIT_STATE_TTL_SEC", "30"))
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:2416:            log_every_sec = float(os.getenv("PIPE_REGIME_LOG_EVERY_SEC", "60"))
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:2437:            if (not is_exit_intent) and (not is_force_intent) and atr_pct < float(os.getenv("ATR_MIN_PCT","0.002")):
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:2440:                log_every_sec = float(os.getenv("PIPE_VOL_LOW_BLOCK_LOG_EVERY_SEC", "60"))
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:2455:                if trend_strength < float(os.getenv("TREND_STRENGTH_MIN","0.0003")) and regime.volatility != "high":  # ключевой параметр
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:2558:            breakout_ttl = float(os.getenv("BREAKOUT_DEDUP_TTL", "30"))
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:2581:            breakout_ttl = float(os.getenv("BREAKOUT_DEDUP_TTL", "30"))
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:262:            tick_size=float(os.getenv("ENTRY_TICK_SIZE", "0.01")),
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:263:            stop_atr_mult=float(os.getenv("ENTRY_STOP_ATR_MULT", "1.5")),
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:264:            take_atr_mult=float(os.getenv("ENTRY_TAKE_ATR_MULT", "2.0")),
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:2750:                if os.getenv("SESSION_OVERRIDE", "0") == "1" or os.getenv("SIMULATE_MARKET", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:2754:                        heartbeat_sec=float(os.getenv("SESSION_OVERRIDE_LOG_SEC", "30")),
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:2767:        override = os.getenv("OVERRIDE_MODE", "0") == "1"
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:282:            lookback=int(os.getenv("BR_VOLUME_LOOKBACK", "20")),
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:283:            confirm_ratio=float(os.getenv("BR_VOLUME_CONFIRM_RATIO", "1.5")),
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:2859:                        heartbeat_sec=float(os.getenv("POSITION_INTENT_BLOCK_HEARTBEAT_SEC", "300")),
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:2897:            if os.getenv("EXECUTION_MODE", "paper").lower() == "real":
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:2912:            if (not is_exit_intent) and (not is_force_intent) and abs(st.get("ema_fast", price) - price) / price < float(os.getenv("IMPULSE_MIN","0.0003")) and regime.volatility != "high":
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:2939:            dedup_ttl = float(os.getenv("SIGNAL_DEDUP_TTL", "2"))
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:2973:                threshold = float(os.getenv("PYRAMIDING_THRESHOLD", "0.0003"))  # 0.03% (ускорение)
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:3000:        base_cooldown = float(os.getenv("TRADE_COOLDOWN_SEC", "45"))
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:3032:            max_trades_per_hour = int(os.getenv("MAX_TRADES_PER_HOUR", "5"))
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:3033:            max_trades_per_symbol = int(os.getenv("MAX_TRADES_PER_SYMBOL", "2"))
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:307:            os.getenv("EXECUTION_MODE", "paper").lower() == "paper"
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:308:            and os.getenv("ENABLE_BR_CONSERVATIVE_BREAKOUT", "0") == "1"
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:3103:            if os.getenv("RISK_SOFT", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:310:        self.br_breakout_symbol = os.getenv("BR_BREAKOUT_SYMBOL", "BRM6@RTSX")
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:3153:                    max_portfolio_heat=float(os.getenv("MAX_PORTFOLIO_HEAT", "0.30")),
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:3154:                    max_symbol_heat=float(os.getenv("MAX_SYMBOL_HEAT", "0.10")),
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:3155:                    max_margin_utilization=float(os.getenv("MAX_MARGIN_UTILIZATION", "0.65")),
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:3156:                    max_daily_loss_pct=float(os.getenv("MAX_DAILY_LOSS_PCT", "0.02")),
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:3157:                    max_drawdown_pct=float(os.getenv("MAX_DRAWDOWN_PCT", "0.03")),
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:3207:                max_heat = float(os.getenv("MAX_PORTFOLIO_HEAT", "0.3"))  # 30% default
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:321:        self.regime_enabled = os.getenv("REGIME_ENABLE", "1") == "1"
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:3229:                max_symbol_heat = float(os.getenv("MAX_SYMBOL_HEAT", "0.1"))  # 10% default
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:324:        self.regime_min_atr_pct = float(os.getenv("REGIME_MIN_ATR_PCT", "0.001"))
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:325:        self.regime_trend_mode = os.getenv("REGIME_TREND_MODE", "ema")  # ema / simple
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:3263:                max_dd = float(os.getenv("MAX_DRAWDOWN", "-0.03"))  # -3%
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:3264:                max_daily_loss = float(os.getenv("MAX_DAILY_LOSS", "-0.02"))  # -2%
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:3350:        if os.getenv("ENABLE_PAPER_FILLS", "1") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:3687:        if not self._filled_once and os.getenv("EXIT_ON_FILL", "1") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:3750:            "execution_mode": os.getenv("EXECUTION_MODE", "paper"),
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:402:        raw = os.getenv(
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:404:            os.getenv("ENTRY_COOLDOWN_SEC_DEFAULT", "60"),
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:4050:        if os.getenv("REPLAY_DISABLE_BR_REGIME", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:4221:        max_len = int(os.getenv("BR_VOLUME_BUFFER_MAX", "200"))
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:4273:        if os.getenv("REPLAY_DISABLE_BR_REGIME", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:4317:        if os.getenv("EXECUTION_MODE", "paper").lower() != "paper":
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:4419:                if os.getenv("ENABLE_PAPER_FILLS", "1") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:448:        raw_interval = os.getenv("LOG_THROTTLE_SEC", "30")
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:4531:        qty = float(os.getenv("BR_BREAKOUT_QTY", "1"))
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:4541:            "execution_mode": os.getenv("EXECUTION_MODE", "paper"),
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:4611:        raw = os.getenv(
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:4613:            os.getenv("BREAKOUT_LEVEL_BUCKET_DEFAULT", "0"),
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:471:        if os.getenv("LOG_DUPLICATE_SIGNAL", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:527:        max_loss = float(os.getenv("PORTFOLIO_MAX_CUMULATIVE_LOSS", "0") or 0.0)
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:531:        dd_limit = float(os.getenv("PORTFOLIO_MAX_DRAWDOWN", "0") or 0.0)
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:540:        explicit = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_DSN")
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:544:        host = os.getenv("PGHOST", "127.0.0.1")
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:545:        port = os.getenv("PGPORT", "5432")
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:546:        db = os.getenv("PGDATABASE", "finam")
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:547:        user = os.getenv("PGUSER", "finam")
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:548:        password = os.getenv("PGPASSWORD", "finam")
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:665:        if os.getenv("ENABLE_BROKER_POSITION_SYNC", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:669:        interval = float(os.getenv("BROKER_POSITION_SYNC_INTERVAL_SEC", "30"))
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:680:            account_id = os.getenv("FINAM_ACCOUNT_ID", "").strip()
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:686:            endpoint = os.getenv("FINAM_GRPC_ENDPOINT", "api.finam.ru:443").strip()
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:694:                timeout=float(os.getenv("BROKER_POSITION_SYNC_TIMEOUT_SEC", "10")),
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:70:PIPE_DEBUG = os.getenv("PIPE_DEBUG", "0") == "1"
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:726:            heartbeat_sec = float(os.getenv("BROKER_POSITION_SYNC_LOG_HEARTBEAT_SEC", "300"))
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:748:        if os.getenv("BROKER_POSITION_HARD_GATE_USE_BROKER_AS_LOCAL", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:775:        if os.getenv("ENABLE_BROKER_POSITION_HARD_GATE", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:778:        tolerance = float(os.getenv("BROKER_POSITION_HARD_GATE_QTY_TOLERANCE", "1e-9"))
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:809:        if os.getenv("ENABLE_BROKER_PROTECTION_GATE", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:849:        if os.getenv("ENABLE_BROKER_POSITION_HARD_GATE", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:905:        if os.getenv("ENABLE_OCO_ORDER_MANAGER", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:942:        if os.getenv("ENABLE_SUBSCRIBE_ORDERS_LISTENER", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:950:        poll_interval = float(os.getenv("SUBSCRIBE_ORDERS_POLL_INTERVAL_SEC", "15"))
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:958:            max_events = int(os.getenv("SUBSCRIBE_ORDERS_MAX_EVENTS_PER_POLL", "1"))
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:968:                heartbeat = float(os.getenv("SUBSCRIBE_ORDERS_APPLIED_HEARTBEAT_SEC", "300"))
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:981:                    heartbeat_sec=float(os.getenv("SUBSCRIBE_ORDERS_ERROR_HEARTBEAT_SEC", "300")),
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:990:        if os.getenv("ENABLE_BROKER_OPEN_ORDERS_SYNC", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_profit_lock_20260514_125724:993:        interval_sec = float(os.getenv("BROKER_OPEN_ORDERS_SYNC_INTERVAL_SEC", "30"))
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:1231:        pct = float(os.getenv("EXIT_FALLBACK_ATR_PCT", "0.003"))
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:1244:        if os.getenv("ENABLE_TAKE_PROFIT_ENGINE", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:1252:            base_stop = float(stop_price or (entry_price * (1.0 - float(os.getenv("TAKE_PROFIT_DEFAULT_STOP_PCT", "0.01")))))
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:1300:        if os.getenv("ENABLE_PROFIT_LOCK_ENGINE", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:1308:            base_stop = float(stop_price or (entry_price * (1.0 - float(os.getenv("PROFIT_LOCK_DEFAULT_STOP_PCT", "0.01")))))
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:1356:        if os.getenv("ENABLE_TRAILING_ORDER_MANAGER", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:1359:        if os.getenv("ENABLE_POSITION_INTENT_GATE", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:1365:                if now_ts - last_ts >= float(os.getenv("POSITION_INTENT_TRAILING_BLOCK_LOG_INTERVAL_SEC", "300")):
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:1374:        dry_run = os.getenv("TRAILING_ORDER_DRY_RUN", "1") == "1"
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:1427:        if os.getenv("ENABLE_POSITION_ORDER_TRACKER", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:1460:        if os.getenv("ENABLE_POSITION_INTENT_GATE", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:1475:        if os.getenv("ENABLE_BROKER_RECONCILIATION_GATE", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:1488:            allow_repair=os.getenv("ALLOW_PORTFOLIO_REPAIR", "0") == "1",
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:1547:        if os.getenv("ENABLE_POSITION_INTENT_GATE", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:1595:        if os.getenv("ENABLE_BROKER_POSITION_APPLY_TO_PM", "0") == "1" and abs(broker_qty) > 1e-9:
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:1618:        should_log_exit_check = now_ts - last_log_ts >= float(os.getenv(interval_key, default_interval))
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:1621:            abs(float(qty or 0.0)) > 1e-9 or os.getenv("EXIT_ENGINE_DEBUG", "0") == "1"
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:1662:            if now_ts - last_intent_block_ts >= float(os.getenv("POSITION_INTENT_BLOCK_LOG_INTERVAL_SEC", "300")):
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:1675:            if now_ts - last_no_avg_ts >= float(os.getenv("EXIT_NO_AVG_LOG_INTERVAL_SEC", "300")):
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:176:        self.execution_mode = os.getenv("EXECUTION_MODE", "paper").strip().lower()
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:1786:        if os.getenv("ENABLE_RESTART_RECOVERY", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:1880:        hb = float(heartbeat_sec if heartbeat_sec is not None else os.getenv("PIPE_DEDUP_LOG_HEARTBEAT_SEC", "300"))
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:1898:        if os.getenv("ENABLE_EXECUTION_DECISION_LAYER", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:1976:        if os.getenv("ENABLE_ORDER_ROUTER", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:2014:        if os.getenv("ENABLE_EXECUTION_DISPATCHER", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:2034:        if os.getenv("ENABLE_EXECUTION_DISPATCHER_LIVE_ROUTE", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:2040:        allowlist_raw = os.getenv("EXECUTION_DISPATCHER_LIVE_SYMBOL_ALLOWLIST", "BRM6@RTSX")
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:2046:        max_qty = float(os.getenv("EXECUTION_DISPATCHER_LIVE_MAX_QTY", "1"))
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:204:        self._quote_log_every = float(os.getenv("QUOTE_LOG_EVERY", "0"))  # 0 = выключено
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:208:            trail_abs=float(os.getenv("TRAILING_ORDER_TRAIL_ABS", "0.40")),
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:209:            min_replace_step=float(os.getenv("TRAILING_ORDER_MIN_REPLACE_STEP", "0.10")),
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:2126:        if os.getenv("SESSION_OVERRIDE", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:2130:                heartbeat_sec=float(os.getenv("SESSION_OVERRIDE_LOG_SEC", "30")),
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:2152:            if os.getenv("SESSION_OVERRIDE", "0") == "1" or os.getenv("SIMULATE_MARKET", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:2189:                os.getenv("ENABLE_BROKER_POSITION_APPLY_TO_PM", "0") != "1"
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:2253:                if os.getenv("ENABLE_PAPER_FILLS", "1") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:2300:        force_signal_mode = os.getenv("FORCE_ONCE_BUY", "0") == "1"
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:233:            qty_tolerance=float(os.getenv("BROKER_RECONCILIATION_QTY_TOLERANCE", "1e-9"))
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:2351:        if os.getenv("SIMULATE_MARKET", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:237:            qty_tolerance=float(os.getenv("BROKER_RECONCILIATION_QTY_TOLERANCE", "1e-9"))
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:242:            ttl_sec=float(os.getenv("POSITION_INTENT_CACHE_TTL_SEC", "60"))
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:246:            ttl_sec=float(os.getenv("EXIT_STATE_TTL_SEC", "30"))
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:2502:            log_every_sec = float(os.getenv("PIPE_REGIME_LOG_EVERY_SEC", "60"))
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:2523:            if (not is_exit_intent) and (not is_force_intent) and atr_pct < float(os.getenv("ATR_MIN_PCT","0.002")):
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:2526:                log_every_sec = float(os.getenv("PIPE_VOL_LOW_BLOCK_LOG_EVERY_SEC", "60"))
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:2541:                if trend_strength < float(os.getenv("TREND_STRENGTH_MIN","0.0003")) and regime.volatility != "high":  # ключевой параметр
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:2644:            breakout_ttl = float(os.getenv("BREAKOUT_DEDUP_TTL", "30"))
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:2667:            breakout_ttl = float(os.getenv("BREAKOUT_DEDUP_TTL", "30"))
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:268:            tick_size=float(os.getenv("ENTRY_TICK_SIZE", "0.01")),
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:269:            stop_atr_mult=float(os.getenv("ENTRY_STOP_ATR_MULT", "1.5")),
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:270:            take_atr_mult=float(os.getenv("ENTRY_TAKE_ATR_MULT", "2.0")),
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:2836:                if os.getenv("SESSION_OVERRIDE", "0") == "1" or os.getenv("SIMULATE_MARKET", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:2840:                        heartbeat_sec=float(os.getenv("SESSION_OVERRIDE_LOG_SEC", "30")),
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:2853:        override = os.getenv("OVERRIDE_MODE", "0") == "1"
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:288:            lookback=int(os.getenv("BR_VOLUME_LOOKBACK", "20")),
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:289:            confirm_ratio=float(os.getenv("BR_VOLUME_CONFIRM_RATIO", "1.5")),
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:2945:                        heartbeat_sec=float(os.getenv("POSITION_INTENT_BLOCK_HEARTBEAT_SEC", "300")),
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:2983:            if os.getenv("EXECUTION_MODE", "paper").lower() == "real":
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:2998:            if (not is_exit_intent) and (not is_force_intent) and abs(st.get("ema_fast", price) - price) / price < float(os.getenv("IMPULSE_MIN","0.0003")) and regime.volatility != "high":
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:3025:            dedup_ttl = float(os.getenv("SIGNAL_DEDUP_TTL", "2"))
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:3059:                threshold = float(os.getenv("PYRAMIDING_THRESHOLD", "0.0003"))  # 0.03% (ускорение)
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:3086:        base_cooldown = float(os.getenv("TRADE_COOLDOWN_SEC", "45"))
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:3118:            max_trades_per_hour = int(os.getenv("MAX_TRADES_PER_HOUR", "5"))
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:3119:            max_trades_per_symbol = int(os.getenv("MAX_TRADES_PER_SYMBOL", "2"))
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:313:            os.getenv("EXECUTION_MODE", "paper").lower() == "paper"
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:314:            and os.getenv("ENABLE_BR_CONSERVATIVE_BREAKOUT", "0") == "1"
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:316:        self.br_breakout_symbol = os.getenv("BR_BREAKOUT_SYMBOL", "BRM6@RTSX")
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:3189:            if os.getenv("RISK_SOFT", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:3239:                    max_portfolio_heat=float(os.getenv("MAX_PORTFOLIO_HEAT", "0.30")),
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:3240:                    max_symbol_heat=float(os.getenv("MAX_SYMBOL_HEAT", "0.10")),
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:3241:                    max_margin_utilization=float(os.getenv("MAX_MARGIN_UTILIZATION", "0.65")),
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:3242:                    max_daily_loss_pct=float(os.getenv("MAX_DAILY_LOSS_PCT", "0.02")),
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:3243:                    max_drawdown_pct=float(os.getenv("MAX_DRAWDOWN_PCT", "0.03")),
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:327:        self.regime_enabled = os.getenv("REGIME_ENABLE", "1") == "1"
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:3293:                max_heat = float(os.getenv("MAX_PORTFOLIO_HEAT", "0.3"))  # 30% default
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:330:        self.regime_min_atr_pct = float(os.getenv("REGIME_MIN_ATR_PCT", "0.001"))
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:3315:                max_symbol_heat = float(os.getenv("MAX_SYMBOL_HEAT", "0.1"))  # 10% default
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:331:        self.regime_trend_mode = os.getenv("REGIME_TREND_MODE", "ema")  # ema / simple
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:3349:                max_dd = float(os.getenv("MAX_DRAWDOWN", "-0.03"))  # -3%
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:3350:                max_daily_loss = float(os.getenv("MAX_DAILY_LOSS", "-0.02"))  # -2%
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:3436:        if os.getenv("ENABLE_PAPER_FILLS", "1") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:3773:        if not self._filled_once and os.getenv("EXIT_ON_FILL", "1") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:3836:            "execution_mode": os.getenv("EXECUTION_MODE", "paper"),
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:408:        raw = os.getenv(
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:410:            os.getenv("ENTRY_COOLDOWN_SEC_DEFAULT", "60"),
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:4136:        if os.getenv("REPLAY_DISABLE_BR_REGIME", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:4307:        max_len = int(os.getenv("BR_VOLUME_BUFFER_MAX", "200"))
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:4359:        if os.getenv("REPLAY_DISABLE_BR_REGIME", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:4403:        if os.getenv("EXECUTION_MODE", "paper").lower() != "paper":
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:4505:                if os.getenv("ENABLE_PAPER_FILLS", "1") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:454:        raw_interval = os.getenv("LOG_THROTTLE_SEC", "30")
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:4617:        qty = float(os.getenv("BR_BREAKOUT_QTY", "1"))
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:4627:            "execution_mode": os.getenv("EXECUTION_MODE", "paper"),
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:4697:        raw = os.getenv(
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:4699:            os.getenv("BREAKOUT_LEVEL_BUCKET_DEFAULT", "0"),
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:477:        if os.getenv("LOG_DUPLICATE_SIGNAL", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:533:        max_loss = float(os.getenv("PORTFOLIO_MAX_CUMULATIVE_LOSS", "0") or 0.0)
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:537:        dd_limit = float(os.getenv("PORTFOLIO_MAX_DRAWDOWN", "0") or 0.0)
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:546:        explicit = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_DSN")
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:550:        host = os.getenv("PGHOST", "127.0.0.1")
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:551:        port = os.getenv("PGPORT", "5432")
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:552:        db = os.getenv("PGDATABASE", "finam")
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:553:        user = os.getenv("PGUSER", "finam")
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:554:        password = os.getenv("PGPASSWORD", "finam")
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:671:        if os.getenv("ENABLE_BROKER_POSITION_SYNC", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:675:        interval = float(os.getenv("BROKER_POSITION_SYNC_INTERVAL_SEC", "30"))
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:686:            account_id = os.getenv("FINAM_ACCOUNT_ID", "").strip()
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:692:            endpoint = os.getenv("FINAM_GRPC_ENDPOINT", "api.finam.ru:443").strip()
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:700:                timeout=float(os.getenv("BROKER_POSITION_SYNC_TIMEOUT_SEC", "10")),
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:732:            heartbeat_sec = float(os.getenv("BROKER_POSITION_SYNC_LOG_HEARTBEAT_SEC", "300"))
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:73:PIPE_DEBUG = os.getenv("PIPE_DEBUG", "0") == "1"
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:754:        if os.getenv("BROKER_POSITION_HARD_GATE_USE_BROKER_AS_LOCAL", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:781:        if os.getenv("ENABLE_BROKER_POSITION_HARD_GATE", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:784:        tolerance = float(os.getenv("BROKER_POSITION_HARD_GATE_QTY_TOLERANCE", "1e-9"))
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:815:        if os.getenv("ENABLE_BROKER_PROTECTION_GATE", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:855:        if os.getenv("ENABLE_BROKER_POSITION_HARD_GATE", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:911:        if os.getenv("ENABLE_OCO_ORDER_MANAGER", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:948:        if os.getenv("ENABLE_SUBSCRIBE_ORDERS_LISTENER", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:956:        poll_interval = float(os.getenv("SUBSCRIBE_ORDERS_POLL_INTERVAL_SEC", "15"))
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:964:            max_events = int(os.getenv("SUBSCRIBE_ORDERS_MAX_EVENTS_PER_POLL", "1"))
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:974:                heartbeat = float(os.getenv("SUBSCRIBE_ORDERS_APPLIED_HEARTBEAT_SEC", "300"))
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:987:                    heartbeat_sec=float(os.getenv("SUBSCRIBE_ORDERS_ERROR_HEARTBEAT_SEC", "300")),
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:996:        if os.getenv("ENABLE_BROKER_OPEN_ORDERS_SYNC", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_real_protective_lifecycle_20260514_132106:999:        interval_sec = float(os.getenv("BROKER_OPEN_ORDERS_SYNC_INTERVAL_SEC", "30"))
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:1190:        pct = float(os.getenv("EXIT_FALLBACK_ATR_PCT", "0.003"))
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:1196:        if os.getenv("ENABLE_TRAILING_ORDER_MANAGER", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:1199:        if os.getenv("ENABLE_POSITION_INTENT_GATE", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:1205:                if now_ts - last_ts >= float(os.getenv("POSITION_INTENT_TRAILING_BLOCK_LOG_INTERVAL_SEC", "300")):
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:1214:        dry_run = os.getenv("TRAILING_ORDER_DRY_RUN", "1") == "1"
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:1252:        if os.getenv("ENABLE_POSITION_ORDER_TRACKER", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:1285:        if os.getenv("ENABLE_POSITION_INTENT_GATE", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:1300:        if os.getenv("ENABLE_BROKER_RECONCILIATION_GATE", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:1313:            allow_repair=os.getenv("ALLOW_PORTFOLIO_REPAIR", "0") == "1",
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:1372:        if os.getenv("ENABLE_POSITION_INTENT_GATE", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:1420:        if os.getenv("ENABLE_BROKER_POSITION_APPLY_TO_PM", "0") == "1" and abs(broker_qty) > 1e-9:
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:1443:        should_log_exit_check = now_ts - last_log_ts >= float(os.getenv(interval_key, default_interval))
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:1446:            abs(float(qty or 0.0)) > 1e-9 or os.getenv("EXIT_ENGINE_DEBUG", "0") == "1"
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:1472:            if now_ts - last_intent_block_ts >= float(os.getenv("POSITION_INTENT_BLOCK_LOG_INTERVAL_SEC", "300")):
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:1485:            if now_ts - last_no_avg_ts >= float(os.getenv("EXIT_NO_AVG_LOG_INTERVAL_SEC", "300")):
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:1583:        if os.getenv("ENABLE_RESTART_RECOVERY", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:1677:        hb = float(heartbeat_sec if heartbeat_sec is not None else os.getenv("PIPE_DEDUP_LOG_HEARTBEAT_SEC", "300"))
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:1695:        if os.getenv("ENABLE_EXECUTION_DECISION_LAYER", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:170:        self.execution_mode = os.getenv("EXECUTION_MODE", "paper").strip().lower()
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:1773:        if os.getenv("ENABLE_ORDER_ROUTER", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:1811:        if os.getenv("ENABLE_EXECUTION_DISPATCHER", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:1831:        if os.getenv("ENABLE_EXECUTION_DISPATCHER_LIVE_ROUTE", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:1837:        allowlist_raw = os.getenv("EXECUTION_DISPATCHER_LIVE_SYMBOL_ALLOWLIST", "BRM6@RTSX")
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:1843:        max_qty = float(os.getenv("EXECUTION_DISPATCHER_LIVE_MAX_QTY", "1"))
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:1923:        if os.getenv("SESSION_OVERRIDE", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:1927:                heartbeat_sec=float(os.getenv("SESSION_OVERRIDE_LOG_SEC", "30")),
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:1949:            if os.getenv("SESSION_OVERRIDE", "0") == "1" or os.getenv("SIMULATE_MARKET", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:1983:                os.getenv("ENABLE_BROKER_POSITION_APPLY_TO_PM", "0") != "1"
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:198:        self._quote_log_every = float(os.getenv("QUOTE_LOG_EVERY", "0"))  # 0 = выключено
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:202:            trail_abs=float(os.getenv("TRAILING_ORDER_TRAIL_ABS", "0.40")),
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:203:            min_replace_step=float(os.getenv("TRAILING_ORDER_MIN_REPLACE_STEP", "0.10")),
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:2047:                if os.getenv("ENABLE_PAPER_FILLS", "1") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:2094:        force_signal_mode = os.getenv("FORCE_ONCE_BUY", "0") == "1"
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:2145:        if os.getenv("SIMULATE_MARKET", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:219:            qty_tolerance=float(os.getenv("BROKER_RECONCILIATION_QTY_TOLERANCE", "1e-9"))
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:223:            qty_tolerance=float(os.getenv("BROKER_RECONCILIATION_QTY_TOLERANCE", "1e-9"))
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:228:            ttl_sec=float(os.getenv("POSITION_INTENT_CACHE_TTL_SEC", "60"))
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:2296:            log_every_sec = float(os.getenv("PIPE_REGIME_LOG_EVERY_SEC", "60"))
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:2317:            if (not is_exit_intent) and (not is_force_intent) and atr_pct < float(os.getenv("ATR_MIN_PCT","0.002")):
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:2320:                log_every_sec = float(os.getenv("PIPE_VOL_LOW_BLOCK_LOG_EVERY_SEC", "60"))
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:232:            ttl_sec=float(os.getenv("EXIT_STATE_TTL_SEC", "30"))
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:2335:                if trend_strength < float(os.getenv("TREND_STRENGTH_MIN","0.0003")) and regime.volatility != "high":  # ключевой параметр
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:2432:            breakout_ttl = float(os.getenv("BREAKOUT_DEDUP_TTL", "30"))
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:2455:            breakout_ttl = float(os.getenv("BREAKOUT_DEDUP_TTL", "30"))
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:254:            tick_size=float(os.getenv("ENTRY_TICK_SIZE", "0.01")),
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:255:            stop_atr_mult=float(os.getenv("ENTRY_STOP_ATR_MULT", "1.5")),
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:256:            take_atr_mult=float(os.getenv("ENTRY_TAKE_ATR_MULT", "2.0")),
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:2624:                if os.getenv("SESSION_OVERRIDE", "0") == "1" or os.getenv("SIMULATE_MARKET", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:2628:                        heartbeat_sec=float(os.getenv("SESSION_OVERRIDE_LOG_SEC", "30")),
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:2641:        override = os.getenv("OVERRIDE_MODE", "0") == "1"
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:2733:                        heartbeat_sec=float(os.getenv("POSITION_INTENT_BLOCK_HEARTBEAT_SEC", "300")),
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:274:            lookback=int(os.getenv("BR_VOLUME_LOOKBACK", "20")),
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:275:            confirm_ratio=float(os.getenv("BR_VOLUME_CONFIRM_RATIO", "1.5")),
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:2771:            if os.getenv("EXECUTION_MODE", "paper").lower() == "real":
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:2786:            if (not is_exit_intent) and (not is_force_intent) and abs(st.get("ema_fast", price) - price) / price < float(os.getenv("IMPULSE_MIN","0.0003")) and regime.volatility != "high":
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:2813:            dedup_ttl = float(os.getenv("SIGNAL_DEDUP_TTL", "2"))
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:2847:                threshold = float(os.getenv("PYRAMIDING_THRESHOLD", "0.0003"))  # 0.03% (ускорение)
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:2874:        base_cooldown = float(os.getenv("TRADE_COOLDOWN_SEC", "45"))
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:2906:            max_trades_per_hour = int(os.getenv("MAX_TRADES_PER_HOUR", "5"))
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:2907:            max_trades_per_symbol = int(os.getenv("MAX_TRADES_PER_SYMBOL", "2"))
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:2977:            if os.getenv("RISK_SOFT", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:299:            os.getenv("EXECUTION_MODE", "paper").lower() == "paper"
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:300:            and os.getenv("ENABLE_BR_CONSERVATIVE_BREAKOUT", "0") == "1"
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:3027:                    max_portfolio_heat=float(os.getenv("MAX_PORTFOLIO_HEAT", "0.30")),
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:3028:                    max_symbol_heat=float(os.getenv("MAX_SYMBOL_HEAT", "0.10")),
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:3029:                    max_margin_utilization=float(os.getenv("MAX_MARGIN_UTILIZATION", "0.65")),
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:302:        self.br_breakout_symbol = os.getenv("BR_BREAKOUT_SYMBOL", "BRM6@RTSX")
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:3030:                    max_daily_loss_pct=float(os.getenv("MAX_DAILY_LOSS_PCT", "0.02")),
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:3031:                    max_drawdown_pct=float(os.getenv("MAX_DRAWDOWN_PCT", "0.03")),
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:3081:                max_heat = float(os.getenv("MAX_PORTFOLIO_HEAT", "0.3"))  # 30% default
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:3103:                max_symbol_heat = float(os.getenv("MAX_SYMBOL_HEAT", "0.1"))  # 10% default
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:3137:                max_dd = float(os.getenv("MAX_DRAWDOWN", "-0.03"))  # -3%
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:3138:                max_daily_loss = float(os.getenv("MAX_DAILY_LOSS", "-0.02"))  # -2%
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:313:        self.regime_enabled = os.getenv("REGIME_ENABLE", "1") == "1"
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:316:        self.regime_min_atr_pct = float(os.getenv("REGIME_MIN_ATR_PCT", "0.001"))
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:317:        self.regime_trend_mode = os.getenv("REGIME_TREND_MODE", "ema")  # ema / simple
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:3224:        if os.getenv("ENABLE_PAPER_FILLS", "1") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:3527:        if not self._filled_once and os.getenv("EXIT_ON_FILL", "1") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:3590:            "execution_mode": os.getenv("EXECUTION_MODE", "paper"),
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:3835:        if os.getenv("REPLAY_DISABLE_BR_REGIME", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:394:        raw = os.getenv(
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:396:            os.getenv("ENTRY_COOLDOWN_SEC_DEFAULT", "60"),
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:4006:        max_len = int(os.getenv("BR_VOLUME_BUFFER_MAX", "200"))
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:4058:        if os.getenv("REPLAY_DISABLE_BR_REGIME", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:4102:        if os.getenv("EXECUTION_MODE", "paper").lower() != "paper":
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:4188:                if os.getenv("ENABLE_PAPER_FILLS", "1") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:4300:        qty = float(os.getenv("BR_BREAKOUT_QTY", "1"))
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:4310:            "execution_mode": os.getenv("EXECUTION_MODE", "paper"),
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:4380:        raw = os.getenv(
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:4382:            os.getenv("BREAKOUT_LEVEL_BUCKET_DEFAULT", "0"),
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:440:        raw_interval = os.getenv("LOG_THROTTLE_SEC", "30")
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:463:        if os.getenv("LOG_DUPLICATE_SIGNAL", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:519:        max_loss = float(os.getenv("PORTFOLIO_MAX_CUMULATIVE_LOSS", "0") or 0.0)
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:523:        dd_limit = float(os.getenv("PORTFOLIO_MAX_DRAWDOWN", "0") or 0.0)
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:532:        explicit = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_DSN")
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:536:        host = os.getenv("PGHOST", "127.0.0.1")
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:537:        port = os.getenv("PGPORT", "5432")
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:538:        db = os.getenv("PGDATABASE", "finam")
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:539:        user = os.getenv("PGUSER", "finam")
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:540:        password = os.getenv("PGPASSWORD", "finam")
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:657:        if os.getenv("ENABLE_BROKER_POSITION_SYNC", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:661:        interval = float(os.getenv("BROKER_POSITION_SYNC_INTERVAL_SEC", "30"))
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:672:            account_id = os.getenv("FINAM_ACCOUNT_ID", "").strip()
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:678:            endpoint = os.getenv("FINAM_GRPC_ENDPOINT", "api.finam.ru:443").strip()
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:67:PIPE_DEBUG = os.getenv("PIPE_DEBUG", "0") == "1"
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:686:                timeout=float(os.getenv("BROKER_POSITION_SYNC_TIMEOUT_SEC", "10")),
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:718:            heartbeat_sec = float(os.getenv("BROKER_POSITION_SYNC_LOG_HEARTBEAT_SEC", "300"))
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:740:        if os.getenv("BROKER_POSITION_HARD_GATE_USE_BROKER_AS_LOCAL", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:767:        if os.getenv("ENABLE_BROKER_POSITION_HARD_GATE", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:770:        tolerance = float(os.getenv("BROKER_POSITION_HARD_GATE_QTY_TOLERANCE", "1e-9"))
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:801:        if os.getenv("ENABLE_BROKER_PROTECTION_GATE", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:841:        if os.getenv("ENABLE_BROKER_POSITION_HARD_GATE", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:897:        if os.getenv("ENABLE_OCO_ORDER_MANAGER", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:934:        if os.getenv("ENABLE_SUBSCRIBE_ORDERS_LISTENER", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:942:        poll_interval = float(os.getenv("SUBSCRIBE_ORDERS_POLL_INTERVAL_SEC", "15"))
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:950:            max_events = int(os.getenv("SUBSCRIBE_ORDERS_MAX_EVENTS_PER_POLL", "1"))
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:960:                heartbeat = float(os.getenv("SUBSCRIBE_ORDERS_APPLIED_HEARTBEAT_SEC", "300"))
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:973:                    heartbeat_sec=float(os.getenv("SUBSCRIBE_ORDERS_ERROR_HEARTBEAT_SEC", "300")),
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:982:        if os.getenv("ENABLE_BROKER_OPEN_ORDERS_SYNC", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_runtime_control_20260514_053715:985:        interval_sec = float(os.getenv("BROKER_OPEN_ORDERS_SYNC_INTERVAL_SEC", "30"))
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:1212:        pct = float(os.getenv("EXIT_FALLBACK_ATR_PCT", "0.003"))
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:1218:        if os.getenv("ENABLE_TRAILING_ORDER_MANAGER", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:1221:        if os.getenv("ENABLE_POSITION_INTENT_GATE", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:1227:                if now_ts - last_ts >= float(os.getenv("POSITION_INTENT_TRAILING_BLOCK_LOG_INTERVAL_SEC", "300")):
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:1236:        dry_run = os.getenv("TRAILING_ORDER_DRY_RUN", "1") == "1"
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:1274:        if os.getenv("ENABLE_POSITION_ORDER_TRACKER", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:1307:        if os.getenv("ENABLE_POSITION_INTENT_GATE", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:1322:        if os.getenv("ENABLE_BROKER_RECONCILIATION_GATE", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:1335:            allow_repair=os.getenv("ALLOW_PORTFOLIO_REPAIR", "0") == "1",
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:1394:        if os.getenv("ENABLE_POSITION_INTENT_GATE", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:1442:        if os.getenv("ENABLE_BROKER_POSITION_APPLY_TO_PM", "0") == "1" and abs(broker_qty) > 1e-9:
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:1465:        should_log_exit_check = now_ts - last_log_ts >= float(os.getenv(interval_key, default_interval))
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:1468:            abs(float(qty or 0.0)) > 1e-9 or os.getenv("EXIT_ENGINE_DEBUG", "0") == "1"
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:1494:            if now_ts - last_intent_block_ts >= float(os.getenv("POSITION_INTENT_BLOCK_LOG_INTERVAL_SEC", "300")):
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:1507:            if now_ts - last_no_avg_ts >= float(os.getenv("EXIT_NO_AVG_LOG_INTERVAL_SEC", "300")):
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:1618:        if os.getenv("ENABLE_RESTART_RECOVERY", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:170:        self.execution_mode = os.getenv("EXECUTION_MODE", "paper").strip().lower()
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:1712:        hb = float(heartbeat_sec if heartbeat_sec is not None else os.getenv("PIPE_DEDUP_LOG_HEARTBEAT_SEC", "300"))
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:1730:        if os.getenv("ENABLE_EXECUTION_DECISION_LAYER", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:1808:        if os.getenv("ENABLE_ORDER_ROUTER", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:1846:        if os.getenv("ENABLE_EXECUTION_DISPATCHER", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:1866:        if os.getenv("ENABLE_EXECUTION_DISPATCHER_LIVE_ROUTE", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:1872:        allowlist_raw = os.getenv("EXECUTION_DISPATCHER_LIVE_SYMBOL_ALLOWLIST", "BRM6@RTSX")
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:1878:        max_qty = float(os.getenv("EXECUTION_DISPATCHER_LIVE_MAX_QTY", "1"))
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:1958:        if os.getenv("SESSION_OVERRIDE", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:1962:                heartbeat_sec=float(os.getenv("SESSION_OVERRIDE_LOG_SEC", "30")),
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:1984:            if os.getenv("SESSION_OVERRIDE", "0") == "1" or os.getenv("SIMULATE_MARKET", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:198:        self._quote_log_every = float(os.getenv("QUOTE_LOG_EVERY", "0"))  # 0 = выключено
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:2021:                os.getenv("ENABLE_BROKER_POSITION_APPLY_TO_PM", "0") != "1"
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:202:            trail_abs=float(os.getenv("TRAILING_ORDER_TRAIL_ABS", "0.40")),
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:203:            min_replace_step=float(os.getenv("TRAILING_ORDER_MIN_REPLACE_STEP", "0.10")),
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:2085:                if os.getenv("ENABLE_PAPER_FILLS", "1") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:2132:        force_signal_mode = os.getenv("FORCE_ONCE_BUY", "0") == "1"
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:2183:        if os.getenv("SIMULATE_MARKET", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:219:            qty_tolerance=float(os.getenv("BROKER_RECONCILIATION_QTY_TOLERANCE", "1e-9"))
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:223:            qty_tolerance=float(os.getenv("BROKER_RECONCILIATION_QTY_TOLERANCE", "1e-9"))
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:228:            ttl_sec=float(os.getenv("POSITION_INTENT_CACHE_TTL_SEC", "60"))
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:232:            ttl_sec=float(os.getenv("EXIT_STATE_TTL_SEC", "30"))
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:2334:            log_every_sec = float(os.getenv("PIPE_REGIME_LOG_EVERY_SEC", "60"))
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:2355:            if (not is_exit_intent) and (not is_force_intent) and atr_pct < float(os.getenv("ATR_MIN_PCT","0.002")):
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:2358:                log_every_sec = float(os.getenv("PIPE_VOL_LOW_BLOCK_LOG_EVERY_SEC", "60"))
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:2373:                if trend_strength < float(os.getenv("TREND_STRENGTH_MIN","0.0003")) and regime.volatility != "high":  # ключевой параметр
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:2470:            breakout_ttl = float(os.getenv("BREAKOUT_DEDUP_TTL", "30"))
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:2493:            breakout_ttl = float(os.getenv("BREAKOUT_DEDUP_TTL", "30"))
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:254:            tick_size=float(os.getenv("ENTRY_TICK_SIZE", "0.01")),
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:255:            stop_atr_mult=float(os.getenv("ENTRY_STOP_ATR_MULT", "1.5")),
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:256:            take_atr_mult=float(os.getenv("ENTRY_TAKE_ATR_MULT", "2.0")),
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:2662:                if os.getenv("SESSION_OVERRIDE", "0") == "1" or os.getenv("SIMULATE_MARKET", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:2666:                        heartbeat_sec=float(os.getenv("SESSION_OVERRIDE_LOG_SEC", "30")),
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:2679:        override = os.getenv("OVERRIDE_MODE", "0") == "1"
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:274:            lookback=int(os.getenv("BR_VOLUME_LOOKBACK", "20")),
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:275:            confirm_ratio=float(os.getenv("BR_VOLUME_CONFIRM_RATIO", "1.5")),
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:2771:                        heartbeat_sec=float(os.getenv("POSITION_INTENT_BLOCK_HEARTBEAT_SEC", "300")),
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:2809:            if os.getenv("EXECUTION_MODE", "paper").lower() == "real":
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:2824:            if (not is_exit_intent) and (not is_force_intent) and abs(st.get("ema_fast", price) - price) / price < float(os.getenv("IMPULSE_MIN","0.0003")) and regime.volatility != "high":
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:2851:            dedup_ttl = float(os.getenv("SIGNAL_DEDUP_TTL", "2"))
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:2885:                threshold = float(os.getenv("PYRAMIDING_THRESHOLD", "0.0003"))  # 0.03% (ускорение)
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:2912:        base_cooldown = float(os.getenv("TRADE_COOLDOWN_SEC", "45"))
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:2944:            max_trades_per_hour = int(os.getenv("MAX_TRADES_PER_HOUR", "5"))
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:2945:            max_trades_per_symbol = int(os.getenv("MAX_TRADES_PER_SYMBOL", "2"))
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:299:            os.getenv("EXECUTION_MODE", "paper").lower() == "paper"
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:300:            and os.getenv("ENABLE_BR_CONSERVATIVE_BREAKOUT", "0") == "1"
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:3015:            if os.getenv("RISK_SOFT", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:302:        self.br_breakout_symbol = os.getenv("BR_BREAKOUT_SYMBOL", "BRM6@RTSX")
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:3065:                    max_portfolio_heat=float(os.getenv("MAX_PORTFOLIO_HEAT", "0.30")),
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:3066:                    max_symbol_heat=float(os.getenv("MAX_SYMBOL_HEAT", "0.10")),
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:3067:                    max_margin_utilization=float(os.getenv("MAX_MARGIN_UTILIZATION", "0.65")),
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:3068:                    max_daily_loss_pct=float(os.getenv("MAX_DAILY_LOSS_PCT", "0.02")),
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:3069:                    max_drawdown_pct=float(os.getenv("MAX_DRAWDOWN_PCT", "0.03")),
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:3119:                max_heat = float(os.getenv("MAX_PORTFOLIO_HEAT", "0.3"))  # 30% default
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:313:        self.regime_enabled = os.getenv("REGIME_ENABLE", "1") == "1"
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:3141:                max_symbol_heat = float(os.getenv("MAX_SYMBOL_HEAT", "0.1"))  # 10% default
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:316:        self.regime_min_atr_pct = float(os.getenv("REGIME_MIN_ATR_PCT", "0.001"))
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:3175:                max_dd = float(os.getenv("MAX_DRAWDOWN", "-0.03"))  # -3%
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:3176:                max_daily_loss = float(os.getenv("MAX_DAILY_LOSS", "-0.02"))  # -2%
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:317:        self.regime_trend_mode = os.getenv("REGIME_TREND_MODE", "ema")  # ema / simple
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:3262:        if os.getenv("ENABLE_PAPER_FILLS", "1") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:3599:        if not self._filled_once and os.getenv("EXIT_ON_FILL", "1") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:3662:            "execution_mode": os.getenv("EXECUTION_MODE", "paper"),
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:394:        raw = os.getenv(
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:3962:        if os.getenv("REPLAY_DISABLE_BR_REGIME", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:396:            os.getenv("ENTRY_COOLDOWN_SEC_DEFAULT", "60"),
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:4133:        max_len = int(os.getenv("BR_VOLUME_BUFFER_MAX", "200"))
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:4185:        if os.getenv("REPLAY_DISABLE_BR_REGIME", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:4229:        if os.getenv("EXECUTION_MODE", "paper").lower() != "paper":
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:4331:                if os.getenv("ENABLE_PAPER_FILLS", "1") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:440:        raw_interval = os.getenv("LOG_THROTTLE_SEC", "30")
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:4443:        qty = float(os.getenv("BR_BREAKOUT_QTY", "1"))
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:4453:            "execution_mode": os.getenv("EXECUTION_MODE", "paper"),
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:4523:        raw = os.getenv(
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:4525:            os.getenv("BREAKOUT_LEVEL_BUCKET_DEFAULT", "0"),
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:463:        if os.getenv("LOG_DUPLICATE_SIGNAL", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:519:        max_loss = float(os.getenv("PORTFOLIO_MAX_CUMULATIVE_LOSS", "0") or 0.0)
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:523:        dd_limit = float(os.getenv("PORTFOLIO_MAX_DRAWDOWN", "0") or 0.0)
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:532:        explicit = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_DSN")
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:536:        host = os.getenv("PGHOST", "127.0.0.1")
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:537:        port = os.getenv("PGPORT", "5432")
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:538:        db = os.getenv("PGDATABASE", "finam")
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:539:        user = os.getenv("PGUSER", "finam")
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:540:        password = os.getenv("PGPASSWORD", "finam")
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:657:        if os.getenv("ENABLE_BROKER_POSITION_SYNC", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:661:        interval = float(os.getenv("BROKER_POSITION_SYNC_INTERVAL_SEC", "30"))
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:672:            account_id = os.getenv("FINAM_ACCOUNT_ID", "").strip()
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:678:            endpoint = os.getenv("FINAM_GRPC_ENDPOINT", "api.finam.ru:443").strip()
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:67:PIPE_DEBUG = os.getenv("PIPE_DEBUG", "0") == "1"
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:686:                timeout=float(os.getenv("BROKER_POSITION_SYNC_TIMEOUT_SEC", "10")),
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:718:            heartbeat_sec = float(os.getenv("BROKER_POSITION_SYNC_LOG_HEARTBEAT_SEC", "300"))
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:740:        if os.getenv("BROKER_POSITION_HARD_GATE_USE_BROKER_AS_LOCAL", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:767:        if os.getenv("ENABLE_BROKER_POSITION_HARD_GATE", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:770:        tolerance = float(os.getenv("BROKER_POSITION_HARD_GATE_QTY_TOLERANCE", "1e-9"))
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:801:        if os.getenv("ENABLE_BROKER_PROTECTION_GATE", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:841:        if os.getenv("ENABLE_BROKER_POSITION_HARD_GATE", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:897:        if os.getenv("ENABLE_OCO_ORDER_MANAGER", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:934:        if os.getenv("ENABLE_SUBSCRIBE_ORDERS_LISTENER", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:942:        poll_interval = float(os.getenv("SUBSCRIBE_ORDERS_POLL_INTERVAL_SEC", "15"))
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:950:            max_events = int(os.getenv("SUBSCRIBE_ORDERS_MAX_EVENTS_PER_POLL", "1"))
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:960:                heartbeat = float(os.getenv("SUBSCRIBE_ORDERS_APPLIED_HEARTBEAT_SEC", "300"))
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:973:                    heartbeat_sec=float(os.getenv("SUBSCRIBE_ORDERS_ERROR_HEARTBEAT_SEC", "300")),
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:982:        if os.getenv("ENABLE_BROKER_OPEN_ORDERS_SYNC", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_strategy_map_20260514_115424:985:        interval_sec = float(os.getenv("BROKER_OPEN_ORDERS_SYNC_INTERVAL_SEC", "30"))
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:1190:        pct = float(os.getenv("EXIT_FALLBACK_ATR_PCT", "0.003"))
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:1196:        if os.getenv("ENABLE_TRAILING_ORDER_MANAGER", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:1199:        if os.getenv("ENABLE_POSITION_INTENT_GATE", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:1205:                if now_ts - last_ts >= float(os.getenv("POSITION_INTENT_TRAILING_BLOCK_LOG_INTERVAL_SEC", "300")):
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:1214:        dry_run = os.getenv("TRAILING_ORDER_DRY_RUN", "1") == "1"
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:1252:        if os.getenv("ENABLE_POSITION_ORDER_TRACKER", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:1285:        if os.getenv("ENABLE_POSITION_INTENT_GATE", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:1300:        if os.getenv("ENABLE_BROKER_RECONCILIATION_GATE", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:1313:            allow_repair=os.getenv("ALLOW_PORTFOLIO_REPAIR", "0") == "1",
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:1372:        if os.getenv("ENABLE_POSITION_INTENT_GATE", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:1420:        if os.getenv("ENABLE_BROKER_POSITION_APPLY_TO_PM", "0") == "1" and abs(broker_qty) > 1e-9:
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:1443:        should_log_exit_check = now_ts - last_log_ts >= float(os.getenv(interval_key, default_interval))
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:1446:            abs(float(qty or 0.0)) > 1e-9 or os.getenv("EXIT_ENGINE_DEBUG", "0") == "1"
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:1472:            if now_ts - last_intent_block_ts >= float(os.getenv("POSITION_INTENT_BLOCK_LOG_INTERVAL_SEC", "300")):
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:1485:            if now_ts - last_no_avg_ts >= float(os.getenv("EXIT_NO_AVG_LOG_INTERVAL_SEC", "300")):
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:1583:        if os.getenv("ENABLE_RESTART_RECOVERY", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:1677:        hb = float(heartbeat_sec if heartbeat_sec is not None else os.getenv("PIPE_DEDUP_LOG_HEARTBEAT_SEC", "300"))
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:1695:        if os.getenv("ENABLE_EXECUTION_DECISION_LAYER", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:170:        self.execution_mode = os.getenv("EXECUTION_MODE", "paper").strip().lower()
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:1773:        if os.getenv("ENABLE_ORDER_ROUTER", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:1811:        if os.getenv("ENABLE_EXECUTION_DISPATCHER", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:1831:        if os.getenv("ENABLE_EXECUTION_DISPATCHER_LIVE_ROUTE", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:1837:        allowlist_raw = os.getenv("EXECUTION_DISPATCHER_LIVE_SYMBOL_ALLOWLIST", "BRM6@RTSX")
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:1843:        max_qty = float(os.getenv("EXECUTION_DISPATCHER_LIVE_MAX_QTY", "1"))
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:1923:        if os.getenv("SESSION_OVERRIDE", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:1927:                heartbeat_sec=float(os.getenv("SESSION_OVERRIDE_LOG_SEC", "30")),
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:1949:            if os.getenv("SESSION_OVERRIDE", "0") == "1" or os.getenv("SIMULATE_MARKET", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:1983:                os.getenv("ENABLE_BROKER_POSITION_APPLY_TO_PM", "0") != "1"
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:198:        self._quote_log_every = float(os.getenv("QUOTE_LOG_EVERY", "0"))  # 0 = выключено
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:202:            trail_abs=float(os.getenv("TRAILING_ORDER_TRAIL_ABS", "0.40")),
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:203:            min_replace_step=float(os.getenv("TRAILING_ORDER_MIN_REPLACE_STEP", "0.10")),
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:2047:                if os.getenv("ENABLE_PAPER_FILLS", "1") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:2094:        force_signal_mode = os.getenv("FORCE_ONCE_BUY", "0") == "1"
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:2145:        if os.getenv("SIMULATE_MARKET", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:219:            qty_tolerance=float(os.getenv("BROKER_RECONCILIATION_QTY_TOLERANCE", "1e-9"))
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:223:            qty_tolerance=float(os.getenv("BROKER_RECONCILIATION_QTY_TOLERANCE", "1e-9"))
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:228:            ttl_sec=float(os.getenv("POSITION_INTENT_CACHE_TTL_SEC", "60"))
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:2296:            log_every_sec = float(os.getenv("PIPE_REGIME_LOG_EVERY_SEC", "60"))
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:2317:            if (not is_exit_intent) and (not is_force_intent) and atr_pct < float(os.getenv("ATR_MIN_PCT","0.002")):
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:2320:                log_every_sec = float(os.getenv("PIPE_VOL_LOW_BLOCK_LOG_EVERY_SEC", "60"))
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:232:            ttl_sec=float(os.getenv("EXIT_STATE_TTL_SEC", "30"))
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:2335:                if trend_strength < float(os.getenv("TREND_STRENGTH_MIN","0.0003")) and regime.volatility != "high":  # ключевой параметр
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:2432:            breakout_ttl = float(os.getenv("BREAKOUT_DEDUP_TTL", "30"))
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:2455:            breakout_ttl = float(os.getenv("BREAKOUT_DEDUP_TTL", "30"))
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:254:            tick_size=float(os.getenv("ENTRY_TICK_SIZE", "0.01")),
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:255:            stop_atr_mult=float(os.getenv("ENTRY_STOP_ATR_MULT", "1.5")),
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:256:            take_atr_mult=float(os.getenv("ENTRY_TAKE_ATR_MULT", "2.0")),
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:2624:                if os.getenv("SESSION_OVERRIDE", "0") == "1" or os.getenv("SIMULATE_MARKET", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:2628:                        heartbeat_sec=float(os.getenv("SESSION_OVERRIDE_LOG_SEC", "30")),
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:2641:        override = os.getenv("OVERRIDE_MODE", "0") == "1"
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:2733:                        heartbeat_sec=float(os.getenv("POSITION_INTENT_BLOCK_HEARTBEAT_SEC", "300")),
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:274:            lookback=int(os.getenv("BR_VOLUME_LOOKBACK", "20")),
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:275:            confirm_ratio=float(os.getenv("BR_VOLUME_CONFIRM_RATIO", "1.5")),
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:2771:            if os.getenv("EXECUTION_MODE", "paper").lower() == "real":
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:2786:            if (not is_exit_intent) and (not is_force_intent) and abs(st.get("ema_fast", price) - price) / price < float(os.getenv("IMPULSE_MIN","0.0003")) and regime.volatility != "high":
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:2813:            dedup_ttl = float(os.getenv("SIGNAL_DEDUP_TTL", "2"))
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:2847:                threshold = float(os.getenv("PYRAMIDING_THRESHOLD", "0.0003"))  # 0.03% (ускорение)
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:2874:        base_cooldown = float(os.getenv("TRADE_COOLDOWN_SEC", "45"))
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:2906:            max_trades_per_hour = int(os.getenv("MAX_TRADES_PER_HOUR", "5"))
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:2907:            max_trades_per_symbol = int(os.getenv("MAX_TRADES_PER_SYMBOL", "2"))
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:2977:            if os.getenv("RISK_SOFT", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:299:            os.getenv("EXECUTION_MODE", "paper").lower() == "paper"
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:300:            and os.getenv("ENABLE_BR_CONSERVATIVE_BREAKOUT", "0") == "1"
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:3027:                    max_portfolio_heat=float(os.getenv("MAX_PORTFOLIO_HEAT", "0.30")),
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:3028:                    max_symbol_heat=float(os.getenv("MAX_SYMBOL_HEAT", "0.10")),
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:3029:                    max_margin_utilization=float(os.getenv("MAX_MARGIN_UTILIZATION", "0.65")),
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:302:        self.br_breakout_symbol = os.getenv("BR_BREAKOUT_SYMBOL", "BRM6@RTSX")
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:3030:                    max_daily_loss_pct=float(os.getenv("MAX_DAILY_LOSS_PCT", "0.02")),
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:3031:                    max_drawdown_pct=float(os.getenv("MAX_DRAWDOWN_PCT", "0.03")),
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:3081:                max_heat = float(os.getenv("MAX_PORTFOLIO_HEAT", "0.3"))  # 30% default
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:3103:                max_symbol_heat = float(os.getenv("MAX_SYMBOL_HEAT", "0.1"))  # 10% default
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:3137:                max_dd = float(os.getenv("MAX_DRAWDOWN", "-0.03"))  # -3%
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:3138:                max_daily_loss = float(os.getenv("MAX_DAILY_LOSS", "-0.02"))  # -2%
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:313:        self.regime_enabled = os.getenv("REGIME_ENABLE", "1") == "1"
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:316:        self.regime_min_atr_pct = float(os.getenv("REGIME_MIN_ATR_PCT", "0.001"))
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:317:        self.regime_trend_mode = os.getenv("REGIME_TREND_MODE", "ema")  # ema / simple
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:3224:        if os.getenv("ENABLE_PAPER_FILLS", "1") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:3527:        if not self._filled_once and os.getenv("EXIT_ON_FILL", "1") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:3590:            "execution_mode": os.getenv("EXECUTION_MODE", "paper"),
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:3812:        if os.getenv("REPLAY_DISABLE_BR_REGIME", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:394:        raw = os.getenv(
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:396:            os.getenv("ENTRY_COOLDOWN_SEC_DEFAULT", "60"),
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:3983:        max_len = int(os.getenv("BR_VOLUME_BUFFER_MAX", "200"))
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:4035:        if os.getenv("REPLAY_DISABLE_BR_REGIME", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:4079:        if os.getenv("EXECUTION_MODE", "paper").lower() != "paper":
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:4165:                if os.getenv("ENABLE_PAPER_FILLS", "1") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:4277:        qty = float(os.getenv("BR_BREAKOUT_QTY", "1"))
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:4287:            "execution_mode": os.getenv("EXECUTION_MODE", "paper"),
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:4357:        raw = os.getenv(
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:4359:            os.getenv("BREAKOUT_LEVEL_BUCKET_DEFAULT", "0"),
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:440:        raw_interval = os.getenv("LOG_THROTTLE_SEC", "30")
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:463:        if os.getenv("LOG_DUPLICATE_SIGNAL", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:519:        max_loss = float(os.getenv("PORTFOLIO_MAX_CUMULATIVE_LOSS", "0") or 0.0)
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:523:        dd_limit = float(os.getenv("PORTFOLIO_MAX_DRAWDOWN", "0") or 0.0)
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:532:        explicit = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_DSN")
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:536:        host = os.getenv("PGHOST", "127.0.0.1")
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:537:        port = os.getenv("PGPORT", "5432")
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:538:        db = os.getenv("PGDATABASE", "finam")
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:539:        user = os.getenv("PGUSER", "finam")
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:540:        password = os.getenv("PGPASSWORD", "finam")
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:657:        if os.getenv("ENABLE_BROKER_POSITION_SYNC", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:661:        interval = float(os.getenv("BROKER_POSITION_SYNC_INTERVAL_SEC", "30"))
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:672:            account_id = os.getenv("FINAM_ACCOUNT_ID", "").strip()
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:678:            endpoint = os.getenv("FINAM_GRPC_ENDPOINT", "api.finam.ru:443").strip()
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:67:PIPE_DEBUG = os.getenv("PIPE_DEBUG", "0") == "1"
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:686:                timeout=float(os.getenv("BROKER_POSITION_SYNC_TIMEOUT_SEC", "10")),
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:718:            heartbeat_sec = float(os.getenv("BROKER_POSITION_SYNC_LOG_HEARTBEAT_SEC", "300"))
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:740:        if os.getenv("BROKER_POSITION_HARD_GATE_USE_BROKER_AS_LOCAL", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:767:        if os.getenv("ENABLE_BROKER_POSITION_HARD_GATE", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:770:        tolerance = float(os.getenv("BROKER_POSITION_HARD_GATE_QTY_TOLERANCE", "1e-9"))
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:801:        if os.getenv("ENABLE_BROKER_PROTECTION_GATE", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:841:        if os.getenv("ENABLE_BROKER_POSITION_HARD_GATE", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:897:        if os.getenv("ENABLE_OCO_ORDER_MANAGER", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:934:        if os.getenv("ENABLE_SUBSCRIBE_ORDERS_LISTENER", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:942:        poll_interval = float(os.getenv("SUBSCRIBE_ORDERS_POLL_INTERVAL_SEC", "15"))
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:950:            max_events = int(os.getenv("SUBSCRIBE_ORDERS_MAX_EVENTS_PER_POLL", "1"))
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:960:                heartbeat = float(os.getenv("SUBSCRIBE_ORDERS_APPLIED_HEARTBEAT_SEC", "300"))
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:973:                    heartbeat_sec=float(os.getenv("SUBSCRIBE_ORDERS_ERROR_HEARTBEAT_SEC", "300")),
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:982:        if os.getenv("ENABLE_BROKER_OPEN_ORDERS_SYNC", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041506:985:        interval_sec = float(os.getenv("BROKER_OPEN_ORDERS_SYNC_INTERVAL_SEC", "30"))
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:1190:        pct = float(os.getenv("EXIT_FALLBACK_ATR_PCT", "0.003"))
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:1196:        if os.getenv("ENABLE_TRAILING_ORDER_MANAGER", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:1199:        if os.getenv("ENABLE_POSITION_INTENT_GATE", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:1205:                if now_ts - last_ts >= float(os.getenv("POSITION_INTENT_TRAILING_BLOCK_LOG_INTERVAL_SEC", "300")):
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:1214:        dry_run = os.getenv("TRAILING_ORDER_DRY_RUN", "1") == "1"
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:1252:        if os.getenv("ENABLE_POSITION_ORDER_TRACKER", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:1285:        if os.getenv("ENABLE_POSITION_INTENT_GATE", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:1300:        if os.getenv("ENABLE_BROKER_RECONCILIATION_GATE", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:1313:            allow_repair=os.getenv("ALLOW_PORTFOLIO_REPAIR", "0") == "1",
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:1372:        if os.getenv("ENABLE_POSITION_INTENT_GATE", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:1420:        if os.getenv("ENABLE_BROKER_POSITION_APPLY_TO_PM", "0") == "1" and abs(broker_qty) > 1e-9:
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:1443:        should_log_exit_check = now_ts - last_log_ts >= float(os.getenv(interval_key, default_interval))
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:1446:            abs(float(qty or 0.0)) > 1e-9 or os.getenv("EXIT_ENGINE_DEBUG", "0") == "1"
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:1472:            if now_ts - last_intent_block_ts >= float(os.getenv("POSITION_INTENT_BLOCK_LOG_INTERVAL_SEC", "300")):
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:1485:            if now_ts - last_no_avg_ts >= float(os.getenv("EXIT_NO_AVG_LOG_INTERVAL_SEC", "300")):
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:1583:        if os.getenv("ENABLE_RESTART_RECOVERY", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:1677:        hb = float(heartbeat_sec if heartbeat_sec is not None else os.getenv("PIPE_DEDUP_LOG_HEARTBEAT_SEC", "300"))
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:1695:        if os.getenv("ENABLE_EXECUTION_DECISION_LAYER", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:170:        self.execution_mode = os.getenv("EXECUTION_MODE", "paper").strip().lower()
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:1773:        if os.getenv("ENABLE_ORDER_ROUTER", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:1811:        if os.getenv("ENABLE_EXECUTION_DISPATCHER", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:1831:        if os.getenv("ENABLE_EXECUTION_DISPATCHER_LIVE_ROUTE", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:1837:        allowlist_raw = os.getenv("EXECUTION_DISPATCHER_LIVE_SYMBOL_ALLOWLIST", "BRM6@RTSX")
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:1843:        max_qty = float(os.getenv("EXECUTION_DISPATCHER_LIVE_MAX_QTY", "1"))
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:1923:        if os.getenv("SESSION_OVERRIDE", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:1927:                heartbeat_sec=float(os.getenv("SESSION_OVERRIDE_LOG_SEC", "30")),
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:1949:            if os.getenv("SESSION_OVERRIDE", "0") == "1" or os.getenv("SIMULATE_MARKET", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:1983:                os.getenv("ENABLE_BROKER_POSITION_APPLY_TO_PM", "0") != "1"
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:198:        self._quote_log_every = float(os.getenv("QUOTE_LOG_EVERY", "0"))  # 0 = выключено
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:202:            trail_abs=float(os.getenv("TRAILING_ORDER_TRAIL_ABS", "0.40")),
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:203:            min_replace_step=float(os.getenv("TRAILING_ORDER_MIN_REPLACE_STEP", "0.10")),
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:2047:                if os.getenv("ENABLE_PAPER_FILLS", "1") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:2094:        force_signal_mode = os.getenv("FORCE_ONCE_BUY", "0") == "1"
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:2145:        if os.getenv("SIMULATE_MARKET", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:219:            qty_tolerance=float(os.getenv("BROKER_RECONCILIATION_QTY_TOLERANCE", "1e-9"))
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:223:            qty_tolerance=float(os.getenv("BROKER_RECONCILIATION_QTY_TOLERANCE", "1e-9"))
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:228:            ttl_sec=float(os.getenv("POSITION_INTENT_CACHE_TTL_SEC", "60"))
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:2296:            log_every_sec = float(os.getenv("PIPE_REGIME_LOG_EVERY_SEC", "60"))
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:2317:            if (not is_exit_intent) and (not is_force_intent) and atr_pct < float(os.getenv("ATR_MIN_PCT","0.002")):
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:2320:                log_every_sec = float(os.getenv("PIPE_VOL_LOW_BLOCK_LOG_EVERY_SEC", "60"))
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:232:            ttl_sec=float(os.getenv("EXIT_STATE_TTL_SEC", "30"))
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:2335:                if trend_strength < float(os.getenv("TREND_STRENGTH_MIN","0.0003")) and regime.volatility != "high":  # ключевой параметр
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:2432:            breakout_ttl = float(os.getenv("BREAKOUT_DEDUP_TTL", "30"))
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:2455:            breakout_ttl = float(os.getenv("BREAKOUT_DEDUP_TTL", "30"))
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:254:            tick_size=float(os.getenv("ENTRY_TICK_SIZE", "0.01")),
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:255:            stop_atr_mult=float(os.getenv("ENTRY_STOP_ATR_MULT", "1.5")),
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:256:            take_atr_mult=float(os.getenv("ENTRY_TAKE_ATR_MULT", "2.0")),
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:2624:                if os.getenv("SESSION_OVERRIDE", "0") == "1" or os.getenv("SIMULATE_MARKET", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:2628:                        heartbeat_sec=float(os.getenv("SESSION_OVERRIDE_LOG_SEC", "30")),
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:2641:        override = os.getenv("OVERRIDE_MODE", "0") == "1"
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:2733:                        heartbeat_sec=float(os.getenv("POSITION_INTENT_BLOCK_HEARTBEAT_SEC", "300")),
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:274:            lookback=int(os.getenv("BR_VOLUME_LOOKBACK", "20")),
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:275:            confirm_ratio=float(os.getenv("BR_VOLUME_CONFIRM_RATIO", "1.5")),
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:2771:            if os.getenv("EXECUTION_MODE", "paper").lower() == "real":
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:2786:            if (not is_exit_intent) and (not is_force_intent) and abs(st.get("ema_fast", price) - price) / price < float(os.getenv("IMPULSE_MIN","0.0003")) and regime.volatility != "high":
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:2813:            dedup_ttl = float(os.getenv("SIGNAL_DEDUP_TTL", "2"))
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:2847:                threshold = float(os.getenv("PYRAMIDING_THRESHOLD", "0.0003"))  # 0.03% (ускорение)
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:2874:        base_cooldown = float(os.getenv("TRADE_COOLDOWN_SEC", "45"))
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:2906:            max_trades_per_hour = int(os.getenv("MAX_TRADES_PER_HOUR", "5"))
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:2907:            max_trades_per_symbol = int(os.getenv("MAX_TRADES_PER_SYMBOL", "2"))
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:2977:            if os.getenv("RISK_SOFT", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:299:            os.getenv("EXECUTION_MODE", "paper").lower() == "paper"
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:300:            and os.getenv("ENABLE_BR_CONSERVATIVE_BREAKOUT", "0") == "1"
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:3027:                    max_portfolio_heat=float(os.getenv("MAX_PORTFOLIO_HEAT", "0.30")),
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:3028:                    max_symbol_heat=float(os.getenv("MAX_SYMBOL_HEAT", "0.10")),
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:3029:                    max_margin_utilization=float(os.getenv("MAX_MARGIN_UTILIZATION", "0.65")),
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:302:        self.br_breakout_symbol = os.getenv("BR_BREAKOUT_SYMBOL", "BRM6@RTSX")
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:3030:                    max_daily_loss_pct=float(os.getenv("MAX_DAILY_LOSS_PCT", "0.02")),
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:3031:                    max_drawdown_pct=float(os.getenv("MAX_DRAWDOWN_PCT", "0.03")),
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:3081:                max_heat = float(os.getenv("MAX_PORTFOLIO_HEAT", "0.3"))  # 30% default
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:3103:                max_symbol_heat = float(os.getenv("MAX_SYMBOL_HEAT", "0.1"))  # 10% default
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:3137:                max_dd = float(os.getenv("MAX_DRAWDOWN", "-0.03"))  # -3%
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:3138:                max_daily_loss = float(os.getenv("MAX_DAILY_LOSS", "-0.02"))  # -2%
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:313:        self.regime_enabled = os.getenv("REGIME_ENABLE", "1") == "1"
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:316:        self.regime_min_atr_pct = float(os.getenv("REGIME_MIN_ATR_PCT", "0.001"))
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:317:        self.regime_trend_mode = os.getenv("REGIME_TREND_MODE", "ema")  # ema / simple
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:3224:        if os.getenv("ENABLE_PAPER_FILLS", "1") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:3527:        if not self._filled_once and os.getenv("EXIT_ON_FILL", "1") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:3590:            "execution_mode": os.getenv("EXECUTION_MODE", "paper"),
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:3835:        if os.getenv("REPLAY_DISABLE_BR_REGIME", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:394:        raw = os.getenv(
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:396:            os.getenv("ENTRY_COOLDOWN_SEC_DEFAULT", "60"),
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:4006:        max_len = int(os.getenv("BR_VOLUME_BUFFER_MAX", "200"))
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:4058:        if os.getenv("REPLAY_DISABLE_BR_REGIME", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:4102:        if os.getenv("EXECUTION_MODE", "paper").lower() != "paper":
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:4188:                if os.getenv("ENABLE_PAPER_FILLS", "1") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:4300:        qty = float(os.getenv("BR_BREAKOUT_QTY", "1"))
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:4310:            "execution_mode": os.getenv("EXECUTION_MODE", "paper"),
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:4380:        raw = os.getenv(
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:4382:            os.getenv("BREAKOUT_LEVEL_BUCKET_DEFAULT", "0"),
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:440:        raw_interval = os.getenv("LOG_THROTTLE_SEC", "30")
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:463:        if os.getenv("LOG_DUPLICATE_SIGNAL", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:519:        max_loss = float(os.getenv("PORTFOLIO_MAX_CUMULATIVE_LOSS", "0") or 0.0)
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:523:        dd_limit = float(os.getenv("PORTFOLIO_MAX_DRAWDOWN", "0") or 0.0)
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:532:        explicit = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_DSN")
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:536:        host = os.getenv("PGHOST", "127.0.0.1")
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:537:        port = os.getenv("PGPORT", "5432")
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:538:        db = os.getenv("PGDATABASE", "finam")
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:539:        user = os.getenv("PGUSER", "finam")
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:540:        password = os.getenv("PGPASSWORD", "finam")
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:657:        if os.getenv("ENABLE_BROKER_POSITION_SYNC", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:661:        interval = float(os.getenv("BROKER_POSITION_SYNC_INTERVAL_SEC", "30"))
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:672:            account_id = os.getenv("FINAM_ACCOUNT_ID", "").strip()
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:678:            endpoint = os.getenv("FINAM_GRPC_ENDPOINT", "api.finam.ru:443").strip()
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:67:PIPE_DEBUG = os.getenv("PIPE_DEBUG", "0") == "1"
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:686:                timeout=float(os.getenv("BROKER_POSITION_SYNC_TIMEOUT_SEC", "10")),
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:718:            heartbeat_sec = float(os.getenv("BROKER_POSITION_SYNC_LOG_HEARTBEAT_SEC", "300"))
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:740:        if os.getenv("BROKER_POSITION_HARD_GATE_USE_BROKER_AS_LOCAL", "0") == "1":
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:767:        if os.getenv("ENABLE_BROKER_POSITION_HARD_GATE", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:770:        tolerance = float(os.getenv("BROKER_POSITION_HARD_GATE_QTY_TOLERANCE", "1e-9"))
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:801:        if os.getenv("ENABLE_BROKER_PROTECTION_GATE", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:841:        if os.getenv("ENABLE_BROKER_POSITION_HARD_GATE", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:897:        if os.getenv("ENABLE_OCO_ORDER_MANAGER", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:934:        if os.getenv("ENABLE_SUBSCRIBE_ORDERS_LISTENER", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:942:        poll_interval = float(os.getenv("SUBSCRIBE_ORDERS_POLL_INTERVAL_SEC", "15"))
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:950:            max_events = int(os.getenv("SUBSCRIBE_ORDERS_MAX_EVENTS_PER_POLL", "1"))
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:960:                heartbeat = float(os.getenv("SUBSCRIBE_ORDERS_APPLIED_HEARTBEAT_SEC", "300"))
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:973:                    heartbeat_sec=float(os.getenv("SUBSCRIBE_ORDERS_ERROR_HEARTBEAT_SEC", "300")),
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:982:        if os.getenv("ENABLE_BROKER_OPEN_ORDERS_SYNC", "0") != "1":
src/finam_core/pipelines/paper_pipeline.py.bak_trade_metadata_20260514_041633:985:        interval_sec = float(os.getenv("BROKER_OPEN_ORDERS_SYNC_INTERVAL_SEC", "30"))
src/finam_core/portfolio/finam_real_portfolio_sync.py:18:        self.account_id = (os.getenv("FINAM_ACCOUNT_ID") or "").strip()
src/finam_core/portfolio/finam_real_portfolio_sync.py:22:        self.url = os.getenv(
src/finam_core/portfolio/latest_real_positions_provider.py:14:            or os.getenv("FINAM_DSN")
src/finam_core/portfolio/latest_real_positions_provider.py:15:            or os.getenv("POSTGRES_DSN")
src/finam_core/portfolio/portfolio_equity_service.py:25:        self.database_url = database_url or os.getenv(
src/finam_core/portfolio/portfolio_mtm_service.py:31:        self.database_url = database_url or os.getenv(
src/finam_core/portfolio/position_intent_repository.py:35:        dsn = (os.getenv("DATABASE_URL") or "").strip()
src/finam_core/portfolio/position_intent_repository.py:39:        host = os.getenv("DB_HOST", "127.0.0.1")
src/finam_core/portfolio/position_intent_repository.py:40:        port = os.getenv("DB_PORT", "5432")
src/finam_core/portfolio/position_intent_repository.py:41:        name = os.getenv("DB_NAME", "finam")
src/finam_core/portfolio/position_intent_repository.py:42:        user = os.getenv("DB_USER", "finam")
src/finam_core/portfolio/position_intent_repository.py:43:        password = os.getenv("DB_PASSWORD", "")
src/finam_core/portfolio/real_portfolio_snapshot.py:96:    path = os.getenv("REAL_PORTFOLIO_JSON", "").strip()
src/finam_core/projections/projection_checkpoint_service.py:20:        self.database_url = database_url or os.getenv("DATABASE_URL")
src/finam_core/projections/projection_store.py:16:        self.database_url = database_url or os.getenv("DATABASE_URL")
src/finam_core/projections/projection_worker.py:36:            interval_sec if interval_sec is not None else os.getenv("PROJECTION_WORKER_INTERVAL_SEC", "5")
src/finam_core/projections/projection_worker.py:39:            limit if limit is not None else os.getenv("PROJECTION_WORKER_LIMIT", "10000")
src/finam_core/reconciliation/broker_order_snapshot_store.py:21:        self.database_url = (database_url or os.getenv("DATABASE_URL") or "").strip()
src/finam_core/reconciliation/broker_order_snapshot_store.py:22:        self.enabled = os.getenv("BROKER_ORDER_SNAPSHOT_STORE_ENABLED", "1") == "1"
src/finam_core/reconciliation/order_ack_repository.py:16:        self.database_url = (database_url or os.getenv("DATABASE_URL") or "").strip()
src/finam_core/reconciliation/order_reconciliation_logger.py:13:        self.database_url = (database_url or os.getenv("DATABASE_URL") or "").strip()
src/finam_core/reconciliation/order_reconciliation_logger.py:14:        self.enabled = os.getenv("ORDER_RECONCILIATION_LOGGER_ENABLED", "1") == "1"
src/finam_core/reconciliation/position_mismatch_gate.py:20:        self.tolerance = float(tolerance if tolerance is not None else os.getenv("POSITION_MISMATCH_TOLERANCE", "0.000001"))
src/finam_core/recovery/recovery_snapshot_service.py:31:        self.database_url = database_url or os.getenv("DATABASE_URL")
src/finam_core/regime/regime_engine.py:123:        log_every_sec = float(os.getenv("REGIME_ENGINE_LOG_EVERY_SEC", "60"))
src/finam_core/regime/regime_engine.py:49:        self.confirm_ticks = int(os.getenv("REGIME_CONFIRM_TICKS", "3"))
src/finam_core/research/runtime_selection_gate.py:39:        return os.getenv("ACTIVE_NG_SYMBOL", "NGM6@RTSX")
src/finam_core/research/runtime_selection_gate.py:41:        return os.getenv("ACTIVE_BR_SYMBOL", "BRM6@RTSX")
src/finam_core/research/runtime_selection_gate.py:43:        return os.getenv("ACTIVE_USDRUB_SYMBOL", "USDRUBF@RTSX")
src/finam_core/research/runtime_selection_gate.py:93:            timeframe = os.getenv("ACTIVE_CONTRACT_TIMEFRAME", "M5")
src/finam_core/risk/correlation_risk.py:28:        self.bucket_limit = float(os.getenv("CORR_BUCKET_LIMIT", "0.35"))
src/finam_core/risk/correlation_risk.py:29:        self.default_bucket = os.getenv("CORR_DEFAULT_BUCKET", "unknown")
src/finam_core/risk/finam_limits_adapter.py:43:        self.default_max_abs_position = float(os.getenv("MAX_ABS_POSITION_DEFAULT", "1"))
src/finam_core/risk/finam_limits_adapter.py:49:        if os.getenv(key):
src/finam_core/risk/finam_limits_adapter.py:50:            return float(os.getenv(key, "1")), f"env:{key}"
src/finam_core/risk/finam_limits_adapter.py:64:            account_id = os.getenv("FINAM_ACCOUNT_ID", os.getenv("ACCOUNT_ID", "")).strip()
src/finam_core/risk/kill_switch.py:27:        self.daily_loss_limit = abs(float(os.getenv("DAILY_LOSS_LIMIT", "1000")))
src/finam_core/risk/kill_switch.py:28:        self.max_drawdown_abs = abs(float(os.getenv("MAX_DRAWDOWN_ABS", "2000")))
src/finam_core/risk/persistent_kill_switch.py:26:        self.database_url = database_url or os.getenv("DATABASE_URL")
src/finam_core/risk/portfolio_heat.py:26:        self.heat_limit = float(os.getenv("PORTFOLIO_HEAT_LIMIT", "0.80"))
src/finam_core/risk/pre_trade_risk.py:87:        if os.getenv("RISK_LATENCY", "0") == "1":
src/finam_core/risk/pre_trade_risk.py:88:            self.latency = LatencyRecorder(maxlen=int(os.getenv("RISK_LATENCY_MAXLEN", "10000")))
src/finam_core/risk/real_stock_safety_gate.py:23:        self.real_stocks_only = os.getenv("REAL_STOCKS_ONLY", "1") == "1"
src/finam_core/risk/real_stock_safety_gate.py:26:        mode = (execution_mode or os.getenv("EXECUTION_MODE", "paper")).strip().lower()
src/finam_core/risk/regime_layer.py:26:        self.min_atr = float(os.getenv("REGIME_MIN_ATR", "0.03"))
src/finam_core/risk/regime_layer.py:27:        self.max_atr = float(os.getenv("REGIME_MAX_ATR", "0.80"))
src/finam_core/risk/regime_layer.py:28:        self.slope_window = int(os.getenv("REGIME_SLOPE_WINDOW", "5"))
src/finam_core/risk/regime_layer.py:29:        self.min_slope = float(os.getenv("REGIME_MIN_SLOPE", "0.0"))
src/finam_core/risk/regime_policy.py:22:        raw = os.getenv(key, "").strip()
src/finam_core/risk/regime_policy.py:47:        raw = os.getenv(key, os.getenv("MAX_SYMBOL_DRAWDOWN_DEFAULT", "0")).strip()
src/finam_core/risk/regime_policy.py:66:        raw = os.getenv(key, os.getenv("LOSS_STREAK_LIMIT_DEFAULT", "0")).strip()
src/finam_core/risk/regime_policy.py:71:        raw = os.getenv(key, os.getenv("LOSS_STREAK_PAUSE_BARS_DEFAULT", "0")).strip()
src/finam_core/risk/regime_policy.py:91:        raw = os.getenv("PORTFOLIO_MAX_OPEN_ABS_POSITION", "0").strip()
src/finam_core/risk/regime_policy.py:95:        raw = os.getenv("PORTFOLIO_MAX_PAPER_ORDERS_PER_RUN", "0").strip()
src/finam_core/risk/regime_policy.py:99:        return os.getenv("PORTFOLIO_KILL_SWITCH", "0").strip() == "1"
src/finam_core/risk/sl_tp_cooldown.py:26:        self.stop_loss_abs = float(os.getenv("RISK_V2_STOP_LOSS_ABS", "0.30"))
src/finam_core/risk/sl_tp_cooldown.py:27:        self.take_profit_abs = float(os.getenv("RISK_V2_TAKE_PROFIT_ABS", "0.60"))
src/finam_core/risk/sl_tp_cooldown.py:28:        self.cooldown_sec = float(os.getenv("RISK_V2_COOLDOWN_SEC", "300"))
src/finam_core/risk/trailing_exit.py:23:        self.stop_abs = float(stop_abs if stop_abs is not None else os.getenv("TRAILING_STOP_ABS", "0.30"))
src/finam_core/risk/trailing_exit.py:24:        self.take_abs = float(take_abs if take_abs is not None else os.getenv("TAKE_PROFIT_ABS", "0.60"))
src/finam_core/risk/trailing_exit.py:25:        self.trail_abs = float(trail_abs if trail_abs is not None else os.getenv("TRAILING_STEP_ABS", "0.30"))
src/finam_core/risk/volatility_risk.py:25:        self.default_atr = float(os.getenv("VOL_RISK_DEFAULT_ATR", "0.10"))
src/finam_core/risk/volatility_risk.py:26:        self.min_atr = float(os.getenv("VOL_RISK_MIN_ATR", "0.03"))
src/finam_core/risk/volatility_risk.py:27:        self.stop_atr_mult = float(os.getenv("VOL_RISK_STOP_ATR_MULT", "1.5"))
src/finam_core/risk/volatility_risk.py:28:        self.take_atr_mult = float(os.getenv("VOL_RISK_TAKE_ATR_MULT", "2.0"))
src/finam_core/risk/volatility_risk.py:29:        self.risk_per_trade = float(os.getenv("VOL_RISK_PER_TRADE", "100.0"))
src/finam_core/risk/volatility_risk.py:30:        self.min_qty = float(os.getenv("VOL_RISK_MIN_QTY", "1"))
src/finam_core/risk/volatility_risk.py:31:        self.max_qty = float(os.getenv("VOL_RISK_MAX_QTY", "1"))
src/finam_core/risk/volatility_risk.py:51:        min_factor = float(os.getenv("VOL_RISK_MIN_CONFIDENCE_FACTOR", "0.25"))
src/finam_core/runtime/capital_growth_mode.py:88:            os.getenv("CAPITAL_GROWTH_PROFILE", "growth")
src/finam_core/runtime/runtime_governance_coordinator_v2.py:146:            os.getenv(
src/finam_core/scripts/build_dataset.py:13:    symbol = os.getenv("SYMBOL") or "NGH6@RTSX"
src/finam_core/scripts/finam_smoke.py:156:    search = os.getenv("FINAM_ASSET_SEARCH", "NG")
src/finam_core/scripts/finam_smoke.py:182:    tf_str = os.getenv("FINAM_TIMEFRAME", "M15").upper()  # e.g. M1/M5/M15/H1/D
src/finam_core/scripts/finam_smoke.py:199:    lookback_hours = int(os.getenv("FINAM_LOOKBACK_HOURS", "24"))
src/finam_core/scripts/finam_smoke.py:89:    host = os.getenv("FINAM_API_HOST", "api.finam.ru:443")
src/finam_core/scripts/finam_smoke.py:90:    token = os.getenv("FINAM_TOKEN")
src/finam_core/scripts/finam_smoke.py:91:    account_id = os.getenv("FINAM_ACCOUNT_ID")
src/finam_core/scripts/live_bars.py:12:    dsn = os.getenv("POSTGRES_DSN")
src/finam_core/scripts/live_bars.py:18:        host=os.getenv("DB_HOST"),
src/finam_core/scripts/live_bars.py:19:        port=int(os.getenv("DB_PORT", 5432)),
src/finam_core/scripts/live_bars.py:20:        username=os.getenv("DB_USERNAME"),
src/finam_core/scripts/live_bars.py:21:        password=os.getenv("DB_PASSWORD"),
src/finam_core/scripts/live_bars.py:22:        database=os.getenv("DB_BASE"),
src/finam_core/scripts/live_bars.py:23:        min_conn=int(os.getenv("DB_MIN_CONN", 1)),
src/finam_core/scripts/live_bars.py:24:        max_conn=int(os.getenv("DB_MAX_CONN", 5)),
src/finam_core/scripts/live_intraday_pipeline.py:38:    v = os.getenv(name)
src/finam_core/scripts/live_quotes.py:5:        host=os.getenv("FINAM_GRPC_HOST") or os.getenv("FINAM_API_HOST"),
src/finam_core/scripts/live_quotes.py:6:        jwt=os.getenv("FINAM_JWT") or os.getenv("FINAM_TOKEN") or os.getenv("JWT"),
src/finam_core/scripts/load_history.py:106:    loader = HistoryLoader(host=os.getenv("FINAM_API_HOST") or "api.finam.ru:443")
src/finam_core/scripts/load_history.py:40:    v = os.getenv(name)
src/finam_core/scripts/smoke_accounts.py:9:FINAM_TOKEN = os.getenv("FINAM_TOKEN")
src/finam_core/scripts/smoke_auth.py:10:    api_secret = os.getenv("FINAM_API_SECRET")
src/finam_core/scripts/smoke_finam_grpc.py:10:    token = os.getenv("FINAM_TOKEN")
src/finam_core/scripts/smoke_finam_grpc.py:7:HOST = os.getenv("FINAM_GRPC_HOST", "api.finam.ru:443")
src/finam_core/scripts/smoke_finam_rest.py:27:        account_id = os.getenv("FINAM_ACCOUNT_ID", "").strip()
src/finam_core/scripts/test_auth_debug.py:10:    api_secret = os.getenv("FINAM_API_SECRET")
src/finam_core/scripts/test_ingest_bars.py:25:SYMBOL = os.getenv("SYMBOL") or "NGH6@RTSX"
src/finam_core/signals/signal_router.py:159:        if os.getenv("ROUTER_DEBUG_LOGS", "0") == "1":
src/finam_core/signals/signal_router.py:35:        self.min_confidence = float(os.getenv("SIGNAL_MIN_CONFIDENCE", "0.0"))
src/finam_core/signals/signal_router.py:36:        self.score_min = float(os.getenv("SIGNAL_SCORE_MIN", "0.0"))
src/finam_core/signals/signal_router.py:37:        self.score_max = float(os.getenv("SIGNAL_SCORE_MAX", "1.0"))
src/finam_core/signals/signal_router.py:38:        self.signal_ttl_sec = float(os.getenv("SIGNAL_TTL_SEC", "30"))
src/finam_core/signals/signal_router.py:45:        self.enable_ai_sentiment_features = os.getenv("ENABLE_AI_SENTIMENT_FEATURES", "0") == "1"
src/finam_core/signals/signal_router.py.bak_log_dedup_20260514_113927:21:        self.min_confidence = float(os.getenv("SIGNAL_MIN_CONFIDENCE", "0.0"))
src/finam_core/signals/signal_router.py.bak_log_dedup_20260514_113927:22:        self.score_min = float(os.getenv("SIGNAL_SCORE_MIN", "0.0"))
src/finam_core/signals/signal_router.py.bak_log_dedup_20260514_113927:23:        self.score_max = float(os.getenv("SIGNAL_SCORE_MAX", "1.0"))
src/finam_core/signals/signal_router.py.bak_log_dedup_20260514_113927:24:        self.signal_ttl_sec = float(os.getenv("SIGNAL_TTL_SEC", "30"))
src/finam_core/signals/signal_router.py.bak_log_dedup_20260514_113927:31:        self.enable_ai_sentiment_features = os.getenv("ENABLE_AI_SENTIMENT_FEATURES", "0") == "1"
src/finam_core/storage/daily_risk_repository.py:13:        self.database_url = database_url or os.getenv(
src/finam_core/storage/dynamic_watchlist_repository.py:15:        self.dsn = dsn or os.getenv(
src/finam_core/storage/fee_profile_repository.py:15:        self.database_url = database_url or os.getenv(
src/finam_core/storage/instrument_spec_repository.py:14:        self.database_url = database_url or os.getenv(
src/finam_core/storage/managed_position_repository.py:16:            or os.getenv("FINAM_DSN")
src/finam_core/storage/managed_position_repository.py:17:            or os.getenv("POSTGRES_DSN")
src/finam_core/storage/margin_requirement_repository.py:15:        self.database_url = database_url or os.getenv(
src/finam_core/storage/postgres_logger.py:23:        self.database_url = os.getenv("DATABASE_URL", "").strip()
src/finam_core/storage/postgres_logger.py:25:            db_host = os.getenv("DB_HOST", "127.0.0.1")
src/finam_core/storage/postgres_logger.py:26:            db_port = os.getenv("DB_PORT", "5432")
src/finam_core/storage/postgres_logger.py:27:            db_name = os.getenv("DB_NAME", "finam")
src/finam_core/storage/postgres_logger.py:28:            db_user = os.getenv("DB_USER", "finam")
src/finam_core/storage/postgres_logger.py:29:            db_password = os.getenv("DB_PASSWORD", "finam")
src/finam_core/storage/postgres_logger.py.bak_log_fill_trades_20260514_083316:23:        self.database_url = os.getenv("DATABASE_URL", "").strip()
src/finam_core/storage/postgres_logger.py.bak_log_fill_trades_20260514_083316:25:            db_host = os.getenv("DB_HOST", "127.0.0.1")
src/finam_core/storage/postgres_logger.py.bak_log_fill_trades_20260514_083316:26:            db_port = os.getenv("DB_PORT", "5432")
src/finam_core/storage/postgres_logger.py.bak_log_fill_trades_20260514_083316:27:            db_name = os.getenv("DB_NAME", "finam")
src/finam_core/storage/postgres_logger.py.bak_log_fill_trades_20260514_083316:28:            db_user = os.getenv("DB_USER", "finam")
src/finam_core/storage/postgres_logger.py.bak_log_fill_trades_20260514_083316:29:            db_password = os.getenv("DB_PASSWORD", "finam")
src/finam_core/storage/postgres_order_event_store.py:13:        self.database_url = database_url or os.getenv("DATABASE_URL")
src/finam_core/storage/real_position_snapshot_repository.py:13:        self.database_url = database_url or os.getenv(
src/finam_core/storage/virtual_signal_trade_repository.py:14:        self.database_url = database_url or os.getenv(
src/finam_core/strategy/breakout_reactive.py:18:        self.window = int(window if window is not None else os.getenv("STRATEGY_BREAKOUT_WINDOW", "20"))
src/finam_core/strategy/breakout_reactive.py:19:        self.breakout_abs = float(breakout_abs if breakout_abs is not None else os.getenv("STRATEGY_BREAKOUT_ABS", "0.02"))
src/finam_core/strategy/breakout_reactive.py:20:        self.qty = float(qty if qty is not None else os.getenv("STRATEGY_QTY", "1.0"))
src/finam_core/strategy/equities/mean_reversion_equity.py:23:        self.window = int(os.getenv("MR_WINDOW", "30"))
src/finam_core/strategy/equities/mean_reversion_equity.py:26:            os.getenv("MR_MIN_DEVIATION_PCT", "0.003")
src/finam_core/strategy/equities/mean_reversion_equity.py:30:            os.getenv("MR_COOLDOWN_SEC", "120")
src/finam_core/strategy/equities/mean_reversion_equity.py:34:            os.getenv("MR_MIN_ATR_PCT", "0.001")
src/finam_core/strategy/simple_reactive.py:16:        force_side = (os.getenv("FORCE_SIDE") or "").strip().upper()
src/finam_core/strategy/simple_reactive.py:17:        force_qty = float(os.getenv("FORCE_QTY", "1.0"))
src/finam_core/utils/logging_config.py:43:    fmt = os.getenv(
src/finam_core/utils/logging_config.py:47:    datefmt = os.getenv("LOG_DATEFMT", "%H:%M:%S")
src/infra/brokers/finam_rest.py:36:        base_url = os.getenv("FINAM_REST_BASE", "https://tradeapi.finam.ru").rstrip("/")
src/infra/brokers/finam_rest.py:37:        token = os.getenv("FINAM_TOKEN", "").strip()
src/infra/brokers/finam_rest.py:40:        timeout = float(os.getenv("FINAM_TIMEOUT", "15"))
src/infra/finam/client.py:62:        self.execution_enabled = os.getenv("EXECUTION_ENABLED", "0") == "1"
src/infra/finam/client.py:63:        self.mode = os.getenv("MODE", "REAL").upper()
src/infra/finam/client.py:64:        self.api_token = os.getenv("FINAM_TOKEN")
src/infra/finam/client.py:65:        self.account_id = os.getenv("FINAM_ACCOUNT_ID")
src/risk/pre_trade_risk.py:87:        if os.getenv("RISK_LATENCY", "0") == "1":
src/risk/pre_trade_risk.py:88:            self.latency = LatencyRecorder(maxlen=int(os.getenv("RISK_LATENCY_MAXLEN", "10000")))
src/scripts/analytics_data_quality_report.py:10:    database_url = os.getenv("DATABASE_URL")
src/scripts/analytics_runtime_supervisor.py:85:    poll_sec = int(os.getenv("ANALYTICS_SUPERVISOR_POLL_SEC", "60"))
src/scripts/analytics_runtime_supervisor.py:86:    timeframe = os.getenv("ANALYTICS_SUPERVISOR_TIMEFRAME", "M5")
src/scripts/analytics_runtime_supervisor.py:87:    commission = os.getenv("ANALYTICS_SUPERVISOR_COMMISSION", "0.0001")
src/scripts/analytics_runtime_supervisor.py:88:    once = os.getenv("ANALYTICS_SUPERVISOR_ONCE", "0") == "1"
src/scripts/analyze_radar_candidates.py:105:    dsn = os.getenv("DATABASE_URL")
src/scripts/analyze_regime_failures_v2.py:8:    database_url = os.getenv("DATABASE_URL")
src/scripts/analyze_replay_pnl.py:32:        f"postgresql://{os.getenv('DB_USER', 'finam')}:{os.getenv('DB_PASSWORD', 'finam')}"
src/scripts/analyze_replay_pnl.py:33:        f"@{os.getenv('DB_HOST', '127.0.0.1')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME', 'finam')}"
src/scripts/analyze_replay_pnl.py:51:    token = (os.getenv("TG_BOT_TOKEN") or os.getenv("TG_TOKEN") or "").strip()
src/scripts/analyze_replay_pnl.py:52:    chat_id = os.getenv("TG_CHAT_ID", "").strip()
src/scripts/analyze_watch_candidates_runtime.py:463:        os.getenv("CAPITAL_GROWTH_PROFILE", "growth")
src/scripts/analyze_watch_candidates_runtime.py:505:        os.getenv("CAPITAL_GROWTH_PROFILE", "growth")
src/scripts/analyze_watch_candidates_runtime.py:855:    dsn = os.getenv("DATABASE_URL")
src/scripts/analyze_watch_candidates_runtime.py:859:    limit = int(os.getenv("WATCH_RUNTIME_LIMIT", "10"))
src/scripts/analyze_watch_candidates_runtime.py:860:    alert_ttl_minutes = int(os.getenv("SIGNAL_ALERT_TTL_MINUTES", "120"))
src/scripts/analyze_watch_candidates_runtime.py:861:    max_alerts_per_group = int(os.getenv("MAX_ALERTS_PER_CORRELATION_GROUP", "2"))
src/scripts/analyze_watch_candidates_runtime.py:862:    max_active_signals = int(os.getenv("MAX_ACTIVE_SIGNALS", "5"))
src/scripts/analyze_watch_candidates_runtime.py:863:    max_active_signals = int(os.getenv("MAX_ACTIVE_SIGNALS", "5"))
src/scripts/apply_regime_runtime_control_v1.py:13:    database_url = os.getenv("DATABASE_URL")
src/scripts/apply_regime_runtime_control_v1.py:7:MIN_FILLS = int(os.getenv("REGIME_CONTROL_MIN_FILLS", "3"))
src/scripts/apply_regime_runtime_control_v1.py:8:MIN_AVG_CASHFLOW_HEALTHY = float(os.getenv("REGIME_CONTROL_MIN_AVG_CASHFLOW_HEALTHY", "0.0"))
src/scripts/apply_regime_runtime_control_v1.py:9:MIN_AVG_CASHFLOW_DEGRADED = float(os.getenv("REGIME_CONTROL_MIN_AVG_CASHFLOW_DEGRADED", "-0.05"))
src/scripts/apply_strategy_health_to_runtime_control.py:14:    database_url = os.getenv("DATABASE_URL")
src/scripts/apply_strategy_performance_monitor_v2.py:11:MIN_PROFIT_FACTOR_DEGRADED = float(os.getenv("SPM_V2_MIN_PF_DEGRADED", "0.75"))
src/scripts/apply_strategy_performance_monitor_v2.py:12:MIN_EXPECTANCY_DEGRADED = float(os.getenv("SPM_V2_MIN_EXPECTANCY_DEGRADED", "-0.05"))
src/scripts/apply_strategy_performance_monitor_v2.py:16:    database_url = os.getenv("DATABASE_URL")
src/scripts/apply_strategy_performance_monitor_v2.py:7:MIN_CLOSED_TRADES = int(os.getenv("SPM_V2_MIN_CLOSED_TRADES", "5"))
src/scripts/apply_strategy_performance_monitor_v2.py:8:MIN_PROFIT_FACTOR_HEALTHY = float(os.getenv("SPM_V2_MIN_PF_HEALTHY", "1.15"))
src/scripts/apply_strategy_performance_monitor_v2.py:9:MIN_EXPECTANCY_HEALTHY = float(os.getenv("SPM_V2_MIN_EXPECTANCY_HEALTHY", "0.0"))
src/scripts/backfill_closed_trade_attribution.py:9:    database_url = os.getenv("DATABASE_URL")
src/scripts/backfill_missing_strategy_attribution_from_map.py:12:    database_url = os.getenv("DATABASE_URL")
src/scripts/backfill_smart_money_continuous.py:47:    database_url = os.getenv("DATABASE_URL")
src/scripts/backfill_strategy_attribution.py:11:    database_url = os.getenv("DATABASE_URL")
src/scripts/backfill_trade_contract_identity.py:11:    database_url = os.getenv("DATABASE_URL")
src/scripts/backtest_compare.py:602:    ap.add_argument("--db", default=os.getenv("BARS_DB") or "data/bars.sqlite", help="SQLite path (default: data/bars.sqlite)")
src/scripts/backtest_compare.py:603:    ap.add_argument("--symbol", default=os.getenv("SYMBOL") or "NGH6@RTSX")
src/scripts/backtest_compare.py:604:    ap.add_argument("--tf", "--timeframe", dest="tf", default=os.getenv("TIMEFRAME") or "M1")
src/scripts/backtest_compare.py:605:    ap.add_argument("--days", type=int, default=int(os.getenv("DAYS") or "7"))
src/scripts/backtest_compare.py:606:    ap.add_argument("--qty", type=float, default=float(os.getenv("QTY") or "1"))
src/scripts/backtest_compare.py:607:    ap.add_argument("--mult", type=float, default=float(os.getenv("MULT") or "1.0"))
src/scripts/backtest_compare.py:608:    ap.add_argument("--commission", type=float, default=float(os.getenv("COMMISSION") or "0.0"), help="commission per side, in currency")
src/scripts/backtest_compare.py:609:    ap.add_argument("--slippage-bps", type=float, default=float(os.getenv("SLIPPAGE_BPS") or "0.0"))
src/scripts/backtest_compare.py:612:    ap.add_argument("--a-k", type=float, default=float(os.getenv("A_K") or "2.0"))
src/scripts/backtest_compare.py:613:    ap.add_argument("--b-k", type=float, default=float(os.getenv("B_K") or "2.5"))
src/scripts/backtest_compare.py:614:    ap.add_argument("--c-donchian", type=int, default=int(os.getenv("C_DONCHIAN") or "20"))
src/scripts/backtest_compare.py:615:    ap.add_argument("--c-atr", type=int, default=int(os.getenv("C_ATR") or "14"))
src/scripts/backtest_compare.py:616:    ap.add_argument("--c-atr-mult", type=float, default=float(os.getenv("C_ATR_MULT") or "2.5"))
src/scripts/backtest_compare.py:618:    ap.add_argument("--outdir", default=os.getenv("BACKTEST_OUTDIR") or "data/backtests")
src/scripts/backtest_from_postgres.py:29:    return os.getenv("DATABASE_URL") or (
src/scripts/backtest_from_postgres.py:30:        f"postgresql://{os.getenv('DB_USER','finam')}:{os.getenv('DB_PASSWORD','finam')}"
src/scripts/backtest_from_postgres.py:31:        f"@{os.getenv('DB_HOST','127.0.0.1')}:{os.getenv('DB_PORT','5432')}/{os.getenv('DB_NAME','finam')}"
src/scripts/backtest_runner.py:1021:    wf_mode = (os.getenv("WF_MODE") or "").strip().lower()
src/scripts/backtest_runner.py:675:    splits = int(os.getenv("WF_SPLITS") or "8")
src/scripts/backtest_runner.py:676:    select_metric = os.getenv("WF_SELECT_METRIC") or "score"
src/scripts/backtest_runner.py:937:    ap.add_argument("--db", default=os.getenv("BARS_DB") or "data/bars.sqlite")
src/scripts/backtest_runner.py:938:    ap.add_argument("--symbol", default=os.getenv("SYMBOL") or "NGH6@RTSX")
src/scripts/backtest_runner.py:939:    ap.add_argument("--timeframe", default=(os.getenv("TIMEFRAME") or "M1").upper())
src/scripts/backtest_runner.py:940:    ap.add_argument("--start", default=os.getenv("START") or "")
src/scripts/backtest_runner.py:941:    ap.add_argument("--end", default=os.getenv("END") or "")
src/scripts/backtest_runner.py:942:    ap.add_argument("--strategy", default=os.getenv("STRATEGY") or "vwap_bands_mr")
src/scripts/backtest_runner.py:944:    ap.add_argument("--starting-cash", type=float, default=float(os.getenv("STARTING_CASH") or "100000"))
src/scripts/backtest_runner.py:945:    ap.add_argument("--qty", type=float, default=float(os.getenv("QTY") or "1.0"))
src/scripts/backtest_runner.py:949:    ap.add_argument("--report", default=(os.getenv("REPORT") or "").strip())
src/scripts/backtest_runner.py:950:    ap.add_argument("--top", type=int, default=int(os.getenv("TOP") or "20"))
src/scripts/backtest_runner.py:951:    ap.add_argument("--order", default=(os.getenv("ORDER") or "score"))
src/scripts/backtest_runner.py:952:    ap.add_argument("--min-trades", type=int, default=int(os.getenv("MIN_TRADES") or "0"))
src/scripts/backtest_runner.py:953:    ap.add_argument("--commission", type=float, default=float(os.getenv("COMMISSION_PER_TRADE") or "0.0"))
src/scripts/backtest_runner.py:954:    ap.add_argument("--slippage-bps", type=float, default=float(os.getenv("SLIPPAGE_BPS") or "0.0"))
src/scripts/backtest_runner.py:955:    ap.add_argument("--allow-short", action="store_true", default=(os.getenv("ALLOW_SHORT", "0") == "1"))
src/scripts/backtest_runner.py:958:    ap.add_argument("--window", default=os.getenv("WINDOW") or "200,400,800")
src/scripts/backtest_runner.py:959:    ap.add_argument("--k", default=os.getenv("K") or "1.5,2.0,2.5")
src/scripts/backtest_runner.py:960:    ap.add_argument("--fast", default=os.getenv("FAST") or "10,20,30")
src/scripts/backtest_runner.py:961:    ap.add_argument("--slow", default=os.getenv("SLOW") or "60,90,120")
src/scripts/backtest_runner.py:962:    ap.add_argument("--stop-pct", dest="stop_pct", default=os.getenv("STOP_PCT") or "0.0")
src/scripts/backtest_runner.py:963:    ap.add_argument("--take-pct", dest="take_pct", default=os.getenv("TAKE_PCT") or "0.0")
src/scripts/backtest_runner.py:964:    ap.add_argument("--session", default=os.getenv("SESSION") or "")
src/scripts/backtest_runner.py:965:    ap.add_argument("--mr-ema", dest="mr_ema", default=os.getenv("MR_EMA") or "0")
src/scripts/backtest_runner.py:966:    ap.add_argument("--mr-max-dev", dest="mr_max_dev", default=os.getenv("MR_MAX_DEV") or "0.0")
src/scripts/backtest_runner.py:967:    ap.add_argument("--regime-layer", dest="regime_layer", default=os.getenv("REGIME_LAYER") or "")
src/scripts/backtest_runner.py:968:    ap.add_argument("--regime-atr-n", dest="regime_atr_n", default=os.getenv("REGIME_ATR_N") or "14")
src/scripts/backtest_runner.py:969:    ap.add_argument("--regime-atr-mode", dest="regime_atr_mode", default=os.getenv("REGIME_ATR_MODE") or "percentile")
src/scripts/backtest_runner.py:970:    ap.add_argument("--regime-atr-threshold", dest="regime_atr_threshold", default=os.getenv("REGIME_ATR_THRESHOLD") or "0.0")
src/scripts/backtest_runner.py:971:    ap.add_argument("--regime-atr-pct-window", dest="regime_atr_pct_window", default=os.getenv("REGIME_ATR_PCT_WINDOW") or "100")
src/scripts/backtest_runner.py:972:    ap.add_argument("--regime-ema-slope", dest="regime_ema_slope", default=os.getenv("REGIME_EMA_SLOPE") or "")
src/scripts/backtest_runner.py:973:    ap.add_argument("--regime-ema-slope-lookback", dest="regime_ema_slope_lookback", default=os.getenv("REGIME_EMA_SLOPE_LOOKBACK") or "20")
src/scripts/backtest_runner.py:974:    ap.add_argument("--regime-ema-slope-threshold", dest="regime_ema_slope_threshold", default=os.getenv("REGIME_EMA_SLOPE_THRESHOLD") or "0.002")
src/scripts/backtest_runner.py:975:    ap.add_argument("--regime-adaptive-mode", dest="regime_adaptive_mode", default=os.getenv("REGIME_ADAPTIVE_MODE") or "")
src/scripts/backtest_runner.py:976:    ap.add_argument("--regime-trend-confirm-bars", dest="regime_trend_confirm_bars", default=os.getenv("REGIME_TREND_CONFIRM_BARS") or "1")
src/scripts/backtest_runner.py:977:    ap.add_argument("--tradeability-gate", dest="tradeability_gate", default=os.getenv("TRADEABILITY_GATE") or "")
src/scripts/backtest_runner.py:978:    ap.add_argument("--tradeability-atr-n", dest="tradeability_atr_n", default=os.getenv("TRADEABILITY_ATR_N") or "14")
src/scripts/backtest_runner.py:979:    ap.add_argument("--tradeability-range-window", dest="tradeability_range_window", default=os.getenv("TRADEABILITY_RANGE_WINDOW") or "100")
src/scripts/backtest_runner.py:980:    ap.add_argument("--tradeability-min-range-atr", dest="tradeability_min_range_atr", default=os.getenv("TRADEABILITY_MIN_RANGE_ATR") or "1.5")
src/scripts/backtest_runner.py:981:    ap.add_argument("--tradeability-max-range-atr", dest="tradeability_max_range_atr", default=os.getenv("TRADEABILITY_MAX_RANGE_ATR") or "0.0")
src/scripts/backtest_runner.py:982:    ap.add_argument("--daily-loss-limit", dest="daily_loss_limit", default=os.getenv("DAILY_LOSS_LIMIT") or "0.0")
src/scripts/backtest_runner.py:983:    ap.add_argument("--save-trades", action="store_true", default=(os.getenv("SAVE_TRADES", "0") == "1"))
src/scripts/backtest_runner.py:984:    ap.add_argument("--limit-grid", type=int, default=int(os.getenv("LIMIT_GRID") or "0"))  # 0 = без лимита
src/scripts/build_dataset.py:13:    symbol = os.getenv("SYMBOL") or "NGH6@RTSX"
src/scripts/check_market_data_quality.py:13:    return os.getenv("DATABASE_URL") or (
src/scripts/check_market_data_quality.py:14:        f"postgresql://{os.getenv('DB_USER','finam')}:{os.getenv('DB_PASSWORD','finam')}"
src/scripts/check_market_data_quality.py:15:        f"@{os.getenv('DB_HOST','127.0.0.1')}:{os.getenv('DB_PORT','5432')}/{os.getenv('DB_NAME','finam')}"
src/scripts/check_protective_order_recovery.py:13:    limit = int(os.getenv("PROTECTIVE_ORDER_RECOVERY_LIMIT", "100"))
src/scripts/check_protective_order_recovery.py:9:load_dotenv(os.getenv("FINAM_ENV_FILE", "/opt/finam-core/deploy/env/.env"), override=False)
src/scripts/check_runtime_state_restore.py:8:    dsn = os.getenv("DATABASE_URL")
src/scripts/commission_aware_strategy_analytics.py:87:    commission_bps = float(os.getenv("ANALYTICS_COMMISSION_BPS", "2.0"))
src/scripts/commission_aware_strategy_analytics.py:88:    slippage_bps = float(os.getenv("ANALYTICS_SLIPPAGE_BPS", "3.0"))
src/scripts/finam_smoke.py:156:    search = os.getenv("FINAM_ASSET_SEARCH", "NG")
src/scripts/finam_smoke.py:182:    tf_str = os.getenv("FINAM_TIMEFRAME", "M15").upper()  # e.g. M1/M5/M15/H1/D
src/scripts/finam_smoke.py:199:    lookback_hours = int(os.getenv("FINAM_LOOKBACK_HOURS", "24"))
src/scripts/finam_smoke.py:89:    host = os.getenv("FINAM_API_HOST", "api.finam.ru:443")
src/scripts/finam_smoke.py:90:    token = os.getenv("FINAM_TOKEN")
src/scripts/finam_smoke.py:91:    account_id = os.getenv("FINAM_ACCOUNT_ID")
src/scripts/first_real_order_check.py:12:    symbol = os.getenv("FIRST_REAL_ORDER_SYMBOL", "SBER@MISX")
src/scripts/first_real_order_check.py:13:    max_qty = float(os.getenv("FIRST_REAL_ORDER_MAX_QTY", "1"))
src/scripts/first_real_order_check.py:14:    max_value = float(os.getenv("FIRST_REAL_ORDER_MAX_VALUE", "3000"))
src/scripts/first_real_order_check.py:16:    enabled = os.getenv("REAL_BUY_EXECUTION_ENABLED", "0") == "1"
src/scripts/first_real_order_check.py:17:    kill_switch = os.getenv("REAL_BUY_KILL_SWITCH", "1") == "1"
src/scripts/first_real_order_check.py:18:    wiring = os.getenv("REAL_BUY_CLIENT_WIRING_CONFIRMED", "0") == "1"
src/scripts/first_real_order_check.py:8:    dsn = os.getenv("DATABASE_URL")
src/scripts/generate_runtime_universe_report.py:51:    database_url = os.getenv("DATABASE_URL")
src/scripts/init_db.py:17:    database_url = os.getenv("DATABASE_URL", "").strip()
src/scripts/init_db.py:21:    host = os.getenv("DB_HOST", "localhost")
src/scripts/init_db.py:22:    port = os.getenv("DB_PORT", "5432")
src/scripts/init_db.py:23:    name = os.getenv("DB_NAME", "finam")
src/scripts/init_db.py:24:    user = os.getenv("DB_USER", "finam")
src/scripts/init_db.py:25:    password = os.getenv("DB_PASSWORD", "finam")
src/scripts/live_bars.py:12:    dsn = os.getenv("POSTGRES_DSN")
src/scripts/live_bars.py:18:        host=os.getenv("DB_HOST"),
src/scripts/live_bars.py:19:        port=int(os.getenv("DB_PORT", 5432)),
src/scripts/live_bars.py:20:        username=os.getenv("DB_USERNAME"),
src/scripts/live_bars.py:21:        password=os.getenv("DB_PASSWORD"),
src/scripts/live_bars.py:22:        database=os.getenv("DB_BASE"),
src/scripts/live_bars.py:23:        min_conn=int(os.getenv("DB_MIN_CONN", 1)),
src/scripts/live_bars.py:24:        max_conn=int(os.getenv("DB_MAX_CONN", 5)),
src/scripts/live_intraday_pipeline.py:38:    v = os.getenv(name)
src/scripts/live_pnl_dashboard.py:10:        os.getenv("DATABASE_URL")
src/scripts/live_pnl_dashboard.py:11:        or os.getenv("POSTGRES_DSN")
src/scripts/live_quotes.py:6:        host=os.getenv("FINAM_GRPC_HOST") or os.getenv("FINAM_API_HOST"),
src/scripts/live_quotes.py:7:        jwt=os.getenv("FINAM_JWT") or os.getenv("FINAM_TOKEN") or os.getenv("JWT"),
src/scripts/live_quotes.py:9:    print("FINAM_GRPC_HOST", os.getenv("FINAM_GRPC_HOST"))
src/scripts/manual_order_call.py:11:load_dotenv(os.getenv("FINAM_ENV_FILE", "/opt/finam-core/deploy/env/.env"), override=False)
src/scripts/monitor_signal_lifecycle.py:84:    dsn = os.getenv("DATABASE_URL")
src/scripts/monitor_signal_lifecycle.py:88:    limit = int(os.getenv("SIGNAL_LIFECYCLE_MONITOR_LIMIT", "50"))
src/scripts/place_protective_for_filled_entries.py:108:    limit = int(os.getenv("PROTECTIVE_PLACEMENT_LIMIT", "100"))
src/scripts/place_protective_for_filled_entries.py:113:    print(f"auto_real_protective_enabled={os.getenv('AUTO_REAL_PROTECTIVE_ORDERS', '0')}")
src/scripts/place_protective_for_filled_entries.py:116:    stop_pct = float(os.getenv("PROTECTIVE_STOP_PCT", "0.01"))
src/scripts/place_protective_for_filled_entries.py:119:        manual_reference_price = os.getenv("PROTECTIVE_REFERENCE_PRICE")
src/scripts/place_protective_for_filled_entries.py:14:load_dotenv(os.getenv("FINAM_ENV_FILE", "/opt/finam-core/deploy/env/.env"), override=False)
src/scripts/place_protective_for_filled_entries.py:151:        auto_enabled = os.getenv("AUTO_REAL_PROTECTIVE_ORDERS", "0") == "1"
src/scripts/place_protective_for_filled_entries.py:26:    database_url = os.getenv("DATABASE_URL", "").strip()
src/scripts/place_protective_for_filled_entries.py:60:    database_url = os.getenv("DATABASE_URL", "").strip()
src/scripts/pnl_by_institutional_regime.py:66:    tax_rate = float(os.getenv("ANALYTICS_ESTIMATED_TAX_RATE", "0.15"))
src/scripts/portfolio_governance_refresh.py:39:    timeframe = os.getenv("PORTFOLIO_GOVERNANCE_TIMEFRAME", "M5")
src/scripts/realized_pnl_engine.py:80:        os.getenv("ANALYTICS_ESTIMATED_TAX_RATE", "0.15")
src/scripts/reconcile_order_acks.py:21:load_dotenv(os.getenv("FINAM_ENV_FILE", "/opt/finam-core/deploy/env/.env"), override=False)
src/scripts/reconcile_order_acks.py:63:    limit = int(os.getenv("ORDER_ACK_RECONCILE_LIMIT", "100"))
src/scripts/replay_br_pipeline.py:119:        account_id = str(os.getenv("FINAM_ACCOUNT_ID", os.getenv("ACCOUNT_ID", "paper")))
src/scripts/replay_br_pipeline.py:193:        os.getenv("DATABASE_URL")
src/scripts/replay_br_pipeline.py:194:        or os.getenv("POSTGRES_DSN")
src/scripts/replay_br_pipeline.py:313:    os.environ["EXECUTION_MODE"] = os.getenv("EXECUTION_MODE", "paper")
src/scripts/research/build_intermarket_regime_snapshot.py:86:    timeframe = os.getenv("INTERMARKET_TIMEFRAME", "M5")
src/scripts/research/build_intermarket_regime_snapshot.py:87:    lookback_bars = int(os.getenv("INTERMARKET_LOOKBACK_BARS", "12"))
src/scripts/restore_runtime_state.py:8:    dsn = os.getenv("DATABASE_URL")
src/scripts/run_adaptive_portfolio_allocator.py:13:    dsn = os.getenv("DATABASE_URL")
src/scripts/run_autonomous_portfolio_brain.py:21:    dsn = os.getenv("DATABASE_URL")
src/scripts/run_broker_reconciliation_engine.py:12:    dsn = os.getenv("DATABASE_URL")
src/scripts/run_capital_growth_daily_loss_guard.py:11:    dsn = os.getenv("DATABASE_URL")
src/scripts/run_capital_growth_daily_loss_guard.py:15:    profile_name = os.getenv("CAPITAL_GROWTH_PROFILE", "growth")
src/scripts/run_capital_growth_mode.py:10:    dsn = os.getenv("DATABASE_URL")
src/scripts/run_capital_growth_portfolio_governor.py:13:    dsn = os.getenv("DATABASE_URL")
src/scripts/run_capital_growth_portfolio_governor.py:18:        os.getenv("CAPITAL_GROWTH_PROFILE", "growth")
src/scripts/run_capital_growth_regime_allocator.py:12:    dsn = os.getenv("DATABASE_URL")
src/scripts/run_client_order_id_recovery_lookup.py:34:    dsn = os.getenv("DATABASE_URL")
src/scripts/run_closed_trade_report.py:89:        dbname=os.getenv("PGDATABASE", "finam_core"),
src/scripts/run_closed_trade_report.py:90:        user=os.getenv("PGUSER") or None,
src/scripts/run_closed_trade_report.py:91:        host=os.getenv("PGHOST") or None,
src/scripts/run_closed_trade_report.py:92:        port=os.getenv("PGPORT") or None,
src/scripts/run_closed_trade_report.py:93:        password=os.getenv("PGPASSWORD") or None,
src/scripts/run_daily_risk_check.py:19:        max_daily_loss_pct=float(os.getenv("MAX_DAILY_LOSS_PCT", "3.0")),
src/scripts/run_daily_risk_check.py:20:        max_drawdown_pct=float(os.getenv("MAX_DRAWDOWN_PCT", "10.0")),
src/scripts/run_execution_correctness_audit.py:8:    dsn = os.getenv("DATABASE_URL")
src/scripts/run_execution_correctness_repair.py:10:    dsn = os.getenv("DATABASE_URL")
src/scripts/run_execution_intent_accounting_bridge.py:11:    dsn = os.getenv("DATABASE_URL")
src/scripts/run_execution_intent_fill_simulator.py:12:    dsn = os.getenv("DATABASE_URL")
src/scripts/run_execution_intent_router.py:14:    dsn = os.getenv("DATABASE_URL")
src/scripts/run_execution_lifecycle_determinism.py:14:    dsn = os.getenv("DATABASE_URL")
src/scripts/run_execution_recovery_supervisor.py:61:        os.getenv(
src/scripts/run_execution_recovery_supervisor.py:97:    dsn = os.getenv("DATABASE_URL")
src/scripts/run_manual_trade_reconciliation.py:64:        dbname=os.getenv("PGDATABASE", "finam_core"),
src/scripts/run_manual_trade_reconciliation.py:65:        user=os.getenv("PGUSER") or None,
src/scripts/run_manual_trade_reconciliation.py:66:        password=os.getenv("PGPASSWORD") or None,
src/scripts/run_manual_trade_reconciliation.py:67:        host=os.getenv("PGHOST") or None,
src/scripts/run_manual_trade_reconciliation.py:68:        port=os.getenv("PGPORT") or None,
src/scripts/run_market_bars_source_backfill.py:13:    dsn = os.getenv("DATABASE_URL")
src/scripts/run_market_bars_source_backfill.py:17:    symbol = os.getenv("BARS_SYMBOL", "SBER@MISX").strip().upper()
src/scripts/run_market_bars_source_backfill.py:18:    timeframe = os.getenv("BARS_TIMEFRAME", "M5").strip().upper()
src/scripts/run_market_pipeline.py:100:    parser.add_argument("--enable-filter-engine", action="store_true", default=(os.getenv("ENABLE_FILTER_ENGINE") == "1"))
src/scripts/run_market_pipeline.py:101:    parser.add_argument("--filter-profile", default=os.getenv("FILTER_PROFILE") or "")
src/scripts/run_market_pipeline.py:102:    parser.add_argument("--tradeability-gate", default=os.getenv("TRADEABILITY_GATE") or "")
src/scripts/run_market_pipeline.py:103:    parser.add_argument("--tradeability-min-range-atr", type=float, default=float(os.getenv("TRADEABILITY_MIN_RANGE_ATR") or "1.5"))
src/scripts/run_market_pipeline.py:104:    parser.add_argument("--tradeability-max-range-atr", type=float, default=float(os.getenv("TRADEABILITY_MAX_RANGE_ATR") or "0.0"))
src/scripts/run_market_pipeline.py:105:    parser.add_argument("--regime-ema-slope", default=os.getenv("REGIME_EMA_SLOPE") or "")
src/scripts/run_market_pipeline.py:106:    parser.add_argument("--regime-adaptive-mode", default=os.getenv("REGIME_ADAPTIVE_MODE") or "")
src/scripts/run_market_pipeline.py:155:ACCOUNT_ID = os.getenv("FINAM_ACCOUNT_ID") or os.getenv("ACCOUNT_ID") or "1943312"
src/scripts/run_market_pipeline.py:162:    p.add_argument("--symbol", default=os.getenv("SYMBOL") or "NGH6@RTSX")
src/scripts/run_market_pipeline.py:163:    p.add_argument("--strategy", default=os.getenv("PIPELINE_STRATEGY") or "once_buy", choices=("once_buy", "simple_reactive", "breakout_reactive", "strategy_stack", "vwap_bands_mr"))
src/scripts/run_market_pipeline.py:168:    p.add_argument("--run-secs", type=float, default=float(os.getenv("RUN_SECS") or "0"))
src/scripts/run_market_pipeline.py:169:    p.add_argument("--starting-cash", type=float, default=float(os.getenv("STARTING_CASH") or "100000"))
src/scripts/run_market_pipeline.py:170:    p.add_argument("--portfolio-snapshot-path", default=os.getenv("PORTFOLIO_SNAPSHOT_PATH") or "")
src/scripts/run_market_pipeline.py:171:    p.add_argument("--portfolio-refresh-sec", type=float, default=float(os.getenv("PORTFOLIO_REFRESH_SEC") or "0"))
src/scripts/run_market_pipeline.py:172:    p.add_argument("--md-heartbeat-sec", type=float, default=float(os.getenv("MD_HEARTBEAT_SEC") or "10"))
src/scripts/run_market_pipeline.py:176:    p.add_argument("--risk-soft", action="store_true", default=(os.getenv("RISK_SOFT") == "1"))
src/scripts/run_market_pipeline.py:177:    p.add_argument("--exit-on-fill", action="store_true", default=(os.getenv("EXIT_ON_FILL", "1") == "1"))
src/scripts/run_market_pipeline.py:180:    p.add_argument("--quote-log-every", type=float, default=float(os.getenv("QUOTE_LOG_EVERY") or "0"))
src/scripts/run_market_pipeline.py:185:    p.add_argument("--enable-filter-engine", action="store_true", default=(os.getenv("ENABLE_FILTER_ENGINE") == "1"))
src/scripts/run_market_pipeline.py:186:    p.add_argument("--filter-profile", default=os.getenv("FILTER_PROFILE") or "")
src/scripts/run_market_pipeline.py:187:    p.add_argument("--tradeability-gate", default=os.getenv("TRADEABILITY_GATE") or "")
src/scripts/run_market_pipeline.py:188:    p.add_argument("--tradeability-min-range-atr", type=float, default=float(os.getenv("TRADEABILITY_MIN_RANGE_ATR") or "1.5"))
src/scripts/run_market_pipeline.py:189:    p.add_argument("--tradeability-max-range-atr", type=float, default=float(os.getenv("TRADEABILITY_MAX_RANGE_ATR") or "0.0"))
src/scripts/run_market_pipeline.py:190:    p.add_argument("--regime-ema-slope", default=os.getenv("REGIME_EMA_SLOPE") or "")
src/scripts/run_market_pipeline.py:191:    p.add_argument("--regime-adaptive-mode", default=os.getenv("REGIME_ADAPTIVE_MODE") or "")
src/scripts/run_market_pipeline.py:293:        if os.getenv("ENABLE_TEST_STRATEGY", "0") == "1":
src/scripts/run_market_pipeline.py:331:    if os.getenv("ENABLE_STARTUP_RECOVERY_GATE", "1") == "1":
src/scripts/run_market_pipeline.py:337:            rebuild_aggregate_type=os.getenv("STARTUP_REBUILD_AGGREGATE_TYPE", "portfolio"),
src/scripts/run_market_pipeline.py:338:            rebuild_aggregate_id=os.getenv("STARTUP_REBUILD_AGGREGATE_ID"),
src/scripts/run_market_pipeline.py:342:    execution_mode = os.getenv("EXECUTION_MODE", "paper")
src/scripts/run_market_pipeline.py:387:    if os.getenv("ENABLE_REALTIME_PROJECTIONS", "1") == "1":
src/scripts/run_market_pipeline.py:405:    if os.getenv("ENABLE_RECOVERY_ORCHESTRATOR", "1") == "1":
src/scripts/run_market_pipeline.py:429:            if os.getenv("SIMULATE_MARKET", "0") == "1":
src/scripts/run_market_pipeline.py:50:load_dotenv(os.getenv("FINAM_ENV_FILE", "/opt/finam-core/deploy/env/.env"), override=False)
src/scripts/run_market_pipeline.py:61:    parser.add_argument("--symbol", default=os.getenv("SYMBOL") or "NGH6@RTSX")
src/scripts/run_market_pipeline.py:64:        default=os.getenv("SYMBOLS") or "",
src/scripts/run_market_pipeline.py:71:        default=(os.getenv("USE_DYNAMIC_UNIVERSE") == "1"),
src/scripts/run_market_pipeline.py:78:        default=int(os.getenv("DYNAMIC_UNIVERSE_LIMIT") or "10"),
src/scripts/run_market_pipeline.py:83:        default=os.getenv("PIPELINE_STRATEGY") or "once_buy",
src/scripts/run_market_pipeline.py:87:    parser.add_argument("--run-secs", type=float, default=float(os.getenv("RUN_SECS") or "0"))
src/scripts/run_market_pipeline.py:88:    parser.add_argument("--starting-cash", type=float, default=float(os.getenv("STARTING_CASH") or "100000"))
src/scripts/run_market_pipeline.py:89:    parser.add_argument("--portfolio-snapshot-path", default=os.getenv("PORTFOLIO_SNAPSHOT_PATH") or "")
src/scripts/run_market_pipeline.py:90:    parser.add_argument("--portfolio-refresh-sec", type=float, default=float(os.getenv("PORTFOLIO_REFRESH_SEC") or "0"))
src/scripts/run_market_pipeline.py:91:    parser.add_argument("--md-heartbeat-sec", type=float, default=float(os.getenv("MD_HEARTBEAT_SEC") or "10"))
src/scripts/run_market_pipeline.py:94:    parser.add_argument("--risk-soft", action="store_true", default=(os.getenv("RISK_SOFT") == "1"))
src/scripts/run_market_pipeline.py:95:    parser.add_argument("--exit-on-fill", action="store_true", default=(os.getenv("EXIT_ON_FILL", "1") == "1"))
src/scripts/run_market_pipeline.py:97:    parser.add_argument("--quote-log-every", type=float, default=float(os.getenv("QUOTE_LOG_EVERY") or "0"))
src/scripts/run_market_radar.py:48:    dsn = os.getenv("DATABASE_URL", "dbname=finam user=finam password=finam host=localhost")
src/scripts/run_oms_invariant_audit.py:15:    dsn = os.getenv("DATABASE_URL")
src/scripts/run_portfolio_execution_planner.py:28:    dsn = os.getenv("DATABASE_URL")
src/scripts/run_portfolio_execution_queue.py:31:    dsn = os.getenv("DATABASE_URL")
src/scripts/run_portfolio_execution_queue.py:42:            lookback_minutes = int(os.getenv("PORTFOLIO_QUEUE_LOOKBACK_MINUTES", "1440"))
src/scripts/run_portfolio_execution_queue.py:87:                max_execute=int(os.getenv("PORTFOLIO_QUEUE_MAX_EXECUTE", "3")),
src/scripts/run_portfolio_execution_queue.py:88:                min_quality_score=float(os.getenv("PORTFOLIO_QUEUE_MIN_QUALITY_SCORE", "45")),
src/scripts/run_portfolio_mtm.py:11:    os.getenv("MARGIN_UTILIZATION_ALERT_PCT", "65")
src/scripts/run_portfolio_mtm.py:15:    os.getenv("PORTFOLIO_BASE_EQUITY", "366337.96")
src/scripts/run_portfolio_reconciliation_engine.py:14:    dsn = os.getenv("DATABASE_URL")
src/scripts/run_position_lifecycle_manager.py:12:    dsn = os.getenv("DATABASE_URL")
src/scripts/run_protective_lifecycle_manager.py:12:    symbol = os.getenv("PROTECTIVE_SYMBOL", "SBER@MISX").strip().upper()
src/scripts/run_protective_lifecycle_manager.py:13:    stop_pct = float(os.getenv("PROTECTIVE_STOP_PCT", "0.005"))
src/scripts/run_protective_lifecycle_manager.py:14:    max_qty = float(os.getenv("PROTECTIVE_MAX_QTY", "1"))
src/scripts/run_protective_lifecycle_manager.py:15:    real_armed = os.getenv("PROTECTIVE_REAL_ARMED", "0") == "1"
src/scripts/run_protective_lifecycle_manager.py:8:    dsn = os.getenv("DATABASE_URL")
src/scripts/run_protective_stop_real_execution_adapter.py:18:    if os.getenv("PROTECTIVE_REAL_ARMED", "0") != "1":
src/scripts/run_protective_stop_real_execution_adapter.py:22:    if os.getenv("REAL_SELL_STOP_ENABLED", "0") != "1":
src/scripts/run_protective_stop_real_execution_adapter.py:26:    dry_run = os.getenv("PROTECTIVE_REAL_DRY_RUN", "1") == "1"
src/scripts/run_protective_stop_real_execution_adapter.py:28:    dsn = os.getenv("DATABASE_URL")
src/scripts/run_protective_stop_real_send_probe.py:10:    if os.getenv("PROTECTIVE_REAL_SEND_PROBE_ARMED", "0") != "1":
src/scripts/run_protective_stop_real_send_probe.py:14:    symbol = os.getenv("PROTECTIVE_SYMBOL", "SBER@MISX").strip().upper()
src/scripts/run_protective_stop_real_send_probe.py:15:    qty = float(os.getenv("PROTECTIVE_PROBE_QTY", "1"))
src/scripts/run_protective_stop_real_send_probe.py:16:    side = os.getenv("PROTECTIVE_PROBE_SIDE", "SELL").strip().upper()
src/scripts/run_protective_stop_real_send_probe.py:17:    stop_price = float(os.getenv("PROTECTIVE_PROBE_STOP_PRICE", "0"))
src/scripts/run_real_buy_execution_adapter.py:123:                if os.getenv("REAL_BUY_CLIENT_WIRING_CONFIRMED", "0") != "1":
src/scripts/run_real_buy_execution_adapter.py:129:                first_symbol = os.getenv("FIRST_REAL_ORDER_SYMBOL", "SBER@MISX")
src/scripts/run_real_buy_execution_adapter.py:141:                    if float(planned_price or 0) > float(os.getenv("FIRST_REAL_ORDER_MAX_VALUE", "3000")):
src/scripts/run_real_buy_execution_adapter.py:147:                    if os.getenv("REAL_BUY_MARKET_ENABLED", "0") != "1":
src/scripts/run_real_buy_execution_adapter.py:180:                    signal.alarm(int(os.getenv("REAL_MARKET_ORDER_TIMEOUT_SEC", "15")))
src/scripts/run_real_buy_execution_adapter.py:19:    dsn = os.getenv("DATABASE_URL")
src/scripts/run_real_buy_execution_adapter.py:23:    real_enabled = os.getenv("REAL_BUY_EXECUTION_ENABLED", "0") == "1"
src/scripts/run_real_buy_execution_adapter.py:24:    kill_switch = os.getenv("REAL_BUY_KILL_SWITCH", "1") == "1"
src/scripts/run_real_buy_execution_adapter.py:26:    max_qty = float(os.getenv("REAL_BUY_MAX_QTY", "100"))
src/scripts/run_real_buy_execution_adapter.py:27:    max_position_value = float(os.getenv("REAL_BUY_MAX_POSITION_VALUE", "30000"))
src/scripts/run_real_order_state_synchronizer.py:18:    dsn = os.getenv("DATABASE_URL")
src/scripts/run_real_order_state_synchronizer.py:23:    broker_sync_enabled = os.getenv("REAL_ORDER_STATE_SYNC_ENABLED", "0") == "1"
src/scripts/run_real_order_state_synchronizer.py:64:                if os.getenv("REAL_ORDER_STATUS_CLIENT_WIRING_CONFIRMED", "0") != "1":
src/scripts/run_real_order_state_synchronizer.py:78:                signal.alarm(int(os.getenv("REAL_ORDER_STATUS_TIMEOUT_SEC", "10")))
src/scripts/run_real_portfolio_position_sync.py:22:    dsn = os.getenv("DATABASE_URL")
src/scripts/run_real_portfolio_position_sync.py:26:    account_id = os.getenv("FINAM_ACCOUNT_ID", "").strip()
src/scripts/run_real_portfolio_position_sync.py:30:    symbol_filter = os.getenv("REAL_POSITION_SYNC_SYMBOL", "").strip().upper()
src/scripts/run_real_portfolio_position_sync.py:31:    endpoint = os.getenv("FINAM_GRPC_ENDPOINT", "api.finam.ru:443").strip()
src/scripts/run_real_portfolio_position_sync.py:32:    timeout = float(os.getenv("BROKER_POSITION_SYNC_TIMEOUT_SEC", "10"))
src/scripts/run_real_portfolio_price_sync.py:45:    dsn = os.getenv("DATABASE_URL")
src/scripts/run_real_portfolio_price_sync.py:49:    symbol = os.getenv("REAL_PRICE_SYNC_SYMBOL", "SBER@MISX").strip().upper()
src/scripts/run_real_sell_execution_adapter.py:126:                if str(os.getenv("REAL_SELL_ORDER_TYPE", "limit")).lower() == "market":
src/scripts/run_real_sell_execution_adapter.py:127:                    if os.getenv("REAL_SELL_MARKET_ENABLED", "0") != "1":
src/scripts/run_real_sell_execution_adapter.py:17:    dsn = os.getenv("DATABASE_URL")
src/scripts/run_real_sell_execution_adapter.py:21:    real_enabled = os.getenv("REAL_SELL_EXECUTION_ENABLED", "0") == "1"
src/scripts/run_real_sell_execution_adapter.py:22:    kill_switch = os.getenv("REAL_SELL_KILL_SWITCH", "1") == "1"
src/scripts/run_real_sell_execution_adapter.py:23:    wiring_confirmed = os.getenv("REAL_SELL_CLIENT_WIRING_CONFIRMED", "0") == "1"
src/scripts/run_real_sell_execution_adapter.py:25:    max_qty = float(os.getenv("REAL_SELL_MAX_QTY", "1"))
src/scripts/run_regime_layer_v2.py:58:    dsn = os.getenv("DATABASE_URL")
src/scripts/run_regime_layer_v2.py:62:    symbol = os.getenv("REGIME_SYMBOL", "SBER@MISX").strip().upper()
src/scripts/run_regime_layer_v2.py:63:    limit = int(os.getenv("REGIME_PRICE_LIMIT", "120"))
src/scripts/run_risk_per_trade_sizing.py:11:    dsn = os.getenv("DATABASE_URL")
src/scripts/run_runtime_capital_allocator.py:10:    dsn = os.getenv("DATABASE_URL")
src/scripts/run_runtime_execution_engine.py:21:        max_symbols=int(os.getenv("RUNTIME_MAX_SYMBOLS", "5")),
src/scripts/run_runtime_execution_engine.py:22:        min_score=float(os.getenv("RUNTIME_MIN_SCORE", "0.35")),
src/scripts/run_runtime_execution_engine.py:30:        supervisor_interval_sec=float(os.getenv("RUNTIME_SUPERVISOR_INTERVAL_SEC", "5")),
src/scripts/run_runtime_execution_engine.py:31:        rebalance_interval_sec=float(os.getenv("RUNTIME_REBALANCE_INTERVAL_SEC", "60")),
src/scripts/run_runtime_execution_engine_v3.py:22:        max_symbols=int(os.getenv("RUNTIME_MAX_SYMBOLS", "5")),
src/scripts/run_runtime_execution_engine_v3.py:23:        min_score=float(os.getenv("RUNTIME_MIN_SCORE", "0.35")),
src/scripts/run_runtime_execution_engine_v3.py:28:    worker_run_secs = int(os.getenv("RUNTIME_WORKER_RUN_SECS", "60"))
src/scripts/run_runtime_execution_engine_v3.py:33:        supervisor_interval_sec=float(os.getenv("RUNTIME_SUPERVISOR_INTERVAL_SEC", "5")),
src/scripts/run_runtime_execution_engine_v3.py:34:        rebalance_interval_sec=float(os.getenv("RUNTIME_REBALANCE_INTERVAL_SEC", "60")),
src/scripts/run_runtime_recovery_coordinator_v2.py:8:    dsn = os.getenv("DATABASE_URL")
src/scripts/run_runtime_universe_allocator.py:10:    max_symbols = int(os.getenv("RUNTIME_ACTIVE_UNIVERSE_LIMIT", "5"))
src/scripts/run_runtime_universe_allocator.py:11:    min_score = float(os.getenv("RUNTIME_ACTIVE_UNIVERSE_MIN_SCORE", "0.35"))
src/scripts/run_sending_intent_recovery.py:12:    threshold_sec = int(os.getenv("SENDING_INTENT_RECOVERY_THRESHOLD_SEC", "30"))
src/scripts/run_sending_intent_recovery.py:8:    dsn = os.getenv("DATABASE_URL")
src/scripts/run_strategy_performance_monitor.py:34:        dbname=os.getenv("PGDATABASE", "finam_core"),
src/scripts/run_strategy_performance_monitor.py:35:        user=os.getenv("PGUSER") or None,
src/scripts/run_strategy_performance_monitor.py:36:        host=os.getenv("PGHOST") or None,
src/scripts/run_strategy_performance_monitor.py:37:        port=os.getenv("PGPORT") or None,
src/scripts/run_strategy_performance_monitor.py:38:        password=os.getenv("PGPASSWORD") or None,
src/scripts/run_strategy_performance_monitor.py.bak_adaptive_controller_20260514_053505:33:        dbname=os.getenv("PGDATABASE", "finam_core"),
src/scripts/run_strategy_performance_monitor.py.bak_adaptive_controller_20260514_053505:34:        user=os.getenv("PGUSER") or None,
src/scripts/run_strategy_performance_monitor.py.bak_adaptive_controller_20260514_053505:35:        host=os.getenv("PGHOST") or None,
src/scripts/run_strategy_performance_monitor.py.bak_adaptive_controller_20260514_053505:36:        port=os.getenv("PGPORT") or None,
src/scripts/run_strategy_performance_monitor.py.bak_adaptive_controller_20260514_053505:37:        password=os.getenv("PGPASSWORD") or None,
src/scripts/run_strategy_performance_monitor.py.bak_strategy_level_20260514_060056:34:        dbname=os.getenv("PGDATABASE", "finam_core"),
src/scripts/run_strategy_performance_monitor.py.bak_strategy_level_20260514_060056:35:        user=os.getenv("PGUSER") or None,
src/scripts/run_strategy_performance_monitor.py.bak_strategy_level_20260514_060056:36:        host=os.getenv("PGHOST") or None,
src/scripts/run_strategy_performance_monitor.py.bak_strategy_level_20260514_060056:37:        port=os.getenv("PGPORT") or None,
src/scripts/run_strategy_performance_monitor.py.bak_strategy_level_20260514_060056:38:        password=os.getenv("PGPASSWORD") or None,
src/scripts/run_synthetic_protective_real_sell_adapter.py:21:    if os.getenv("SYNTHETIC_PROTECTIVE_SELL_ENABLED", "0") != "1":
src/scripts/run_synthetic_protective_real_sell_adapter.py:25:    dry_run = os.getenv("SYNTHETIC_PROTECTIVE_SELL_DRY_RUN", "1") == "1"
src/scripts/run_synthetic_protective_real_sell_adapter.py:26:    order_type = os.getenv("SYNTHETIC_PROTECTIVE_SELL_ORDER_TYPE", "market").strip().lower()
src/scripts/run_synthetic_protective_real_sell_adapter.py:32:    dsn = os.getenv("DATABASE_URL")
src/scripts/run_synthetic_protective_trigger.py:12:    symbol = os.getenv("PROTECTIVE_SYMBOL", "SBER@MISX").strip().upper()
src/scripts/run_synthetic_protective_trigger.py:13:    stop_pct = float(os.getenv("PROTECTIVE_STOP_PCT", "0.005"))
src/scripts/run_synthetic_protective_trigger.py:14:    max_qty = float(os.getenv("PROTECTIVE_MAX_QTY", "1"))
src/scripts/run_synthetic_protective_trigger.py:15:    armed = os.getenv("SYNTHETIC_PROTECTIVE_ARMED", "0") == "1"
src/scripts/run_synthetic_protective_trigger.py:16:    live_dry_run = os.getenv("SYNTHETIC_PROTECTIVE_DRY_RUN", "1") == "1"
src/scripts/run_synthetic_protective_trigger.py:17:    force_trigger = os.getenv("SYNTHETIC_PROTECTIVE_FORCE_TRIGGER", "0") == "1"
src/scripts/run_synthetic_protective_trigger.py:8:    dsn = os.getenv("DATABASE_URL")
src/scripts/runtime_anomaly_correlation.py:17:    dsn = os.getenv("DATABASE_URL")
src/scripts/runtime_anomaly_correlation.py:22:        os.getenv("ANOMALY_CORRELATION_SIGNAL_THRESHOLD", "2")
src/scripts/runtime_anomaly_correlation.py:26:        os.getenv("ANOMALY_CORRELATION_WATCHLIST_THRESHOLD", "3")
src/scripts/runtime/apply_active_contract_lifecycle_filter.py:15:        return os.getenv("ACTIVE_NG_SYMBOL", "NGM6@RTSX")
src/scripts/runtime/apply_active_contract_lifecycle_filter.py:17:        return os.getenv("ACTIVE_BR_SYMBOL", "BRM6@RTSX")
src/scripts/runtime/apply_active_contract_lifecycle_filter.py:19:        return os.getenv("ACTIVE_USDRUB_SYMBOL", "USDRUBF@RTSX")
src/scripts/runtime/apply_active_contract_lifecycle_filter.py:33:    default_timeframe = os.getenv("ACTIVE_CONTRACT_TIMEFRAME", "M5")
src/scripts/runtime_drift_detection.py:18:    dsn = os.getenv("DATABASE_URL")
src/scripts/runtime_drift_detection.py:23:        os.getenv("RUNTIME_DRIFT_WATCHLIST_DROP_PCT", "70")
src/scripts/runtime_drift_detection.py:27:        os.getenv("RUNTIME_DRIFT_SIGNAL_DROP_PCT", "80")
src/scripts/runtime_drift_detection.py:31:        os.getenv("RUNTIME_DRIFT_STALE_SNAPSHOT_MINUTES", "20")
src/scripts/runtime_health_supervisor_v2.py:16:    dsn = os.getenv("DATABASE_URL")
src/scripts/runtime_health_supervisor_v2.py:20:    send_ok = os.getenv("RUNTIME_HEALTH_V2_SEND_OK", "0") == "1"
src/scripts/runtime_operational_dashboard.py:18:    dsn = os.getenv("DATABASE_URL")
src/scripts/runtime_operational_dashboard.py:22:    send_always = os.getenv(
src/scripts/runtime_rebalance_loop.py:14:    python_bin = os.getenv("PYTHON_BIN") or sys.executable
src/scripts/runtime_reliability_guard.py:16:    dsn = os.getenv("DATABASE_URL")
src/scripts/runtime_reliability_guard.py:20:    send_ok = os.getenv("RELIABILITY_GUARD_SEND_OK", "0") == "1"
src/scripts/runtime_risk_freeze_admin.py:25:    dsn = os.getenv("DATABASE_URL")
src/scripts/runtime_supervisor.py:72:    max_log_age_min = float(os.getenv("RUNTIME_SUPERVISOR_MAX_LOG_AGE_MIN", "30"))
src/scripts/runtime_supervisor.py:73:    send_ok = os.getenv("RUNTIME_SUPERVISOR_SEND_OK", "0") == "1"
src/scripts/runtime_supervisor.py:74:    auto_recovery = os.getenv("RUNTIME_SUPERVISOR_AUTO_RECOVERY", "0") == "1"
src/scripts/run_trailing_exit_dry_run_audit.py:12:    symbol = os.getenv("TRAILING_EXIT_SYMBOL", "SBER@MISX")
src/scripts/run_trailing_exit_dry_run_audit.py:13:    trail_pct = float(os.getenv("TRAILING_EXIT_PCT", "0.01"))
src/scripts/run_trailing_exit_dry_run_audit.py:8:    dsn = os.getenv("DATABASE_URL")
src/scripts/run_trailing_exit_runtime_loop.py:10:    interval_sec = int(os.getenv("TRAILING_EXIT_LOOP_INTERVAL_SEC", "15"))
src/scripts/run_trailing_exit_runtime_loop.py:11:    max_ticks = int(os.getenv("TRAILING_EXIT_LOOP_MAX_TICKS", "1"))
src/scripts/run_trailing_exit_state_supervisor.py:12:    enabled = os.getenv("TRAILING_EXIT_ENABLED", "0") == "1"
src/scripts/run_trailing_exit_state_supervisor.py:13:    symbol = os.getenv("TRAILING_EXIT_SYMBOL", "SBER@MISX")
src/scripts/run_trailing_exit_state_supervisor.py:14:    trail_pct = float(os.getenv("TRAILING_EXIT_PCT", "0.01"))
src/scripts/run_trailing_exit_state_supervisor.py:15:    max_qty = float(os.getenv("TRAILING_EXIT_MAX_QTY", "1"))
src/scripts/run_trailing_exit_state_supervisor.py:16:    max_position_age_sec = int(os.getenv("TRAILING_EXIT_MAX_POSITION_AGE_SEC", "300"))
src/scripts/run_trailing_exit_state_supervisor.py:17:    live_dry_run = os.getenv("TRAILING_EXIT_LIVE_DRY_RUN", "1") == "1"
src/scripts/run_trailing_exit_state_supervisor.py:18:    real_armed = os.getenv("TRAILING_EXIT_REAL_ARMED", "0") == "1"
src/scripts/run_trailing_exit_state_supervisor.py:19:    shadow_sell_enabled = os.getenv("TRAILING_EXIT_SHADOW_SELL_ENABLED", "0") == "1"
src/scripts/run_trailing_exit_state_supervisor.py:20:    force_trigger = os.getenv("TRAILING_EXIT_FORCE_TRIGGER", "0") == "1"
src/scripts/run_trailing_exit_state_supervisor.py:8:    dsn = os.getenv("DATABASE_URL")
src/scripts/run_trailing_exit_supervisor.py:10:    dsn = os.getenv("DATABASE_URL")
src/scripts/run_trailing_exit_supervisor.py:14:    enabled = os.getenv("TRAILING_EXIT_ENABLED", "0") == "1"
src/scripts/run_trailing_exit_supervisor.py:15:    symbol_filter = os.getenv("TRAILING_EXIT_SYMBOL", "SBER@MISX")
src/scripts/run_trailing_exit_supervisor.py:16:    trail_pct = float(os.getenv("TRAILING_EXIT_PCT", "0.01"))
src/scripts/run_volatility_scan.py:117:    parser.add_argument("--table", default=os.getenv("BARS_TABLE", "market_data"))
src/scripts/run_volatility_scan.py:120:    database_url = os.getenv("DATABASE_URL")
src/scripts/save_runtime_state_snapshot.py:17:    dsn = os.getenv("DATABASE_URL")
src/scripts/seed_runtime_control_from_strategy_map.py:11:    database_url = os.getenv("DATABASE_URL")
src/scripts/seed_strategy_runtime_control.py:23:    database_url = os.getenv("DATABASE_URL")
src/scripts/send_capital_growth_digest.py:14:    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
src/scripts/send_capital_growth_digest.py:15:    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
src/scripts/send_capital_growth_digest.py:42:    dsn = os.getenv("DATABASE_URL")
src/scripts/send_capital_growth_digest.py:46:    profile = os.getenv("CAPITAL_GROWTH_PROFILE", "growth")
src/scripts/send_capital_growth_digest.py:93:    if os.getenv("SEND_CAPITAL_GROWTH_DIGEST", "0") == "1":
src/scripts/send_evening_strategy_report.py:13:        dbname=os.getenv("PGDATABASE", "finam_core"),
src/scripts/send_evening_strategy_report.py:14:        user=os.getenv("PGUSER") or None,
src/scripts/send_evening_strategy_report.py:15:        host=os.getenv("PGHOST") or None,
src/scripts/send_evening_strategy_report.py:16:        port=os.getenv("PGPORT") or None,
src/scripts/send_evening_strategy_report.py:17:        password=os.getenv("PGPASSWORD") or None,
src/scripts/send_execution_freeze_alert.py:16:FREEZE_MINUTES = int(os.getenv("EXECUTION_FREEZE_MINUTES", "120"))
src/scripts/send_execution_freeze_alert.py:17:DEDUP_MINUTES = int(os.getenv("EXECUTION_FREEZE_DEDUP_MINUTES", "180"))
src/scripts/send_execution_freeze_alert.py:35:        dbname=os.getenv("PGDATABASE", "finam_core"),
src/scripts/send_execution_freeze_alert.py:36:        user=os.getenv("PGUSER") or None,
src/scripts/send_execution_freeze_alert.py:37:        host=os.getenv("PGHOST") or None,
src/scripts/send_execution_freeze_alert.py:38:        port=os.getenv("PGPORT") or None,
src/scripts/send_execution_freeze_alert.py:39:        password=os.getenv("PGPASSWORD") or None,
src/scripts/send_grafana_alerts_telegram.py:117:    if not (os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("TG_BOT_TOKEN") or os.getenv("TG_ALERT_BOT_TOKEN")) or not (os.getenv("TELEGRAM_CHAT_ID") or os.getenv("TG_CHAT_ID") or os.getenv("TG_ALERT_CHAT")):
src/scripts/send_grafana_alerts_telegram.py:128:            cooldown_min = int(os.getenv("TELEGRAM_ALERT_COOLDOWN_MIN", "30"))
src/scripts/send_grafana_alerts_telegram.py:130:            cooldown_min = int(os.getenv("TELEGRAM_ALERT_COOLDOWN_MIN", "30"))
src/scripts/send_grafana_alerts_telegram.py:30:    token = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("TG_BOT_TOKEN") or os.getenv("TG_ALERT_BOT_TOKEN")
src/scripts/send_grafana_alerts_telegram.py:31:    chat_id = os.getenv("TELEGRAM_CHAT_ID") or os.getenv("TG_CHAT_ID") or os.getenv("TG_ALERT_CHAT")
src/scripts/send_grafana_alerts_telegram.py:40:        "--connect-timeout", os.getenv("TG_CURL_CONNECT_TIMEOUT", "10"),
src/scripts/send_grafana_alerts_telegram.py:41:        "--max-time", os.getenv("TG_CURL_MAX_TIME", "30"),
src/scripts/send_grafana_alerts_telegram.py:44:    proxy = os.getenv("TG_PROXY") or os.getenv("TELEGRAM_PROXY")
src/scripts/send_market_event_calendar_alerts_telegram.py:35:        os.getenv("TG_ALERT_BOT_TOKEN")
src/scripts/send_market_event_calendar_alerts_telegram.py:36:        or os.getenv("TELEGRAM_BOT_TOKEN")
src/scripts/send_market_event_calendar_alerts_telegram.py:37:        or os.getenv("TG_BOT_TOKEN")
src/scripts/send_market_event_calendar_alerts_telegram.py:40:        os.getenv("TG_ALERT_CHAT")
src/scripts/send_market_event_calendar_alerts_telegram.py:41:        or os.getenv("TELEGRAM_CHAT_ID")
src/scripts/send_market_event_calendar_alerts_telegram.py:42:        or os.getenv("TG_CHAT_ID")
src/scripts/send_market_event_calendar_alerts_telegram.py:52:        "--connect-timeout", os.getenv("TG_CURL_CONNECT_TIMEOUT", "10"),
src/scripts/send_market_event_calendar_alerts_telegram.py:53:        "--max-time", os.getenv("TG_CURL_MAX_TIME", "30"),
src/scripts/send_market_event_calendar_alerts_telegram.py:56:    proxy = os.getenv("TG_PROXY") or os.getenv("TELEGRAM_PROXY")
src/scripts/send_one_limit.py:10:    price = float(os.getenv("PRICE", "130.00"))
src/scripts/send_one_limit.py:8:    symbol = os.getenv("SYM", "SVETP@MISX")
src/scripts/send_one_limit.py:9:    qty = float(os.getenv("QTY", "10"))
src/scripts/send_runtime_control_alerts.py:13:DEDUP_MINUTES = int(os.getenv("RUNTIME_ALERT_DEDUP_MINUTES", "180"))
src/scripts/send_runtime_control_alerts.py:18:        dbname=os.getenv("PGDATABASE", "finam_core"),
src/scripts/send_runtime_control_alerts.py:19:        user=os.getenv("PGUSER") or None,
src/scripts/send_runtime_control_alerts.py:20:        host=os.getenv("PGHOST") or None,
src/scripts/send_runtime_control_alerts.py:21:        port=os.getenv("PGPORT") or None,
src/scripts/send_runtime_control_alerts.py:22:        password=os.getenv("PGPASSWORD") or None,
src/scripts/show_account_pretty.py:120:    account_id = os.getenv("FINAM_ACCOUNT_ID") or os.getenv("ACCOUNT_ID")
src/scripts/show_account_pretty.py:124:    host = os.getenv("FINAM_HOST") or os.getenv("FINAM_GRPC_HOST") or "api.finam.ru:443"
src/scripts/show_account_pretty.py:128:        jwt = os.getenv("FINAM_JWT", "") or tm.get_token()
src/scripts/show_account.py:18:    account_id = os.getenv("FINAM_ACCOUNT_ID") or os.getenv("ACCOUNT_ID")
src/scripts/show_account.py:22:    host = os.getenv("FINAM_GRPC_HOST", "api.finam.ru:443")
src/scripts/show_trade_journal.py:12:    database_url = os.getenv("DATABASE_URL", "").strip()
src/scripts/show_trade_journal.py:16:    limit = int(os.getenv("TRADE_JOURNAL_LIMIT", "200"))
src/scripts/smoke_accounts.py:9:FINAM_TOKEN = os.getenv("FINAM_TOKEN")
src/scripts/smoke_auth.py:10:    api_secret = os.getenv("FINAM_API_SECRET")
src/scripts/smoke_finam_grpc.py:10:    token = os.getenv("FINAM_TOKEN")
src/scripts/smoke_finam_grpc.py:7:HOST = os.getenv("FINAM_GRPC_HOST", "api.finam.ru:443")
src/scripts/smoke_finam_rest.py:27:        account_id = os.getenv("FINAM_ACCOUNT_ID", "").strip()
src/scripts/smoke_quotes_stream.py:4:SYMBOLS = [x.strip() for x in (os.getenv('SYMBOLS') or '').split(',') if x.strip()] or [os.getenv('SYMBOL') or 'NGH6@RTSX']
src/scripts/strategy_decision_report.py:10:    database_url = os.getenv("DATABASE_URL")
src/scripts/strategy_optimization_report.py:10:    database_url = os.getenv("DATABASE_URL")
src/scripts/strategy_performance_report.py:10:    database_url = os.getenv("DATABASE_URL")
src/scripts/test_auth_debug.py:10:    api_secret = os.getenv("FINAM_API_SECRET")
src/scripts/test_ingest_bars.py:25:SYMBOL = os.getenv("SYMBOL") or "NGH6@RTSX"
src/scripts/test_marketdata_client.py:4:SYMBOLS = [x.strip() for x in (os.getenv('SYMBOLS') or '').split(',') if x.strip()] or [os.getenv('SYMBOL') or 'NGH6@RTSX']
src/scripts/test_order_limit.py:10:    symbol = os.getenv("SYMBOL") or "NGH6@RTSX"
src/scripts/test_order_limit.py:14:    dry = os.getenv("DRY_RUN", "1") != "0"
src/scripts/update_dynamic_watchlist_from_opportunities.py:10:LIMIT = int(os.getenv("OPPORTUNITY_WATCHLIST_LIMIT", "5"))
src/scripts/update_dynamic_watchlist_from_opportunities.py:11:MIN_FRESHNESS_ADJUSTED_SCORE = float(os.getenv("MIN_FRESHNESS_ADJUSTED_SCORE", "0.35"))
src/scripts/update_dynamic_watchlist_from_opportunities.py:12:FRESHNESS_EXPIRED_SCORE = float(os.getenv("FRESHNESS_EXPIRED_SCORE", "0.25"))
src/scripts/update_dynamic_watchlist_from_opportunities.py:13:SCORE_DROP_THRESHOLD = float(os.getenv("ROTATION_SCORE_DROP_THRESHOLD", "0.20"))
src/scripts/update_market_event_calendar.py:33:    path = Path(os.getenv("MARKET_EVENT_CALENDAR_TSV", "data/market_event_calendar.tsv"))
src/scripts/update_market_opportunity_metrics_from_moex_top.py:7:TOP_N = int(os.getenv("MOEX_TOP_TO_OPPORTUNITY_LIMIT", "30"))
src/scripts/update_market_opportunity_metrics.py:12:    database_url = os.getenv("DATABASE_URL")
src/scripts/update_market_opportunity_metrics.py:7:BUCKET = os.getenv("OPPORTUNITY_SCAN_BUCKET", "intraday")
src/scripts/update_market_opportunity_metrics.py:8:TIMEFRAME = os.getenv("OPPORTUNITY_SCAN_TIMEFRAME", "M5")
src/scripts/update_moex_liquid_universe.py:32:    path = Path(os.getenv("MOEX_LIQUID_UNIVERSE_TSV", "data/moex_liquid_universe.tsv"))
src/scripts/update_moex_top_universe_from_volatility_scan.py:7:BUCKET = os.getenv("OPPORTUNITY_SCAN_BUCKET", "intraday")
src/scripts/update_moex_top_universe_from_volatility_scan.py:8:TIMEFRAME = os.getenv("OPPORTUNITY_SCAN_TIMEFRAME", "M5")
src/scripts/update_moex_top_universe_from_volatility_scan.py:9:TOP_N = int(os.getenv("MOEX_TOP_UNIVERSE_LIMIT", "30"))

## Runtime governance tables usage
scripts/audit_project_gap_analysis.sh:40:  grep -R --exclude-dir='__pycache__' "runtime_regime_overrides\|runtime_strategy_scores\|runtime_active_universe\|strategy_regime_matrix" -n src scripts | sort
scripts/create_runtime_active_universe.sql:17:create index if not exists idx_runtime_active_universe_enabled_priority
scripts/create_runtime_active_universe.sql:18:on runtime_active_universe(is_enabled, priority desc, score desc);
scripts/create_runtime_active_universe.sql:1:create table if not exists runtime_active_universe (
scripts/create_runtime_active_universe.sql:20:create index if not exists idx_runtime_active_universe_strategy
scripts/create_runtime_active_universe.sql:21:on runtime_active_universe(strategy, is_enabled);
scripts/migrate_regime_runtime_overrides_v3.sh:27:CREATE INDEX IF NOT EXISTS idx_runtime_regime_overrides_symbol
scripts/migrate_regime_runtime_overrides_v3.sh:28:ON runtime_regime_overrides(root_symbol, strategy);
scripts/migrate_regime_runtime_overrides_v3.sh:30:CREATE INDEX IF NOT EXISTS idx_runtime_regime_overrides_action
scripts/migrate_regime_runtime_overrides_v3.sh:31:ON runtime_regime_overrides(runtime_action);
scripts/migrate_regime_runtime_overrides_v3.sh:5:CREATE TABLE IF NOT EXISTS runtime_regime_overrides (
scripts/migrate_runtime_regime_overrides_default_policy.sh:5:ALTER TABLE runtime_regime_overrides
scripts/migrate_runtime_regime_overrides_default_policy.sh:8:UPDATE runtime_regime_overrides
scripts/migrate_runtime_strategy_scores_v1.sh:22:CREATE INDEX IF NOT EXISTS idx_runtime_strategy_scores_key
scripts/migrate_runtime_strategy_scores_v1.sh:23:ON runtime_strategy_scores(strategy, root_symbol, regime, created_at DESC);
scripts/migrate_runtime_strategy_scores_v1.sh:25:CREATE INDEX IF NOT EXISTS idx_runtime_strategy_scores_created_at
scripts/migrate_runtime_strategy_scores_v1.sh:26:ON runtime_strategy_scores(created_at DESC);
scripts/migrate_runtime_strategy_scores_v1.sh:28:CREATE OR REPLACE VIEW runtime_strategy_scores_latest AS
scripts/migrate_runtime_strategy_scores_v1.sh:43:FROM runtime_strategy_scores
scripts/migrate_runtime_strategy_scores_v1.sh:5:CREATE TABLE IF NOT EXISTS runtime_strategy_scores (
scripts/migrate_strategy_regime_matrix_v1.sh:44:CREATE INDEX IF NOT EXISTS idx_strategy_regime_matrix_runtime_action
scripts/migrate_strategy_regime_matrix_v1.sh:45:ON strategy_regime_matrix(runtime_action);
scripts/migrate_strategy_regime_matrix_v1.sh:47:CREATE INDEX IF NOT EXISTS idx_strategy_regime_matrix_lookup
scripts/migrate_strategy_regime_matrix_v1.sh:48:ON strategy_regime_matrix(strategy, timeframe, regime, trend, volatility);
scripts/migrate_strategy_regime_matrix_v1.sh:50:CREATE INDEX IF NOT EXISTS idx_strategy_regime_matrix_symbol
scripts/migrate_strategy_regime_matrix_v1.sh:51:ON strategy_regime_matrix(symbol, strategy, timeframe);
scripts/migrate_strategy_regime_matrix_v1.sh:5:CREATE TABLE IF NOT EXISTS strategy_regime_matrix (
scripts/test_continuous_runtime_governance.sh:10:grep -q "sync_runtime_active_universe_from_ng_live_state.py" src/scripts/run_continuous_runtime_governance.py
scripts/test_intermarket_selection_modifier_v1.sh:50:grep -q "runtime_strategy_scores_latest" src/scripts/runtime/apply_intermarket_selection_modifier.py
scripts/test_pipeline_runtime_active_universe_gate.sh:15:    "_runtime_active_universe_allows_paper",
scripts/test_pipeline_runtime_active_universe_gate.sh:16:    "runtime_active_universe",
scripts/test_pipeline_runtime_active_universe_gate.sh:18:    "gate=runtime_active_universe",
scripts/test_regime_matrix_runtime_modifier_v2.sh:40:grep -q "strategy_regime_matrix" src/scripts/runtime/apply_regime_matrix_runtime_modifier.py
scripts/test_regime_runtime_overrides_v3.sh:41:grep -q "runtime_regime_overrides" scripts/migrate_regime_runtime_overrides_v3.sh
scripts/test_research_pipeline_intermarket_runtime_wiring.sh:9:grep -q "sync_runtime_strategy_scores_from_selection.py" src/scripts/research_pipeline_orchestrator.py
scripts/test_research_pipeline_orchestrator.sh:11:grep -q "sync_runtime_active_universe_from_strategy_selection.py" src/scripts/research_pipeline_orchestrator.py
scripts/test_research_pipeline_regime_matrix_wiring.sh:11:grep -q "build_strategy_regime_matrix.py" src/scripts/research_pipeline_orchestrator.py
scripts/test_research_pipeline_regime_matrix_wiring.sh:20:matrix_pos = text.find("build_strategy_regime_matrix.py")
scripts/test_research_pipeline_regime_matrix_wiring.sh:8:  src/scripts/analytics/build_strategy_regime_matrix.py
scripts/test_runtime_active_universe_table.sh:10:where table_name = 'runtime_active_universe'
scripts/test_runtime_active_universe_table.sh:14:echo "OK: runtime_active_universe table"
scripts/test_runtime_active_universe_table.sh:5:  -f scripts/create_runtime_active_universe.sql >/dev/null
scripts/test_runtime_execution_engine.sh:14:    "runtime_active_universe",
scripts/test_runtime_override_gate.sh:76:grep -q "runtime_regime_overrides" src/finam_core/runtime/regime_runtime_override_repository.py
scripts/test_runtime_regime_overrides_default_policy.sh:10:grep -q "is_default_policy" scripts/migrate_runtime_regime_overrides_default_policy.sh
scripts/test_runtime_strategy_scores_sync.sh:10:grep -q "RUNTIME_STRATEGY_SCORES_SYNC_OK" src/scripts/runtime/sync_runtime_strategy_scores_from_selection.py
scripts/test_runtime_strategy_scores_sync.sh:6:python -m py_compile src/scripts/runtime/sync_runtime_strategy_scores_from_selection.py
scripts/test_runtime_strategy_scores_sync.sh:8:grep -q "runtime_strategy_selection" src/scripts/runtime/sync_runtime_strategy_scores_from_selection.py
scripts/test_runtime_strategy_scores_sync.sh:9:grep -q "runtime_strategy_scores" src/scripts/runtime/sync_runtime_strategy_scores_from_selection.py
scripts/test_runtime_universe_allocator.sh:21:    "runtime_active_universe",
scripts/test_runtime_universe_allocator.sh:37:from runtime_active_universe
scripts/test_runtime_universe_allocator.sh:7:  -f scripts/create_runtime_active_universe.sql >/dev/null
scripts/test_runtime_universe_allocator_v2_regression.sh:45:        if "insert into runtime_active_universe" in sql:
scripts/test_runtime_universe_allocator_v2_regression.sh:95:    if "insert into runtime_active_universe" in item[0]
scripts/test_runtime_universe_provider_active_universe.sh:13:assert "runtime_active_universe" in text
scripts/test_runtime_universe_provider_active_universe.sh:18:print("OK: RuntimeUniverseProvider uses runtime_active_universe with fallback")
scripts/test_strategy_regime_matrix_v1.sh:42:grep -q "strategy_regime_matrix" scripts/migrate_strategy_regime_matrix_v1.sh
scripts/test_strategy_regime_matrix_v1.sh:43:grep -q "STRATEGY_REGIME_MATRIX_V1_OK" src/scripts/analytics/build_strategy_regime_matrix.py
scripts/test_strategy_regime_matrix_v1.sh:6:python -m py_compile src/scripts/analytics/build_strategy_regime_matrix.py
scripts/test_strategy_regime_matrix_v1.sh:9:from scripts.analytics.build_strategy_regime_matrix import classify_matrix_action
scripts/test_sync_runtime_active_universe_from_active_edge.sh:10:grep -q "SYNC_RUNTIME_ACTIVE_UNIVERSE_FROM_ACTIVE_EDGE_OK" src/scripts/sync_runtime_active_universe_from_active_edge.py
scripts/test_sync_runtime_active_universe_from_active_edge.sh:6:python -m py_compile src/scripts/sync_runtime_active_universe_from_active_edge.py
scripts/test_sync_runtime_active_universe_from_active_edge.sh:8:grep -q "ng_active_edge_state" src/scripts/sync_runtime_active_universe_from_active_edge.py
scripts/test_sync_runtime_active_universe_from_active_edge.sh:9:grep -q "active_edge_block" src/scripts/sync_runtime_active_universe_from_active_edge.py
scripts/test_sync_runtime_active_universe_from_governance.sh:10:grep -q "SYNC_RUNTIME_ACTIVE_UNIVERSE_FROM_GOVERNANCE_OK" src/scripts/sync_runtime_active_universe_from_governance.py
scripts/test_sync_runtime_active_universe_from_governance.sh:6:python -m py_compile src/scripts/sync_runtime_active_universe_from_governance.py
scripts/test_sync_runtime_active_universe_from_governance.sh:8:grep -q "runtime_governance_decisions" src/scripts/sync_runtime_active_universe_from_governance.py
scripts/test_sync_runtime_active_universe_from_governance.sh:9:grep -q "runtime_active_universe" src/scripts/sync_runtime_active_universe_from_governance.py
scripts/test_sync_runtime_active_universe_from_ng_live_state.sh:10:grep -q "SYNC_RUNTIME_ACTIVE_UNIVERSE_FROM_NG_LIVE_STATE_OK" src/scripts/sync_runtime_active_universe_from_ng_live_state.py
scripts/test_sync_runtime_active_universe_from_ng_live_state.sh:6:python -m py_compile src/scripts/sync_runtime_active_universe_from_ng_live_state.py
scripts/test_sync_runtime_active_universe_from_ng_live_state.sh:8:grep -q "ng_live_runtime_state" src/scripts/sync_runtime_active_universe_from_ng_live_state.py
scripts/test_sync_runtime_active_universe_from_ng_live_state.sh:9:grep -q "runtime_state = 'ACTIVE'" src/scripts/sync_runtime_active_universe_from_ng_live_state.py
scripts/test_sync_runtime_active_universe_from_strategy_selection.sh:10:grep -q "runtime_strategy_selection" src/scripts/sync_runtime_active_universe_from_strategy_selection.py
scripts/test_sync_runtime_active_universe_from_strategy_selection.sh:11:grep -q "runtime_active_universe" src/scripts/sync_runtime_active_universe_from_strategy_selection.py
scripts/test_sync_runtime_active_universe_from_strategy_selection.sh:7:  src/scripts/sync_runtime_active_universe_from_strategy_selection.py \
src/finam_core/analytics/symbol_strategy_resolver.py:14:    1. runtime_active_universe
src/finam_core/analytics/symbol_strategy_resolver.py:25:        for table in ("runtime_active_universe", "dynamic_watchlist"):
src/finam_core/contracts/instrument_display_name_resolver.py:14:            or self._from_runtime_active_universe(value)
src/finam_core/contracts/instrument_display_name_resolver.py:39:    def _from_runtime_active_universe(self, symbol: str) -> str | None:
src/finam_core/contracts/instrument_display_name_resolver.py:42:        FROM runtime_active_universe
src/finam_core/data/runtime_universe_provider.py:22:        from runtime_active_universe
src/finam_core/data/runtime_universe_provider.py:7:    """Русский комментарий: читает активный runtime-universe из runtime_active_universe с fallback на dynamic_watchlist."""
src/finam_core/pipelines/paper_pipeline.py:5430:    def _runtime_active_universe_allows_paper(self, symbol: str, strategy: str = "default") -> tuple[bool, str]:
src/finam_core/pipelines/paper_pipeline.py:5436:                return True, "runtime_active_universe_gate_disabled"
src/finam_core/pipelines/paper_pipeline.py:5440:                return True, "runtime_active_universe_no_pg_logger"
src/finam_core/pipelines/paper_pipeline.py:5447:                        from runtime_active_universe
src/finam_core/pipelines/paper_pipeline.py:5457:                return False, f"runtime_active_universe_not_enabled:symbol={symbol}"
src/finam_core/pipelines/paper_pipeline.py:5462:                f"runtime_active_universe_ok:symbol={symbol}:strategy={active_strategy}:regime={active_regime}:score={active_score}:priority={active_priority}",
src/finam_core/pipelines/paper_pipeline.py:5471:            return True, f"runtime_active_universe_error_soft:{type(exc).__name__}:{exc}"
src/finam_core/pipelines/paper_pipeline.py:5917:        """Русский комментарий: применяет runtime_regime_overrides перед PaperExecution."""
src/finam_core/pipelines/paper_pipeline.py:6071:        active_universe_allowed, active_universe_reason = self._runtime_active_universe_allows_paper(
src/finam_core/pipelines/paper_pipeline.py:6077:                f"PIPE_ENTRY_GATE_BLOCK symbol={br_symbol} gate=runtime_active_universe reason={active_universe_reason}",
src/finam_core/risk/runtime_override_gate.py:27:    Применяет runtime_regime_overrides перед созданием заявки.
src/finam_core/runtime/regime_matrix_modifier.py:23:    Применяет точечную поправку из strategy_regime_matrix.
src/finam_core/runtime/regime_runtime_override_repository.py:47:        FROM runtime_regime_overrides
src/finam_core/runtime/runtime_active_strategy_provider.py:21:    symbol + strategy + timeframe берутся из runtime_active_universe.
src/finam_core/runtime/runtime_active_strategy_provider.py:33:        FROM runtime_active_universe
src/finam_core/runtime/runtime_execution_engine.py:173:        Если symbol остаётся в runtime_active_universe, следующий supervisor_tick
src/finam_core/runtime/runtime_universe_allocator.py:214:                cur.execute("delete from runtime_active_universe")
src/finam_core/runtime/runtime_universe_allocator.py:235:                        insert into runtime_active_universe (
src/finam_core/runtime/runtime_universe_allocator.py:48:            insert into runtime_active_universe (
src/finam_core/runtime/runtime_universe_allocator.py:73:        update runtime_active_universe rau
src/finam_core/runtime/runtime_universe_allocator.py:83:        from runtime_active_universe
src/scripts/analytics/build_strategy_regime_matrix.py:89:    INSERT INTO strategy_regime_matrix (
src/scripts/audit_strategy_universe.py:21:        "runtime_active_universe",
src/scripts/collect_runtime_observations.py:67:                FROM runtime_active_universe u
src/scripts/portfolio_governance_refresh.py:15:    FROM runtime_active_universe
src/scripts/research_pipeline_orchestrator.py:120:            py, "src/scripts/analytics/build_strategy_regime_matrix.py",
src/scripts/research_pipeline_orchestrator.py:236:                "src/scripts/sync_runtime_active_universe_from_strategy_selection.py",
src/scripts/research_pipeline_orchestrator.py:241:            step_name="sync_runtime_active_universe",
src/scripts/research_pipeline_orchestrator.py:248:        [sys.executable, "src/scripts/runtime/sync_runtime_strategy_scores_from_selection.py"],
src/scripts/run_autonomous_portfolio_brain.py:96:                from runtime_active_universe
src/scripts/run_capital_growth_regime_allocator.py:78:                from runtime_active_universe
src/scripts/run_continuous_runtime_governance.py:15:    ["src/scripts/sync_runtime_active_universe_from_ng_live_state.py"],
src/scripts/runtime/apply_context_runtime_filter.py:25:        FROM runtime_strategy_scores_latest
src/scripts/runtime/apply_context_runtime_filter.py:77:    INSERT INTO runtime_strategy_scores (
src/scripts/runtime/apply_intermarket_selection_modifier.py:13:    Применяет последний intermarket_regime_snapshot к runtime_strategy_scores.
src/scripts/runtime/apply_intermarket_selection_modifier.py:48:    FROM runtime_strategy_scores_latest;
src/scripts/runtime/apply_intermarket_selection_modifier.py:52:    INSERT INTO runtime_strategy_scores (
src/scripts/runtime/apply_regime_matrix_runtime_modifier.py:27:        FROM runtime_strategy_scores_latest
src/scripts/runtime/apply_regime_matrix_runtime_modifier.py:51:        LEFT JOIN strategy_regime_matrix srm
src/scripts/runtime/apply_regime_matrix_runtime_modifier.py:79:    INSERT INTO runtime_strategy_scores (
src/scripts/runtime/build_regime_runtime_overrides.py:21:    FROM runtime_strategy_scores_latest;
src/scripts/runtime/build_regime_runtime_overrides.py:25:    INSERT INTO runtime_regime_overrides (
src/scripts/runtime/build_runtime_capital_allocator.py:65:                LEFT JOIN runtime_active_universe u
src/scripts/runtime/sync_runtime_strategy_scores_from_selection.py:11:    INSERT INTO runtime_strategy_scores (
src/scripts/sync_runtime_active_universe_from_active_edge.py:12:                UPDATE runtime_active_universe u
src/scripts/sync_runtime_active_universe_from_active_edge.py:27:                UPDATE runtime_active_universe u
src/scripts/sync_runtime_active_universe_from_governance.py:12:                UPDATE runtime_active_universe u
src/scripts/sync_runtime_active_universe_from_governance.py:28:                UPDATE runtime_active_universe u
src/scripts/sync_runtime_active_universe_from_ng_live_state.py:12:                INSERT INTO runtime_active_universe (
src/scripts/sync_runtime_active_universe_from_strategy_selection.py:21:    ALTER TABLE runtime_active_universe
src/scripts/sync_runtime_active_universe_from_strategy_selection.py:27:    CREATE INDEX IF NOT EXISTS idx_runtime_active_universe_enabled
src/scripts/sync_runtime_active_universe_from_strategy_selection.py:28:    ON runtime_active_universe(is_enabled, priority DESC);
src/scripts/sync_runtime_active_universe_from_strategy_selection.py:30:    CREATE INDEX IF NOT EXISTS idx_runtime_active_universe_symbol
src/scripts/sync_runtime_active_universe_from_strategy_selection.py:31:    ON runtime_active_universe(symbol);
src/scripts/sync_runtime_active_universe_from_strategy_selection.py:35:    INSERT INTO runtime_active_universe (
src/scripts/sync_runtime_active_universe_from_strategy_selection.py:9:    CREATE TABLE IF NOT EXISTS runtime_active_universe (

## Tests
scripts/test_active_contract_lifecycle_filter.sh
scripts/test_active_contract_lifecycle_promotion_gate.sh
scripts/test_active_orders_reconciliation_oms_sync.sh
scripts/test_active_orders_reconciliation_optional_managed.sh
scripts/test_active_orders_reconciliation_status_mapper.sh
scripts/test_active_policy_reader.sh
scripts/test_adaptive_capital_allocator_v2.sh
scripts/test_adaptive_portfolio_allocator.sh
scripts/test_adaptive_position_features_persistable.sh
scripts/test_adaptive_position_sizer.sh
scripts/test_adaptive_position_trade_payload.sh
scripts/test_adaptive_regime_decision_analytics.sh
scripts/test_adaptive_regime_filter.sh
scripts/test_adaptive_regime_payload_persistence.sh
scripts/test_adaptive_regime_repository.sh
scripts/test_adaptive_regime_repository_symbol_scope.sh
scripts/test_adaptive_strategy_controller.sh
scripts/test_adaptive_strategy_controller_v2.sh
scripts/test_adaptive_strategy_weighting_engine.sh
scripts/test_ai_no_trading_imports.sh
scripts/test_ai_sentiment_event_repository.sh
scripts/test_analytics_data_quality_report.sh
scripts/test_analytics_inspect_trades_schema.sh
scripts/test_analytics_runtime_supervisor_compile.sh
scripts/test_analytics_trade_statistics.sh
scripts/test_analyze_adaptive_position_pnl.sh
scripts/test_analyze_regime_performance_compile.sh
scripts/test_apply_regime_runtime_control_v1.sh
scripts/test_apply_strategy_health_notification.sh
scripts/test_apply_strategy_health_to_runtime_control.sh
scripts/test_apply_strategy_health_to_runtime_control_sql.sh
scripts/test_apply_strategy_performance_monitor_v2.sh
scripts/test_asset_execution_policy.sh
scripts/test_attention_allocator.sh
scripts/test_audit_strategy_universe_compile.sh
scripts/test_auto_breakeven_manager.sh
scripts/test_backfill_closed_trade_attribution_compile.sh
scripts/test_backfill_closed_trade_attribution_sql.sh
scripts/test_backfill_finam_futures_symbols_arg.sh
scripts/test_backfill_missing_strategy_attribution_from_map.sh
scripts/test_backfill_smart_money_continuous.sh
scripts/test_backfill_strategy_attribution.sh
scripts/test_backfill_trade_contract_identity.sh
scripts/test_bar_volume_features.sh
scripts/test_best_exit_alpha_policy.sh
scripts/test_broker_capabilities_gate.sh
scripts/test_broker_error_normalization.sh
scripts/test_broker_event_idempotency.sh
scripts/test_broker_manual_trade_sync.sh
scripts/test_broker_order_reconciliation_service.sh
scripts/test_broker_order_snapshot_alert_views.sh
scripts/test_broker_order_snapshot_store.sh
scripts/test_broker_order_snapshot_views.sh
scripts/test_broker_order_sync_service.sh
scripts/test_broker_protection_gate.sh
scripts/test_broker_reconciliation_engine.sh
scripts/test_broker_reconciliation_pipeline_gate.sh
scripts/test_broker_reconciliation.sh
scripts/test_broker_status_mapper.sh
scripts/test_br_paper_fallback_trade_object.sh
scripts/test_br_regime_layer.sh
scripts/test_br_volatility_intelligence.sh
scripts/test_build_drawdown_summary_compile.sh
scripts/test_build_portfolio_intelligence_snapshot_compile.sh
scripts/test_build_replay_closed_trades_compile.sh
scripts/test_build_strategy_rank_decisions_daily_compile.sh
scripts/test_build_strategy_scorecard_daily_compile.sh
scripts/test_calculate_execution_advisory.sh
scripts/test_cancel_replace_stop_manager.sh
scripts/test_capital_growth_daily_loss_guard.sh
scripts/test_capital_growth_digest.sh
scripts/test_capital_growth_mode.sh
scripts/test_capital_growth_portfolio_governor.sh
scripts/test_capital_growth_profile.sh
scripts/test_checkpoint_aware_projection_updater.sh
scripts/test_clean_closed_trades_performance_sql.sh
scripts/test_cleanup_invalid_strategy_rows.sh
scripts/test_client_order_id_pre_persist.sh
scripts/test_client_order_id_recovery_lookup.sh
scripts/test_closed_trade_analytics_views.sh
scripts/test_closed_trade_attribution_service.sh
scripts/test_closed_trade_engine.sh
scripts/test_closed_trade_metadata_propagation.sh
scripts/test_closed_trade_reconstruction_v2_audit_gate.sh
scripts/test_closed_trade_reconstruction_v2.sh
scripts/test_closed_trade_report_compile.sh
scripts/test_closed_trade_report_excludes_backfill.sh
scripts/test_closed_trades_integration_v1.sh
scripts/test_closed_trade_strategy_stats_v1.sh
scripts/test_closed_trades_v2.sh
scripts/test_close_virtual_futures_trade.sh
scripts/test_collect_runtime_observations.sh
scripts/test_commission_aware_strategy_analytics.sh
scripts/test_compare_adaptive_risk_performance_compile.sh
scripts/test_context_runtime_filter_v1.sh
scripts/test_continuous_market_bars_ingestion.sh
scripts/test_continuous_runtime_governance.sh
scripts/test_continuous_smart_money_aggregator.sh
scripts/test_continuous_trade_analytics_views.sh
scripts/test_contract_identity_resolver.sh
scripts/test_contract_identity.sh
scripts/test_contract_resolver.sh
scripts/test_contract_specs_and_futures_pnl.sh
scripts/test_cooldown_guard.sh
scripts/test_correlation_exposure_filter.sh
scripts/test_cross_contract_liquidity_allocator.sh
scripts/test_cross_contract_liquidity_persistence.sh
scripts/test_cross_sectional_selector.sh
scripts/test_daily_risk_repository.sh
scripts/test_daily_risk_tracker.sh
scripts/test_db_signal_to_closed_trade_join.sh
scripts/test_dead_letter_auto_replay_worker.sh
scripts/test_dead_letter_replay_service.sh
scripts/test_dead_letter_service.sh
scripts/test_dispatcher_limit_order_journal_mock.sh
scripts/test_dlq_auto_replay_systemd.sh
scripts/test_dlq_healthcheck.sh
scripts/test_drawdown_summary.sh
scripts/test_duplicate_fill_protection.sh
scripts/test_dynamic_strategy_resolver.sh
scripts/test_dynamic_watchlist_repository.sh
scripts/test_dynamic_watchlist_rotation_logger_integration.sh
scripts/test_dynamic_watchlist_trade_priority_score.sh
scripts/test_engine_coordinator_execution_route_flag.sh
scripts/test_engine_coordinator_execution_route_runtime.sh
scripts/test_engine_coordinator_flags.sh
scripts/test_engine_coordinator_full_smoke.sh
scripts/test_engine_coordinator_master_flag.sh
scripts/test_engine_coordinator_master_recovery_hook.sh
scripts/test_engine_coordinator_on_quote_runtime.sh
scripts/test_engine_coordinator_reconcile_flag.sh
scripts/test_engine_coordinator_reconcile_runtime_flag.sh
scripts/test_entry_confidence_gate.sh
scripts/test_entry_confidence_institutional_flow.sh
scripts/test_entry_gate_coordinator_contract.sh
scripts/test_entry_gate_coordinator_regime_control.sh
scripts/test_entry_gate_coordinator.sh
scripts/test_entry_point_execution_contract.sh
scripts/test_entry_point_selector.sh
scripts/test_equity_curve.sh
scripts/test_event_audit_integrations.sh
scripts/test_event_bus_projection_integration.sh
scripts/test_event_store_factory_shared_bus.sh
scripts/test_event_store_reader.sh
scripts/test_event_store.sh
scripts/test_execution_correctness_audit.sh
scripts/test_execution_correctness_repair.sh
scripts/test_execution_decision_layer.sh
scripts/test_execution_decision_pipeline.sh
scripts/test_execution_dispatcher_event_store.sh
scripts/test_execution_dispatcher_futures_gate.sh
scripts/test_execution_dispatcher_futures_margin_guard.sh
scripts/test_execution_dispatcher_live_route_pipeline.sh
scripts/test_execution_dispatcher_live_route.sh
scripts/test_execution_dispatcher_oms_guard.sh
scripts/test_execution_dispatcher_persistent_kill_switch.sh
scripts/test_execution_dispatcher_pipeline_contract.sh
scripts/test_execution_dispatcher_pipeline.sh
scripts/test_execution_dispatcher_real_fill_persistence.sh
scripts/test_execution_dispatcher_real_metadata_runtime.sh
scripts/test_execution_dispatcher.sh
scripts/test_execution_dispatcher_strategy_runtime_gate.sh
scripts/test_execution_freeze_alert_compile.sh
scripts/test_execution_gateway_compile.sh
scripts/test_execution_intent_accounting_bridge.sh
scripts/test_execution_intent_fill_simulator.sh
scripts/test_execution_intent_fsm.sh
scripts/test_execution_intent_router.sh
scripts/test_execution_intent_transition_service.sh
scripts/test_execution_lifecycle_determinism.sh
scripts/test_execution_lineage_report.sh
scripts/test_execution_recovery_supervisor.sh
scripts/test_execution_report_listener.sh
scripts/test_execution_state_transition_logger.sh
scripts/test_execution_symbol_observability.sh
scripts/test_execution_symbol_payload_persistence.sh
scripts/test_execution_symbol_position_manager_consistency.sh
scripts/test_execution_symbol_resolver.sh
scripts/test_exit_alpha_bar_replay.sh
scripts/test_exit_alpha_parameter_grid.sh
scripts/test_exit_alpha_policy.sh
scripts/test_exit_alpha_radar_dashboard_view.sh
scripts/test_exit_engine.sh
scripts/test_exit_lifecycle_manager_body.sh
scripts/test_exit_lifecycle_manager_compile.sh
scripts/test_exit_lifecycle_real_strategy.sh
scripts/test_exit_optimization_compile.sh
scripts/test_exit_optimization.sh
scripts/test_exit_paper_fill_metadata_attach.sh
scripts/test_exit_policy_advisor.sh
scripts/test_exit_policy_advisory_compile.sh
scripts/test_exit_policy_advisory_pipeline_compile.sh
scripts/test_exit_policy_selector_compile.sh
scripts/test_exit_policy_simulation_compile.sh
scripts/test_exit_policy_simulator.sh
scripts/test_exit_state_machine.sh
scripts/test_external_replay_adapter.sh
scripts/test_extracted_layers_compile.sh
scripts/test_feature_snapshots_v1.sh
scripts/test_fee_calculator.sh
scripts/test_fill_event_router.sh
scripts/test_fill_fallback_contract_identity_no_intent.sh
scripts/test_fill_fallback_contract_identity.sh
scripts/test_fill_fallback_strategy_attribution.sh
scripts/test_fill_metadata_contract_identity.sh
scripts/test_fill_metadata_factory.sh
scripts/test_fill_metadata_regime_label.sh
scripts/test_fill_persistence_always_initialized.sh
scripts/test_fill_persistence_fallback_metadata.sh
scripts/test_fill_persistence_fallback_no_intent_scope.sh
scripts/test_fill_persistence_logging.sh
scripts/test_fill_persistence_payload_override.sh
scripts/test_fill_persistence_service.sh
scripts/test_finam_futures_market_bars.sh
scripts/test_finam_futures_signal_radar.sh
scripts/test_finam_order_client_adapter.sh
scripts/test_finam_order_identity_extraction.sh
scripts/test_finam_orders_cancel_replace_methods.sh
scripts/test_finam_orders_client_safe.sh
scripts/test_finam_order_status_adapter.sh
scripts/test_finam_radar_chain_templates.sh
scripts/test_finam_real_portfolio_sync.sh
scripts/test_find_market_bar_gaps.sh
scripts/test_first_real_order_check.sh
scripts/test_forced_pipeline_risk_gate_smoke.sh
scripts/test_futures_access_gate.sh
scripts/test_futures_active_contract_resolver.sh
scripts/test_futures_context_normalizer.sh
scripts/test_futures_contract_universe.sh
scripts/test_futures_margin_guard.sh
scripts/test_futures_market_bars_backfill.sh
scripts/test_futures_mtf_regime_aggregator.sh
scripts/test_futures_pnl_calculator.sh
scripts/test_futures_regime_engine.sh
scripts/test_futures_regime_governance.sh
scripts/test_futures_regime_snapshots.sh
scripts/test_futures_runner_runtime_wiring.sh
scripts/test_futures_session_analytics.sh
scripts/test_grafana_alert_views_ru.sh
scripts/test_grafana_analytics_files.sh
scripts/test_grafana_dashboard_provisioning.sh
scripts/test_grafana_exit_alpha_radar_dashboard.sh
scripts/test_grafana_lifecycle_panels.sh
scripts/test_grafana_provisioning.sh
scripts/test_grafana_trailing_panel.sh
scripts/test_grafana_views_ru.sh
scripts/test_incremental_exit_advice_pipeline_compile.sh
scripts/test_incremental_exit_intelligence.sh
scripts/test_institutional_execution_gate.sh
scripts/test_institutional_flow_regime_persistence.sh
scripts/test_institutional_flow_regime.sh
scripts/test_institutional_trade_quality_score.sh
scripts/test_instrument_reference_seed.sh
scripts/test_instrument_reference_sync.sh
scripts/test_instrument_spec_repository.sh
scripts/test_intermarket_regime_v1.sh
scripts/test_intermarket_selection_modifier_v1.sh
scripts/test_intrabar_mae_mfe.sh
scripts/test_intrabar_trade_quality_compile.sh
scripts/test_latest_real_positions_provider.sh
scripts/test_lifecycle_stale_position_advisor.sh
scripts/test_lifecycle_stale_position_repository_compile.sh
scripts/test_limit_entry_full_chain_dry_run.sh
scripts/test_list_dlq_events.sh
scripts/test_log_risk_event_signature.sh
scripts/test_managed_position_repository.sh
scripts/test_managed_position_service.sh
scripts/test_manual_order_call_uses_safe_client.sh
scripts/test_manual_position_pnl_analyzer.sh
scripts/test_manual_position_pnl_formatter.sh
scripts/test_manual_position_pnl_sender.sh
scripts/test_manual_position_snapshot_repository.sh
scripts/test_manual_trade_journal.sh
scripts/test_manual_trade_reconciliation_compile.sh
scripts/test_manual_trade_reconciliation_runner_compile.sh
scripts/test_margin_calculator.sh
scripts/test_market_bar_coverage_audit.sh
scripts/test_market_bars_source.sh
scripts/test_market_data_ensure_subscribed.sh
scripts/test_marketdata_runtime_config_v1.sh
scripts/test_market_event_calendar_repository.sh
scripts/test_market_event_calendar_telegram_alerts.sh
scripts/test_market_event_calendar_unique_key.sh
scripts/test_market_opportunity_continuous_futures.sh
scripts/test_market_opportunity_freshness_score.sh
scripts/test_market_opportunity_metrics_table.sh
scripts/test_market_opportunity_scoring_v2.sh
scripts/test_market_opportunity_smart_money_columns.sh
scripts/test_market_order_dry_run_accepted.sh
scripts/test_market_order_pending_reconcile.sh
scripts/test_market_order_pre_persist.sh
scripts/test_market_radar_anomaly_guard.sh
scripts/test_market_radar_candidates.sh
scripts/test_market_radar_db_save.sh
scripts/test_market_radar_filters.sh
scripts/test_market_radar_mock.sh
scripts/test_market_radar_pipeline_compile.sh
scripts/test_market_radar_strategy_mapping_allocator.sh
scripts/test_market_radar_telegram_flag.sh
scripts/test_market_radar_top10_timer.sh
scripts/test_market_session_calendar.sh
scripts/test_mean_reversion_equity.sh
scripts/test_moex_candle_provider_compile.sh
scripts/test_moex_find_security_compile.sh
scripts/test_moex_liquid_universe.sh
scripts/test_moex_opportunity_scanner.sh
scripts/test_moex_symbol_resolver.sh
scripts/test_moex_top_universe_table.sh
scripts/test_net_trade_evaluator.sh
scripts/test_ng_active_edge_resolver.sh
scripts/test_ng_conservative_breakout_m1.sh
scripts/test_ng_conservative_breakout.sh
scripts/test_ng_contract_lifecycle.sh
scripts/test_ng_knife.sh
scripts/test_ng_live_runtime_state_machine.sh
scripts/test_ng_m1_paper_pipeline_hook.sh
scripts/test_ng_m1_runtime_policy.sh
scripts/test_ng_m1_session_regime_matrix.sh
scripts/test_ng_real_guard.sh
scripts/test_ng_regime_analytics.sh
scripts/test_ng_regime_v2.sh
scripts/test_ng_replay_expansion.sh
scripts/test_ng_replay_universe.sh
scripts/test_ng_runtime_regime_policy.sh
scripts/test_ng_runtime_regime_policy_v2.sh
scripts/test_ng_runtime_telemetry.sh
scripts/test_ng_session_regime_matrix.sh
scripts/test_ng_strategy.sh
scripts/test_normalized_trade_analytics_views.sh
scripts/test_notification_router.sh
scripts/test_oco_capabilities_gate.sh
scripts/test_oco_order_manager.sh
scripts/test_oco_subscribe_orders_pipeline.sh
scripts/test_oms_dispatch_guard.sh
scripts/test_oms_invariant_audit.sh
scripts/test_oms_order_journal_fsm.sh
scripts/test_oms_order_journal.sh
scripts/test_oms_update_status_from_broker_order.sh
scripts/test_open_orders_sync.sh
scripts/test_order_ack_broker_source.sh
scripts/test_order_ack_in_orders_client.sh
scripts/test_order_ack_logger.sh
scripts/test_order_ack_model.sh
scripts/test_order_ack_views.sh
scripts/test_order_event_store.sh
scripts/test_order_reconciliation_alert_views.sh
scripts/test_order_reconciliation_logger.sh
scripts/test_order_reconciliation_views.sh
scripts/test_order_router_pipeline.sh
scripts/test_order_router.sh
scripts/test_orders_client_runtime_config_safety.sh
scripts/test_order_state_machine_fills.sh
scripts/test_order_state_machine.sh
scripts/test_order_validity_policy.sh
scripts/test_paper_fill_signal_metadata.sh
scripts/test_paper_pipeline_dynamic_strategy_name.sh
scripts/test_paper_pipeline_fill_persistence_service.sh
scripts/test_paper_pipeline_ng_selection_gate_compile.sh
scripts/test_paper_pipeline_portfolio_risk_gate.sh
scripts/test_paper_pipeline_runtime_config_v1.sh
scripts/test_paper_pipeline_runtime_override_gate_wiring.sh
scripts/test_paper_pipeline_runtime_override_helper_smoke.sh
scripts/test_paper_pipeline_runtime_selection_gate_compile.sh
scripts/test_paper_pipeline_runtime_state_gate.sh
scripts/test_paper_pipeline_signal_router_split.sh
scripts/test_parameter_sweep_summary_compile.sh
scripts/test_partial_close_engine.sh
scripts/test_partial_close_pipeline_compile.sh
scripts/test_pass_client_order_id_all_order_types.sh
scripts/test_pass_client_order_id_to_finam.sh
scripts/test_persistent_kill_switch.sh
scripts/test_pipeline_adaptive_position_accept_path.sh
scripts/test_pipeline_adaptive_position_sizer.sh
scripts/test_pipeline_adaptive_regime_filter.sh
scripts/test_pipeline_cooldown_guard_wiring.sh
scripts/test_pipeline_dynamic_strategy_resolver.sh
scripts/test_pipeline_entry_confidence_gate.sh
scripts/test_pipeline_entry_gate_coordinator_call.sh
scripts/test_pipeline_entry_gate_coordinator_init.sh
scripts/test_pipeline_entry_gate_init_order.sh
scripts/test_pipeline_entry_point_selector_wired.sh
scripts/test_pipeline_eventbus_projection_wiring.sh
scripts/test_pipeline_event_store_factory_wiring.sh
scripts/test_pipeline_execution_symbol_metadata_consistency.sh
scripts/test_pipeline_execution_symbol_resolver_accept_path.sh
scripts/test_pipeline_execution_symbol_resolver.sh
scripts/test_pipeline_fill_trade_management_wiring.sh
scripts/test_pipeline_institutional_execution_gate.sh
scripts/test_pipeline_institutional_flow_context.sh
scripts/test_pipeline_kernel_compile.sh
scripts/test_pipeline_limit_route_dispatch.sh
scripts/test_pipeline_orchestrator_compile.sh
scripts/test_pipeline_real_execution_route.sh
scripts/test_pipeline_reconciliation_repair_integration.sh
scripts/test_pipeline_reconciliation_repair_route.sh
scripts/test_pipeline_recovery_orchestrator_wiring.sh
scripts/test_pipeline_regime_label_injection.sh
scripts/test_pipeline_risk_visibility.sh
scripts/test_pipeline_runtime_active_universe_gate.sh
scripts/test_pipeline_runtime_md_resubscribe.sh
scripts/test_pipeline_runtime_reload_before_session.sh
scripts/test_pipeline_runtime_symbol_eviction_position_guard.sh
scripts/test_pipeline_runtime_symbol_eviction.sh
scripts/test_pipeline_runtime_symbol_reload.sh
scripts/test_pipeline_session_block_log_dedup.sh
scripts/test_pipeline_signal_intent_adapter_bridge.sh
scripts/test_pipeline_smart_money_context.sh
scripts/test_pipeline_smart_money_hook.sh
scripts/test_pipeline_strategy_by_symbol_guard.sh
scripts/test_pipeline_trade_gate_extraction.sh
scripts/test_pipeline_uses_execution_dispatcher.sh
scripts/test_place_limit_order_dry_run.sh
scripts/test_place_protective_for_filled_entries.sh
scripts/test_place_protective_reads_unprotected_entries.sh
scripts/test_pnl_by_institutional_regime.sh
scripts/test_pnl_reconstruction.sh
scripts/test_policy_decision_registry.sh
scripts/test_policy_impact_report.sh
scripts/test_policy_rotation_timer_compile.sh
scripts/test_portfolio_allocator.sh
scripts/test_portfolio_aware_signal_filter.sh
scripts/test_portfolio_candidate_filter.sh
scripts/test_portfolio_equity_service.sh
scripts/test_portfolio_execution_planner.sh
scripts/test_portfolio_execution_queue.sh
scripts/test_portfolio_governance_advisor.sh
scripts/test_portfolio_governance_advisory_pipeline_compile.sh
scripts/test_portfolio_governance_event_pipeline_compile.sh
scripts/test_portfolio_governance_refresh_alert_compile.sh
scripts/test_portfolio_governance_refresh_compile.sh
scripts/test_portfolio_governance_repository_compile.sh
scripts/test_portfolio_heat_advisor.sh
scripts/test_portfolio_heat_advisory_pipeline_compile.sh
scripts/test_portfolio_heat_engine.sh
scripts/test_portfolio_heat_repository_compile.sh
scripts/test_portfolio_heat_risk_gate.sh
scripts/test_portfolio_intelligence_repository_compile.sh
scripts/test_portfolio_intelligence_snapshot.sh
scripts/test_portfolio_mtm_service.sh
scripts/test_portfolio_rebuilder.sh
scripts/test_portfolio_reconciliation_engine.sh
scripts/test_portfolio_reconciliation_layer.sh
scripts/test_portfolio_reconciliation_repair.sh
scripts/test_portfolio_research_allocator.sh
scripts/test_portfolio_risk_gate.sh
scripts/test_portfolio_risk_v3.sh
scripts/test_portfolio_sync_systemd.sh
scripts/test_portfolio_ui_split_views.sh
scripts/test_position_intent_db.sh
scripts/test_position_intent_order_gate.sh
scripts/test_position_intent_repository.sh
scripts/test_position_intent.sh
scripts/test_position_intent_trade_role.sh
scripts/test_position_lifecycle_formatter.sh
scripts/test_position_lifecycle_pipeline_compile.sh
scripts/test_position_lifecycle_real_strategy.sh
scripts/test_position_lifecycle_reconcile_events.sh
scripts/test_position_lifecycle_reconciler.sh
scripts/test_position_lifecycle_reconciliation_pipeline.sh
scripts/test_position_lifecycle_self_healer.sh
scripts/test_position_lifecycle_self_healing_pipeline.sh
scripts/test_position_lifecycle_service_compile.sh
scripts/test_position_lifecycle_service_partial_close.sh
scripts/test_position_lifecycle_service_profit_lock.sh
scripts/test_position_lifecycle_service_take_profit.sh
scripts/test_position_lifecycle_service_trailing_body.sh
scripts/test_position_lifecycle_service_trailing.sh
scripts/test_position_lifecycle_startup_load.sh
scripts/test_position_lifecycle_state_repository.sh
scripts/test_position_manager_authoritative_sync.sh
scripts/test_position_mismatch_hard_block.sh
scripts/test_position_mismatch_provider_before_real_order.sh
scripts/test_position_order_tracker.sh
scripts/test_position_portfolio_sync_layer.sh
scripts/test_position_rebuild_comparator.sh
scripts/test_position_recovery_service.sh
scripts/test_position_registry.sh
scripts/test_position_state_reconciliation.sh
scripts/test_position_symbol_normalizer.sh
scripts/test_postgres_logger_execution_event_mock.sh
scripts/test_postgres_logger_fill_payload_metadata.sh
scripts/test_postgres_logger_log_fill_payload_db.sh
scripts/test_postgres_opportunity_scanner.sh
scripts/test_probe_finam_symbols.sh
scripts/test_production_checkpoint_execution_v2.sh
scripts/test_production_dashboard.sh
scripts/test_production_healthcheck.sh
scripts/test_profit_lock_engine.sh
scripts/test_profit_lock_events_and_grafana.sh
scripts/test_profit_lock_pipeline_compile.sh
scripts/test_projection_checkpoint_service.sh
scripts/test_projection_dlq_integration.sh
scripts/test_projection_engine.sh
scripts/test_projection_lag_healthcheck.sh
scripts/test_projection_store.sh
scripts/test_projection_updater_cli.sh
scripts/test_projection_updater.sh
scripts/test_projection_worker_healthcheck.sh
scripts/test_projection_worker_health_systemd.sh
scripts/test_projection_worker.sh
scripts/test_projection_worker_systemd.sh
scripts/test_protection_level_calculator.sh
scripts/test_protective_duplicate_prevention.sh
scripts/test_protective_lifecycle_manager.sh
scripts/test_protective_manual_required_fallback.sh
scripts/test_protective_order_link_after_entry_ack.sh
scripts/test_protective_order_link_attach_after_stop_take_ack.sh
scripts/test_protective_order_link.sh
scripts/test_protective_order_link_views.sh
scripts/test_protective_order_recovery_alert_views.sh
scripts/test_protective_order_recovery_check.sh
scripts/test_protective_real_stop_placement_path.sh
scripts/test_protective_stop_client_order_id_wiring.sh
scripts/test_protective_stop_price_calculation.sh
scripts/test_protective_stop_real_dry_run.sh
scripts/test_protective_stop_real_execution_adapter.sh
scripts/test_protective_stop_real_send_probe.sh
scripts/test_quarantine_orphan_trade_fills.sh
scripts/test_quote_normalizer_orchestrator_compile.sh
scripts/test_quote_normalizer.sh
scripts/test_quote_signal_processor_compile.sh
scripts/test_radar_candidate_analyzer_compile.sh
scripts/test_radar_persistence_engine.sh
scripts/test_radar_persistence_repository_compile.sh
scripts/test_rank_strategies_daily_compile.sh
scripts/test_real_allowed_symbols_gate.sh
scripts/test_real_buy_execution_adapter.sh
scripts/test_real_dry_run_execution.sh
scripts/test_real_execution_capabilities_gate.sh
scripts/test_real_execution_dry_run.sh
scripts/test_real_execution_journal_mock.sh
scripts/test_real_execution_metadata_passthrough.sh
scripts/test_real_execution_modes.sh
scripts/test_real_execution_order_event_store.sh
scripts/test_real_execution_order_state.sh
scripts/test_real_execution_policy_integration.sh
scripts/test_real_execution_safety_before_place_order.sh
scripts/test_real_execution_safety_gate.sh
scripts/test_real_execution_safety_layer.sh
scripts/test_real_execution_switch.sh
scripts/test_real_futures_market_bars.sh
scripts/test_realized_pnl_engine.sh
scripts/test_real_market_order_timeout_guard.sh
scripts/test_real_order_state_synchronizer.sh
scripts/test_real_portfolio_position_sync.sh
scripts/test_real_portfolio_price_sync.sh
scripts/test_real_portfolio_snapshot.sh
scripts/test_real_position_qty_provider_wiring.sh
scripts/test_real_position_snapshot_repository_mock.sh
scripts/test_real_position_to_managed_sync.sh
scripts/test_real_protective_lifecycle_pipeline.sh
scripts/test_real_protective_lifecycle.sh
scripts/test_real_sell_execution_adapter.sh
scripts/test_real_stock_safety_gate_cli.sh
scripts/test_real_stock_safety_gate.sh
scripts/test_realtime_projection_subscriber.sh
scripts/test_reconcile_order_acks_cli.sh
scripts/test_recover_futures_fill_context.sh
scripts/test_recovery_health_systemd.sh
scripts/test_recovery_orchestrator_freeze.sh
scripts/test_recovery_orchestrator_gate_indent.sh
scripts/test_recovery_orchestrator_healthcheck.sh
scripts/test_recovery_orchestrator.sh
scripts/test_recovery_snapshot_service.sh
scripts/test_regime_engine_hysteresis.sh
scripts/test_regime_engine_log_rate_limit.sh
scripts/test_regime_failure_analyzer_v2.sh
scripts/test_regime_labeler.sh
scripts/test_regime_layer_v2.sh
scripts/test_regime_matrix_runtime_modifier_v2.sh
scripts/test_regime_policy_persistence.sh
scripts/test_regime_risk_policy.sh
scripts/test_regime_runtime_overrides_v3.sh
scripts/test_regime_snapshot_repository.sh
scripts/test_regime_unknown_cleanup.sh
scripts/test_replay_batch_summary_compile.sh
scripts/test_replay_campaign_performance_summary_compile.sh
scripts/test_replay_campaign_summary_compile.sh
scripts/test_replay_campaign_telemetry.sh
scripts/test_replay_disable_br_regime.sh
scripts/test_replay_ng_conservative_breakout.sh
scripts/test_replay_to_grafana_pipeline.sh
scripts/test_research_layer_v1.sh
scripts/test_research_pipeline_context_runtime_filter_wiring.sh
scripts/test_research_pipeline_exit_policy_context_wiring.sh
scripts/test_research_pipeline_feature_snapshots_wiring.sh
scripts/test_research_pipeline_grafana_views.sh
scripts/test_research_pipeline_intermarket_runtime_wiring.sh
scripts/test_research_pipeline_orchestrator.sh
scripts/test_research_pipeline_regime_matrix_runtime_modifier_wiring.sh
scripts/test_research_pipeline_regime_matrix_wiring.sh
scripts/test_research_pipeline_regime_performance_wiring.sh
scripts/test_research_pipeline_regime_runtime_overrides_wiring.sh
scripts/test_research_pipeline_run_log.sh
scripts/test_research_pipeline_trade_context_feature_enrichment_wiring.sh
scripts/test_research_portfolio_equity.sh
scripts/test_research_regime_classifier.sh
scripts/test_research_runtime_grafana_views.sh
scripts/test_research_runtime_supervisor_futures_tokens.sh
scripts/test_research_runtime_supervisor.sh
scripts/test_resolve_dlq_event.sh
scripts/test_restart_recovery_coordinator.sh
scripts/test_restart_recovery.sh
scripts/test_risk_per_trade_sizing.sh
scripts/test_risk_router_compile.sh
scripts/test_rotate_active_policy_compile.sh
scripts/test_run_closed_trade_report_metadata_join.sh
scripts/test_run_external_replay_pipeline_compile.sh
scripts/test_run_market_pipeline_dynamic_universe.sh
scripts/test_run_market_pipeline_env_file.sh
scripts/test_run_market_pipeline_startup_gate.sh
scripts/test_run_parameter_sweep_compile.sh
scripts/test_run_replay_batch_compile.sh
scripts/test_run_replay_batch_moex_compile.sh
scripts/test_run_replay_campaign_compile.sh
scripts/test_run_replay_campaign_moex_compile.sh
scripts/test_run_runtime_execution_engine_compile.sh
scripts/test_run_runtime_governance_daily_compile.sh
scripts/test_run_runtime_governance_service_compile.sh
scripts/test_runtime_active_universe_table.sh
scripts/test_runtime_adaptive_risk_integration.sh
scripts/test_runtime_adaptive_risk.sh
scripts/test_runtime_allocator_decision_classification.sh
scripts/test_runtime_allocator_decision_logger.sh
scripts/test_runtime_anomaly_correlation.sh
scripts/test_runtime_auto_recovery.sh
scripts/test_runtime_capital_allocator.sh
scripts/test_runtime_config_v1.sh
scripts/test_runtime_control_alerts_compile.sh
scripts/test_runtime_control_dynamic_universe_feed.sh
scripts/test_runtime_control_uses_continuous_symbol.sh
scripts/test_runtime_drift_detection.sh
scripts/test_runtime_execution_engine_active_strategy_gate.sh
scripts/test_runtime_execution_engine.sh
scripts/test_runtime_execution_engine_strategy_gate.sh
scripts/test_runtime_execution_engine_v3_compile.sh
scripts/test_runtime_execution_engine_v3_provider_compat.sh
scripts/test_runtime_execution_engine_v3_reap_exited.sh
scripts/test_runtime_execution_engine_v3_rebalance.sh
scripts/test_runtime_execution_engine_v3_supervisor_compile.sh
scripts/test_runtime_execution_sizer.sh
scripts/test_runtime_governance_alert_compile.sh
scripts/test_runtime_governance_alert_dedup_compile.sh
scripts/test_runtime_governance_coordinator.sh
scripts/test_runtime_governance_coordinator_v2.sh
scripts/test_runtime_governance_dashboard.sh
scripts/test_runtime_governance_decision_pipeline_compile.sh
scripts/test_runtime_governance_engine.sh
scripts/test_runtime_governance_ng_m1_policy_gate.sh
scripts/test_runtime_governance_telemetry.sh
scripts/test_runtime_log_fill_signal_metadata.sh
scripts/test_runtime_operational_dashboard.sh
scripts/test_runtime_override_gate.sh
scripts/test_runtime_policy_mode_integration.sh
scripts/test_runtime_policy_mode_resolver.sh
scripts/test_runtime_rebalance_allocator.sh
scripts/test_runtime_rebalance_cross_contract_liquidity.sh
scripts/test_runtime_rebalance_cycle.sh
scripts/test_runtime_rebalance_loop.sh
scripts/test_runtime_rebalance_market_event_alerts.sh
scripts/test_runtime_rebalance_market_event_calendar.sh
scripts/test_runtime_recovery_coordinator_v2.sh
scripts/test_runtime_recovery_integration.sh
scripts/test_runtime_regime_overrides_default_policy.sh
scripts/test_runtime_reliability_guard.sh
scripts/test_runtime_risk_freeze_admin.sh
scripts/test_runtime_rolling_strategy_stats.sh
scripts/test_runtime_selection_gate_active_contract_hard_check.sh
scripts/test_runtime_selection_gate_v1.sh
scripts/test_runtime_selector_paper_runtime_candidate.sh
scripts/test_runtime_state_persistence.sh
scripts/test_runtime_state_restore.sh
scripts/test_runtime_state_snapshot_timer.sh
scripts/test_runtime_strategy_cooldown_builder.sh
scripts/test_runtime_strategy_cooldown_provider.sh
scripts/test_runtime_strategy_gate_provider.sh
scripts/test_runtime_strategy_scores_sync.sh
scripts/test_runtime_strategy_selection_event_risk_gate.sh
scripts/test_runtime_strategy_selection_provider.sh
scripts/test_runtime_strategy_selection_repository.sh
scripts/test_runtime_strategy_selector.sh
scripts/test_runtime_subprocess_worker_compile.sh
scripts/test_runtime_supervisor_compile.sh
scripts/test_runtime_supervisor_recovery_integration.sh
scripts/test_runtime_supervisor_timer_templates.sh
scripts/test_runtime_symbol_mapper.sh
scripts/test_runtime_symbol_reload_service.sh
scripts/test_runtime_universe_allocator.sh
scripts/test_runtime_universe_allocator_v2_compile.sh
scripts/test_runtime_universe_allocator_v2_regression.sh
scripts/test_runtime_universe_provider_active_universe.sh
scripts/test_runtime_universe_provider.sh
scripts/test_runtime_universe_provider_sources.sh
scripts/test_runtime_universe_report.sh
scripts/test_runtime_universe_rotation_logger.sh
scripts/test_runtime_universe_rotation_log_table.sh
scripts/test_run_volatility_scan_mock.sh
scripts/test_run_volatility_scan_save_mock.sh
scripts/test_safe_cleanup_docs.sh
scripts/test_seed_runtime_control_from_strategy_map.sh
scripts/test_seed_strategy_runtime_control.sh
scripts/test_select_best_adaptive_policy_compile.sh
scripts/test_select_cross_sectional_instruments_compile.sh
scripts/test_selection_contract_normalization_v1.sh
scripts/test_selection_layer_v1.sh
scripts/test_selection_status_model_v1.sh
scripts/test_send_grafana_alerts_telegram.sh
scripts/test_sending_intent_recovery.sh
scripts/test_send_watchlist_telegram_compile.sh
scripts/test_sentiment_engine.sh
scripts/test_sentiment_feature_provider.sh
scripts/test_sentiment_signal_enricher.sh
scripts/test_session_routing.sh
scripts/test_session_runtime_gate.sh
scripts/test_short_client_order_id.sh
scripts/test_signal_alert_dedup_ttl.sh
scripts/test_signal_alert_formatter.sh
scripts/test_signal_alert_sender.sh
scripts/test_signal_confidence_engine.sh
scripts/test_signal_fill_link_runtime.sh
scripts/test_signal_intent_backward_compat.sh
scripts/test_signal_intent_v2.sh
scripts/test_signal_lifecycle_engine.sh
scripts/test_signal_lifecycle_monitor_compile.sh
scripts/test_signal_paper_trade_tracker.sh
scripts/test_signal_probability_estimator.sh
scripts/test_signal_repository_compile.sh
scripts/test_signal_repository_db_insert.sh
scripts/test_signal_router_ai_enrichment.sh
scripts/test_signal_router_compile.sh
scripts/test_signal_to_closed_trade_metadata_chain.sh
scripts/test_signal_trade_runtime_repository_wiring.sh
scripts/test_signal_trade_runtime.sh
scripts/test_smart_entry_signal_metadata.sh
scripts/test_smart_entry_strategy_metadata.sh
scripts/test_smart_money_feature_repository.sh
scripts/test_smart_money_features.sh
scripts/test_snapshot_aware_comparator_integration.sh
scripts/test_snapshot_aware_portfolio_rebuilder.sh
scripts/test_startup_execution_recovery_chain.sh
scripts/test_startup_recovery_gate_rebuild_comparator.sh
scripts/test_startup_recovery_gate.sh
scripts/test_statistical_validation_decision.sh
scripts/test_statistical_validation_engine.sh
scripts/test_statistics_repository_compile.sh
scripts/test_stop_replacement_engine.sh
scripts/test_strategy_analytics_engine.sh
scripts/test_strategy_attribution_smoke_fill.sh
scripts/test_strategy_blocked_cooldown_compile.sh
scripts/test_strategy_canonicalizer.sh
scripts/test_strategy_decision_report.sh
scripts/test_strategy_decision_runtime_sql.sh
scripts/test_strategy_event_risk_context.sh
scripts/test_strategy_feature_regime_attribution_views.sh
scripts/test_strategy_health_engine.sh
scripts/test_strategy_intent_adapter.sh
scripts/test_strategy_lifecycle_state_machine.sh
scripts/test_strategy_map_pipeline_compile.sh
scripts/test_strategy_optimization_report.sh
scripts/test_strategy_optimization_runtime_sql.sh
scripts/test_strategy_performance_monitor_compile.sh
scripts/test_strategy_performance_monitor_v2.sh
scripts/test_strategy_performance_report.sh
scripts/test_strategy_promotion_engine_v1.sh
scripts/test_strategy_promotion_feed_repository.sh
scripts/test_strategy_promotion_feed.sh
scripts/test_strategy_ranker.sh
scripts/test_strategy_ranking_v2.sh
scripts/test_strategy_rank_persistence.sh
scripts/test_strategy_rank_weight_provider.sh
scripts/test_strategy_recovery_hysteresis.sh
scripts/test_strategy_regime_matrix_v1.sh
scripts/test_strategy_regime_performance_v1.sh
scripts/test_strategy_report_excludes_unknown.sh
scripts/test_strategy_runtime_compile.sh
scripts/test_strategy_runtime_control_service.sh
scripts/test_strategy_runtime_gate.sh
scripts/test_strategy_runtime_notification.sh
scripts/test_strategy_runtime_regime_control.sh
scripts/test_strategy_scorecard_persistence.sh
scripts/test_strategy_scorecard.sh
scripts/test_strategy_scorecard_v2.sh
scripts/test_strategy_statistics_context_quality_source.sh
scripts/test_strategy_statistics_v2.sh
scripts/test_subscribe_orders_normalizer.sh
scripts/test_subscribe_orders_snapshot.sh
scripts/test_symbol_strategy_map_ng_m1.sh
scripts/test_symbol_strategy_mapper.sh
scripts/test_symbol_strategy_resolver_compile.sh
scripts/test_sync_runtime_active_universe_from_active_edge.sh
scripts/test_sync_runtime_active_universe_from_governance.sh
scripts/test_sync_runtime_active_universe_from_ng_live_state.sh
scripts/test_sync_runtime_active_universe_from_strategy_selection.sh
scripts/test_synthetic_protective_force_trigger.sh
scripts/test_synthetic_protective_real_sell_adapter.sh
scripts/test_synthetic_protective_runtime_loop.sh
scripts/test_synthetic_protective_trigger.sh
scripts/test_systemd_governance_service.sh
scripts/test_systemd_market_event_alerts.sh
scripts/test_systemd_order_ack_reconcile_timeout.sh
scripts/test_systemd_order_ack_reconcile_timer.sh
scripts/test_systemd_paper_runtime_service.sh
scripts/test_systemd_protective_recovery_check_timer.sh
scripts/test_systemd_radar_timer.sh
scripts/test_systemd_telegram_alerts.sh
scripts/test_take_profit_events_and_grafana.sh
scripts/test_telegram_alert_cooldown.sh
scripts/test_telegram_alert_deduplication.sh
scripts/test_telegram_alert_manual_entry_fields.sh
scripts/test_telegram_alert_ru_formatter.sh
scripts/test_telegram_bot_news_ingest.sh
scripts/test_telegram_bridge_proxy.sh
scripts/test_telegram_notifier_env_file.sh
scripts/test_telegram_sentiment_listener.sh
scripts/test_telegram_signal_dispatcher.sh
scripts/test_telegram_signal_router.sh
scripts/test_telegram_signal_taxonomy.sh
scripts/test_telethon_news_ingest.sh
scripts/test_trade_attribution_v2.sh
scripts/test_trade_context_feature_enrichment_v1.sh
scripts/test_trade_context_snapshot.sh
scripts/test_trade_exit_policy_context.sh
scripts/test_trade_fill_quality_audit.sh
scripts/test_trade_gate_service.sh
scripts/test_trade_management_service.sh
scripts/test_trade_outcome_reporter.sh
scripts/test_trade_path_reconstruction.sh
scripts/test_trade_quality.sh
scripts/test_trade_risk_context.sh
scripts/test_trades_drawdown_curve_views.sh
scripts/test_trades_drawdown_summary.sh
scripts/test_trades_equity_curve_views.sh
scripts/test_trade_signal_notifier_send_text.sh
scripts/test_trade_signal_notifier.sh
scripts/test_trade_source_contract.sh
scripts/test_trade_source_paper_pipeline.sh
scripts/test_trades_paired_pnl_summary.sh
scripts/test_trades_paired_pnl_views.sh
scripts/test_trade_timestamp_normalizer.sh
scripts/test_trading_engine_coordinator_on_quote_flag.sh
scripts/test_trading_engine_coordinator.sh
scripts/test_trailing_exit_dry_run_audit.sh
scripts/test_trailing_exit_max_qty_guard.sh
scripts/test_trailing_exit_production_checkpoint.sh
scripts/test_trailing_exit_real_arm.sh
scripts/test_trailing_exit_real_shadow_sell.sh
scripts/test_trailing_exit_runtime_loop.sh
scripts/test_trailing_exit_state_live_dry_run.sh
scripts/test_trailing_exit_state_supervisor.sh
scripts/test_trailing_exit_supervisor.sh
scripts/test_trailing_order_manager.sh
scripts/test_trailing_replace_stop_pipeline.sh
scripts/test_trailing_runtime_pre_sync.sh
scripts/test_trend_filter.sh
scripts/test_trend_gate_service.sh
scripts/test_turnover_churn_analytics.sh
scripts/test_update_dynamic_watchlist_from_opportunities.sh
scripts/test_update_market_event_calendar.sh
scripts/test_update_market_opportunity_metrics_from_moex_top.sh
scripts/test_update_market_opportunity_metrics.sh
scripts/test_update_moex_top_universe_from_volatility_scan.sh
scripts/test_validate_campaign_statistics_compile.sh
scripts/test_virtual_signal_trade_repository_mock.sh
scripts/test_volatility_breakout_equity.sh
scripts/test_volatility_scanner.sh
scripts/test_walkforward_engine_compile.sh
scripts/test_watch_candidate_runtime_analyzer_compile.sh
scripts/test_watch_runtime_probability_net_eval.sh
scripts/test_wire_transition_service_order_synchronizer.sh
scripts/test_wire_transition_service_real_buy.sh
scripts/test_wire_transition_service_real_sell.sh

