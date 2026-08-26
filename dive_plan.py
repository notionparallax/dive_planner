"""
Dive planner using decotengu for Bühlmann ZHL-16C-GF decompression calculations.
"""
from decodaitengu.planning import plan_dive as _plan_dive
from decodaitengu.types import Gas as _Gas, Cylinder as _Cylinder
from dataclasses import dataclass


# === Dataclasses ===

@dataclass
class GasConfig:
    o2: int
    he: int


@dataclass
class CylinderConfig:
    gas: GasConfig
    volume_l: float
    fill_pressure_bar: int
    name: str


# === Configuration ===
GF_LOW = 0.50
GF_HIGH = 0.70  # changed from 0.80
DESCENT_RATE = 20  # m/min
ASCENT_RATE = 10   # m/min
SAC_BOTTOM = 20    # L/min at surface
SAC_DECO = 17      # L/min at surface
SURFACE_PRESSURE = 1.01325  # bar
WATER_TEMP_C = 18  # degrees C (working temperature)
FILL_TEMP_C = 40   # degrees C (tank temperature after filling)

# Cylinders (legacy constants)
BACK_GAS_VOL = 24.4   # litres
BACK_GAS_PRESSURE = 210  # bar
BACK_GAS_AVAILABLE = BACK_GAS_VOL * BACK_GAS_PRESSURE

DECO_O2_VOL = 11.1    # litres
DECO_O2_PRESSURE = 200  # bar
DECO_O2_AVAILABLE = DECO_O2_VOL * DECO_O2_PRESSURE

DECO_50_VOL = 11.1    # litres
DECO_50_PRESSURE = 200  # bar
DECO_50_AVAILABLE = DECO_50_VOL * DECO_50_PRESSURE

# Gas mixes (legacy tuples)
BACK_GAS = (22, 27)   # O2%, He% - Trimix 22/27
DECO_50 = (50, 0)     # EAN50
DECO_O2 = (100, 0)    # Pure O2

# Default switch depths
_DECO_50_SWITCH_DEPTH = 21
_DECO_O2_SWITCH_DEPTH = 6

# Cylinder dataclass instances
BACK_GAS_CYLINDER = CylinderConfig(GasConfig(23, 25), 24.4, 210, "Back Gas")
DECO_50_CYLINDER = CylinderConfig(GasConfig(50, 0), 11.1, 150, "EAN50")
DECO_O2_CYLINDER = CylinderConfig(GasConfig(100, 0), 11.1, 150, "O2")


def run_profile(depth, bottom_time, deco_gases_lost=False,
               back_gas=None, deco_cylinders_config=None,
               gf_low=None, gf_high=None,
               descent_rate=None, ascent_rate=None,
               sac_bottom=None, sac_deco=None,
               back_gas_pressure=None, deco_50_pressure=None, deco_o2_pressure=None,
               back_gas_vol=None, deco_50_vol=None, deco_o2_vol=None,
               lean_gas=None, lean_switch=None, lean_enabled=True,
               rich_gas=None, rich_switch=None, rich_enabled=True,
               descent_stops=None,
               travel_gas_config=None,
               gas_switch_time=None):
    """Run a decompression calculation and return a DiveSummary.

    Args:
        deco_cylinders_config: list of (o2, he, switch_depth_m) tuples.
                               When provided, deco_gases_lost is ignored.
        back_gas: (o2, he) tuple; defaults to BACK_GAS_CYLINDER gas.
        descent_stops: list of (depth_m, time_min) stops during descent (e.g. S-drills).
    """
    _gf_low = gf_low if gf_low is not None else GF_LOW
    _gf_high = gf_high if gf_high is not None else GF_HIGH
    _descent_rate = descent_rate if descent_rate is not None else DESCENT_RATE
    _ascent_rate = ascent_rate if ascent_rate is not None else ASCENT_RATE
    _back_gas = back_gas if back_gas is not None else (BACK_GAS_CYLINDER.gas.o2, BACK_GAS_CYLINDER.gas.he)
    _sac_bottom = sac_bottom if sac_bottom is not None else SAC_BOTTOM
    _sac_deco = sac_deco if sac_deco is not None else SAC_DECO
    _back_gas_pressure = back_gas_pressure if back_gas_pressure is not None else BACK_GAS_PRESSURE
    _deco_50_pressure = deco_50_pressure if deco_50_pressure is not None else DECO_50_PRESSURE
    _deco_o2_pressure = deco_o2_pressure if deco_o2_pressure is not None else DECO_O2_PRESSURE
    _back_gas_vol = back_gas_vol if back_gas_vol is not None else BACK_GAS_VOL
    _deco_50_vol = deco_50_vol if deco_50_vol is not None else DECO_50_VOL
    _deco_o2_vol = deco_o2_vol if deco_o2_vol is not None else DECO_O2_VOL
    _lean_gas = lean_gas if lean_gas is not None else (50, 0)
    _lean_switch = lean_switch if lean_switch is not None else _DECO_50_SWITCH_DEPTH
    _rich_gas = rich_gas if rich_gas is not None else (100, 0)
    _rich_switch = rich_switch if rich_switch is not None else _DECO_O2_SWITCH_DEPTH
    _gas_switch_time = gas_switch_time if gas_switch_time is not None else 1.0

    _h2 = int(_back_gas[2]) if len(_back_gas) > 2 else 0
    back_gas_obj = _Gas(
        o2=_back_gas[0], he=_back_gas[1], h2=_h2,
        switch_depth=float(depth), use_on_descent=True, label='back',
    )
    back_cyl_obj = _Cylinder(volume_litres=_back_gas_vol, fill_bar=_back_gas_pressure)

    if deco_cylinders_config is not None:
        _deco_gases_raw = deco_cylinders_config
        deco_gas_objs = []
        deco_cyl_objs = []
        for idx, (o2, he, sd) in enumerate(_deco_gases_raw):
            if float(sd) >= depth:
                continue
            if idx == 0:
                label = 'lean'
                vol = _deco_50_vol
                pressure = _deco_50_pressure
            else:
                label = 'rich'
                vol = _deco_o2_vol
                pressure = _deco_o2_pressure
            deco_gas_objs.append(_Gas(o2=o2, he=he, switch_depth=float(sd), label=label))
            deco_cyl_objs.append(_Cylinder(volume_litres=vol, fill_bar=pressure))
    else:
        _lost_list = deco_gases_lost if isinstance(deco_gases_lost, list) else []
        def _is_lost(role):
            return deco_gases_lost is True or deco_gases_lost == role or role in _lost_list

        _deco_gases_tagged = []
        if lean_enabled and not _is_lost('lean'):
            _deco_gases_tagged.append(('lean', *_lean_gas, _lean_switch))
        if rich_enabled and not _is_lost('rich'):
            _deco_gases_tagged.append(('rich', *_rich_gas, _rich_switch))

        deco_gas_objs = []
        deco_cyl_objs = []
        for (role, o2, he, sd) in _deco_gases_tagged:
            if float(sd) >= depth:
                continue
            if role == 'lean':
                label = 'lean'
                vol = _deco_50_vol
                pressure = _deco_50_pressure
            else:
                label = 'rich'
                vol = _deco_o2_vol
                pressure = _deco_o2_pressure
            deco_gas_objs.append(_Gas(o2=o2, he=he, switch_depth=float(sd), label=label))
            deco_cyl_objs.append(_Cylinder(volume_litres=vol, fill_bar=pressure))

    # Travel gas (descent-only): unified API — use_on_descent=True, use_on_ascent=False
    _tv_config = travel_gas_config  # (o2, he, bar, vol, switch_depth) or None
    if _tv_config is not None:
        tv_o2, tv_he, tv_bar, tv_vol, tv_switch = _tv_config
        travel_gas_obj = _Gas(
            o2=tv_o2, he=tv_he,
            switch_depth=float(tv_switch),
            use_on_descent=True, use_on_ascent=False,
            label='travel',
        )
        travel_cyl_obj = _Cylinder(volume_litres=tv_vol, fill_bar=tv_bar)
        all_gas_objs = [travel_gas_obj, back_gas_obj] + deco_gas_objs
        all_cyl_objs = [travel_cyl_obj, back_cyl_obj] + deco_cyl_objs
    else:
        all_gas_objs = [back_gas_obj] + deco_gas_objs
        all_cyl_objs = [back_cyl_obj] + deco_cyl_objs

    return _plan_dive(
        depth=depth,
        bottom_time=bottom_time,
        gases=all_gas_objs,
        cylinders=all_cyl_objs,
        gf=(_gf_low * 100, _gf_high * 100),
        descent_rate=_descent_rate,
        ascent_rate=_ascent_rate,
        sac_bottom=_sac_bottom,
        sac_deco=_sac_deco,
        descent_stops=descent_stops,
        gas_switch_time=_gas_switch_time,
    )


def calculate_min_gas_and_turn_from_summary(summary, back_gas_pressure, back_gas_vol=None,
                                             sac_bottom=None, emergency_sac=None):
    """Calculate minimum gas (2 divers ascending on back gas) and turn pressure from DiveSummary.

    This is the single source of truth for open-water minimum-gas / turn-pressure math —
    both the Streamlit app (via run_scenario) and the API/optimiser (via calc_gas_plan)
    read the 'min_gas' dict this produces rather than recomputing it themselves.

    Args:
        summary: DiveSummary from run_profile().
        back_gas_pressure: Fill pressure of back gas cylinder [bar].
        back_gas_vol: Volume of back gas cylinder [L]. Defaults to BACK_GAS_VOL.
        sac_bottom: SAC the dive was planned at [L/min]. Defaults to SAC_BOTTOM.
        emergency_sac: Stressed/out-of-gas SAC rate to use for the min-gas safety margin
            [L/min]. Defaults to sac_bottom (i.e. no stress multiplier) — pass e.g. 30 to
            model an elevated emergency breathing rate on top of the planned dive.
    """
    _back_gas_vol = back_gas_vol if back_gas_vol is not None else BACK_GAS_VOL
    _sac_bottom = sac_bottom if sac_bottom is not None else SAC_BOTTOM
    _emergency_sac = emergency_sac if emergency_sac is not None else _sac_bottom

    depth = summary.max_depth
    abs_p_bottom = SURFACE_PRESSURE + depth / 10.0

    # Gas used during descent + bottom (before ascent starts).
    # Find profile points at max_depth (not hardcoded indices, which break with S-drill stops).
    max_d = summary.max_depth
    bottom_pts = [(t, d) for t, d in summary.profile if abs(d - max_d) < 0.1]
    if len(bottom_pts) >= 2:
        descent_time = bottom_pts[0][0]
        bottom_leave_time = bottom_pts[1][0]
        bottom_duration = bottom_leave_time - descent_time
    elif len(bottom_pts) == 1:
        descent_time = bottom_pts[0][0]
        bottom_duration = 0.0
    else:
        descent_time = depth / DESCENT_RATE
        bottom_duration = 0.0

    avg_descent_p = (SURFACE_PRESSURE + abs_p_bottom) / 2.0
    gas_descent = _sac_bottom * descent_time * avg_descent_p / SURFACE_PRESSURE
    gas_bottom = _sac_bottom * bottom_duration * abs_p_bottom / SURFACE_PRESSURE
    gas_used_before_ascent = gas_descent + gas_bottom
    bar_used_before_ascent = gas_used_before_ascent / _back_gas_vol
    bar_at_turn = back_gas_pressure - bar_used_before_ascent

    # Min gas = (1 min problem-solving at depth + ascent back gas) x 2 divers, at the
    # emergency SAC rate. back_gas_ascent_litres was computed at the planned sac_bottom,
    # so scale it linearly to the emergency rate rather than re-running the dive.
    stress_factor = _emergency_sac / _sac_bottom
    ascent_back_gas_one = summary.back_gas_ascent_litres * stress_factor
    problem_solve_one = _emergency_sac * 1.0 * abs_p_bottom / SURFACE_PRESSURE
    min_gas_litres = (ascent_back_gas_one + problem_solve_one) * 2
    turn_pressure_bar = min_gas_litres / _back_gas_vol

    return {
        'min_gas_litres': min_gas_litres,
        'turn_pressure_bar': turn_pressure_bar,
        'bar_at_turn': bar_at_turn,
        'bar_used_bottom': bar_used_before_ascent,
        'can_start_before_140': bar_at_turn >= 140,
        'has_enough_gas': bar_at_turn >= turn_pressure_bar,
    }


def run_scenario(name, depth, bottom_time, deco_gases_lost=False, cfg=None,
                 back_gas=None,
                 back_gas_pressure=None, deco_50_pressure=None, deco_o2_pressure=None,
                 back_gas_vol=None, deco_50_vol=None, deco_o2_vol=None,
                 gf_low=None, gf_high=None, descent_rate=None, ascent_rate=None,
                 sac_bottom=None, sac_deco=None,
                 lean_gas=None, lean_switch=None, lean_enabled=True,
                 rich_gas=None, rich_switch=None, rich_enabled=True,
                 descent_stops=None,
                 travel_gas_config=None,
                 gas_switch_time=None,
                 emergency_sac=None):
    """Run a complete scenario and return results dict.

    cfg: optional dict with keys:
        back_cylinder: CylinderConfig
        deco_cylinders: list of (CylinderConfig, switch_depth_m)
        gf_low, gf_high: float
        descent_rate, ascent_rate: float
        sac_bottom, sac_deco: float
    back_gas_pressure: override fill pressure for back gas (default: BACK_GAS_PRESSURE)
    deco_50_pressure: override fill pressure for EAN50 (default: DECO_50_PRESSURE)
    deco_o2_pressure: override fill pressure for O2 (default: DECO_O2_PRESSURE)
    descent_stops: list of (depth_m, time_min) stops during descent (e.g. S-drills).
    emergency_sac: stressed SAC rate [L/min] for the returned 'min_gas' safety margin
        (see calculate_min_gas_and_turn_from_summary). Defaults to sac_bottom.
    When cfg is provided, also returns 'cylinders' in the result.
    """
    _back_gas_pressure = back_gas_pressure if back_gas_pressure is not None else BACK_GAS_PRESSURE
    _deco_50_pressure = deco_50_pressure if deco_50_pressure is not None else DECO_50_PRESSURE
    _deco_o2_pressure = deco_o2_pressure if deco_o2_pressure is not None else DECO_O2_PRESSURE
    _back_gas_vol = back_gas_vol if back_gas_vol is not None else BACK_GAS_VOL
    _deco_50_vol = deco_50_vol if deco_50_vol is not None else DECO_50_VOL
    _deco_o2_vol = deco_o2_vol if deco_o2_vol is not None else DECO_O2_VOL
    _lean_gas = lean_gas if lean_gas is not None else (50, 0)
    _lean_switch = lean_switch if lean_switch is not None else _DECO_50_SWITCH_DEPTH
    _rich_gas = rich_gas if rich_gas is not None else (100, 0)
    _rich_switch = rich_switch if rich_switch is not None else _DECO_O2_SWITCH_DEPTH
    _cfg = cfg or {}
    _sac_bottom = sac_bottom if sac_bottom is not None else (_cfg.get('sac_bottom') if _cfg.get('sac_bottom') is not None else SAC_BOTTOM)
    _sac_deco = sac_deco if sac_deco is not None else (_cfg.get('sac_deco') if _cfg.get('sac_deco') is not None else SAC_DECO)
    _gf_low = gf_low if gf_low is not None else _cfg.get('gf_low', GF_LOW)
    _gf_high = gf_high if gf_high is not None else _cfg.get('gf_high', GF_HIGH)
    _descent_rate = descent_rate if descent_rate is not None else _cfg.get('descent_rate', DESCENT_RATE)
    _ascent_rate = ascent_rate if ascent_rate is not None else _cfg.get('ascent_rate', ASCENT_RATE)

    back_cyl = _cfg.get('back_cylinder') or BACK_GAS_CYLINDER
    deco_cyls_with_depths = _cfg.get('deco_cylinders')
    # Use explicitly passed back_gas if provided, otherwise fall back to BACK_GAS_CYLINDER
    if back_gas is not None:
        back_gas_tuple = back_gas
    else:
        back_gas_tuple = (back_cyl.gas.o2, back_cyl.gas.he)

    if cfg is not None:
        # cfg path: build Gas/Cylinder objects from CylinderConfig objects
        _back_gas_pressure = back_cyl.fill_pressure_bar
        back_gas_obj = _Gas(o2=back_cyl.gas.o2, he=back_cyl.gas.he, label=back_cyl.name)
        back_cyl_obj = _Cylinder(volume_litres=back_cyl.volume_l, fill_bar=back_cyl.fill_pressure_bar)

        deco_gas_objs = []
        deco_cyl_objs = []
        has_switch_stop = False
        switch_depth = _lean_switch
        if deco_cyls_with_depths is not None:
            first_non_o2 = next(((c, sd) for c, sd in deco_cyls_with_depths if c.gas.o2 < 100), None)
            has_switch_stop = first_non_o2 is not None
            if has_switch_stop:
                switch_depth = float(first_non_o2[1])
            for cyl, sd in deco_cyls_with_depths:
                if float(sd) >= depth:
                    continue  # skip gas whose switch depth is at or beyond dive depth
                deco_gas_objs.append(_Gas(o2=cyl.gas.o2, he=cyl.gas.he, switch_depth=float(sd), label=cyl.name))
                deco_cyl_objs.append(_Cylinder(volume_litres=cyl.volume_l, fill_bar=cyl.fill_pressure_bar))

        summary = _plan_dive(
            depth=depth,
            bottom_time=bottom_time,
            back_gas=back_gas_obj,
            deco_gases=deco_gas_objs,
            gf=(_gf_low * 100, _gf_high * 100),
            descent_rate=_descent_rate,
            ascent_rate=_ascent_rate,
            sac_bottom=_sac_bottom,
            sac_deco=_sac_deco,
            back_cylinder=back_cyl_obj,
            deco_cylinders=deco_cyl_objs,
            descent_stops=descent_stops,
            gas_switch_time=gas_switch_time if gas_switch_time is not None else 1.0,
        )

        all_cylinders_list = [back_cyl] + ([c for c, _ in deco_cyls_with_depths] if deco_cyls_with_depths else [])
        cylinders_result = []
        for cyl in all_cylinders_list:
            usage = summary.gas_usage.get(cyl.name)
            used_litres = usage.consumed_litres if usage else 0.0
            bar_used = used_litres / cyl.volume_l
            remaining_bar = cyl.fill_pressure_bar - bar_used
            cylinders_result.append({
                'name': cyl.name,
                'gas': {'o2': cyl.gas.o2, 'he': cyl.gas.he},
                'volume_l': cyl.volume_l,
                'fill_bar': cyl.fill_pressure_bar,
                'used_litres': used_litres,
                'used_bar': bar_used,
                'remaining_bar': remaining_bar,
            })

        _min_gas_back_vol = back_cyl.volume_l

        back_remaining = cylinders_result[0]['remaining_bar'] if cylinders_result else None
        lean_remaining = next(
            (c['remaining_bar'] for c in cylinders_result if c['gas']['o2'] == _lean_gas[0] and c['gas']['he'] == _lean_gas[1]), None)
        rich_remaining = next(
            (c['remaining_bar'] for c in cylinders_result if c['gas']['o2'] == _rich_gas[0]), None)
        gas_used = {c['name']: {'litres': c['used_litres'], 'bar': c['used_bar']}
                    for c in cylinders_result}
        travel_remaining = None  # cfg path doesn't support travel gas
    else:
        # Non-cfg path: use run_profile with lean/rich gas params
        summary = run_profile(
            depth, bottom_time, deco_gases_lost,
            back_gas=back_gas_tuple,
            gf_low=_gf_low, gf_high=_gf_high,
            descent_rate=_descent_rate, ascent_rate=_ascent_rate,
            sac_bottom=_sac_bottom, sac_deco=_sac_deco,
            back_gas_pressure=_back_gas_pressure,
            deco_50_pressure=_deco_50_pressure,
            deco_o2_pressure=_deco_o2_pressure,
            back_gas_vol=_back_gas_vol,
            deco_50_vol=_deco_50_vol,
            deco_o2_vol=_deco_o2_vol,
            lean_gas=_lean_gas, lean_switch=_lean_switch, lean_enabled=lean_enabled,
            rich_gas=_rich_gas, rich_switch=_rich_switch, rich_enabled=rich_enabled,
            descent_stops=descent_stops,
            travel_gas_config=travel_gas_config,
            gas_switch_time=gas_switch_time,
        )

        back_usage = summary.gas_usage.get('back')
        lean_usage = summary.gas_usage.get('lean')
        rich_usage = summary.gas_usage.get('rich')
        travel_usage = summary.gas_usage.get('travel')

        back_remaining = back_usage.remaining_bar if back_usage else _back_gas_pressure
        lean_remaining = (lean_usage.remaining_bar if lean_usage else _deco_50_pressure) if lean_enabled else None
        rich_remaining = (rich_usage.remaining_bar if rich_usage else _deco_o2_pressure) if rich_enabled else None
        travel_remaining = travel_usage.remaining_bar if travel_usage else (
            travel_gas_config[2] if travel_gas_config else None
        )

        gas_used = {
            'back_gas': back_usage.consumed_litres if back_usage else 0.0,
            'lean': lean_usage.consumed_litres if lean_usage else 0.0,
            'rich': rich_usage.consumed_litres if rich_usage else 0.0,
        }

        _min_gas_back_vol = _back_gas_vol

        has_switch_stop = False
        switch_depth = _lean_switch
        cylinders_result = None
        if travel_remaining is None:
            pass  # already None

    min_gas = calculate_min_gas_and_turn_from_summary(
        summary,
        back_gas_pressure=_back_gas_pressure,
        back_gas_vol=_min_gas_back_vol,
        sac_bottom=_sac_bottom,
        emergency_sac=emergency_sac,
    )

    # Build deco_stops
    deco_stops = [(s.depth, s.time) for s in summary.stops]
    total_time = summary.runtime
    total_deco = summary.total_deco_time
    stop_runtimes = dict(summary.stop_runtimes)

    profile_times = [t for t, d in summary.profile]
    profile_depths = [d for t, d in summary.profile]

    result = {
        'name': name,
        'depth': depth,
        'bottom_time': bottom_time,
        'total_time': total_time,
        'total_deco': total_deco,
        'deco_stops': deco_stops,
        'times': profile_times,
        'depths': profile_depths,
        'deco_gases_lost': deco_gases_lost,
        'stop_runtimes': stop_runtimes,
        'otu': summary.otu,
        'cns': summary.cns_percent,
        'gas_used': gas_used,
        'back_remaining_bar': back_remaining,
        'lean_remaining_bar': lean_remaining,
        'rich_remaining_bar': rich_remaining,
        'travel_remaining_bar': travel_remaining,
        'lean_gas': _lean_gas if lean_enabled else None,
        'rich_gas': _rich_gas if rich_enabled else None,
        'lean_switch': _lean_switch if lean_enabled else None,
        'rich_switch': _rich_switch if rich_enabled else None,
        'min_gas': min_gas,
        'max_gas_density': summary.max_gas_density,
        'icd_warnings': summary.icd_warnings,
    }
    result['ceiling_profile'] = summary.ceiling_profile
    result['gas_pressure_profile'] = summary.gas_pressure_profile

    if cfg is not None:
        result['cylinders'] = cylinders_result

    return result


def calculate_best_mix(depth, target_end=30, max_po2_bottom=1.4, o2_narcotic=False):
    """
    Calculate the optimal trimix for a given depth.

    When o2_narcotic=False (default, GUE/IANTD model):
        END = (depth + 10) × N2_frac - 10  (only N2 is narcotic)
    When o2_narcotic=True (NOAA/some agency model):
        END = (depth + 10) × (1 - He_frac) - 10  (O2 + N2 both narcotic)

    O2 is set to maximum allowable at depth (capped by max_po2_bottom).

    Returns:
        dict with o2%, he%, n2%, po2_at_depth, end, depth, target_end, max_po2
    """
    ambient_bar = SURFACE_PRESSURE + depth / 10.0

    # O2%: max allowed by PO2 limit
    o2_frac = max_po2_bottom / ambient_bar
    o2_pct = int(o2_frac * 100)  # round down for safety
    o2_frac = o2_pct / 100.0

    if o2_narcotic:
        # O2 counts as narcotic: He_frac = 1 - (END + 10) / (depth + 10)
        he_frac = 1.0 - (target_end + 10.0) / (depth + 10.0)
    else:
        # Only N2 is narcotic. At END depth breathing air, narcotic N2 partial
        # pressure = (END+10) * 0.79. We want the same N2 partial pressure at depth:
        #   N2_frac * (depth+10) = 0.79 * (END+10)  →  N2_frac = 0.79*(END+10)/(depth+10)
        n2_target = 0.79 * (target_end + 10.0) / (depth + 10.0)
        he_frac = 1.0 - o2_frac - n2_target

    he_frac = max(0.0, he_frac)
    he_pct = round(he_frac * 100)
    he_frac = he_pct / 100.0

    # Verify N2 is non-negative
    n2_frac = 1.0 - o2_frac - he_frac
    if n2_frac < 0:
        he_frac = 1.0 - o2_frac
        he_pct = int(he_frac * 100)
        he_frac = he_pct / 100.0
        n2_frac = 1.0 - o2_frac - he_frac

    n2_pct = 100 - o2_pct - he_pct

    actual_po2 = ambient_bar * o2_frac
    if o2_narcotic:
        actual_end = (depth + 10) * (1 - he_frac) - 10
    else:
        # END = (depth+10)*n2_frac/0.79 - 10
        actual_end = (depth + 10) * n2_frac / 0.79 - 10

    return {
        'o2': o2_pct,
        'he': he_pct,
        'n2': n2_pct,
        'po2_at_depth': actual_po2,
        'end': actual_end,
        'depth': depth,
        'target_end': target_end,
        'max_po2': max_po2_bottom,
    }


def _gas_density_gl(o2_pct, he_pct, depth_m, h2_pct=0):
    """Gas density [g/L] at depth using ideal gas law at 37°C body temperature."""
    MW_O2, MW_N2, MW_HE, MW_H2 = 31.998, 28.014, 4.003, 2.016
    R, T = 0.083145, 310.15
    f_o2, f_he = o2_pct / 100.0, he_pct / 100.0
    f_h2 = h2_pct / 100.0
    mw_mix = f_o2 * MW_O2 + (1.0 - f_o2 - f_he - f_h2) * MW_N2 + f_he * MW_HE + f_h2 * MW_H2
    abs_p = SURFACE_PRESSURE + depth_m / 10.0
    return (mw_mix * abs_p) / (R * T)


def calc_travel_gas_min(sac_bottom, h2_switch_depth, final_gas_switch_depth,
                        descent_rate, ascent_rate, travel_vol, travel_bar,
                        surface_pressure=1.01325):
    """Calculate travel gas consumption and minimum requirement for H2 diving.

    final_gas_switch_depth: switch depth of whichever deco gas the emergency ascent
        would continue on past h2_switch_depth — the shallowest switch depth among
        the deco gases actually carried, or 0 (surface, back gas only) if none.

    Returns dict with:
    - descent_litres: gas consumed descending to h2_switch_depth
    - descent_remaining_bar: travel gas remaining after descent (per diver)
    - min_required_bar: minimum travel gas needed (descent + emergency ascent × 2 divers)
    - has_enough: True if travel_bar >= min_required_bar
    """
    # Descent 0m → h2_switch_depth
    p_start = surface_pressure
    p_switch = surface_pressure + h2_switch_depth * 0.09985
    avg_p_descent = (p_start + p_switch) / 2.0
    descent_time = h2_switch_depth / descent_rate
    descent_litres = sac_bottom * descent_time * avg_p_descent

    # Emergency ascent h2_switch_depth → final_gas_switch_depth (×2 divers)
    p_final = surface_pressure + final_gas_switch_depth * 0.09985
    avg_p_ascent = (p_switch + p_final) / 2.0
    ascent_time = (h2_switch_depth - final_gas_switch_depth) / ascent_rate
    ascent_litres_per_diver = sac_bottom * ascent_time * avg_p_ascent

    min_litres = descent_litres + ascent_litres_per_diver * 2
    min_bar = min_litres / travel_vol
    descent_bar_used = descent_litres / travel_vol

    return {
        'descent_litres': descent_litres,
        'descent_remaining_bar': travel_bar - descent_bar_used,
        'min_required_bar': min_bar,
        'has_enough': travel_bar >= min_bar,
    }


def find_max_bottom_time(depth, back_gas=None, gas_rule='double_ascent',
                        back_gas_pressure=None, deco_50_pressure=None,
                        deco_o2_pressure=None,
                        back_gas_vol=None, deco_50_vol=None, deco_o2_vol=None,
                        gf_low=None, gf_high=None, descent_rate=None,
                        ascent_rate=None, sac_bottom=None, sac_deco=None,
                        lean_gas=None, lean_switch=None, lean_enabled=True,
                        rich_gas=None, rich_switch=None, rich_enabled=True,
                        min_reserve=10,
                        descent_stops=None,
                        gas_switch_time=None,
                        contingency_scenarios=None,
                        travel_gas_config=None):
    """
    Find the maximum bottom time satisfying the gas rule.

    gas_rule='double_ascent': all contingency scenarios (T+3 @ D+3, lost deco gas)
        must have non-negative back gas remaining within the fill pressure.
        The binding constraint is the worst-case scenario in the planning table.
    gas_rule='thirds': bar_at_turn >= 2/3 of fill pressure
    back_gas_pressure: override fill pressure (default: BACK_GAS_PRESSURE)
    deco_50_pressure: override fill pressure for EAN50 (default: DECO_50_PRESSURE)
    deco_o2_pressure: override fill pressure for O2 (default: DECO_O2_PRESSURE)
    contingency_scenarios: optional list of dicts, each with keys:
        depth (int, absolute), time_offset (int, added to T), time_absolute (int or None),
        lost (False/'lean'/'rich'/list), gf_low (float or None), gf_high (float or None),
        ascent_rate (float or None), sac_bottom (float or None), sac_deco (float or None).
        If provided, replaces the hardcoded 8-scenario set.
    travel_gas_config: (o2, he, bar, vol, switch_depth) tuple or None.
    Uses binary search over bottom time.
    """
    _back_gas = back_gas if back_gas is not None else BACK_GAS
    _back_gas_pressure = back_gas_pressure if back_gas_pressure is not None else BACK_GAS_PRESSURE
    _deco_50_pressure = deco_50_pressure if deco_50_pressure is not None else DECO_50_PRESSURE
    _deco_o2_pressure = deco_o2_pressure if deco_o2_pressure is not None else DECO_O2_PRESSURE
    _gf_low = gf_low if gf_low is not None else GF_LOW
    _gf_high = gf_high if gf_high is not None else GF_HIGH
    _descent_rate = descent_rate if descent_rate is not None else DESCENT_RATE
    _ascent_rate = ascent_rate if ascent_rate is not None else ASCENT_RATE
    _sac_bottom = sac_bottom if sac_bottom is not None else SAC_BOTTOM
    _sac_deco = sac_deco if sac_deco is not None else SAC_DECO
    _back_gas_vol = back_gas_vol if back_gas_vol is not None else BACK_GAS_VOL
    _deco_50_vol = deco_50_vol if deco_50_vol is not None else DECO_50_VOL
    _deco_o2_vol = deco_o2_vol if deco_o2_vol is not None else DECO_O2_VOL
    _lean_gas = lean_gas if lean_gas is not None else (50, 0)
    _lean_switch = lean_switch if lean_switch is not None else _DECO_50_SWITCH_DEPTH
    _rich_gas = rich_gas if rich_gas is not None else (100, 0)
    _rich_switch = rich_switch if rich_switch is not None else _DECO_O2_SWITCH_DEPTH
    thirds_pressure = _back_gas_pressure * 2 / 3

    lo, hi = 1, 120
    best = lo
    while lo <= hi:
        mid = (lo + hi) // 2
        try:
            if gas_rule == 'double_ascent':
                if contingency_scenarios is not None:
                    # Use caller-supplied scenario list
                    _scenarios_to_check = [
                        (s['depth'],
                         s['time_absolute'] if s.get('time_absolute') is not None else mid + s.get('time_offset', 0),
                         s.get('lost', False),
                         s.get('gf_low') or _gf_low,
                         s.get('gf_high') or _gf_high,
                         s.get('ascent_rate') or _ascent_rate,
                         s.get('sac_bottom') or _sac_bottom,
                         s.get('sac_deco') or _sac_deco,
                        )
                        for s in contingency_scenarios
                    ]
                else:
                    # Default hardcoded scenario set — a "lost X" contingency only makes
                    # sense for a gas that's actually part of the plan.
                    _scenarios_to_check = [
                        (depth,     mid,     False,  _gf_low, _gf_high, _ascent_rate, _sac_bottom, _sac_deco),
                        (depth,     mid + 3, False,  _gf_low, _gf_high, _ascent_rate, _sac_bottom, _sac_deco),
                        (depth + 3, mid,     False,  _gf_low, _gf_high, _ascent_rate, _sac_bottom, _sac_deco),
                        (depth + 3, mid + 3, False,  _gf_low, _gf_high, _ascent_rate, _sac_bottom, _sac_deco),
                    ]
                    if lean_enabled:
                        _scenarios_to_check.append((depth,     mid,     'lean', _gf_low, _gf_high, _ascent_rate, _sac_bottom, _sac_deco))
                    if rich_enabled:
                        _scenarios_to_check.append((depth,     mid,     'rich', _gf_low, _gf_high, _ascent_rate, _sac_bottom, _sac_deco))
                    if lean_enabled:
                        _scenarios_to_check.append((depth + 3, mid + 3, 'lean', _gf_low, _gf_high, _ascent_rate, _sac_bottom, _sac_deco))
                    if rich_enabled:
                        _scenarios_to_check.append((depth + 3, mid + 3, 'rich', _gf_low, _gf_high, _ascent_rate, _sac_bottom, _sac_deco))
                ok = True
                for d, bt, lost, s_gfl, s_gfh, s_ar, s_sb, s_sd in _scenarios_to_check:
                    r = run_scenario("test", d, bt, deco_gases_lost=lost,
                                     back_gas=_back_gas,
                                     back_gas_pressure=_back_gas_pressure,
                                     deco_50_pressure=_deco_50_pressure,
                                     deco_o2_pressure=_deco_o2_pressure,
                                     back_gas_vol=_back_gas_vol,
                                     deco_50_vol=_deco_50_vol,
                                     deco_o2_vol=_deco_o2_vol,
                                     lean_gas=_lean_gas, lean_switch=_lean_switch, lean_enabled=lean_enabled,
                                     rich_gas=_rich_gas, rich_switch=_rich_switch, rich_enabled=rich_enabled,
                                     gf_low=s_gfl, gf_high=s_gfh,
                                     descent_rate=_descent_rate, ascent_rate=s_ar,
                                     sac_bottom=s_sb, sac_deco=s_sd,
                                     descent_stops=descent_stops,
                                     travel_gas_config=travel_gas_config,
                                     gas_switch_time=gas_switch_time)
                    if r['back_remaining_bar'] < min_reserve:
                        ok = False
                        break
                    lost_list = lost if isinstance(lost, list) else []
                    if lean_enabled and lost not in (True, 'lean') and 'lean' not in lost_list and r['lean_remaining_bar'] < min_reserve:
                        ok = False
                        break
                    if rich_enabled and lost not in (True, 'rich') and 'rich' not in lost_list and r['rich_remaining_bar'] < min_reserve:
                        ok = False
                        break
            else:
                r = run_scenario("test", depth, mid, deco_gases_lost=False,
                                 back_gas=_back_gas,
                                 back_gas_pressure=_back_gas_pressure,
                                 deco_50_pressure=_deco_50_pressure,
                                 deco_o2_pressure=_deco_o2_pressure,
                                 back_gas_vol=_back_gas_vol,
                                 deco_50_vol=_deco_50_vol,
                                 deco_o2_vol=_deco_o2_vol,
                                 lean_gas=_lean_gas, lean_switch=_lean_switch, lean_enabled=lean_enabled,
                                 rich_gas=_rich_gas, rich_switch=_rich_switch, rich_enabled=rich_enabled,
                                 gf_low=_gf_low, gf_high=_gf_high,
                                 descent_rate=_descent_rate, ascent_rate=_ascent_rate,
                                 sac_bottom=_sac_bottom, sac_deco=_sac_deco,
                                 descent_stops=descent_stops,
                                 gas_switch_time=gas_switch_time)
                ok = r['min_gas']['bar_at_turn'] >= thirds_pressure
            if ok:
                best = mid
                lo = mid + 1
            else:
                hi = mid - 1
        except Exception:
            hi = mid - 1
    return best
