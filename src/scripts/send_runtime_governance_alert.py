from __future__ import annotations

import argparse

from finam_core.analytics.statistics_repository import build_psycopg_url
from finam_core.analytics.symbol_strategy_resolver import SymbolStrategyResolver
from finam_core.contracts.instrument_display_name_resolver import InstrumentDisplayNameResolver
from finam_core.notifications.telegram_signal_dispatcher import TelegramSignalDispatcher
from finam_core.notifications.telegram_alert_deduplication import TelegramAlertDeduplicator
from finam_core.notifications.telegram_signal_taxonomy import TelegramSignalMessage
from finam_core.runtime.runtime_governance_coordinator_v2 import RuntimeGovernanceCoordinatorV2


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--timeframe", default="M5")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    database_url = build_psycopg_url()

    strategy = SymbolStrategyResolver(database_url).resolve(args.symbol)
    display_name = InstrumentDisplayNameResolver(database_url).resolve(args.symbol)

    decision = RuntimeGovernanceCoordinatorV2(database_url).decide(
        symbol=args.symbol,
        strategy=strategy,
        timeframe=args.timeframe,
    )

    should_alert = (
        args.force
        or decision.heat_status in {"HIGH", "CRITICAL", "EXTREME"}
        or not decision.allow_new_entries
        or decision.watch_only
        or decision.lifecycle_severity in {"HIGH", "CRITICAL"}
    )

    if not should_alert:
        print(
            "RUNTIME_GOVERNANCE_ALERT_SKIPPED "
            f"symbol={args.symbol} reason=governance_normal",
            flush=True,
        )
        return 0

    risk_comment = (
        f"Статус перегрева портфеля: {decision.heat_status}. "
        f"Множитель риска: {decision.risk_multiplier}. "
        f"Новые входы: {'разрешены' if decision.allow_new_entries else 'заблокированы'}. "
        f"Lifecycle: {decision.lifecycle_action} / {decision.lifecycle_severity}."
    )

    reason = (
        f"Решение runtime governance: {decision.reason}. "
        f"Режим: {decision.mode}."
    )

    alert_status = (
        decision.lifecycle_action
        if decision.lifecycle_severity in {"HIGH", "CRITICAL"}
        else decision.heat_status
    )

    alert_key = (
        f"runtime_governance:"
        f"{args.symbol}:"
        f"{decision.heat_status}:"
        f"{decision.lifecycle_action}"
    )

    dedup = TelegramAlertDeduplicator(database_url)
    dedup.migrate()

    dedup_decision = dedup.should_send(
        alert_key=alert_key,
        status=alert_status,
        cooldown_sec=1800,
    )

    if not dedup_decision.should_send:
        print(
            "RUNTIME_GOVERNANCE_ALERT_DEDUP_SKIPPED "
            f"symbol={args.symbol} "
            f"alert_key={alert_key} "
            f"reason={dedup_decision.reason}",
            flush=True,
        )
        return 0

    message = TelegramSignalMessage(
        channel_type="RISK",
        symbol=args.symbol,
        display_name=display_name,
        direction="WARNING",
        source="runtime_governance",
        strategy=strategy,
        timeframe=args.timeframe,
        confidence=1.0,
        risk_comment=risk_comment,
        reason=reason,
    )

    result = TelegramSignalDispatcher().dispatch(message)

    if result.status in {"SENT", "SKIPPED"}:
        dedup.mark_sent(
            alert_key=alert_key,
            status=alert_status,
        )

    print(
        "RUNTIME_GOVERNANCE_ALERT_RESULT "
        f"symbol={args.symbol} "
        f"status={result.status} "
        f"channel={result.channel_type} "
        f"target_env={result.target_env} "
        f"alert_key={alert_key} "
        f"reason={result.reason}",
        flush=True,
    )

    return 0 if result.status in {"SENT", "SKIPPED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
