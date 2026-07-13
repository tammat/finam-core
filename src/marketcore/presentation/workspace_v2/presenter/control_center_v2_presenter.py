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
            ControlCenterTrafficLightV2("data", "Данные", f"Готово {ready} из {total}", "OK" if total and ready == total else "WARNING", "/workspace-v2/control-center/edge-oos/data-quality"),
            ControlCenterTrafficLightV2("edge", "Edge", f"OOS PASS: {passed}", "OK" if passed else "BLOCKED", "/workspace-v2/control-center/edge-oos/relationship-factory"),
            ControlCenterTrafficLightV2("watch", "Наблюдение", f"{candidates} кандидатов · {observations} сигналов", "OK" if promoted else "WARNING", "/workspace-v2/control-center/edge-oos/strategy-generator"),
            ControlCenterTrafficLightV2("quotes", "Котировки", f"Подтверждено: {quotes}", "OK" if quotes else "WARNING", "/workspace-v2/control-center/edge-oos/execution-edge"),
            ControlCenterTrafficLightV2("live", "LIVE", "Продвижение запрещено", "BLOCKED", "/workspace-v2/control-center/edge-oos/legacy"),
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
        )

    @staticmethod
    def _candidate(row) -> RelationshipCandidateV2:
        sources = row.get("source_symbols") or []
        source = " + ".join(sources) if isinstance(sources, list) else str(sources)
        verdict = str(row.get("verdict_code") or "UNVERIFIED")
        return RelationshipCandidateV2(
            family=FAMILY_NAMES.get(str(row.get("relationship_family")), "Связь"),
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
        )

    @staticmethod
    def _stage(row) -> SignalFunnelStageV2:
        count = int(row.get("stage_count") or 0)
        rate = row.get("pass_rate_pct")
        stage_code = str(row.get("stage_code") or "")
        status = "BLOCKED" if stage_code == "ORDERS" and count == 0 else "OK"
        return SignalFunnelStageV2(
            label=str(row.get("stage_name") or stage_code).replace("_", " "),
            count=count,
            conversion=(f"Конверсия {float(rate):.1f}%" if rate is not None else "Начальная стадия"),
            status=status,
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
            action_target=str(row["action_target"]),
        )
