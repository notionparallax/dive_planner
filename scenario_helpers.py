"""Scenario parsing helpers — pure data transforms, no Streamlit imports."""
import base64
import json
import math

import pandas as pd

_EMERGENCY_ASCENT_RATE = 18  # m/min — fast but survivable

_SCENARIO_COLS = ["enabled", "name", "depth", "time",
                  "lost", "gf_low", "gf_high", "ascent_rate", "sac_override"]


def _default_scenario_rows(lean_o2_pct: int, rich_o2_pct: int) -> list[dict]:
    """Return the default 10-scenario list as a list of dicts."""
    return [
        dict(enabled=True, name="Main",                   depth="+0", time="+0", lost="",     gf_low="",   gf_high="",   ascent_rate="", sac_override=""),
        dict(enabled=True, name="Longer",                 depth="+0", time="+3", lost="",     gf_low="",   gf_high="",   ascent_rate="", sac_override=""),
        dict(enabled=True, name="Deeper",                 depth="+3", time="+0", lost="",     gf_low="",   gf_high="",   ascent_rate="", sac_override=""),
        dict(enabled=True, name="D & L",                  depth="+3", time="+3", lost="",     gf_low="",   gf_high="",   ascent_rate="", sac_override=""),
        dict(enabled=True, name=f"No {lean_o2_pct}%",     depth="+0", time="+0", lost="lean", gf_low="",   gf_high="",   ascent_rate="", sac_override=""),
        dict(enabled=True, name=f"No {rich_o2_pct}%",     depth="+0", time="+0", lost="rich", gf_low="",   gf_high="",   ascent_rate="", sac_override=""),
        dict(enabled=True, name=f"No {lean_o2_pct}% (D)", depth="+3", time="+3", lost="lean", gf_low="",   gf_high="",   ascent_rate="", sac_override=""),
        dict(enabled=True, name=f"No {rich_o2_pct}% (D)", depth="+3", time="+3", lost="rich", gf_low="",   gf_high="",   ascent_rate="", sac_override=""),
        dict(enabled=True, name="Bounce",                 depth="+0", time="10", lost="",     gf_low="",   gf_high="",   ascent_rate="", sac_override=""),
        dict(enabled=True, name="Emergency",              depth="+0", time="+0", lost="",     gf_low="99", gf_high="99", ascent_rate="fast", sac_override=""),
    ]


def _parse_dim(val: str, base: int) -> int:
    """Parse a depth/time cell: '+3' -> base+3, '45' -> 45. Empty/None/NaN -> base."""
    import math
    if val is None:
        return base
    try:
        if math.isnan(float(val)):
            return base
    except (TypeError, ValueError):
        pass
    v = str(val).strip()
    if not v or v.lower() in ('nan', 'none', 'null'):
        return base
    if v.startswith('+') or v.startswith('-'):
        return base + int(v)
    return int(float(v))


def _resolve_lost(val: str) -> list[str]:
    """Parse lost column: '' -> [], 'lean' -> ['lean'], 'lean,rich' -> ['lean','rich']."""
    if val is None:
        return []
    v = str(val).strip()
    if not v or v.lower() in ('nan', 'none', 'null', 'false'):
        return []
    return [x.strip() for x in v.split(',') if x.strip()]


def _row_to_call_kwargs(row: dict, D: int, T: int, gfl: float, gfh: float,
                        base_ascent_rate, base_sac_bottom: float, base_sac_deco: float) -> dict:
    """Convert a scenario row dict to kwargs ready to pass to run_scenario."""
    depth = _parse_dim(row["depth"], D)
    time  = _parse_dim(row["time"],  T)
    lost_list = _resolve_lost(row.get("lost", ""))
    # deco_gases_lost: False, 'lean', 'rich', or ['lean','rich']
    if not lost_list:
        lost = False
    elif len(lost_list) == 1:
        lost = lost_list[0]
    else:
        lost = lost_list  # run_profile handles list in >=1.4.0

    def _clean(v):
        """Return stripped string, or '' if None/NaN/null."""
        if v is None: return ''
        s = str(v).strip()
        return '' if s.lower() in ('nan', 'none', 'null', '') else s

    gfl_raw = _clean(row.get("gf_low", ""))
    gfh_raw = _clean(row.get("gf_high", ""))
    row_gfl = float(gfl_raw) / 100 if gfl_raw else gfl
    row_gfh = float(gfh_raw) / 100 if gfh_raw else gfh

    ar_raw = _clean(row.get("ascent_rate", "")).lower()
    if ar_raw == "fast":
        row_ar = _EMERGENCY_ASCENT_RATE
    elif ar_raw:
        row_ar = float(ar_raw)
    else:
        row_ar = base_ascent_rate

    sac_raw = _clean(row.get("sac_override", ""))
    row_sac = float(sac_raw) if sac_raw else base_sac_bottom

    return dict(depth=depth, bottom_time=time, deco_gases_lost=lost,
                gf_low=row_gfl, gf_high=row_gfh,
                ascent_rate=row_ar, sac_bottom=row_sac, sac_deco=base_sac_deco)


def _scenarios_to_b64(df) -> str:
    return base64.urlsafe_b64encode(
        json.dumps(df.to_dict(orient='records')).encode()
    ).decode()


def _b64_to_scenarios_df(s: str, lean_o2_pct: int, rich_o2_pct: int):
    try:
        rows = json.loads(base64.urlsafe_b64decode(s.encode()).decode())
        import pandas as pd
        return pd.DataFrame(rows)[_SCENARIO_COLS]
    except Exception:
        import pandas as pd
        return pd.DataFrame(_default_scenario_rows(lean_o2_pct, rich_o2_pct))


def _build_contingency_specs(rows, D: int, gfl: float, gfh: float, ar, sb: float, sd: float) -> list[dict]:
    """Convert enabled scenario rows into contingency_scenarios dicts for find_max_bottom_time."""
    ar_val = list(ar) if isinstance(ar, tuple) and ar and isinstance(ar[0], tuple) else ar
    specs = []
    for row in rows:
        if row.get("enabled") is False:
            continue
        raw_time = str(row.get("time", "")).strip()
        if raw_time and not raw_time.lower().startswith(('nan', 'none', 'null')):
            is_relative = raw_time.startswith('+') or raw_time.startswith('-')
            time_val = int(float(raw_time))
            time_offset = time_val if is_relative else None
            time_absolute = None if is_relative else time_val
        else:
            time_offset, time_absolute = 0, None

        kw = _row_to_call_kwargs(row, D, 0, gfl, gfh, ar_val, sb, sd)
        specs.append({
            'depth': kw['depth'],
            'time_offset': time_offset if time_offset is not None else 0,
            'time_absolute': time_absolute,
            'lost': kw['deco_gases_lost'],
            'gf_low': kw['gf_low'],
            'gf_high': kw['gf_high'],
            'ascent_rate': kw['ascent_rate'] if kw['ascent_rate'] != ar_val else None,
            'sac_bottom': kw['sac_bottom'] if kw['sac_bottom'] != sb else None,
            'sac_deco': kw['sac_deco'] if kw['sac_deco'] != sd else None,
        })
    return specs

