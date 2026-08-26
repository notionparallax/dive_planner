"""
Bottom time optimiser: binary search over bottom time for fixed gas mixes.
"""
from dive_plan import run_scenario, GasConfig, CylinderConfig
from gas_planning import calc_gas_plan, calc_switch_depth

def check_constraints(scenario, back_cylinder, deco_cyls_with_depths,
                      dive_mode, contingency, practical_empty_bar,
                      max_cns, max_otu, max_runtime):
    """
    Check all constraints for a given scenario.
    Returns (passes: bool, violations: list[str])

    Open-water back-gas sufficiency is read from scenario['min_gas'], which
    run_scenario() already computed via dive_plan.calculate_min_gas_and_turn_from_summary
    (the one place that math is done — not recomputed here).
    """
    violations = []

    if scenario['cns'] > max_cns:
        violations.append(f"CNS {scenario['cns']:.1f}% > limit {max_cns}%")

    if scenario['otu'] > max_otu:
        violations.append(f"OTU {scenario['otu']:.0f} > limit {max_otu}")

    if max_runtime is not None and scenario['total_time'] > max_runtime:
        violations.append(f"Runtime {scenario['total_time']:.1f} min > limit {max_runtime} min")

    if dive_mode == 'cave':
        for cyl_data in scenario.get('cylinders', []):
            if cyl_data.get('name') == back_cylinder.name:
                if cyl_data['remaining_bar'] < practical_empty_bar:
                    violations.append(
                        f"Back gas depleted below practical empty "
                        f"({cyl_data['remaining_bar']:.0f} bar < {practical_empty_bar} bar)"
                    )
    else:
        mg = scenario['min_gas']
        turn_pressure_bar = mg['turn_pressure_bar'] * contingency
        if mg['bar_at_turn'] < turn_pressure_bar:
            violations.append(
                f"Back gas insufficient: need {turn_pressure_bar:.0f} bar at turn, "
                f"have {mg['bar_at_turn']:.0f} bar"
            )

    # Deco gas constraints: check remaining bar >= practical_empty after dive
    for cyl_data in scenario.get('cylinders', []):
        for deco_cyl, _ in deco_cyls_with_depths:
            if cyl_data.get('name') == deco_cyl.name:
                if cyl_data['remaining_bar'] < practical_empty_bar:
                    violations.append(
                        f"{deco_cyl.name} depleted below practical empty "
                        f"({cyl_data['remaining_bar']:.0f} bar < {practical_empty_bar} bar)"
                    )

    return len(violations) == 0, violations


def _bottom_time_kwargs(dive_mode, gf_low, gf_high, sac_bottom, sac_deco, sac_emergency,
                        contingency, practical_empty_bar, max_cns, max_otu, max_runtime,
                        min_bottom_time, max_bottom_time):
    """Bundle the constraint/rate params shared by every optimise_bottom_time() call within
    one higher-level search (optimise_deco_gas / optimise_both_deco_gases / optimise_gas_mix),
    so each call site passes **kwargs instead of repeating the same ~13 arguments."""
    return dict(
        dive_mode=dive_mode, gf_low=gf_low, gf_high=gf_high,
        sac_bottom=sac_bottom, sac_deco=sac_deco, sac_emergency=sac_emergency,
        contingency=contingency, practical_empty_bar=practical_empty_bar,
        max_cns=max_cns, max_otu=max_otu, max_runtime=max_runtime,
        min_bottom_time=min_bottom_time, max_bottom_time=max_bottom_time,
    )


def optimise_bottom_time(
    depth: float,
    back_cylinder: CylinderConfig,
    deco_cyls_with_depths: list,   # list of (CylinderConfig, switch_depth_m)
    dive_mode: str = 'open_water',
    gf_low: float = 0.50,
    gf_high: float = 0.70,
    sac_bottom: float = 20.0,
    sac_deco: float = 15.0,
    sac_emergency: float = 30.0,
    contingency: float = 1.0,
    practical_empty_bar: float = 20.0,
    max_cns: float = 80.0,
    max_otu: float = 300.0,
    max_runtime: float = None,
    min_bottom_time: int = 1,
    max_bottom_time: int = 180,
    descent_rate: float = 20.0,
) -> dict:
    """
    Binary search for maximum bottom time satisfying all constraints.

    Returns a dict with:
      max_bottom_time: int — the maximum passing bottom time (minutes)
      binding_constraints: list[str] — constraints that fail at max_bottom_time + 1
      scenario: dict — full run_scenario result for the optimal bottom time
      gas_plan: dict — gas plan for the optimal bottom time
      steps_checked: int — number of deco calculations performed
    """
    cfg = {
        'back_cylinder': back_cylinder,
        'deco_cylinders': deco_cyls_with_depths,
        'gf_low': gf_low,
        'gf_high': gf_high,
        'sac_bottom': sac_bottom,
        'sac_deco': sac_deco,
        'descent_rate': descent_rate,
    }

    import math
    # Ensure min_bottom_time is at least the descent time + 1 to avoid engine error
    min_viable_bt = max(min_bottom_time, math.ceil(depth / descent_rate) + 1)

    def evaluate(bt):
        try:
            scenario = run_scenario("opt", depth, bt, deco_gases_lost=False, cfg=cfg,
                                    emergency_sac=sac_emergency)
        except Exception as exc:
            return False, [f"Calculation failed: {exc}"], None
        passes, violations = check_constraints(
            scenario, back_cylinder, deco_cyls_with_depths,
            dive_mode, contingency, practical_empty_bar,
            max_cns, max_otu, max_runtime,
        )
        return passes, violations, scenario

    steps_checked = 0

    # First check if min_viable_bt even passes
    passes, violations, scenario = evaluate(min_viable_bt)
    steps_checked += 1
    if not passes:
        return {
            'max_bottom_time': 0,
            'binding_constraints': violations,
            'scenario': None,
            'gas_plan': None,
            'steps_checked': steps_checked,
            'feasible': False,
        }

    # Binary search
    lo, hi = min_viable_bt, max_bottom_time
    best_bt = min_viable_bt
    best_scenario = scenario

    while lo <= hi:
        mid = (lo + hi) // 2
        passes, violations, scenario = evaluate(mid)
        steps_checked += 1
        if passes:
            best_bt = mid
            best_scenario = scenario
            lo = mid + 1
        else:
            hi = mid - 1

    # Get violations at best_bt + 1 to show binding constraints
    if best_bt < max_bottom_time:
        _, binding, _ = evaluate(best_bt + 1)
        steps_checked += 1
    else:
        binding = ['Search limit reached (max_bottom_time)']

    gas_plan = calc_gas_plan(
        best_scenario['min_gas'], back_cylinder, deco_cyls_with_depths,
        dive_mode=dive_mode,
        contingency=contingency,
        practical_empty_bar=practical_empty_bar,
    )

    return {
        'max_bottom_time': best_bt,
        'binding_constraints': binding,
        'scenario': best_scenario,
        'gas_plan': gas_plan,
        'steps_checked': steps_checked,
        'feasible': True,
    }


def optimise_deco_gas(
    depth: float,
    back_cylinder: CylinderConfig,
    deco1_volume_l: float,
    deco1_fill_bar: int,
    deco2_cylinder: CylinderConfig,      # fixed deco gas 2
    deco2_switch_depth_m: int,
    dive_mode: str = 'open_water',
    gf_low: float = 0.50,
    gf_high: float = 0.70,
    sac_bottom: float = 20.0,
    sac_deco: float = 15.0,
    sac_emergency: float = 30.0,
    contingency: float = 1.0,
    practical_empty_bar: float = 20.0,
    max_cns: float = 80.0,
    max_otu: float = 300.0,
    max_runtime: float = None,
    min_bottom_time: int = 1,
    max_bottom_time: int = 180,
    max_ppo2_deco: float = 1.6,
    deco1_o2_min: int = 21,
    deco1_o2_max: int = 80,
    deco1_o2_step: int = 5,
) -> dict:
    """
    Search over deco gas 1 O2% to maximise bottom time.

    For each candidate O2% for deco gas 1:
    - Calculate switch depth from ppO2 limit
    - Skip if switch depth < 9m (would overlap with deco2 territory)
    - Run optimise_bottom_time with [deco1, deco2] gas list
    - Record result

    Returns:
      best_deco1_o2: int
      best_deco1_switch_depth: float
      best_bottom_time: int
      all_results: list sorted by bottom time desc
      best_result: full optimise_bottom_time() result
      total_steps_checked: int
      mixes_evaluated: int
    """
    bt_kwargs = _bottom_time_kwargs(
        dive_mode, gf_low, gf_high, sac_bottom, sac_deco, sac_emergency,
        contingency, practical_empty_bar, max_cns, max_otu, max_runtime,
        min_bottom_time, max_bottom_time,
    )

    all_results = []
    total_steps_checked = 0

    for o2_pct in range(deco1_o2_min, min(deco1_o2_max, 100) + 1, deco1_o2_step):
        switch_depth = calc_switch_depth(o2_pct / 100.0, max_ppo2_deco)
        # Skip if switch depth would be at or shallower than deco2 (no point)
        if switch_depth <= deco2_switch_depth_m:
            continue
        # Also skip if switch depth is deeper than half the bottom depth
        # (wouldn't be useful as a deco gas)
        if switch_depth > depth * 0.8:
            continue

        deco1_cyl = CylinderConfig(
            GasConfig(o2_pct, 0),
            deco1_volume_l,
            deco1_fill_bar,
            f"Deco 1 (EAN{o2_pct})",
        )
        deco_cyls = [(deco1_cyl, int(switch_depth))]
        if deco2_cylinder is not None:
            deco_cyls.append((deco2_cylinder, deco2_switch_depth_m))

        result = optimise_bottom_time(
            depth=depth,
            back_cylinder=back_cylinder,
            deco_cyls_with_depths=deco_cyls,
            **bt_kwargs,
        )
        total_steps_checked += result['steps_checked']

        sc = result.get('scenario') or {}
        all_results.append({
            'deco1_o2': o2_pct,
            'deco1_switch_depth': switch_depth,
            'max_bottom_time': result['max_bottom_time'],
            'feasible': result['feasible'],
            'binding_constraints': result['binding_constraints'],
            'total_deco': sc.get('total_deco'),
            'total_time': sc.get('total_time'),
            'cns': sc.get('cns'),
            'otu': sc.get('otu'),
        })

    # Sort by bottom time desc, then switch depth desc (richer gas = shallower switch = better)
    all_results.sort(key=lambda r: (r['max_bottom_time'], r['deco1_switch_depth']), reverse=True)

    best = all_results[0] if all_results else None
    best_result = None

    if best and best['feasible']:
        best_deco1_cyl = CylinderConfig(
            GasConfig(best['deco1_o2'], 0),
            deco1_volume_l,
            deco1_fill_bar,
            f"Deco 1 (EAN{best['deco1_o2']})",
        )
        deco_cyls = [(best_deco1_cyl, int(best['deco1_switch_depth']))]
        if deco2_cylinder is not None:
            deco_cyls.append((deco2_cylinder, deco2_switch_depth_m))
        best_result = optimise_bottom_time(
            depth=depth,
            back_cylinder=back_cylinder,
            deco_cyls_with_depths=deco_cyls,
            **bt_kwargs,
        )
        total_steps_checked += best_result['steps_checked']

    return {
        'best_deco1_o2': best['deco1_o2'] if best else None,
        'best_deco1_switch_depth': best['deco1_switch_depth'] if best else None,
        'best_bottom_time': best['max_bottom_time'] if best else 0,
        'all_results': all_results,
        'best_result': best_result,
        'total_steps_checked': total_steps_checked,
        'mixes_evaluated': len(all_results),
    }


def optimise_both_deco_gases(
    depth: float,
    back_cylinder: CylinderConfig,
    deco1_volume_l: float,
    deco1_fill_bar: int,
    deco2_volume_l: float,
    deco2_fill_bar: int,
    dive_mode: str = 'open_water',
    gf_low: float = 0.50,
    gf_high: float = 0.70,
    sac_bottom: float = 20.0,
    sac_deco: float = 15.0,
    sac_emergency: float = 30.0,
    contingency: float = 1.0,
    practical_empty_bar: float = 20.0,
    max_cns: float = 80.0,
    max_otu: float = 300.0,
    max_runtime: float = None,
    min_bottom_time: int = 1,
    max_bottom_time: int = 180,
    max_ppo2_deco: float = 1.6,
    deco1_o2_min: int = 21,
    deco1_o2_max: int = 80,
    deco2_o2_min: int = 50,
    deco2_o2_max: int = 100,
    refinement_steps: tuple = (20, 10, 5),
) -> dict:
    """
    Coarse-to-fine grid search over both deco gas O2% values to maximise bottom time.

    At each pass the search grid narrows around the current best candidate.
    Constraint: deco1 switch depth must be deeper than deco2 switch depth.

    Returns:
      best_deco1_o2, best_deco1_switch_depth
      best_deco2_o2, best_deco2_switch_depth
      best_bottom_time
      all_results: all evaluated pairs sorted by bottom time desc
      best_result: full optimise_bottom_time() result for the winner
      total_steps_checked, mixes_evaluated
    """
    bt_kwargs = _bottom_time_kwargs(
        dive_mode, gf_low, gf_high, sac_bottom, sac_deco, sac_emergency,
        contingency, practical_empty_bar, max_cns, max_otu, max_runtime,
        min_bottom_time, max_bottom_time,
    )

    evaluated = {}   # (d1_o2, d2_o2) -> result record or None
    total_steps_checked = 0
    best_d1, best_d2, best_bt = None, None, -1

    def _eval_pair(d1_o2, d2_o2):
        nonlocal total_steps_checked, best_bt, best_d1, best_d2
        key = (d1_o2, d2_o2)
        if key in evaluated:
            return evaluated[key]

        sd1 = calc_switch_depth(d1_o2 / 100.0, max_ppo2_deco)
        sd2 = calc_switch_depth(d2_o2 / 100.0, max_ppo2_deco)

        # deco1 must switch deeper than deco2; deco1 switch must be useful (not near bottom)
        if sd1 <= sd2 or sd1 > depth * 0.8:
            evaluated[key] = None
            return None

        d2_label = "Deco 2 (O2)" if d2_o2 == 100 else f"Deco 2 (EAN{d2_o2})"
        deco_cyls = [
            (CylinderConfig(GasConfig(d1_o2, 0), deco1_volume_l, deco1_fill_bar, f"Deco 1 (EAN{d1_o2})"), int(sd1)),
            (CylinderConfig(GasConfig(d2_o2, 0), deco2_volume_l, deco2_fill_bar, d2_label), int(sd2)),
        ]

        result = optimise_bottom_time(
            depth=depth, back_cylinder=back_cylinder,
            deco_cyls_with_depths=deco_cyls,
            **bt_kwargs,
        )
        total_steps_checked += result['steps_checked']

        sc = result.get('scenario') or {}
        record = {
            'deco1_o2': d1_o2,
            'deco1_switch_depth': sd1,
            'deco2_o2': d2_o2,
            'deco2_switch_depth': sd2,
            'max_bottom_time': result['max_bottom_time'],
            'feasible': result['feasible'],
            'binding_constraints': result['binding_constraints'],
            'total_deco': sc.get('total_deco'),
            'total_time': sc.get('total_time'),
            'cns': sc.get('cns'),
            'otu': sc.get('otu'),
        }
        evaluated[key] = record

        if result['max_bottom_time'] > best_bt:
            best_bt = result['max_bottom_time']
            best_d1, best_d2 = d1_o2, d2_o2

        return record

    for pass_idx, step in enumerate(refinement_steps):
        if pass_idx == 0:
            d1_lo, d1_hi = deco1_o2_min, deco1_o2_max
            d2_lo, d2_hi = deco2_o2_min, deco2_o2_max
        else:
            prev = refinement_steps[pass_idx - 1]
            d1_lo = max(deco1_o2_min, best_d1 - prev)
            d1_hi = min(deco1_o2_max, best_d1 + prev)
            d2_lo = max(deco2_o2_min, best_d2 - prev)
            d2_hi = min(deco2_o2_max, best_d2 + prev)

        for d1 in range(d1_lo, d1_hi + 1, step):
            for d2 in range(d2_lo, d2_hi + 1, step):
                _eval_pair(d1, d2)

    all_results = sorted(
        [r for r in evaluated.values() if r is not None],
        key=lambda r: (r['max_bottom_time'], r['deco2_switch_depth']),
        reverse=True,
    )

    best = all_results[0] if all_results else None
    best_result = None

    if best and best['feasible']:
        d2_label = "Deco 2 (O2)" if best['deco2_o2'] == 100 else f"Deco 2 (EAN{best['deco2_o2']})"
        deco_cyls = [
            (CylinderConfig(GasConfig(best['deco1_o2'], 0), deco1_volume_l, deco1_fill_bar, f"Deco 1 (EAN{best['deco1_o2']})"), int(best['deco1_switch_depth'])),
            (CylinderConfig(GasConfig(best['deco2_o2'], 0), deco2_volume_l, deco2_fill_bar, d2_label), int(best['deco2_switch_depth'])),
        ]
        best_result = optimise_bottom_time(
            depth=depth, back_cylinder=back_cylinder,
            deco_cyls_with_depths=deco_cyls,
            **bt_kwargs,
        )
        total_steps_checked += best_result['steps_checked']

    return {
        'best_deco1_o2': best['deco1_o2'] if best else None,
        'best_deco1_switch_depth': best['deco1_switch_depth'] if best else None,
        'best_deco2_o2': best['deco2_o2'] if best else None,
        'best_deco2_switch_depth': best['deco2_switch_depth'] if best else None,
        'best_bottom_time': best['max_bottom_time'] if best else 0,
        'all_results': all_results,
        'best_result': best_result,
        'total_steps_checked': total_steps_checked,
        'mixes_evaluated': len(all_results),
    }


def optimise_gas_mix(
    depth: float,
    back_cylinder_volume_l: float,
    back_cylinder_fill_bar: int,
    deco_cyls_with_depths: list,   # list of (CylinderConfig, switch_depth_m)
    dive_mode: str = 'open_water',
    gf_low: float = 0.50,
    gf_high: float = 0.70,
    sac_bottom: float = 20.0,
    sac_deco: float = 15.0,
    sac_emergency: float = 30.0,
    contingency: float = 1.0,
    practical_empty_bar: float = 20.0,
    max_cns: float = 80.0,
    max_otu: float = 300.0,
    max_runtime: float = None,
    min_bottom_time: int = 1,
    max_bottom_time: int = 180,
    max_ppo2_bottom: float = 1.4,
    he_step: int = 5,
) -> dict:
    """
    Grid search over back gas He% to maximise bottom time.

    O2% is fixed at the maximum allowed by the ppO2 limit at depth.
    He% is varied from 0 to (100 - o2_pct) in steps of `he_step`.

    Returns:
      best_o2: int
      best_he: int
      best_bottom_time: int
      all_results: list of {o2, he, max_bottom_time, feasible, binding_constraints}
      best_result: full optimise_bottom_time() result for the best mix
      total_steps_checked: int
    """
    import math

    abs_pressure = depth / 10.0 + 1.0
    # Maximum O2% that keeps ppO2 at or below limit at this depth
    max_o2_pct = int(max_ppo2_bottom / abs_pressure * 100)
    # Clamp to valid range
    max_o2_pct = max(18, min(max_o2_pct, 40))  # don't go below 18% or above 40% for back gas

    candidates = []
    for he in range(0, 100 - max_o2_pct + 1, he_step):
        # N2 = 100 - o2 - he; require at least 0% N2
        if max_o2_pct + he > 100:
            break
        candidates.append((max_o2_pct, he))

    bt_kwargs = _bottom_time_kwargs(
        dive_mode, gf_low, gf_high, sac_bottom, sac_deco, sac_emergency,
        contingency, practical_empty_bar, max_cns, max_otu, max_runtime,
        min_bottom_time, max_bottom_time,
    )

    all_results = []
    total_steps_checked = 0

    for o2_pct, he_pct in candidates:
        back_cyl = CylinderConfig(
            GasConfig(o2_pct, he_pct),
            back_cylinder_volume_l,
            back_cylinder_fill_bar,
            f"Back Gas ({o2_pct}/{he_pct})",
        )
        result = optimise_bottom_time(
            depth=depth,
            back_cylinder=back_cyl,
            deco_cyls_with_depths=deco_cyls_with_depths,
            **bt_kwargs,
        )
        total_steps_checked += result['steps_checked']
        all_results.append({
            'o2': o2_pct,
            'he': he_pct,
            'n2': 100 - o2_pct - he_pct,
            'max_bottom_time': result['max_bottom_time'],
            'feasible': result['feasible'],
            'binding_constraints': result['binding_constraints'],
            'total_deco': result['scenario'].get('total_deco') if result.get('scenario') else None,
            'cns': result['scenario'].get('cns') if result.get('scenario') else None,
            'otu': result['scenario'].get('otu') if result.get('scenario') else None,
        })

    # Sort by max_bottom_time descending; for ties prefer more He (less narcosis)
    all_results.sort(key=lambda r: (r['max_bottom_time'], r['he']), reverse=True)

    best = all_results[0] if all_results else None
    best_full_result = None

    if best and best['feasible']:
        best_cyl = CylinderConfig(
            GasConfig(best['o2'], best['he']),
            back_cylinder_volume_l,
            back_cylinder_fill_bar,
            f"Back Gas ({best['o2']}/{best['he']})",
        )
        best_full_result = optimise_bottom_time(
            depth=depth,
            back_cylinder=best_cyl,
            deco_cyls_with_depths=deco_cyls_with_depths,
            **bt_kwargs,
        )
        total_steps_checked += best_full_result['steps_checked']

    return {
        'best_o2': best['o2'] if best else None,
        'best_he': best['he'] if best else None,
        'best_bottom_time': best['max_bottom_time'] if best else 0,
        'all_results': all_results,
        'best_result': best_full_result,
        'total_steps_checked': total_steps_checked,
        'mixes_evaluated': len(candidates),
        'abs_pressure': abs_pressure,
    }
