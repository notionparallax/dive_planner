"""
Pure gas planning logic: cave rule-of-thirds, open-water minimum gas,
switch depth calculation, and orchestration.
"""
from math import floor
from dive_plan import CylinderConfig, SURFACE_PRESSURE


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


def calc_cave_deco_min_gas(steps, cylinder: CylinderConfig,
                            emergency_sac: float = 30.0,
                            contingency: float = 1.0,
                            practical_empty_bar: float = 20.0) -> dict:
    """
    Cave deco gas minimum: 2× the gas used on ascent with this cylinder's gas.

    Deco gases are only used on ascent in cave mode (no penetration portion),
    so the reserve doubles what you need for ascent.
    """
    o2 = cylinder.gas.o2
    he = cylinder.gas.he

    ascent_started = False
    gas_used_litres = 0.0

    for i in range(1, len(steps)):
        prev = steps[i - 1]
        curr = steps[i]
        dt = curr.time - prev.time
        if dt <= 0:
            continue

        if not ascent_started and prev.phase == 'const':
            ascent_started = True

        if not ascent_started:
            continue

        if curr.gas.o2 == o2 and curr.gas.he == he:
            avg_p = (prev.abs_p + curr.abs_p) / 2.0
            ambient_ata = avg_p / SURFACE_PRESSURE
            gas_used_litres += emergency_sac * dt * ambient_ata

    min_litres = gas_used_litres * 2 * contingency
    min_bar = min_litres / cylinder.volume_l
    available_litres = (cylinder.fill_pressure_bar - practical_empty_bar) * cylinder.volume_l
    sufficient = available_litres >= min_litres

    return {
        'min_litres': min_litres,
        'min_bar': min_bar,
        'available_litres': available_litres,
        'sufficient': sufficient,
        'practical_empty': practical_empty_bar,
    }


def calc_ow_min_gas(steps, depth: float, cylinder: CylinderConfig,
                    emergency_sac: float = 30.0,
                    contingency: float = 1.0,
                    practical_empty_bar: float = 20.0) -> dict:
    """
    Open-water minimum gas for a 2-diver back-gas ascent.

    = (1 min problem-solving at max depth + back-gas ascent to first deco switch)
      × 2 divers × emergency_sac
    """
    o2 = cylinder.gas.o2
    he = cylinder.gas.he

    max_p = max(s.abs_p for s in steps)
    problem_solve_one = emergency_sac * 1.0 * (max_p / SURFACE_PRESSURE)

    # Sum back gas from start of ascent to first gas switch
    ascent_started = False
    back_gas_ascent = 0.0
    for i in range(1, len(steps)):
        prev = steps[i - 1]
        curr = steps[i]
        dt = curr.time - prev.time
        if dt <= 0:
            continue

        if not ascent_started and prev.phase == 'const':
            ascent_started = True

        if not ascent_started:
            continue

        if curr.gas.o2 == o2 and curr.gas.he == he:
            avg_p = (prev.abs_p + curr.abs_p) / 2.0
            ambient_ata = avg_p / SURFACE_PRESSURE
            back_gas_ascent += emergency_sac * dt * ambient_ata
        else:
            break  # switched to deco gas

    min_litres = (problem_solve_one + back_gas_ascent) * 2 * contingency
    turn_pressure_bar = min_litres / cylinder.volume_l + practical_empty_bar

    # Bar remaining at start of ascent (gas used on descent + bottom)
    gas_before_ascent = 0.0
    for i in range(1, len(steps)):
        prev = steps[i - 1]
        curr = steps[i]
        dt = curr.time - prev.time
        if dt <= 0:
            continue
        if curr.phase in ('descent', 'const'):
            avg_p = (prev.abs_p + curr.abs_p) / 2.0
            ambient_ata = avg_p / SURFACE_PRESSURE
            gas_before_ascent += emergency_sac * dt * ambient_ata
        else:
            break

    bar_used = gas_before_ascent / cylinder.volume_l
    bar_at_turn = cylinder.fill_pressure_bar - bar_used
    has_enough_gas = bar_at_turn >= turn_pressure_bar
    binding = 'gas_sufficient' if has_enough_gas else 'insufficient_gas'

    return {
        'min_litres': min_litres,
        'turn_pressure_bar': turn_pressure_bar,
        'bar_at_turn': bar_at_turn,
        'has_enough_gas': has_enough_gas,
        'binding': binding,
        'practical_empty': practical_empty_bar,
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


def calc_gas_plan(steps, depth: float, back_cylinder: CylinderConfig,
                  deco_cylinders: list, dive_mode: str = 'open_water',
                  emergency_sac: float = 30.0, contingency: float = 1.0,
                  practical_empty_bar: float = 20.0) -> dict:
    """
    Orchestrate gas planning for all cylinders.

    Returns a dict with back_gas analysis and per-deco-cylinder analysis.
    """
    result = {}

    if dive_mode == 'cave':
        result['back_gas'] = {
            'name': back_cylinder.name,
            'cave_turn': calc_cave_turn_pressure(back_cylinder.fill_pressure_bar, practical_empty_bar),
        }
    else:
        result['back_gas'] = {
            'name': back_cylinder.name,
            'ow_min_gas': calc_ow_min_gas(steps, depth, back_cylinder, emergency_sac, contingency, practical_empty_bar),
        }

    result['deco_gases'] = []
    for cyl in deco_cylinders:
        o2_frac = cyl.gas.o2 / 100.0
        switch_depth = calc_switch_depth(o2_frac) if o2_frac > 0 else None
        deco_info = {
            'name': cyl.name,
            'gas': {'o2': cyl.gas.o2, 'he': cyl.gas.he},
            'switch_depth_m': switch_depth,
        }
        if dive_mode == 'cave':
            deco_info['min_gas'] = calc_cave_deco_min_gas(steps, cyl, emergency_sac, contingency, practical_empty_bar)
        result['deco_gases'].append(deco_info)

    return result
