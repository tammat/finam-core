from __future__ import annotations

from marketcore.presentation.workspace_v2.resolver.control_center_v2_resolver import ControlCenterV2Resolver
from marketcore.presentation.workspace_v2.viewmodel.control_center_v2_viewmodel import (
    ControlCenterTrafficLightV2,
    ControlCenterV2ViewModel,
    RelationshipCandidateV2,
    SignalFunnelStageV2,
    SignalLossReasonV2,
)


FAMILY_NAMES = {
    "INDEX_TO_STOCK": "Индекс → акция",
    "SECTOR_TO_STOCK": "Сектор → акция",
    "COMMODITY_TO_STOCK": "Сырьё → акция",
    "FX_TO_STOCK": "Валюта → акция",
    "MULTIFACTOR_TO_STOCK": "Факторы → акция",
    "OVERNIGHT_TO_OPEN": "Ночь → открытие",
    "LIQUIDITY_TO_RETURN": "Ликвидность → доходность",
    "PAIR_SPREAD": "Парный спред",
}

FUNNEL_STAGE_LABELS = {
    "RESEARCH": "Исследования",
    "CANDIDATE": "Кандидаты",
    "VALIDATED_EDGE": "Подтверждённое преимущество",
    "OOS": "Вневыборочная проверка",
    "FORWARD": "Форвардное наблюдение",
    "SHADOW": "Теневое наблюдение",
    "PAPER": "Бумажная торговля",
    "RUNTIME": "Допуск к исполнению",
    "LIVE": "Реальная торговля",
    "PROFIT": "Прибыль",
}

REASON_LABELS = {
    "DATA": "Данные",
    "VOLATILITY": "Волатильность",
    "LIQUIDITY": "Ликвидность",
    "RISK": "Риск",
    "EDGE": "Edge",
    "MARKET": "Рынок",
    "EXIT": "Выход",
    "SETUP": "Условия входа",
    "EXECUTION": "Исполнение",
    "RESEARCH": "Исследование",
    "LIFECYCLE": "Жизненный цикл",
    "BLOCK": "Блокировка",
    "QUALITY": "Качество",
    "UNKNOWN": "Нет предпосылок",
    "OTHER": "Прочее",
}

REASON_ACTIONS = {
    "DATA": "Обновить историю и повторить проверку качества",
    "VOLATILITY": "Разделить результаты по режимам волатильности",
    "LIQUIDITY": "Ограничить слабую ликвидность и проверить bid/ask",
    "RISK": "Проверить лимиты риска и размер позиции",
    "EDGE": "Пересмотреть гипотезу и устойчивость параметров",
    "MARKET": "Разделить результаты по режимам рынка",
    "EXIT": "Проверить политику выхода и время удержания",
    "SETUP": "Уточнить условия входа без просмотра финального OOS",
    "EXECUTION": "Оценить издержки и качество исполнения",
    "RESEARCH": "Проверить методику и защиту от переобучения",
    "LIFECYCLE": "Проверить связи гипотезы и её текущий статус",
    "BLOCK": "Сначала снять блокирующее ограничение",
    "QUALITY": "Восстановить качество исходных данных",
    "UNKNOWN": "Проверить наличие рыночных предпосылок",
    "OTHER": "Разобрать исходные коды причин",
}


class ControlCenterV2Presenter:
    def __init__(self) -> None:
        self._resolver = ControlCenterV2Resolver()

    def load(self) -> ControlCenterV2ViewModel:
        data = self._resolver.resolve()
        quality = data["quality"]
        summary = data["relationship_summary"]
        forward = data["forward"]
        execution = data["execution"]

        ready = int(quality.get("ready") or 0)
        total = int(quality.get("total") or 0)
        passed = int(summary.get("passed") or 0)
        candidates = int(forward.get("candidates") or 0)
        observations = int(forward.get("observations") or 0)
        promoted = int(forward.get("promoted") or 0)
        quotes = int(execution.get("quote_verified") or 0)

        lights = (
            ControlCenterTrafficLightV2("data", "Данные", f"Готово {ready} из {total}", "OK" if total and ready == total else "WARNING", "/workspace-v2/control-center/edge-oos/data-quality", "research.control.traffic.data.value", (("ready", ready), ("total", total))),
            ControlCenterTrafficLightV2("edge", "Edge", f"OOS PASS: {passed}", "OK" if passed else "BLOCKED", "/workspace-v2/control-center/edge-oos/relationship-factory", "research.control.traffic.edge.value", (("passed", passed),)),
            ControlCenterTrafficLightV2("watch", "Наблюдение", f"{candidates} кандидатов · {observations} сигналов", "OK" if observations > 0 else "WARNING", "/workspace-v2/control-center/edge-oos/strategy-generator", "research.control.traffic.watch.value", (("candidates", candidates), ("observations", observations))),
            ControlCenterTrafficLightV2("quotes", "Котировки", f"Подтверждено: {quotes}", "OK" if quotes else "WARNING", "/workspace-v2/control-center/edge-oos/execution-edge", "research.control.traffic.quotes.value", (("verified", quotes),)),
            ControlCenterTrafficLightV2("live", "LIVE", "Продвижение запрещено", "BLOCKED", "/workspace-v2/control-center/edge-oos/legacy", "research.control.traffic.live.blocked", ()),
        )

        relationships = tuple(self._candidate(row) for row in data["relationships"])
        funnel_stages = tuple(self._stage(row) for row in data["funnel_stages"])
        loss_reasons = tuple(self._reason(row) for row in data["loss_reasons"])
        return ControlCenterV2ViewModel(
            title="Центр управления",
            subtitle="Edge · OOS · Фабрика связей",
            traffic_lights=lights,
            relationship_summary=summary,
            relationships=relationships,
            funnel_stages=funnel_stages,
            loss_reasons=loss_reasons,
            funnel_comparable=bool(data["funnel_comparable"]),
            shadow_summary=data["shadow"],
            execution_quality=tuple(data["execution_quality"]),
            execution_variants=tuple(data["execution_variants"]),
            microstructure_priorities=tuple(data["microstructure_priorities"]),
            volatility_analysis=tuple(data["volatility_analysis"]),
            risk_analysis=tuple(data["risk_analysis"]),
            entry_analysis=tuple(data["entry_analysis"]),
            market_prerequisites=tuple(data["market_prerequisites"]),
            exit_analysis=tuple(data["exit_analysis"]),
            block_analysis=tuple(data["block_analysis"]),
            shadow_requirements=tuple(data["shadow_requirements"]),
            shadow_process=tuple(data["shadow_process"]),
            shadow_alerts=tuple(data["shadow_alerts"]),
            forward_blockers=tuple(data["forward_blockers"]),
            forward_pass_process=tuple(data["forward_pass_process"]),
            forward_readiness=tuple(data["forward_readiness"]),
            edge_search_process=tuple(data["edge_search_process"]),
            edge_search_results=tuple(data["edge_search_results"]),
            swing_summary=data["swing_summary"],
        )

    @staticmethod
    def _candidate(row) -> RelationshipCandidateV2:
        family_code = str(row.get("relationship_family") or "UNKNOWN")
        regime_code = str(row.get("regime_group") or "ALL")
        session_code = str(row.get("session_code") or "ALL")
        sources = row.get("source_symbols") or []
        source = " + ".join(sources) if isinstance(sources, list) else str(sources)
        verdict = str(row.get("verdict_code") or "UNVERIFIED")
        return RelationshipCandidateV2(
            family=FAMILY_NAMES.get(family_code, "Связь"),
            source=source,
            target=str(row.get("target_symbol") or "—"),
            regime=str(row.get("regime_group") or "Все").replace("_", " "),
            session=str(row.get("session_code") or "Все").replace("_", " "),
            oos_trades=int(row.get("oos_trades") or 0),
            profit_factor=float(row.get("oos_profit_factor") or 0),
            expectancy_bps=float(row.get("oos_expectancy_bps") or 0),
            coverage_pct=float(row.get("regime_coverage_ratio") or 0) * 100,
            verdict={"OOS_PASS": "PASS", "OOS_FAIL": "FAIL", "UNVERIFIED": "Нет подтверждения"}.get(verdict, verdict),
            status="OK" if verdict == "OOS_PASS" else ("BLOCKED" if verdict == "OOS_FAIL" else "WARNING"),
            family_code=family_code,
            regime_code=regime_code,
            session_code=session_code,
            verdict_code=verdict,
        )

    @staticmethod
    def _stage(row) -> SignalFunnelStageV2:
        count = int(row.get("stage_count") or 0)
        rate = row.get("pass_rate_pct")
        stage_code = str(row.get("stage_code") or "")
        status = str(row.get("stage_status") or "WARNING")
        reason_code = str(row.get("reason_code") or "")
        if rate is not None:
            conversion = f"Конверсия из предыдущей стадии: {float(rate):.1f}%"
        elif reason_code == "INITIAL_STAGE":
            conversion = "Первая стадия: конверсия не рассчитывается"
        else:
            conversion = "Конверсия не рассчитана: стадии пока несопоставимы"
        return SignalFunnelStageV2(
            label=FUNNEL_STAGE_LABELS.get(
                stage_code,
                str(row.get("stage_name") or stage_code).replace("_", " "),
            ),
            count=count,
            conversion=conversion,
            status=status,
            stage_code=stage_code,
            pass_rate_pct=(float(rate) if rate is not None else None),
            source_identity=str(row.get("source_identity") or ""),
            source_as_of=row.get("source_as_of"),
            freshness_code=str(row.get("freshness_code") or "UNAVAILABLE"),
            quality_code=str(row.get("quality_code") or "UNVERIFIED"),
            reason_code=reason_code,
            net_pnl=row.get("net_pnl"),
            cost_impact=row.get("cost_impact"),
        )

    @staticmethod
    def _reason(row) -> SignalLossReasonV2:
        code = str(row.get("reason_group") or "OTHER").upper()
        count = int(row.get("rows_total") or 0)
        return SignalLossReasonV2(
            code=code,
            label=REASON_LABELS.get(code, "Прочее"),
            count=count,
            action=REASON_ACTIONS.get(code, REASON_ACTIONS["OTHER"]),
            status="WARNING" if count else "OK",
            action_target=str(row.get("action_target") or ""),
        )
