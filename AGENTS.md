# AGENTS.md — Agent/Developer Reference for dive_planner

This document is for AI coding agents and developers who need to understand the codebase quickly. It covers architecture, key functions, gotchas, and how to make changes safely.

---

## Repository layout

```mermaid
treeView-beta
c:\repos\dive_planner\
├── streamlit_app.py      # Streamlit web UI (~1060 lines)
├── dive_plan.py          # Core planning engine (~700 lines)
├── gas_planning.py       # Pure gas calculation helpers
├── api.py                # FastAPI REST backend (not used by Streamlit deployment)
├── optimiser.py          # Binary search + grid search for API path
├── requirements.txt      # Production deps — keep decodaitengu>=1.4.0
└── static/               # HTML/CSS/JS for FastAPI static mount
```

Sibling repo: `c:\repos\decotengu\` — the `decodaitengu` PyPI package. Installed editable in `.venv` during local dev.

---

## Dependency flow

```txt
streamlit_app.py  →  dive_plan.py  →  decodaitengu.planning.plan_dive()
                  →  gas_planning.py
api.py            →  dive_plan.py
                  →  gas_planning.py
optimiser.py      →  dive_plan.py
                  →  gas_planning.py
```

`decodaitengu` is a pure planning library — it implements Bühlmann ZHL-16C-GF and returns a `DiveSummary`. The dive planner never touches tissue compartment maths directly.

---

## Key functions

### `dive_plan.py`

#### `run_profile(depth, bottom_time, ...) → DiveSummary`

Low-level wrapper around `decodaitengu.planning.plan_dive()`. Accepts either:

- `deco_cylinders_config` list of `(o2, he, switch_depth_m)` tuples (preferred)
- legacy separate `lean_gas`/`rich_gas`/`lean_switch`/`rich_switch` params

Also accepts:

- `travel_gas_config=(o2, he, bar, vol, switch_depth)` — for hypoxic descent gas
- `descent_stops=[(depth_m, time_min)]` — for S-drill pauses

**Important:** Must always pass `descent_stops` through — an earlier bug omitted this from `find_max_bottom_time`, causing the auto timer to ignore the S-drill. Fixed in commit `73770c2`.

#### `run_scenario(name, depth, bottom_time, deco_gases_lost=False, cfg=None, ...) → dict`

Two call paths:

- **`cfg=` path** (API/optimiser): accepts `cfg={'back_cylinder': CylinderConfig, 'deco_cylinders': [(CylinderConfig, sd)], ...}`. Gas labels are from `CylinderConfig.name`.
- **Non-cfg path** (Streamlit app): uses legacy `lean_gas`/`rich_gas`/`travel_gas` params. Gas labels are `'back'`, `'lean'`, `'rich'`, `'travel'`.

Return dict keys: `name`, `depth`, `bottom_time`, `total_time`, `total_deco`, `deco_stops`, `times`, `depths`, `back_remaining_bar`, `lean_remaining_bar`, `rich_remaining_bar`, `travel_remaining_bar`, `gas_used`, `min_gas`, `max_gas_density`, `otu`, `cns`, `icd_warnings`, `ceiling_profile`, `gas_pressure_profile`.

`min_gas` (both paths) comes from `calculate_min_gas_and_turn_from_summary()` — the single implementation of open-water minimum-gas/turn-pressure math. Pass `emergency_sac` to `run_scenario()` to compute it at a stressed SAC rate instead of the planned `sac_bottom` (used by the optimiser; the Streamlit app doesn't pass it, so its numbers are unchanged).

#### `find_max_bottom_time(depth, back_gas, gas_rule='double_ascent', ..., min_reserve=10, descent_stops=None) → int`

Binary search (lo=1, hi=120 minutes, 1-minute steps). At each candidate time, runs all 8 contingency scenarios. If any cylinder in any scenario drops below `min_reserve`, that time fails.

**`min_reserve` is the minimum gas reserve in bar (from the UI's "Minimum gas reserve" setting).**

The function returns an integer (whole minutes) — auto bottom time always snaps to whole minutes.

#### `calculate_best_mix(depth, target_end=30, max_po2_bottom=1.4, o2_narcotic=False) → dict`

Computes optimal trimix for a target END. `o2_narcotic=False` uses the GUE model (only N2 narcotic); `True` uses PADI/NOAA model (O2+N2 narcotic).

#### `_gas_density_gl(o2_pct, he_pct, depth_m, h2_pct=0) → float`

Ideal-gas density in g/L at 37°C using real molar masses.

---

### `gas_planning.py`

Pure functions, no UI or decotengu dependency (except `CylinderConfig`, `SURFACE_PRESSURE` from `dive_plan`).

- `calc_switch_depth(o2_frac, max_ppo2=1.6)` → MOD in whole metres. Uses 1.01325 bar surface pressure (EAN50 → 21m, not 22m). Pure O2 clamped to 6m by convention.
- `calc_cave_turn_pressure(fill_pressure_bar, ...)` → Rule-of-thirds turn pressure.
- `calc_gas_plan(min_gas, back_cylinder, deco_cylinders_with_depths, dive_mode, ...)` → Orchestrator; reports the already-computed `min_gas` dict for open water (doesn't recompute it — see below) or `calc_cave_turn_pressure` for cave, plus each deco cylinder's known switch depth.

There used to be `calc_ow_min_gas(steps, ...)` and `calc_cave_deco_min_gas(steps, ...)` here, independently recomputing open-water/cave-deco minimum gas from a per-step dive trace (`steps`). Removed: `decodaitengu.plan_dive()` has never returned a `steps` trace (only aggregate `profile`/`gas_usage`), so `run_scenario()`'s `cfg=` path always passed `steps=None` and `calc_gas_plan()` silently skipped the whole check — `optimiser.optimise_bottom_time()` could report a plan `feasible` with the back gas cylinder empty. Fixed by deleting that dead path and making `calc_gas_plan()` read the `min_gas` dict `run_scenario()` already computes (see above) instead of recomputing it. Cave-mode deco-gas minimum gas has no replacement — it needs a per-depth ascent gas-usage breakdown nothing in this codebase produces — so `calc_gas_plan()` only reports switch depths for cave-mode deco gases, not a min-gas figure.

---

### `streamlit_app.py` — structure

| Lines (approx) | Content |
|---|---|
| 1–60 | Imports, helper functions (`_qpi`, `_qpf`, `_qpb`, `_qp_set`) |
| 62–278 | Sidebar inputs (depth/time, gases table, deco model, rates, S-drill, gas consumption, Best Mix expander, Settings expander) |
| 280–340 | Computed values (switch depths, travel gas logic, descent_stops_tuple) |
| 344–362 | `@st.cache_data _get_max_time(...)` — auto bottom time call |
| 364–490 | `@st.cache_data _compute_scenarios(...)` — runs all 10 scenarios |
| 492–620 | Planning table construction and display |
| 620–720 | Dive profile Plotly chart |
| 720–840 | Scenario selector, ICD/warnings expanders |
| 840–880 | CSV export |
| 880–1013 | Fill cost calculator, how-to-use expander, version caption |

---

## URL parameters

All settings are encoded in the URL. URL params are read with `_qpi`/`_qpf`/`_qpb` helpers and written back only when values change (`_qp_set`). This prevents re-render race conditions (see commit `79f7a92`).

Full list:

| Param | Type | Default | Meaning |
|---|---|---|---|
| `depth` | int | 48 | Target depth (m) |
| `auto_time` | bool | 1 | Auto bottom time |
| `manual_bt` | int | 31 | Manual bottom time |
| `o2` | int | 21 | Back gas O2% |
| `he` | int | 0 | Back gas He% |
| `h2_bg` | int | 0 | Back gas H2% (H2 mode only) |
| `bgp` | int | 230 | Back gas fill bar |
| `bgv` | float | 24.4 | Back gas volume (L) |
| `lean_on` | bool | 1 | Lean gas carried (adds/removes the Lean row + deco gas) |
| `lo2` | int | 50 | Lean gas O2% |
| `lhe` | int | 0 | Lean gas He% |
| `lp` | int | 200 | Lean gas fill bar |
| `lv` | float | 11.1 | Lean gas volume (L) |
| `rich_on` | bool | 1 | Rich gas carried (adds/removes the Rich row + deco gas) |
| `ro2` | int | 100 | Rich gas O2% |
| `rhe` | int | 0 | Rich gas He% |
| `rp` | int | 200 | Rich gas fill bar |
| `rv` | float | 11.1 | Rich gas volume (L) |
| `units` | str | metric | Display units: `metric` or `imperial` — display-only, all internal calc stays metric |
| `tv_o2` | int | 21 | Travel gas O2% |
| `tv_he` | int | 0 | Travel gas He% |
| `tv_bar` | int | 230 | Travel gas fill bar |
| `tv_vol` | float | 24.4 | Travel gas volume (L) |
| `h2_sd` | int | 40 | H2→back gas switch depth (m) |
| `gfl` | int | 50 | GF low (%) |
| `gfh` | int | 80 | GF high (%) |
| `dr` | int | 20 | Descent rate (m/min) |
| `ar` | int | 10 | Deep ascent rate (m/min) |
| `ar_s` | float | 3.0 | Shallow ascent rate (m/min, 6m→surface) |
| `sdrill` | bool | 0 | S-drill stop enabled |
| `sd` | int | 5 | S-drill stop depth (m) |
| `st` | int | 1 | S-drill stop time (min) |
| `sac_bot` | int | 20 | Bottom SAC (L/min) |
| `sac_dec` | int | 17 | Deco SAC (L/min) |
| `gs_time` | float | 1.0 | Gas switch pause (min) |
| `ppo2_bot` | float | 1.4 | ppO2 bottom limit (bar) |
| `ppo2_ctol` | float | 0.02 | Contingency ppO2 tolerance above limit |
| `dens_lim` | float | 6.2 | Gas density warn threshold (g/L) |
| `cns_warn` | int | 80 | CNS warn threshold (%) |
| `min_res` | int | 10 | Minimum gas reserve (bar) |
| `o2_narc` | bool | 0 | O₂ narcotic END model |
| `fc_o2` | float | 0.05 | Fill cost per litre O2 |
| `fc_he` | float | 0.13 | Fill cost per litre He |
| `fc_tmix` | float | 40.0 | Trimix blend charge |
| `fc_nit` | float | 10.0 | Nitrox blend charge |

---

## END formula

Two models for Equivalent Narcotic Depth:

```python
# O2 non-narcotic (GUE, default, o2_narcotic=False)
end = (depth + 10) * (fN2 / 0.79) - 10

# O2 narcotic (PADI/NOAA, o2_narcotic=True)
end = (depth + 10) * (1 - fHe) - 10
```

The `o2_narc` URL param controls this. The checkbox is in the ⚙️ Settings expander.

**Critical ordering:** The `o2_narc` URL param MUST be read from query params BEFORE the Best Mix Calculator expander is rendered in the sidebar. The Best Mix Calculator also uses `o2_narcotic` and appears earlier in the sidebar code than the Settings expander. Always pre-read `o2_narc` at the top of the sidebar section.

---

## The `decodaitengu` library

**Package:** `decodaitengu` (pip name). Source at `c:\repos\decotengu\`. Must be `>=1.4.0` — `gas_switch_time` param was added in 1.4.0.

**Primary imports:**

```python
from decodaitengu.planning import plan_dive as _plan_dive
from decodaitengu.types import Gas as _Gas, Cylinder as _Cylinder, DiveSummary
```

**`plan_dive()` key params:**

```python
plan_dive(
    depth, bottom_time,
    gases=[Gas(o2=0.21, he=0.0, h2=0.0)],
    cylinders=[Cylinder(gas=..., volume=11.1, start_pressure=200, name='back')],
    gf=(50, 80),           # (gf_low_pct, gf_high_pct)
    descent_rate=20.0,
    ascent_rate=10.0,      # or [(6, 10.0), (0, 3.0)] for segmented
    sac_bottom=20.0,
    sac_deco=17.0,
    descent_stops=[(5, 1)],  # [(depth_m, duration_min)]
    gas_switch_time=1.0,
) -> DiveSummary
```

**`DiveSummary` key fields:**

- `runtime` — total dive time (min)
- `total_deco_time` — sum of all deco stop times
- `stops` — list of `DecoStop(depth, time)`
- `gas_usage` — dict of `{label: GasUsage}`; GasUsage has `.remaining_bar`
- `otu`, `cns_percent` — oxygen toxicity
- `max_gas_density` — maximum g/L encountered
- `icd_warnings` — list of ICD warning strings
- `ceiling_profile` — `[(time, depth, ceiling)]`
- `gas_pressure_profile` — `{label: [(time, bar)]}`

**Gas labels:** In the non-cfg path the labels are `'back'`, `'lean'`, `'rich'`, `'travel'`. The library uses these same labels in `gas_usage` and `gas_pressure_profile`.

---

## Known gotchas

### 1. `edit` tool gets interrupted in this environment

Use `powershell` with a here-string (`@'...'@`) + `Set-Content` for large file writes, or use `pylance_mcp_server-pylanceRunCodeSnippet` with Python string replacement for surgical edits.

### 2. `decodaitengu` version on Streamlit Cloud

Streamlit Cloud caches the environment. A version bump in `requirements.txt` only takes effect on the next rebuild. Always ensure `requirements.txt` says `decodaitengu>=1.4.0` or higher.

### 3. `descent_stops` must be passed everywhere

`find_max_bottom_time()` and `run_scenario()` both accept `descent_stops`. Forgetting to pass it means the auto timer ignores the S-drill stop, underestimating gas consumption.

### 4. `o2_narc` ordering in sidebar

The `o2_narc` URL param must be read before the Best Mix Calculator expander is rendered. It is used inside that expander AND in the table END row. Reordering sidebar sections carelessly can break one of these uses.

### 5. `_qp_set` debounce

Only write URL params when the value has changed. Writing all params unconditionally on every render causes a rapid re-render loop. The `_qp_set(updates: dict)` helper handles this.

### 6. Two call paths in `run_scenario`

The `cfg=` path (API) and the non-cfg path (Streamlit) have different gas labelling. Don't mix them. The Streamlit app always uses the non-cfg path.

### 7. `calc_switch_depth` uses real surface pressure

Uses 1.01325 bar (not 1.0 bar), so EAN50 MOD is 21m not 22m. Pure O2 is clamped to 6m by convention even though strict MOD is ~5.9m.

### 8. Descent rate matters a lot when comparing against Subsurface

`decodaitengu` does switch gas during free ascent (not just at scheduled stops — see `_ascend_with_deco` in `c:\repos\decotengu\decodaitengu\planning.py`), so that's not a source of divergence. An earlier check here claimed this app's total deco ran ~10-20% shorter than Subsurface's — that number was wrong, produced by comparing at this app's default 20 m/min descent rate instead of the much faster one Subsurface's plans in `subsurface_test_plans.txt` imply (both their 50m and 60m dives show a 1-minute descent, i.e. ~45-60 m/min). Re-run with a matched fast descent rate and ascent_rate=10 (which already matched well): all three test plans land within 1-3 minutes of total deco and within a minute of runtime, and the gap isn't one-directional — test 3 (60m, 18/45) comes out 1 minute *longer* than Subsurface, not shorter. What's left concentrates in single 1-minute stops right at a gas-switch depth (21m, 18m), consistent with rounding-boundary sensitivity rather than a wrong M-value/GF calc. If you're validating a specific plan against Subsurface, match the descent rate first before concluding there's a real gap.

### 9. H2 mode

Triggered when back gas O2 < 4%. Adds Travel gas row, H2 switch depth input, and prominent warning banner. H2 coefficients are unvalidated — for research only.

`back_gas` in `streamlit_app.py` is always the 3-tuple `(o2, he, h2)`. Any narcotic-fraction calc (END row, Best Mix Calculator, etc.) must exclude `back_gas[2]` (H2) the same way it excludes He — H2 is not narcotic. The live END row was missing this until it was fixed to match the H2 exclusion already applied to helium.

---

## How to run locally

```bash
cd c:\repos\dive_planner
.venv\Scripts\python.exe -m streamlit run streamlit_app.py
```

The `.venv` has `decodaitengu` installed editable from `c:\repos\decotengu` (`pip install -e`).

To exercise a specific function from the CLI without the UI, e.g.:

```bash
.venv\Scripts\python.exe -c "import dive_plan; print(dive_plan.run_scenario('test', 45, 20, back_gas=(21, 0))['deco_stops'])"
```

There is no standalone CLI planner script — the pre-Streamlit `dive_plan.py` CLI/plotting code (`print_table`, `plot_profiles`, `generate_planning_table`, `main`) and the scripts that drove it (`run_50m_230.py`, `compare_narcosis_models.py`) were removed; `streamlit_app.py` is the only entry point now.

---

## Recent significant commits

| Hash      | Summary                                                            |
|-----------|--------------------------------------------------------------------|
| `8b6e28d` | fix: correct END formula for O2 narcotic toggle                    |
| `caede95` | feat: O2 narcotic toggle applies to END row in table               |
| `80df352` | feat: improve gas left section labels                              |
| `7511ee4` | feat: show used/remaining bar for all gas rows                     |
| `7e99f6a` | fix: bump decodaitengu minimum to >=1.4.0                          |
| `0fa6aae` | fix: gs_time URL safety, thread gas_switch_time through auto-timer |
| `63706ca` | refactor: use unified gas API, add gas_switch_time to UI           |
| `73770c2` | Fix: pass descent_stops to find_max_bottom_time                    |
| `79f7a92` | Fix URL debounce race condition; add decodaitengu version display  |
