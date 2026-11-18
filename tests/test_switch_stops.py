"""Minimum stop at gas switches: threaded through run_scenario / find_max_bottom_time."""

import dive_plan


def _stops(gs, **kw):
    r = dive_plan.run_scenario("t", 40, 25, back_gas=(21, 0), gas_switch_time=gs, **kw)
    return dict(r["deco_stops"]), r


def test_switch_stop_appears_in_deco_stops():
    stops, r = _stops(2)
    assert stops[21.0] == 2.0
    assert r["total_deco"] == sum(stops.values())


def test_switch_stop_off():
    stops, _ = _stops(0)
    assert 21.0 not in stops


def test_lost_lean_has_no_21m_switch_stop():
    stops, _ = _stops(2, deco_gases_lost="lean")
    assert 21.0 not in stops


def test_descent_switch_time_threads_through_travel_mode():
    travel = (21, 0, 230, 24.4, 40)  # o2, he, bar, vol, switch depth
    kw = dict(back_gas=(10, 50), travel_gas_config=travel, gas_switch_time=1)
    fly = dive_plan.run_scenario("t", 80, 20, descent_gas_switch_time=0, **kw)
    paused = dive_plan.run_scenario("t", 80, 20, descent_gas_switch_time=3, **kw)
    # Bottom time runs from leaving the surface, so a longer descent pause means less
    # time at 80 m — the plans just have to differ.
    assert paused["total_time"] != fly["total_time"]


def test_auto_bottom_time_accepts_descent_switch_time():
    t = dive_plan.find_max_bottom_time(40, (21, 0), gas_switch_time=2, descent_gas_switch_time=0)
    assert isinstance(t, int) and t > 0
