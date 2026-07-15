from marketcore.presentation.framework.registry import UiStatusCode
from marketcore.presentation.workspace_v2.presenter.home_v2_presenter import HomeV2Presenter


def test_verified_profit_metric_is_green_but_unverified_decision_is_not() -> None:
    presenter = HomeV2Presenter()
    metric = presenter._profit_card("expected", "title", "0", UiStatusCode.WARNING, 1, "VERIFIED")
    decision = presenter._profit_card("decision", "title", "none", UiStatusCode.WARNING, 1, "NO_VERIFIED_KPI")
    assert metric.status_code == UiStatusCode.OK
    assert decision.status_code == UiStatusCode.WARNING


def test_data_readiness_has_explicit_fallback() -> None:
    assert HomeV2Presenter._operating_status().get("data_ready") in (True, False)
