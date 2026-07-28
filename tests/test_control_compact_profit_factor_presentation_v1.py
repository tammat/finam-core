from marketcore.presentation.workspace_v2.renderer.control_compact_v3_domain_renderer import (
    _profit_factor_ru,
)


def test_profit_factor_sentinel_is_not_presented_as_real_metric():
    assert _profit_factor_ru(999, 1) == "PF — · недостаточно данных"
    assert _profit_factor_ru(999, 2) == "PF — · нет убыточных сделок"


def test_profit_factor_is_numeric_only_with_observed_losses():
    assert _profit_factor_ru(2.54, 2) == "PF 2.54"
    assert _profit_factor_ru(None, 10) == "PF — · недостаточно данных"
