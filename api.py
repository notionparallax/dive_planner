"""FastAPI backend for the dive planner."""
import math
from typing import Optional, Union

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from dive_plan import (
    GasConfig, CylinderConfig,
    run_scenario, SURFACE_PRESSURE,
)
from gas_planning import calc_gas_plan, calc_switch_depth

app = FastAPI(title="Dive Planner API")


# ── Request model ──────────────────────────────────────────────────────────────

class PlanRequest(BaseModel):
    depth: float = 45.0
    bottom_time: float = 27.0
    gf_low: float = 0.50
    gf_high: float = 0.70
    dive_mode: str = 'open_water'  # 'cave' or 'open_water'

    # Back gas
    back_gas_o2: int = 23
    back_gas_he: Optional[int] = 0
    back_gas_volume_l: float = 24.4
    back_gas_fill_bar: int = 210

    # Deco gas 1 (e.g. EAN50)
    deco1_enabled: bool = True
    deco1_o2: int = 50
    deco1_he: Optional[int] = 0
    deco1_volume_l: float = 11.1
    deco1_fill_bar: int = 150
    deco1_switch_depth_m: Optional[float] = None

    # Deco gas 2 (e.g. 100% O2)
    deco2_enabled: bool = True
    deco2_o2: int = 100
    deco2_he: Optional[int] = 0
    deco2_volume_l: float = 11.1
    deco2_fill_bar: int = 150
    deco2_switch_depth_m: Optional[float] = None

    # SAC rates
    sac_bottom: float = 20.0
    sac_deco: float = 15.0
    sac_emergency: float = 30.0
    contingency: float = 1.0
    practical_empty_bar: float = 20.0

    # ppO2 limits
    max_ppo2_bottom: float = 1.4
    max_ppo2_deco: float = 1.6

    deco_gases_lost: Union[bool, str] = False


class OptimiseRequest(BaseModel):
    depth: float = 45.0
    gf_low: float = 0.50
    gf_high: float = 0.70
    dive_mode: str = 'open_water'

    back_gas_o2: int = 23
    back_gas_he: Optional[int] = 0
    back_gas_volume_l: float = 24.4
    back_gas_fill_bar: int = 210

    deco1_enabled: bool = True
    deco1_o2: int = 50
    deco1_he: Optional[int] = 0
    deco1_volume_l: float = 11.1
    deco1_fill_bar: int = 150
    deco1_switch_depth_m: Optional[float] = None

    deco2_enabled: bool = True
    deco2_o2: int = 100
    deco2_he: Optional[int] = 0
    deco2_volume_l: float = 11.1
    deco2_fill_bar: int = 150
    deco2_switch_depth_m: Optional[float] = None

    sac_bottom: float = 20.0
    sac_deco: float = 15.0
    sac_emergency: float = 30.0
    contingency: float = 1.0
    practical_empty_bar: float = 20.0

    max_ppo2_bottom: float = 1.4
    max_ppo2_deco: float = 1.6

    # Constraint limits
    max_cns: float = 80.0
    max_otu: float = 300.0
    max_runtime: Optional[float] = None
    min_bottom_time: int = 1
    max_bottom_time: int = 180


class FullOptimiseRequest(BaseModel):
    depth: float = 45.0
    gf_low: float = 0.50
    gf_high: float = 0.70
    dive_mode: str = 'open_water'

    # Back gas is fixed (user specifies mix; not optimised)
    back_gas_o2: int = 23
    back_gas_he: Optional[int] = 0
    back_gas_volume_l: float = 24.4
    back_gas_fill_bar: int = 210

    # Deco gas 1: O2% is searched (volume/fill fixed)
    deco1_volume_l: float = 11.1
    deco1_fill_bar: int = 150
    deco1_o2_min: int = 21
    deco1_o2_max: int = 80

    # Deco gas 2: O2% is also searched (volume/fill fixed)
    deco2_volume_l: float = 11.1
    deco2_fill_bar: int = 150
    deco2_o2_min: int = 50
    deco2_o2_max: int = 100

    sac_bottom: float = 20.0
    sac_deco: float = 15.0
    sac_emergency: float = 30.0
    contingency: float = 1.0
    practical_empty_bar: float = 20.0

    max_ppo2_bottom: float = 1.4
    max_ppo2_deco: float = 1.6

    max_cns: float = 80.0
    max_otu: float = 300.0
    max_runtime: Optional[float] = None
    min_bottom_time: int = 1
    max_bottom_time: int = 180


# ── Helpers ────────────────────────────────────────────────────────────────────

def _sanitize(obj):
    """Recursively convert numpy/decotengu types to plain Python."""
    if isinstance(obj, dict):
        return {(str(k) if isinstance(k, float) else k): _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_sanitize(x) for x in obj]
    if hasattr(obj, 'item'):  # numpy scalar
        return obj.item()
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    return obj


def _cylinder(o2, he, volume_l, fill_bar, name):
    """Build a CylinderConfig, treating a None He% (e.g. old JS sending null) as 0."""
    return CylinderConfig(GasConfig(o2, he or 0), volume_l, fill_bar, name)


def _resolve_switch_depth(switch_depth_m, o2_pct, max_ppo2_deco):
    """Use an explicit override if given, else derive MOD from O2% at the ppO2 deco limit."""
    if switch_depth_m is not None:
        return switch_depth_m
    if o2_pct > 0:
        return calc_switch_depth(o2_pct / 100.0, max_ppo2_deco)
    return None


def _gas_at_depth(depth, back_cylinder, deco_cyls_with_depths):
    """Return a short gas label for the gas being breathed at a given stop depth."""
    # On ascent, switch to the deco gas with the minimum switch_depth that is >= stop depth
    applicable = [(cyl, sd) for cyl, sd in deco_cyls_with_depths if sd >= depth]
    if applicable:
        cyl, _ = min(applicable, key=lambda x: x[1])
        label = f"{cyl.gas.o2}% O₂"
        if cyl.gas.he:
            label += f"/{cyl.gas.he}% He"
        return label
    o2, he = back_cylinder.gas.o2, back_cylinder.gas.he
    return f"Tx {o2}/{he}" if he else f"EAN{o2}" if o2 != 21 else "Air"


def _build_deco_schedule(deco_stops, stop_runtimes, back_cylinder, deco_cyls_with_depths):
    schedule = []
    for depth, stop_time in deco_stops:
        rt_info = stop_runtimes.get(depth)
        schedule.append({
            'depth': float(depth),
            'stop_time': float(stop_time),
            'runtime': float(rt_info) if rt_info is not None else None,
            'gas': _gas_at_depth(float(depth), back_cylinder, deco_cyls_with_depths),
        })
    return schedule


# ── Endpoints ──────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/plan")
def plan_dive(req: PlanRequest):
    back_cylinder = _cylinder(req.back_gas_o2, req.back_gas_he, req.back_gas_volume_l,
                              req.back_gas_fill_bar, f"Back Gas ({req.back_gas_o2}/{req.back_gas_he or 0})")
    deco1_cylinder = _cylinder(req.deco1_o2, req.deco1_he, req.deco1_volume_l,
                               req.deco1_fill_bar, f"Deco 1 ({req.deco1_o2}/{req.deco1_he or 0})")
    deco2_cylinder = _cylinder(req.deco2_o2, req.deco2_he, req.deco2_volume_l,
                               req.deco2_fill_bar, f"Deco 2 ({req.deco2_o2}/{req.deco2_he or 0})")

    sd1 = _resolve_switch_depth(req.deco1_switch_depth_m, req.deco1_o2, req.max_ppo2_deco)
    sd2 = _resolve_switch_depth(req.deco2_switch_depth_m, req.deco2_o2, req.max_ppo2_deco)

    # Build deco cylinders list (filter out disabled or lost gases)
    deco_cyls_with_depths = []
    if req.deco1_enabled and req.deco_gases_lost not in (True, 'ean50') and sd1 is not None:
        deco_cyls_with_depths.append((deco1_cylinder, int(sd1)))
    if req.deco2_enabled and req.deco_gases_lost not in (True, 'o2') and sd2 is not None:
        deco_cyls_with_depths.append((deco2_cylinder, int(sd2)))

    cfg = {
        'back_cylinder': back_cylinder,
        'deco_cylinders': deco_cyls_with_depths,
        'gf_low': req.gf_low,
        'gf_high': req.gf_high,
        'sac_bottom': req.sac_bottom,
        'sac_deco': req.sac_deco,
    }

    scenario = run_scenario(
        "API Plan", req.depth, req.bottom_time,
        deco_gases_lost=req.deco_gases_lost,
        cfg=cfg,
        emergency_sac=req.sac_emergency,
    )

    gas_plan = calc_gas_plan(
        scenario['min_gas'], back_cylinder, deco_cyls_with_depths,
        dive_mode=req.dive_mode,
        contingency=req.contingency,
        practical_empty_bar=req.practical_empty_bar,
    )

    # Build structured deco schedule
    scenario['deco_schedule'] = _build_deco_schedule(
        scenario.get('deco_stops', []),
        scenario.get('stop_runtimes', {}),
        back_cylinder,
        deco_cyls_with_depths,
    )

    # Switch depths info
    scenario['switch_depths'] = {
        'deco1': sd1,
        'deco2': sd2,
    }

    scenario['gas_plan'] = gas_plan
    scenario['dive_mode'] = req.dive_mode
    scenario['gf_low'] = req.gf_low
    scenario['gf_high'] = req.gf_high

    # Remove non-serialisable/redundant fields
    scenario.pop('stop_runtimes', None)

    return JSONResponse(content=_sanitize(scenario))


@app.post("/api/optimise/bottom-time")
def optimise_bottom_time_endpoint(req: OptimiseRequest):
    from optimiser import optimise_bottom_time

    back_cylinder = _cylinder(req.back_gas_o2, req.back_gas_he, req.back_gas_volume_l,
                              req.back_gas_fill_bar, f"Back Gas ({req.back_gas_o2}/{req.back_gas_he or 0})")
    deco1_cylinder = _cylinder(req.deco1_o2, req.deco1_he, req.deco1_volume_l,
                               req.deco1_fill_bar, f"Deco 1 ({req.deco1_o2}/{req.deco1_he or 0})")
    deco2_cylinder = _cylinder(req.deco2_o2, req.deco2_he, req.deco2_volume_l,
                               req.deco2_fill_bar, f"Deco 2 ({req.deco2_o2}/{req.deco2_he or 0})")

    sd1 = _resolve_switch_depth(req.deco1_switch_depth_m, req.deco1_o2, req.max_ppo2_deco)
    sd2 = _resolve_switch_depth(req.deco2_switch_depth_m, req.deco2_o2, req.max_ppo2_deco)

    deco_cyls_with_depths = []
    if req.deco1_enabled and sd1 is not None:
        deco_cyls_with_depths.append((deco1_cylinder, int(sd1)))
    if req.deco2_enabled and sd2 is not None:
        deco_cyls_with_depths.append((deco2_cylinder, int(sd2)))

    result = optimise_bottom_time(
        depth=req.depth,
        back_cylinder=back_cylinder,
        deco_cyls_with_depths=deco_cyls_with_depths,
        dive_mode=req.dive_mode,
        gf_low=req.gf_low,
        gf_high=req.gf_high,
        sac_bottom=req.sac_bottom,
        sac_deco=req.sac_deco,
        sac_emergency=req.sac_emergency,
        contingency=req.contingency,
        practical_empty_bar=req.practical_empty_bar,
        max_cns=req.max_cns,
        max_otu=req.max_otu,
        max_runtime=req.max_runtime,
        min_bottom_time=req.min_bottom_time,
        max_bottom_time=req.max_bottom_time,
    )

    # Enrich scenario with deco schedule if feasible
    scenario = result.get('scenario')
    if scenario:
        scenario['deco_schedule'] = _build_deco_schedule(
            scenario.get('deco_stops', []),
            scenario.get('stop_runtimes', {}),
            back_cylinder,
            deco_cyls_with_depths,
        )
        scenario.pop('stop_runtimes', None)
        scenario['switch_depths'] = {'deco1': sd1, 'deco2': sd2}

    response = {
        'feasible': result['feasible'],
        'max_bottom_time': result['max_bottom_time'],
        'binding_constraints': result['binding_constraints'],
        'steps_checked': result['steps_checked'],
        'depth': req.depth,
        'dive_mode': req.dive_mode,
        'gf_low': req.gf_low,
        'gf_high': req.gf_high,
        'scenario': scenario,
        'gas_plan': result.get('gas_plan'),
    }

    return JSONResponse(content=_sanitize(response))


@app.post("/api/optimise/full")
def optimise_full_endpoint(req: FullOptimiseRequest):
    from optimiser import optimise_both_deco_gases

    back_cylinder = _cylinder(req.back_gas_o2, req.back_gas_he, req.back_gas_volume_l,
                              req.back_gas_fill_bar, f"Back Gas ({req.back_gas_o2}/{req.back_gas_he or 0})")

    result = optimise_both_deco_gases(
        depth=req.depth,
        back_cylinder=back_cylinder,
        deco1_volume_l=req.deco1_volume_l,
        deco1_fill_bar=req.deco1_fill_bar,
        deco2_volume_l=req.deco2_volume_l,
        deco2_fill_bar=req.deco2_fill_bar,
        dive_mode=req.dive_mode,
        gf_low=req.gf_low,
        gf_high=req.gf_high,
        sac_bottom=req.sac_bottom,
        sac_deco=req.sac_deco,
        sac_emergency=req.sac_emergency,
        contingency=req.contingency,
        practical_empty_bar=req.practical_empty_bar,
        max_cns=req.max_cns,
        max_otu=req.max_otu,
        max_runtime=req.max_runtime,
        min_bottom_time=req.min_bottom_time,
        max_bottom_time=req.max_bottom_time,
        max_ppo2_deco=req.max_ppo2_deco,
        deco1_o2_min=req.deco1_o2_min,
        deco1_o2_max=req.deco1_o2_max,
        deco2_o2_min=req.deco2_o2_min,
        deco2_o2_max=req.deco2_o2_max,
    )

    best_result = result.get('best_result')
    best_scenario = best_result.get('scenario') if best_result else None

    if best_scenario and result['best_deco1_o2'] is not None:
        bd1_o2 = result['best_deco1_o2']
        bd1_sd = result['best_deco1_switch_depth']
        bd2_o2 = result['best_deco2_o2']
        bd2_sd = result['best_deco2_switch_depth']

        d2_label = "Deco 2 (O2)" if bd2_o2 == 100 else f"Deco 2 (EAN{bd2_o2})"
        best_deco1_cyl = _cylinder(bd1_o2, 0, req.deco1_volume_l, req.deco1_fill_bar, f"Deco 1 (EAN{bd1_o2})")
        best_deco2_cyl = _cylinder(bd2_o2, 0, req.deco2_volume_l, req.deco2_fill_bar, d2_label)
        best_deco_cyls = [(best_deco1_cyl, int(bd1_sd)), (best_deco2_cyl, int(bd2_sd))]

        best_scenario['deco_schedule'] = _build_deco_schedule(
            best_scenario.get('deco_stops', []),
            best_scenario.get('stop_runtimes', {}),
            back_cylinder,
            best_deco_cyls,
        )
        best_scenario.pop('stop_runtimes', None)
        best_scenario['switch_depths'] = {'deco1': bd1_sd, 'deco2': bd2_sd}
        best_scenario['gas_plan'] = best_result.get('gas_plan')
        best_scenario['dive_mode'] = req.dive_mode
        best_scenario['gf_low'] = req.gf_low
        best_scenario['gf_high'] = req.gf_high

    response = {
        'best_deco1_o2': result['best_deco1_o2'],
        'best_deco1_switch_depth': result['best_deco1_switch_depth'],
        'best_deco2_o2': result['best_deco2_o2'],
        'best_deco2_switch_depth': result['best_deco2_switch_depth'],
        'best_bottom_time': result['best_bottom_time'],
        'back_gas': {'o2': req.back_gas_o2, 'he': req.back_gas_he or 0},
        'all_results': result['all_results'],
        'mixes_evaluated': result['mixes_evaluated'],
        'total_steps_checked': result['total_steps_checked'],
        'depth': req.depth,
        'dive_mode': req.dive_mode,
        'gf_low': req.gf_low,
        'gf_high': req.gf_high,
        'scenario': best_scenario,
        'gas_plan': best_result.get('gas_plan') if best_result else None,
        'binding_constraints': best_result.get('binding_constraints', []) if best_result else [],
    }
    return JSONResponse(content=_sanitize(response))


# ── Static files (after API routes) ───────────────────────────────────────────
app.mount("/", StaticFiles(directory="static", html=True), name="static")


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)
