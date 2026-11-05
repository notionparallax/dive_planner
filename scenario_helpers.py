"""Scenario parsing helpers — pure data transforms, no Streamlit imports."""
import base64
import json
import math

import pandas as pd

_EMERGENCY_ASCENT_RATE = 18  # m/min — fast but survivable

_SCENARIO_COLS = ["enabled", "print", "name", "short", "depth", "time",
                  "lost", "gf_low", "gf_high", "ascent_rate", "sac_override"]

# Columns that only affect the printed sticker, not the dive calculation —
# kept out of the compute cache key so toggling them doesn't re-run scenarios.
_STICKER_COLS = ("print", "short")


def _default_short(name: str) -> str:
    """Best-effort sticker heading for a scenario with no explicit short name."""
    n = str(name or "").strip()
    if n.lower().startswith("no "):
        rest = n[3:].strip()
        deep = rest.endswith("(D)")
        rest = rest.replace("(D)", "").replace("%", "").strip()
        return f"-{rest}{'D' if deep else ''}"
    return n[:5]


def _row(name, short, depth, time, lost="", printed=True, gf_low="", gf_high="", ascent_rate=""):
    return dict(enabled=True, print=printed, name=name, short=short, depth=depth, time=time,
                lost=lost, gf_low=gf_low, gf_high=gf_high, ascent_rate=ascent_rate, sac_override="")


def _default_scenario_rows(lean_o2_pct: int, rich_o2_pct: int,
                            lean_enabled: bool = True, rich_enabled: bool = True) -> list[dict]:
    """Return the default scenario list as a list of dicts.

    "No X%" (lost-gas) contingency rows are only generated for a gas that's
    actually part of the plan (lean_enabled/rich_enabled) — there's nothing to
    lose if the cylinder was never carried.

    `print` picks the six columns that go on the sticker by default (Main,
    D&L, each deeper+longer lost-gas, Bounce, Emergency) — if you're really
    losing a deco gas, the conservative D+3/T+3 version is the one to have on
    the slate. `short` is the sticker heading.
    """
    rows = [
        _row("Main",   "Main", "+0", "+0"),
        _row("Longer", "L",    "+0", "+3", printed=False),
        _row("Deeper", "D",    "+3", "+0", printed=False),
        _row("D & L",  "D&L",  "+3", "+3"),
    ]
    if lean_enabled:
        rows.append(_row(f"No {lean_o2_pct}%", f"-{lean_o2_pct}", "+0", "+0", lost="lean", printed=False))
    if rich_enabled:
        rows.append(_row(f"No {rich_o2_pct}%", f"-{rich_o2_pct}", "+0", "+0", lost="rich", printed=False))
    if lean_enabled:
        rows.append(_row(f"No {lean_o2_pct}% (D)", f"-{lean_o2_pct}D", "+3", "+3", lost="lean"))
    if rich_enabled:
        rows.append(_row(f"No {rich_o2_pct}% (D)", f"-{rich_o2_pct}D", "+3", "+3", lost="rich"))
    rows.append(_row("Bounce",    "Bnce", "+0", "10"))
    rows.append(_row("Emergency", "99",   "+0", "+0", gf_low="99", gf_high="99", ascent_rate="fast"))
    return rows


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


def _b64_to_scenarios_df(s: str, lean_o2_pct: int, rich_o2_pct: int,
                          lean_enabled: bool = True, rich_enabled: bool = True):
    """Decode scenarios from the URL, salvaging as much as possible.

    Rows from older URLs (missing columns added since, e.g. print/short) are
    filled in rather than discarded: a row whose name matches a default
    scenario takes that default's values, anything else gets neutral blanks.
    Unknown keys are dropped; non-dict rows are skipped. Only if nothing at all
    can be decoded do we fall back to the defaults.
    """
    defaults = _default_scenario_rows(lean_o2_pct, rich_o2_pct, lean_enabled, rich_enabled)
    try:
        raw = s.encode()
        raw += b"=" * (-len(raw) % 4)  # tolerate stripped base64 padding
        rows = json.loads(base64.urlsafe_b64decode(raw).decode())
    except Exception:
        return pd.DataFrame(defaults)[_SCENARIO_COLS]
    if isinstance(rows, dict):
        rows = [rows]
    if not isinstance(rows, list):
        return pd.DataFrame(defaults)[_SCENARIO_COLS]

    by_name = {d["name"]: d for d in defaults}
    out = []
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        name = row.get("name")
        name = f"Scenario {i + 1}" if name is None or str(name).strip() in ("", "nan", "None") else str(name)
        fallback = by_name.get(name, {})
        fixed = {}
        for col in _SCENARIO_COLS:
            if col in row and row[col] is not None:
                fixed[col] = row[col]
            elif col in fallback:
                fixed[col] = fallback[col]
            elif col in ("enabled", "print"):
                fixed[col] = True
            elif col == "short":
                fixed[col] = _default_short(name)
            else:
                fixed[col] = ""
        fixed["name"] = name
        for col in ("enabled", "print"):
            v = fixed[col]
            if isinstance(v, str):
                fixed[col] = v.strip().lower() not in ("0", "false", "no", "")
            else:
                fixed[col] = bool(v)
        for col in _SCENARIO_COLS:
            if col not in ("enabled", "print") and not isinstance(fixed[col], str):
                v = fixed[col]
                fixed[col] = "" if isinstance(v, float) and math.isnan(v) else str(v)
        out.append(fixed)
    if not out:
        return pd.DataFrame(defaults)[_SCENARIO_COLS]
    return pd.DataFrame(out)[_SCENARIO_COLS]


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

