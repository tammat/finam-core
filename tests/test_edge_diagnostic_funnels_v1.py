from scripts.build_edge_diagnostic_funnels_v1 import _stages


def row(**overrides):
    value={"parameter_json":{"entry_policy_code":"META_ENTRY_V2","exit_policy_code":"DYNAMIC_EXIT_V1"},
           "total_trades":100,"in_sample_passed":True,"stability_passed":True,
           "execution_pass":True,"capacity_pass":True,"portfolio_pass":True,"max_drawdown":-1000,
           "evidence":{"session_breakdown":{"MOEX_MAIN":{"trades":50,"net_expectancy":1,"net_profit_factor":1.2}},
             "exit_reason_breakdown":{"ATR_TRAIL":10},"contract_spec_coverage":1,
             "average_fill_ratio":.9,"execution_policy":{"minimum_fill_ratio":.25,"research_equity_rub":100000,"max_gross_leverage":3},
             "stressed_expectancy":1,"empty_portfolio":True,"capacity_rub":600000}}
    value.update(overrides)
    return value


def test_all_six_funnels_are_monotone_and_pass_complete_evidence():
    for code in ("ENTRY","EXIT","SESSION","EXECUTION","RISK","PORTFOLIO"):
        counts=[count for _,count in _stages([row()],code)]
        assert counts == sorted(counts,reverse=True)
        assert counts[-1] == 1


def test_entry_funnel_identifies_missing_contract_before_trades():
    assert dict(_stages([row(parameter_json={})],"ENTRY")) == {
        "INPUT":1,"CONTRACT":0,"TRADES":0,"GROSS_EDGE":0,
    }
