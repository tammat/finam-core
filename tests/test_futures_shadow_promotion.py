from finam_core.analytics.futures_shadow_promotion import simulate_shadow,promotion_decision

def test_stop_wins_same_bar():
    out=simulate_shadow(entry_price=100,side='LONG',atr=2,stop_atr=1,take_atr=2,bars=[(105,97,101)])
    assert out.exit_reason=='STOP' and out.net_r==-1

def test_short_take():
    out=simulate_shadow(entry_price=100,side='SHORT',atr=2,stop_atr=1,take_atr=2,bars=[(101,95,96)])
    assert out.exit_reason=='TAKE' and out.net_r==2

def test_promotion_guards():
    assert not promotion_decision([0]*79,[1]*79,oos_size=20)['promote']
    result=promotion_decision([-0.2,0.1]*40,[0.2]*80,oos_size=20)
    assert result['promote']
