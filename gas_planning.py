"""
Pure gas planning logic: cave rule-of-thirds, switch depth calculation, and orchestration.

Open-water minimum gas is NOT computed here — that math lives in a single place,
dive_plan.calculate_min_gas_and_turn_from_summary(), which calc_gas_plan() below just
reports. An earlier version of this module recomputed it independently from a per-step
dive trace ('steps') that decodaitengu's plan_dive() has never actually produced, so that
code path was permanently a no-op; see calc_gas_plan()'s docstring.
"""
from math import floor
from dive_plan import CylinderConfig


def calc_cave_turn_pressure(fill_pressure_bar: float,
                            practical_empty_bar: float = 20.0) -> dict:
    """
    Cave rule-of-thirds turn pressure.

    e.g. fill=210, practical_empty=20 → usable=190, rounded=180, third=60, turn=150
    """
    fill = fill_pressure_bar
    usable = fill - practical_empty_bar
    rounded_usable = floor(usable / 30) * 30
    third = rounded_usable / 3
    turn_pressure = fill - third
    return {
        'fill': fill,
        'practical_empty': practical_empty_bar,
        'usable': usable,
        'rounded_usable': rounded_usable,
        'third': third,
        'turn_pressure': turn_pressure,
    }


def calc_switch_depth(o2_frac: float, max_ppo2: float = 1.6, surface_pressure: float = 1.01325) -> int:
    """MOD in whole metres: deepest depth where this gas stays at or below max_ppo2.

    Uses real surface pressure (1.01325 bar) so EAN50 correctly gives 21m, not 22m.
    Pure O2 is clamped to minimum 6m — the accepted community convention
    (ppO2 ≈ 1.61 bar at 6m is universally accepted for O2 deco stops).
    """
    import math
    depth_m = (max_ppo2 / o2_frac - surface_pressure) * 10
    result = math.floor(depth_m)
    if o2_frac >= 0.99:  # pure O2: community convention is 6m switch
        result = max(result, 6)
    return result


def calc_gas_plan(min_gas: dict, back_cylinder: CylinderConfig,
                  deco_cylinders_with_depths: list, dive_mode: str = 'open_water',
                  contingency: float = 1.0,
                  practical_empty_bar: float = 20.0) -> dict:
    """
    Orchestrate gas plan reporting for the back gas and deco gases.

    min_gas: the dict already returned by run_scenario()['min_gas'] (computed by
        dive_plan.calculate_min_gas_and_turn_from_summary) for this exact dive — the
        one place that math is done. Not recomputed here.
    deco_cylinders_with_depths: list of (CylinderConfig, switch_depth_m) — the switch
        depths actually used to plan the dive, not re-derived from ppO2.
    contingency: multiplier applied on top of the reported open-water min gas
        (e.g. 1.1-1.5x margin). Cave mode's rule-of-thirds turn pressure has no
        equivalent contingency knob.

    Cave-mode deco-gas minimum gas is not reported: it would need a per-depth
    ascent gas-usage breakdown that decodaitengu's DiveSummary doesn't expose
    (there is no 'steps' trace — only aggregate profile/gas_usage). Only the
    deco gas's switch depth is reported for cave mode.
    """
    result = {}

    if dive_mode == 'cave':
        result['back_gas'] = {
            'name': back_cylinder.name,
            'cave_turn': calc_cave_turn_pressure(back_cylinder.fill_pressure_bar, practical_empty_bar),
        }
    else:
        min_litres = min_gas['min_gas_litres'] * contingency
        turn_pressure_bar = min_gas['turn_pressure_bar'] * contingency
        result['back_gas'] = {
            'name': back_cylinder.name,
            'ow_min_gas': {
                'min_litres': min_litres,
                'turn_pressure_bar': turn_pressure_bar,
                'bar_at_turn': min_gas['bar_at_turn'],
                'has_enough_gas': min_gas['bar_at_turn'] >= turn_pressure_bar,
                'practical_empty': practical_empty_bar,
            },
        }

    result['deco_gases'] = [
        {
            'name': cyl.name,
            'gas': {'o2': cyl.gas.o2, 'he': cyl.gas.he},
            'switch_depth_m': sd,
        }
        for cyl, sd in deco_cylinders_with_depths
    ]

    return result
