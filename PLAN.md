# Dive Planner — Structured Gas Planning & Optimisation

## Overview

Extend the existing `dive_plan.py` into a structured, web-accessible dive planning system.
Built in three phases, with a FastAPI backend and plain HTML/JS frontend.

---

## Phase 1 — Gas Planning & Single Dive Plan

### Minimum Gas & Turn Pressure

**Cave mode (rule of thirds)**
- Turn pressure = total fill pressure ÷ 3, rounded DOWN to nearest multiple of 30 bar
  - e.g. 230 bar → 210 bar → thirds of 70 bar each (in / out / reserve), so turn pressure is 230-70 = 160 bar
- Applies to back gas, deco gasses need to be double the minumum, as they'll only be used on ascent, so there's no penetratiion portion.

**Open water mode**
- Minimum gas = (1 min problem-solving at depth + ascent on back gas to first deco switch) × 2 divers
- Uses emergency SAC rate
- Turn pressure = min_gas_litres ÷ cylinder_volume

**Emergency SAC**: configurable, default **30 L/min** (vs 20 L/min for normal bottom SAC)

**Contingency factor**: optional multiplier (e.g. 1.1–1.5×) applied on top of min gas

### Gas Configuration (all configurable)
- **Back gas**: O2%, He%, cylinder volume (L), fill pressure (bar)
- **Deco gas 1** (e.g. EAN50): O2%, He%, cylinder volume, fill pressure, switch depth (m) (should be calculatred from maximum pp02, assume 1.6 unless the user changes it)
- **Deco gas 2** (e.g. 100% O2): O2%, He%, cylinder volume, fill pressure, switch depth (m) (see above)

### API & UI
- `POST /api/plan` — accepts dive parameters, returns full plan as JSON
- UI form: depth, bottom time, gas config, dive mode (cave / open water), SAC rates
- UI output: deco schedule, gas remaining per cylinder, turn pressure check, CNS/OTU

---

## Phase 2 — Bottom Time Optimiser

Given **fixed gas mixes**, find the maximum bottom time subject to constraints.

**Algorithm**: binary search on bottom time, running full deco calc at each step.

**Constraints** (all configurable):
- CNS% ≤ limit (default 80%)
- OTU ≤ limit (default 300)
- Total runtime ≤ limit (optional, e.g. 120 min)
- Back gas used ≤ (fill_pressure − turn_pressure) × cylinder_volume
- Deco gases don't run out

**API & UI**
- `POST /api/optimise/bottom-time`
- UI tab: shows max bottom time, the binding constraint, resulting deco schedule

---

## Phase 3 — Full Gas Mix + Bottom Time Optimiser

Jointly optimise:
- Back gas O2% and He%
- Deco gas switch depths
- Bottom time

Subject to the same constraints as Phase 2, plus:
- Max ppO2 at depth ≤ **1.4 bar** (bottom)
- Max ppO2 deco ≤ **1.6 bar**
- Min ppO2 ≥ **0.18 bar** (no hypoxic mix)

**Algorithm**: `scipy.optimize` or grid search over mix space with binary search on
bottom time at each candidate mix.

**API & UI**
- `POST /api/optimise/full`
- UI tab: shows optimal back gas mix, switch depths, max bottom time

---

## Architecture

```
dive_planner/
├── dive_plan.py          # core deco engine (refactored to use dataclasses)
├── gas_planning.py       # min gas, rule of thirds, turn pressure
├── optimiser.py          # bottom time + gas mix optimisation
├── api.py                # FastAPI app
└── static/
    ├── index.html
    ├── app.js
    └── style.css
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/plan` | POST | Single dive plan |
| `/api/optimise/bottom-time` | POST | Max bottom time for fixed mixes |
| `/api/optimise/full` | POST | Optimise mixes + bottom time |
| `/api/profile-image` | POST | Return dive profile PNG |

---

## Open Questions / Decisions to Revisit

- Should deco gas rule-of-thirds be enabled in cave mode by default, or optional?
  - by default
- Should the UI support saving/loading dive configurations?
  - in future versions
- Any other dive environments beyond cave and open water (e.g. wreck, altitude)?
  - not for now
- GF (gradient factor) low/high — fixed or included in optimisation?
  - vaiable, but default to 50/70 unless the user changes it

---

## Build Order

1. Refactor `dive_plan.py` core (extract dataclasses, clean up config)
2. Implement `gas_planning.py` (cave + OW min gas, turn pressure, contingency)
3. Create `api.py` FastAPI skeleton + `/api/plan` endpoint
4. Build Phase 1 HTML UI
5. Implement bottom time optimiser + `/api/optimise/bottom-time`
6. Add optimiser tab to UI
7. Implement full gas mix optimiser + `/api/optimise/full`
8. Add full optimiser tab to UI
9. Wire up profile image endpoint + display in UI
