# Dive Planner

A technical dive planning web app built on [DecoTengu](https://github.com/notionparallax/decodaitengu) (Bühlmann ZHL-16C-GF decompression model).

**Live app:** [diveplanner-demo-page.streamlit.app](https://diveplanner-demo-page.streamlit.app)

---

## What it does

Given a target depth and gas configuration, the planner runs **10 scenarios** simultaneously — the main plan plus contingencies (deeper, longer, lost deco gas, emergency) — and finds the maximum bottom time where **all** contingency scenarios finish with gas remaining. The result is a planning table used to brief the dive.

It follows common open-circuit trimix planning conventions, though most parameters are adjustable.

---

## Quick start

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

All configuration is stored in the URL, so you can share a complete dive plan as a link.

---

## Files

| File | Purpose |
|---|---|
| `streamlit_app.py` | Web UI — all display, inputs, and chart code |
| `dive_plan.py` | Planning engine — scenario runner, auto bottom time, min gas, best mix |
| `gas_planning.py` | Pure gas rules — rule of thirds, OW min gas, switch depths |
| `api.py` | FastAPI REST backend (optional; not used by the Streamlit deployment) |
| `optimiser.py` | Binary search + grid optimisers for the API path |
| `requirements.txt` | Production dependencies |

---

## The planning table

Each column is a scenario. Rows show deco stop depths with `runtime (stop_time)` values.

| Scenario | Depth | Time | Gases |
|---|---|---|---|
| Main | D | T | all |
| Longer | D | T+3 | all |
| Deeper | D+3 | T | all |
| D & L | D+3 | T+3 | all |
| no {lean}% | D | T | no lean deco gas |
| no {rich}% | D | T | no rich deco gas |
| no {lean}% (D) | D+3 | T+3 | no lean deco gas |
| no {rich}% (D) | D+3 | T+3 | no rich deco gas |
| Bounce | D | 10 min | all |
| Emergency (GF99/99) | D | T | all, fast ascent 18 m/min |

The **🖐️** marker on a column header shows the constraining scenario — the one with the smallest gas margin, which determines the maximum bottom time.

---

## Auto bottom time

When "Auto bottom time" is enabled, the app binary-searches for the longest bottom time where all 8 contingency scenarios end with every cylinder above the **Minimum gas reserve** (default 10 bar). The reserve confirms the cylinder is not empty but is not counted as usable gas.

Descent stops (S-drill), gas switch times, and SAC rate are all included in the search.

---

## Sidebar settings

### Gases & Cylinders

An editable table with rows for Back gas, Lean deco gas, and Rich deco gas (plus a Travel gas row for hypoxic mixes). Columns: O2%, He%, fill pressure (bar), cylinder volume (litres).

- **Lean gas** is typically EAN50, switched at its MOD (21m at ppO2 1.6)
- **Rich gas** is typically O2, switched at 6m by convention
- **Travel gas** appears automatically when back gas O2 < 18% (hypoxic trimix)

### Deco model

- **GF low / GF high**: gradient factors as percentages. Common choices range from 20/70 (more conservative) to 30/85 (less conservative).

### Rates

- **Descent rate**: default 20 m/min
- **Ascent (deep)**: default 10 m/min, from depth to 6m
- **Ascent (shallow)**: default 3 m/min, 6m → surface

### Descent stop (S-drill)

Adds a pause during descent (depth and duration configurable), included in gas calculations and auto bottom time.

### Gas consumption

- **SAC bottom / SAC deco**: surface-equivalent consumption in L/min
- **Gas switch time**: minutes paused at each deco switch depth (default 1 min)

### ⚙️ Settings

- **ppO2 limits**: warning thresholds for bottom and contingency scenarios
- **Gas density limit**: warn threshold in g/L (6.2 g/L is a common limit)
- **CNS warn threshold**: default 80%
- **Minimum gas reserve**: minimum bar any cylinder may reach (default 10 bar)
- **O₂ is narcotic**: changes the END calculation. Default off (only N2 counted as narcotic). When on, O2 also contributes to narcosis.
- **Units**: Metric (m) or Imperial (ft) display — internal calculation always stays metric. Default metric.

---

## END (Equivalent Narcotic Depth)

| Model | Formula | Example Tx22/27 at 51m |
|---|---|---|
| O₂ non-narcotic (default) | `(depth+10) × (fN2 / 0.79) − 10` | ~29m |
| O₂ narcotic (PADI/NOAA) | `(depth+10) × (1 − fHe) − 10` | ~35m |

---

## Gas display

Gas remaining rows in the table show **used / remaining** (e.g. `45/185 bar`).

---

## URL parameters

Every setting is encoded in the URL, making dive plans fully shareable. Key parameters:

| Param | Meaning | Default |
|---|---|---|
| `depth` | Target depth (m) | 40 |
| `auto_time` | Auto bottom time on/off | 1 |
| `o2`, `he` | Back gas mix | 21, 0 |
| `bgp`, `bgv` | Back gas pressure (bar) and volume (L) | 230, 24.4 |
| `lean_on`, `lo2`, `lhe`, `lp`, `lv` | Lean gas on/off, mix, pressure, volume | 1, 50, 0, 200, 11.1 |
| `rich_on`, `ro2`, `rhe`, `rp`, `rv` | Rich gas on/off, mix, pressure, volume | 1, 100, 0, 200, 11.1 |
| `units` | Display units: `metric` or `imperial` | metric |
| `gfl`, `gfh` | GF low and high (%) | 50, 80 |
| `dr`, `ar`, `ar_s` | Descent rate, deep/shallow ascent rates | 20, 10, 3.0 |
| `sdrill`, `sd`, `st` | S-drill on/off, depth (m), time (min) | 0, 5, 1 |
| `sac_bot`, `sac_dec` | Bottom and deco SAC (L/min) | 20, 17 |
| `gs_time` | Gas switch pause (min) | 1.0 |
| `min_res` | Minimum gas reserve (bar) | 10 |
| `o2_narc` | O₂ narcotic END model | 0 |

Full parameter list is in [AGENTS.md](AGENTS.md).

---

## Decompression model

Uses **decodaitengu** (`decodaitengu>=1.4.0`), implementing Bühlmann ZHL-16C with gradient factors.

**Known limitation:** Spot-checks against Subsurface (same depth/time/GF/SAC, and a descent rate fast enough to match the ~1-minute descents in Subsurface's plans) land within 1-3 minutes on total deco time and within a minute on runtime — see `subsurface_test_plans.txt` for the reference plans. The gap isn't one-directional (this planner comes out shorter in some cases, longer in others), and what's there concentrates in single 1-minute stops right at a gas-switch depth (21m, 18m) — a rounding-boundary sensitivity, not a systematic under- or over-call. An earlier version of this note claimed a 10-20% shortfall; that number came from comparing at this app's default 20 m/min descent rate rather than the much faster one Subsurface's plans imply, which inflated the apparent gap.

H2 (hydrogen) support is experimental with unvalidated coefficients — do not use for real dives.

---

## Dependencies

```requirements
decodaitengu>=1.4.0
streamlit>=1.32
plotly>=5.20
pandas>=2.0
```
