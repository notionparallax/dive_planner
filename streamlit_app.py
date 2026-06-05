"""Dive planner web interface."""
import io
import csv as _csv
import os
import sys

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dive_plan import (  # noqa: E402
    ASCENT_RATE,
    BACK_GAS,
    BACK_GAS_PRESSURE,
    BACK_GAS_VOL,
    DECO_50_PRESSURE,
    DECO_50_VOL,
    DECO_O2_PRESSURE,
    DECO_O2_VOL,
    DESCENT_RATE,
    FILL_TEMP_C,
    GF_HIGH,
    GF_LOW,
    SAC_BOTTOM,
    SAC_DECO,
    SURFACE_PRESSURE,
    WATER_TEMP_C,
    _gas_density_gl,
    find_max_bottom_time,
    run_scenario,
)
from gas_planning import calc_switch_depth  # noqa: E402

st.set_page_config(
    page_title="Dive Planner",
    page_icon="🤿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── URL query param helpers ──────────────────────────────────────────────────
_qp = st.query_params

def _qpi(key, default):
    try: return int(_qp[key])
    except: return default

def _qpf(key, default):
    try: return float(_qp[key])
    except: return default

def _qpb(key, default):
    try: return _qp[key].lower() in ('1', 'true', 'yes')
    except: return default


# ─── Sidebar inputs ───────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🤿 Dive Planner")

    st.subheader("Depth & Time")
    depth = int(st.number_input("Depth (m)", min_value=10, max_value=80, value=_qpi("depth", 48), step=1))
    auto_time = st.checkbox("Auto bottom time", value=_qpb("auto_time", True),
                            help="Find max bottom time where all contingency scenarios (deeper, longer, lost deco gas) have gas remaining")
    manual_bt_val = None
    if not auto_time:
        manual_bt_val = int(st.number_input("Bottom time (min)", min_value=5, max_value=120, value=_qpi("manual_bt", 31), step=1))

    st.subheader("Gases & Cylinders")
    _gas_defaults = pd.DataFrame({
        "Gas":     ["Back",  "Lean",  "Rich"],
        "O2%":     [_qpi("o2",  21),  _qpi("lo2", 50),  _qpi("ro2", 100)],
        "He%":     [_qpi("he",   0),  _qpi("lhe",  0),  _qpi("rhe",   0)],
        "Bar":     [_qpi("bgp", 230), _qpi("lp",  200), _qpi("rp",  200)],
        "Litres":  [_qpf("bgv", 24.4),_qpf("lv",  11.1),_qpf("rv",  11.1)],
    })
    _gas_table = st.data_editor(
        _gas_defaults,
        column_config={
            "Gas":    st.column_config.TextColumn(disabled=True, width="small"),
            "O2%":    st.column_config.NumberColumn(min_value=4,   max_value=100, step=1,   format="%d", width="small"),
            "He%":    st.column_config.NumberColumn(min_value=0,   max_value=90,  step=1,   format="%d", width="small"),
            "Bar":    st.column_config.NumberColumn(min_value=50,  max_value=300, step=5,   format="%d", width="small"),
            "Litres": st.column_config.NumberColumn(min_value=3.0, max_value=30.0,step=0.1, format="%.1f", width="small"),
        },
        hide_index=True,
        use_container_width=True,
        key="gas_table",
        num_rows="fixed",
    )
    o2           = int(_gas_table.iloc[0]["O2%"])
    he           = int(_gas_table.iloc[0]["He%"])
    back_gas_pressure = int(_gas_table.iloc[0]["Bar"])
    back_gas_vol = float(_gas_table.iloc[0]["Litres"])
    lean_o2      = int(_gas_table.iloc[1]["O2%"])
    lean_he      = int(_gas_table.iloc[1]["He%"])
    lean_switch  = int(calc_switch_depth(lean_o2 / 100.0))
    deco_50_pressure = int(_gas_table.iloc[1]["Bar"])
    deco_50_vol  = float(_gas_table.iloc[1]["Litres"])
    rich_o2      = int(_gas_table.iloc[2]["O2%"])
    rich_he      = int(_gas_table.iloc[2]["He%"])
    rich_switch  = int(calc_switch_depth(rich_o2 / 100.0))
    deco_o2_pressure = int(_gas_table.iloc[2]["Bar"])
    deco_o2_vol  = float(_gas_table.iloc[2]["Litres"])
    back_gas = (o2, he)

    st.subheader("Deco Model")
    col1, col2 = st.columns(2)
    gf_low = col1.number_input("GF low %", min_value=10, max_value=100, value=_qpi("gfl", 50), step=5) / 100
    gf_high = col2.number_input("GF high %", min_value=10, max_value=100, value=_qpi("gfh", 80), step=5) / 100

    st.subheader("Rates")
    col1, col2 = st.columns(2)
    descent_rate = int(col1.number_input("Descent (m/min)", min_value=5, max_value=40, value=_qpi("dr", 20), step=1))
    ascent_rate = int(col2.number_input("Ascent (m/min)", min_value=3, max_value=20, value=_qpi("ar", 10), step=1))

    st.subheader("Descent Stop (S-drill)")
    enable_stop = st.checkbox("Enable S-drill stop", value=_qpb("sdrill", False))
    descent_stops_tuple = None
    s_depth = _qpi("sd", 5)
    s_time = _qpi("st", 1)
    if enable_stop:
        col1, col2 = st.columns(2)
        s_depth = int(col1.number_input("Depth (m)", min_value=3, max_value=20, value=s_depth, step=1))
        s_time = int(col2.number_input("Duration (min)", min_value=1, max_value=30, value=s_time, step=1))
        descent_stops_tuple = ((s_depth, s_time),)

    st.subheader("Gas Consumption")
    col1, col2 = st.columns(2)
    sac_bottom = int(col1.number_input("SAC bottom (L/min)", min_value=10, max_value=40, value=_qpi("sac_bot", 20), step=1))
    sac_deco = int(col2.number_input("SAC deco (L/min)", min_value=10, max_value=30, value=_qpi("sac_dec", 17), step=1))

    with st.expander("⚙️ Settings", expanded=False):
        st.caption("Warning thresholds")
        ppo2_bottom = st.number_input(
            "ppO₂ bottom limit (bar)",
            min_value=1.0, max_value=1.6, value=_qpf("ppo2_bot", 1.4), step=0.05, format="%.2f",
            help="Back gas ppO₂ above this triggers a warning on the main dive and standard scenarios. GUE/WKPP standard: 1.4 bar.",
        )
        ppo2_contingency_tol = st.number_input(
            "Contingency ppO₂ tolerance (bar)",
            min_value=0.0, max_value=0.3, value=_qpf("ppo2_ctol", 0.2), step=0.05, format="%.2f",
            help=f"Extra headroom added to the bottom limit for contingency scenarios (Deeper / Longer / D&L). "
                 f"At defaults: contingency limit = {_qpf('ppo2_bot', 1.4):.2f} + {_qpf('ppo2_ctol', 0.2):.2f} = {_qpf('ppo2_bot', 1.4) + _qpf('ppo2_ctol', 0.2):.2f} bar.",
        )
        density_limit = st.number_input(
            "Gas density limit (g/L)",
            min_value=4.0, max_value=10.0, value=_qpf("dens_lim", 6.2), step=0.1, format="%.1f",
            help="Warn if back gas density exceeds this value. GUE/WKPP limit is 6.2 g/L; above this CNS risk increases.",
        )
        cns_warn = st.number_input(
            "CNS warn threshold (%)",
            min_value=50, max_value=100, value=_qpi("cns_warn", 80), step=5,
            help="Warn if CNS oxygen toxicity reaches this percentage in any scenario. Single-dive limit is 80%; NOAA allows 100% for working divers.",
        )

# Write URL params after sidebar
st.query_params.update({
    "o2": o2, "he": he, "depth": depth,
    "auto_time": int(auto_time), "manual_bt": manual_bt_val or 31,
    "bgp": back_gas_pressure, "bgv": back_gas_vol,
    "lp": deco_50_pressure, "lv": deco_50_vol,
    "rp": deco_o2_pressure, "rv": deco_o2_vol,
    "lo2": lean_o2, "lhe": lean_he,
    "ro2": rich_o2, "rhe": rich_he,
    "gfl": int(gf_low * 100), "gfh": int(gf_high * 100),
    "dr": descent_rate, "ar": ascent_rate,
    "sdrill": int(enable_stop),
    "sd": s_depth if enable_stop else 5,
    "st": s_time if enable_stop else 1,
    "sac_bot": sac_bottom, "sac_dec": sac_deco,
    "ppo2_bot": ppo2_bottom, "ppo2_ctol": ppo2_contingency_tol,
    "dens_lim": density_limit, "cns_warn": cns_warn,
})


# ─── Compute ──────────────────────────────────────────────────────────────────
@st.cache_data
def _get_max_time(depth, back_gas, bgp, d50p, do2p, bgv, d50v, do2v, gfl, gfh, dr, ar, sb, sd,
                  lean_gas, lean_switch, rich_gas, rich_switch):
    return find_max_bottom_time(
        depth, back_gas,
        back_gas_pressure=bgp, deco_50_pressure=d50p, deco_o2_pressure=do2p,
        back_gas_vol=bgv, deco_50_vol=d50v, deco_o2_vol=do2v,
        gf_low=gfl, gf_high=gfh, descent_rate=dr, ascent_rate=ar,
        sac_bottom=sb, sac_deco=sd,
        lean_gas=lean_gas, lean_switch=lean_switch,
        rich_gas=rich_gas, rich_switch=rich_switch,
    )


_EMERGENCY_ASCENT_RATE = 18  # m/min — fast but survivable


@st.cache_data
def _compute_scenarios(back_gas, depth, T, bgp, d50p, do2p, bgv, d50v, do2v, gfl, gfh, dr, ar, sb, sd, dst,
                       lean_gas, lean_switch, rich_gas, rich_switch):
    D = depth
    descent_stops = list(dst) if dst else None
    scenario_defs = [
        (D,     T,      False,    "Main"),
        (D,     T + 3,  False,    "Longer"),
        (D + 3, T,      False,    "Deeper"),
        (D + 3, T + 3,  False,    "D & L"),
        (D,     T,      "lean",   f"no {lean_gas[0]}%"),
        (D,     T,      "rich",   f"no {rich_gas[0]}%"),
        (D + 3, T + 3,  "lean",   f"no {lean_gas[0]}% (D)"),
        (D + 3, T + 3,  "rich",   f"no {rich_gas[0]}% (D)"),
        (D,     10,     False,    "Bounce"),
    ]
    results = []
    for d, bt, lost, tag in scenario_defs:
        r = run_scenario(
            tag, d, bt, deco_gases_lost=lost,
            back_gas=back_gas,
            back_gas_pressure=bgp, deco_50_pressure=d50p, deco_o2_pressure=do2p,
            back_gas_vol=bgv, deco_50_vol=d50v, deco_o2_vol=do2v,
            gf_low=gfl, gf_high=gfh,
            descent_rate=dr, ascent_rate=ar,
            sac_bottom=sb, sac_deco=sd,
            lean_gas=lean_gas, lean_switch=lean_switch,
            rich_gas=rich_gas, rich_switch=rich_switch,
            descent_stops=descent_stops,
        )
        r["leave_time"] = bt
        r["tag"] = tag
        results.append(r)

    # Emergency scenario: GF 99/99, fast ascent, main depth/time
    emerg = run_scenario(
        "Emergency\n(GF99/99)", D, T, deco_gases_lost=False,
        back_gas=back_gas,
        back_gas_pressure=bgp, deco_50_pressure=d50p, deco_o2_pressure=do2p,
        back_gas_vol=bgv, deco_50_vol=d50v, deco_o2_vol=do2v,
        gf_low=0.99, gf_high=0.99,
        descent_rate=dr, ascent_rate=_EMERGENCY_ASCENT_RATE,
        sac_bottom=sb, sac_deco=sd,
        lean_gas=lean_gas, lean_switch=lean_switch,
        rich_gas=rich_gas, rich_switch=rich_switch,
        descent_stops=descent_stops,
    )
    emerg["leave_time"] = T
    emerg["tag"] = "Emergency\n(GF99/99)"
    results.append(emerg)

    return results, scenario_defs


with st.spinner("Computing…"):
    T = (
        _get_max_time(depth, back_gas, back_gas_pressure, deco_50_pressure, deco_o2_pressure,
                      back_gas_vol, deco_50_vol, deco_o2_vol,
                      gf_low, gf_high, descent_rate, ascent_rate, sac_bottom, sac_deco,
                      (lean_o2, lean_he), lean_switch, (rich_o2, rich_he), rich_switch)
        if auto_time else manual_bt_val
    )
    results, scenario_defs = _compute_scenarios(
        back_gas, depth, T,
        back_gas_pressure, deco_50_pressure, deco_o2_pressure,
        back_gas_vol, deco_50_vol, deco_o2_vol,
        gf_low, gf_high, descent_rate, ascent_rate, sac_bottom, sac_deco,
        descent_stops_tuple,
        (lean_o2, lean_he), lean_switch, (rich_o2, rich_he), rich_switch,
    )

# ─── Header ───────────────────────────────────────────────────────────────────
st.title(f"🤿 {depth}m | Tx {o2}/{he} | GF {int(gf_low*100)}/{int(gf_high*100)}")
st.caption(
    f"Max bottom time: **{T}'** | Descent: {descent_rate} m/min | "
    f"Ascent: {ascent_rate} m/min | SAC: {sac_bottom}/{sac_deco} L/min"
)

# ─── Safety warnings + column header emojis ──────────────────────────────────
_CNS_WARN = float(cns_warn)
_DENSITY_WARN = float(density_limit)

# ppO2 limit: contingency scenarios get the bottom limit + tolerance
_CONTINGENCY_TAGS = {"Longer", "Deeper", "D & L", "no lean%(D)", "no rich%(D)"}
def _ppo2_limit_for(tag: str) -> float:
    if any(t in tag for t in _CONTINGENCY_TAGS):
        return float(ppo2_bottom) + float(ppo2_contingency_tol)
    return float(ppo2_bottom)

# Per-result warning strings (for expander) and emoji sets (for column headers)
_col_warnings: list[list[str]] = [[] for _ in results]
for i, r in enumerate(results):
    tag = r["tag"].replace("\n", " ")
    if r["cns"] >= _CNS_WARN:
        _col_warnings[i].append(f"⚠️ **{tag}**: CNS {r['cns']:.0f}% (limit {int(_CNS_WARN)}%)")
    if r["max_gas_density"] >= _DENSITY_WARN:
        _col_warnings[i].append(
            f"⚠️ **{tag}**: gas density {r['max_gas_density']:.2f} g/L "
            f"(GUE/WKPP limit {_DENSITY_WARN} g/L)"
        )
    # Back gas ppO2 at depth
    abs_p = SURFACE_PRESSURE + r["depth"] / 10.0
    ppo2 = (back_gas[0] / 100.0) * abs_p
    _limit = _ppo2_limit_for(tag)
    if ppo2 > _limit:
        _col_warnings[i].append(
            f"⚠️ **{tag}**: back gas ppO₂ {ppo2:.2f} bar at {r['depth']}m "
            f"(limit {_limit:.2f} bar)"
        )

# Constraining scenario: first 8 results match the auto-timer contingency scenarios
_constraint_scenarios = results[:8]
def _gas_margin(r):
    lost = r.get("deco_gases_lost", False)
    margins = [r["back_remaining_bar"]]
    if lost not in (True, "lean"):
        margins.append(r["lean_remaining_bar"])
    if lost not in (True, "rich"):
        margins.append(r["rich_remaining_bar"])
    return min(margins)

_constraint_idx = min(range(len(_constraint_scenarios)), key=lambda i: _gas_margin(_constraint_scenarios[i]))

all_warnings = [w for ws in _col_warnings for w in ws]
if all_warnings:
    with st.expander(f"⚠️ {len(all_warnings)} warning(s)", expanded=True):
        for w in all_warnings:
            st.markdown(w)

# Build column labels with warning emoji and constraining scenario marker
col_labels = []
for i, r in enumerate(results):
    prefix = "🖐️ " if i == _constraint_idx else ("⚠️ " if _col_warnings[i] else "")
    col_labels.append(f"{prefix}{r['leave_time']}'\n{r['depth']}m\n{r['tag']}")

# ─── Planning table ───────────────────────────────────────────────────────────
st.subheader("Planning Table")


# Determine all deco stop depths across all scenarios
all_stop_depths = sorted(
    {d for r in results for d, t in r["deco_stops"]}, reverse=True
)

# Determine depth rows
depth_set = sorted({r["depth"] for r in results}, reverse=True)

# Set of all deco stop row labels (used to avoid coloring non-stop rows like "48m", "Total deco" etc.)
stop_depth_labels = {f"{int(sd)}m" for sd in all_stop_depths}

table_rows = {}

# Depth rows (leave time)
for dd in depth_set:
    row = []
    for r in results:
        row.append(str(r["bottom_time"]) if r["depth"] == dd else "")
    table_rows[f"{int(dd)}m"] = row

# Deco stop rows — clean labels without * or - prefix
for sd in all_stop_depths:
    label = f"{int(sd)}m"
    row = []
    for r in results:
        st_val = next((t for dp, t in r["deco_stops"] if dp == sd), None)
        if st_val is None:
            row.append("")
        else:
            rt = r["stop_runtimes"].get(sd)
            row.append(f"{rt:.0f} ({st_val:.0f})" if rt is not None else f"({st_val:.0f})")
    table_rows[label] = row

# Total time row
table_rows["0m"] = [f"{r['total_time']:.0f}" for r in results]
table_rows[" "] = [""] * len(results)
table_rows["Total deco"] = [f"{r['total_deco']:.0f}" for r in results]
table_rows["Runtime"] = [f"{r['total_time']:.0f}" for r in results]
table_rows["Turn pressure"] = [f"{r['min_gas']['bar_at_turn']:.0f}" for r in results]
table_rows["  "] = [""] * len(results)
table_rows["OTU"] = [f"{r['otu']:.0f}" for r in results]
table_rows["CNS %"] = [f"{r['cns']:.0f}%" for r in results]
table_rows["END"] = [f"{(r['depth']+10)*(1-back_gas[1]/100)-10:.0f}m" for r in results]
table_rows["PO2"] = [f"{(SURFACE_PRESSURE + r['depth']/10)*(back_gas[0]/100):.2f}" for r in results]
table_rows["Gas density"] = [f"{_gas_density_gl(back_gas[0], back_gas[1], r['depth']):.2f} g/L" for r in results]
table_rows["   "] = [""] * len(results)
table_rows["Back gas left"] = [f"{r['back_remaining_bar']:.0f} bar" for r in results]
table_rows[f"Lean ({lean_o2}/{lean_he})"] = [
    "--" if r["deco_gases_lost"] in (True, "lean") else f"{r['lean_remaining_bar']:.0f} bar"
    for r in results
]
table_rows[f"Rich ({rich_o2}/{rich_he})"] = [
    "--" if r["deco_gases_lost"] in (True, "rich") else f"{r['rich_remaining_bar']:.0f} bar"
    for r in results
]

df = pd.DataFrame(table_rows, index=col_labels).T
df = df.reset_index()
df = df.rename(columns={"index": ""})

col_to_lost = {label: r["deco_gases_lost"] for r, label in zip(results, col_labels)}

def _color_cells(data):
    styles = pd.DataFrame("", index=data.index, columns=data.columns)
    for i in range(len(data)):
        row_label = data.iloc[i, 0]
        # "0m" (surface/total time row) gets richest available gas color
        is_surface = row_label == "0m"
        if row_label not in stop_depth_labels and not is_surface:
            continue
        try:
            row_depth = 0 if is_surface else int(row_label.rstrip('m'))
        except (ValueError, AttributeError):
            continue
        for j, col_name in enumerate(data.columns):
            if j == 0:
                continue
            lost = col_to_lost.get(col_name, False)
            if row_depth <= rich_switch:
                # Rich gas zone (incl. surface): green if rich available, yellow if rich is lost
                if lost not in (True, "rich"):
                    styles.iloc[i, j] = "background-color: rgba(0,180,0,0.18)"
                else:
                    styles.iloc[i, j] = "background-color: rgba(200,200,0,0.18)"
            elif row_depth <= lean_switch:
                # Lean gas zone: yellow if lean available
                if lost not in (True, "lean"):
                    styles.iloc[i, j] = "background-color: rgba(200,200,0,0.18)"
    return styles

styled_df = df.style.apply(_color_cells, axis=None)
_col_config = {"": st.column_config.TextColumn(width="medium")}
for i, lbl in enumerate(col_labels):
    help_parts = []
    if i == _constraint_idx:
        help_parts.append("🖐️ Constraining scenario — tightest gas margin")
    for w in _col_warnings[i]:
        # strip markdown bold for tooltip
        help_parts.append(w.replace("**", ""))
    _col_config[lbl] = st.column_config.TextColumn(
        width="small",
        help="\n\n".join(help_parts) if help_parts else None,
    )
st.dataframe(
    styled_df,
    column_config=_col_config,
    hide_index=True,
    width='stretch',
)

# ─── Scenario selector ────────────────────────────────────────────────────────
tags = [r["tag"] for r in results]
selected_tag = st.radio(
    "Scenario (controls ceiling band + gas chart):",
    tags, horizontal=True, index=0,
)
sel = next(r for r in results if r["tag"] == selected_tag)

# ─── Charts ───────────────────────────────────────────────────────────────────
st.subheader("Dive Profiles")

COLORS = [
    "#4c9be8",  # Main - blue
    "#56b84b",  # Longer - green
    "#f0922b",  # Deeper - orange
    "#ae79d4",  # D & L - purple
    "#e377c2",  # no 50% - pink
    "#d62728",  # no O2 - red
    "#f7b6d2",  # no 50% (D) - light pink
    "#ff9896",  # no O2 (D) - light red
    "#8c8c8c",  # Bounce - grey
    "#ff4444",  # Emergency - bright red
]


def _hex_to_rgba(hex_color: str, alpha: float = 0.15) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"


fig = make_subplots(
    rows=2, cols=1,
    shared_xaxes=True,
    subplot_titles=("Depth Profile", "Gas Pressure"),
    vertical_spacing=0.08,
    row_heights=[0.6, 0.4],
)

# ── Depth profile traces ──────────────────────────────────────────────────────
for i, r in enumerate(results):
    is_sel = r["tag"] == selected_tag
    color = COLORS[i]
    fig.add_trace(
        go.Scatter(
            x=r["times"],
            y=r["depths"],
            mode="lines",
            name=r["tag"],
            line=dict(color=color, width=3 if is_sel else 1.5),
            opacity=1.0 if is_sel else 0.4,
            legendgroup=r["tag"],
            legendgrouptitle_text=None,
            showlegend=True,
            hovertemplate=(
                f"<b>{r['tag']}</b><br>"
                "T+%{x:.0f} min<br>"
                "Depth: %{y:.0f}m<extra></extra>"
            ),
        ),
        row=1, col=1,
    )

# ── Ceiling band for selected scenario ───────────────────────────────────────
cp = sel.get("ceiling_profile", [])
if cp:
    cp_deco = [(t, d, c) for t, d, c in cp if c > 0.5]
    if cp_deco:
        t_vals = [t for t, d, c in cp_deco]
        d_vals = [d for t, d, c in cp_deco]
        c_vals = [c for t, d, c in cp_deco]
        sel_color = COLORS[tags.index(selected_tag)]

        fig.add_trace(
            go.Scatter(
                x=t_vals, y=c_vals,
                mode="lines",
                name=f"Ceiling ({selected_tag})",
                line=dict(color=sel_color, width=1.5, dash="dash"),
                legendgroup=selected_tag,
                showlegend=True,
                hovertemplate="Ceiling: %{y:.0f}m @ T+%{x:.0f}min<extra></extra>",
            ),
            row=1, col=1,
        )

        fig.add_trace(
            go.Scatter(
                x=t_vals + t_vals[::-1],
                y=c_vals + d_vals[::-1],
                fill="toself",
                fillcolor=_hex_to_rgba(sel_color, 0.15),
                line=dict(color="rgba(0,0,0,0)"),
                showlegend=False,
                hoverinfo="skip",
                name="_ceiling_fill",
            ),
            row=1, col=1,
        )

# ── Gas switch depth markers ──────────────────────────────────────────────────
fig.add_hline(
    y=lean_switch,
    line=dict(color="#56b84b", width=1, dash="dot"),
    annotation_text=f"Lean {lean_o2}/{lean_he} @ {lean_switch}m",
    annotation_position="top right",
    row=1, col=1,
)
fig.add_hline(
    y=rich_switch,
    line=dict(color="#17becf", width=1, dash="dot"),
    annotation_text=f"Rich {rich_o2}/{rich_he} @ {rich_switch}m",
    annotation_position="top right",
    row=1, col=1,
)

# ── Gas pressure traces ───────────────────────────────────────────────────────
GAS_COLORS = {"back": "#4c9be8", "lean": "#56b84b", "rich": "#17becf"}
GAS_LABELS = {"back": "Back gas", "lean": f"Lean ({lean_o2}/{lean_he})", "rich": f"Rich ({rich_o2}/{rich_he})"}

gpp = sel.get("gas_pressure_profile", {})
for gas_key, color in GAS_COLORS.items():
    if gas_key not in gpp:
        continue
    pts = gpp[gas_key]
    fig.add_trace(
        go.Scatter(
            x=[t for t, p in pts],
            y=[p for t, p in pts],
            mode="lines",
            name=GAS_LABELS[gas_key],
            line=dict(color=color, width=2),
            legendgroup=f"gas_{gas_key}",
            showlegend=True,
            hovertemplate=f"<b>{GAS_LABELS[gas_key]}</b>: %{{y:.0f}} bar @ T+%{{x:.0f}}min<extra></extra>",
        ),
        row=2, col=1,
    )

# Turn pressure reference line
turn_p = sel["min_gas"]["bar_at_turn"]
fig.add_hline(
    y=turn_p,
    line=dict(color="#d62728", width=1, dash="dash"),
    annotation_text=f"Turn: {turn_p:.0f} bar",
    annotation_position="top right",
    row=2, col=1,
)

# ── Layout ────────────────────────────────────────────────────────────────────
fig.update_layout(
    height=680,
    template="plotly_dark",
    margin=dict(l=60, r=80, t=60, b=40),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1,
    ),
    hovermode="x",
)
fig.update_yaxes(autorange="reversed", title_text="Depth (m)", row=1, col=1)
fig.update_yaxes(title_text="Pressure (bar)", rangemode="tozero", row=2, col=1)
fig.update_xaxes(title_text="Time (min)", row=2, col=1)

st.plotly_chart(fig, width='stretch')

# ─── CSV download ─────────────────────────────────────────────────────────────
st.subheader("Export")


def _build_csv_bytes():
    buf = io.StringIO()
    w = _csv.writer(buf)
    w.writerow([f"PLANNING TABLE: {depth}m | Tx {back_gas[0]}/{back_gas[1]} | ZHL-16C-GF {int(gf_low*100)}/{int(gf_high*100)}"])
    w.writerow([f"Max bottom time (double ascent): {T}'"])
    w.writerow([])
    w.writerow([""] + [f"{r['leave_time']}'" if r['tag'] != 'Bounce' else "" for r in results])
    w.writerow([""] + [f"{r['depth']}m" for r in results])
    w.writerow([""] + [r["tag"] for r in results])
    w.writerow([])
    for dd in sorted({r["depth"] for r in results}, reverse=True):
        w.writerow([f"{int(dd)}m"] + [str(r["bottom_time"]) if r["depth"] == dd else "" for r in results])
    for sd in sorted({d for r in results for d, t in r["deco_stops"]}, reverse=True):
        lbl = f"{int(sd)}m"
        row = [lbl]
        for r in results:
            st_val = next((t for dp, t in r["deco_stops"] if dp == sd), None)
            if st_val is None:
                row.append("")
            else:
                rt = r["stop_runtimes"].get(sd)
                row.append(f"{rt:.0f} ({st_val:.0f})" if rt is not None else f"({st_val:.0f})")
        w.writerow(row)
    w.writerow(["0m"] + [f"{r['total_time']:.0f}" for r in results])
    w.writerow([])
    w.writerow(["Depth"] + [r["depth"] for r in results])
    w.writerow(["Total deco"] + [f"{r['total_deco']:.0f}" for r in results])
    w.writerow(["Runtime"] + [f"{r['total_time']:.0f}" for r in results])
    w.writerow(["Turn pressure"] + [f"{r['min_gas']['bar_at_turn']:.0f}" for r in results])
    w.writerow([])
    w.writerow(["OTU"] + [f"{r['otu']:.0f}" for r in results])
    w.writerow(["CNS %"] + [f"{r['cns']:.0f}%" for r in results])
    w.writerow(["END"] + [f"{(r['depth']+10)*(1-back_gas[1]/100)-10:.0f}m" for r in results])
    w.writerow(["PO2"] + [f"{(SURFACE_PRESSURE + r['depth']/10)*(back_gas[0]/100):.2f}" for r in results])
    w.writerow(["Gas density g/L"] + [f"{_gas_density_gl(back_gas[0], back_gas[1], r['depth']):.2f}" for r in results])
    w.writerow([])
    w.writerow(["Back gas left"] + [f"{r['back_remaining_bar']:.0f}" for r in results])
    w.writerow([f"Lean ({lean_o2}/{lean_he})"] + ["--" if r["deco_gases_lost"] in (True, "lean") else f"{r['lean_remaining_bar']:.0f}" for r in results])
    w.writerow([f"Rich ({rich_o2}/{rich_he})"] + ["--" if r["deco_gases_lost"] in (True, "rich") else f"{r['rich_remaining_bar']:.0f}" for r in results])
    w.writerow([])
    w.writerow(["ASSUMPTIONS"])
    w.writerow(["SAC", f"{sac_bottom} L/min (bottom)", f"{sac_deco} L/min (deco)"])
    w.writerow(["Descent", f"{descent_rate} m/min", f"Ascent {ascent_rate} m/min"])
    if descent_stops_tuple:
        for ds_d, ds_t in descent_stops_tuple:
            w.writerow(["Descent stop", f"{ds_t} min @ {ds_d}m (S-drill)"])
    hot = (273.15 + FILL_TEMP_C) / (273.15 + WATER_TEMP_C)
    w.writerow([f"Hot fill ({FILL_TEMP_C}°C→{WATER_TEMP_C}°C)",
                f"back {back_gas_pressure * hot:.0f} bar",
                f"lean {deco_50_pressure * hot:.0f} bar",
                f"rich {deco_o2_pressure * hot:.0f} bar"])
    return buf.getvalue().encode("utf-8-sig")


fname = f"plan_{depth}m_Tx{back_gas[0]}_{back_gas[1]}_{back_gas_pressure}bar.csv"
st.download_button(
    label="⬇️ Download CSV",
    data=_build_csv_bytes(),
    file_name=fname,
    mime="text/csv",
)

