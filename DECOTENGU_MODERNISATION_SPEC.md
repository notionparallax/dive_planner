# DecoTengu Modernisation Spec

## Background

DecoTengu is a Python dive decompression library implementing the Bühlmann decompression model with Erik Baker's gradient factors. It was written by Artur Wroblewski (wrobell@pld-linux.org), hosted on GNU Savannah, and last released to PyPI as v0.14.1 on 23 May 2018. The GitHub repository at github.com/gully/decotengu is an explicit mirror/fork from 2016 — gully states he forked it "to make some plots" and directs issues back to the original author.

The original Savannah repository appears inactive. This spec assumes an independent fork.

**License:** GPL-3.0. Any fork must maintain GPL-3.0 licensing.

---


## Phase 1: Foundation (Correctness & Maintainability)

### 0. Rename master branch to main

**Priority:** High  
**Why:** Modern convention. GitHub defaults to `main`. Rename the local and remote branch.

**Requirements:**
- `git branch -m master main`
- Update remote: `git push -u origin main` and set default branch on GitHub
- Delete old remote branch: `git push origin --delete master`

### 1.0 update to python 3.12

**Priority:** High  
**Why:** python 3.12 is a widely used version, and should stand in good stead for the next few years


### 1.1 Type Hints Throughout

**Priority:** High  
**Why:** The codebase predates PEP 484. Type hints enable IDE support, catch bugs, and serve as documentation.

**Requirements:**

- Add type annotations to all public and private functions
- Use modern syntax (Python 3.10+ union `X | None`, `list[T]`, etc.)
- Add `py.typed` marker file
- Target: pass `mypy --strict` with no errors
- Key types to define:
  ```python
  @dataclass
  class Gas:
      o2: float  # fraction, e.g. 0.21
      he: float  # fraction, e.g. 0.35
      n2: float  # computed property: 1 - o2 - he

  @dataclass  
  class Stop:
      depth: float  # metres
      time: float   # minutes at this stop
      runtime: float  # cumulative minutes from start
      gas: Gas

  @dataclass
  class TissueState:
      n2_pressures: tuple[float, ...]  # 16 compartments
      he_pressures: tuple[float, ...]  # 16 compartments

  @dataclass
  class Step:
      phase: Phase  # enum: DESCENT, BOTTOM, ASCENT, DECO_STOP
      depth: float
      time: float
      runtime: float
      gas: Gas
      tissues: TissueState
      gf: float  # current GF ceiling
      ceiling: float
  ```

### 1.2 Doc Strings Throughout

**Priority:** High  
**Why:** Increase legibility of code




### 1.5 Modern Packaging

**Priority:** High  
**Why:** `setup.py` is legacy. Modern tooling expects `pyproject.toml`.

**Requirements:**

- Replace `setup.py` + `setup.cfg` with `pyproject.toml`
- Build backend: `hatchling` or `setuptools` (with pyproject.toml config)
- Minimum Python version: 3.10
- Add `[project.optional-dependencies]` for dev/test extras
- Add GitHub Actions CI (test matrix: Python 3.10, 3.11, 3.12, 3.13)
- Add `ruff` for linting/formatting
- Add `pytest` configuration (migrate from existing tests)

---

## Phase 2: Completeness (Built-in Calculations)

### 2.1 ZHL-16C Support with Helium Compartments

**Note:** it should be possible to ask the system to calculate using A, B or C models, but it should default to C if not specified
**Priority:** Critical  
**Why:** The existing implementation only models ZHL-16B with nitrogen-only tissue compartments. Modern dive computers (Shearwater, Ratio, Garmin) all use ZHL-16C. Trimix planning without He compartments produces incorrect deco schedules.

**Requirements:**

- Implement all 16 tissue compartments with **separate N2 and He tracking**
- He half-times (Bühlmann 1990): 1.51, 3.02, 4.72, 6.99, 10.21, 14.48, 20.53, 29.11, 41.20, 55.19, 70.69, 90.34, 115.29, 147.42, 188.24, 240.03 minutes
- He a-coefficients: 1.7474, 1.3838, 1.1925, 1.0465, 0.9226, 0.8211, 0.7309, 0.6514, 0.5944, 0.5434, 0.5002, 0.4609, 0.4256, 0.3957, 0.3699, 0.3497
- He b-coefficients: 0.4245, 0.5747, 0.6527, 0.7223, 0.7582, 0.7957, 0.8279, 0.8553, 0.8757, 0.8903, 0.8997, 0.9073, 0.9122, 0.9171, 0.9217, 0.9267
- ZHL-16C N2 coefficients (replace current 16B):
  - N2 half-times: 4.0, 8.0, 12.5, 18.5, 27.0, 38.3, 54.3, 77.0, 109.0, 146.0, 187.0, 239.0, 305.0, 390.0, 498.0, 635.0
  - N2 a-coefficients: 1.2599, 1.0000, 0.8618, 0.7562, 0.6200, 0.5043, 0.4410, 0.4000, 0.3750, 0.3500, 0.3295, 0.3065, 0.2835, 0.2610, 0.2480, 0.2327
  - N2 b-coefficients: 0.5050, 0.6514, 0.7222, 0.7825, 0.8126, 0.8434, 0.8693, 0.8910, 0.9092, 0.9222, 0.9319, 0.9403, 0.9477, 0.9544, 0.9602, 0.9653
- Combined tissue ceiling calculation using the standard formula:
  ```
  P_comp = max over all compartments of:
    ((P_N2_tissue / b_N2 + a_N2) combined with (P_He_tissue / b_He + a_He))
  ```
  Using the weighted a/b approach:
  ```
  a = (a_N2 * P_N2 + a_He * P_He) / (P_N2 + P_He)
  b = (b_N2 * P_N2 + b_He * P_He) / (P_N2 + P_He)
  P_ceiling = (P_N2 + P_He - a) * b
  ```
- Gradient factor interpolation applies to the combined ceiling as before
- Retain ZHL-16B as a selectable option for backward compatibility

**Validation:** Compare output against Subsurface and MultiDeco for:
- Air at 30m/20min (smoke test, no He)
- Tx 21/35 at 60m/20min (He-heavy mix)
- Tx 10/70 at 100m/15min (hypoxic trimix)

### 2.2 Configurable Algorithm Selection

**Priority:** High  
**Why:** Users should be able to select their model without patching internals.

**Requirements:**

```python
from decotengu import Engine, ZHL16C, ZHL16B

engine = Engine(model=ZHL16C)  # default
engine = Engine(model=ZHL16B)  # legacy
```

- Model is a class/dataclass containing coefficient tables and the ceiling calculation method
- Easy to add new models (e.g. ZHL-16C with 1a compartment modifications)


### 2.3 CNS and OTU Tracking

**Priority:** High  
**Why:** Currently must be calculated externally by walking all steps. These are safety-critical metrics.

**Requirements:**

- Track CNS% accumulation across the dive profile using NOAA single-exposure limits
- Track OTU (UPTD) using the formula: `OTU = t × ((PO2 - 0.5) / 0.5)^0.83` for PO2 > 0.5
- Expose on each `Step` and as final totals:
  ```python
  result = engine.calculate(60, 20)
  print(result.cns_percent)  # e.g. 34.2
  print(result.otu)          # e.g. 42.7
  ```
- Handle multi-gas switches (PO2 changes mid-dive)
- use algo described in https://scubaboard.com/community/threads/need-an-excel-formula-that-will-calculate-cns.237903/post-10750263 as default for calcs, but alow user to pick the noaa table as an option.
- CNS limits table (NOAA 2014 or configurable):
  - PO2 1.6: 45 min
  - PO2 1.5: 120 min
  - PO2 1.4: 150 min
  - PO2 1.3: 180 min
  - PO2 1.2: 210 min
  - PO2 1.1: 240 min
  - PO2 1.0: 300 min
  - PO2 0.9: 360 min
  - PO2 0.8: 450 min
  - PO2 0.7: 570 min
  - PO2 0.6: 720 min
  - Interpolate linearly between entries

### 2.4 Gas Consumption Tracking

**Priority:** High  
**Why:** Essential for dive planning. Currently requires external calculation walking every step.

**Requirements:**

- Accept cylinder definitions:
  ```python
  engine.add_gas(21, 35, switch_depth=None, label="back",
                 cylinder_litres=24.4, fill_bar=200)
  engine.add_gas(50, 0, switch_depth=21, label="ean50",
                 cylinder_litres=11.1, fill_bar=200)
  engine.add_gas(100, 0, switch_depth=6, label="o2",
                 cylinder_litres=11.1, fill_bar=200)
  ```
- Accept SAC rates (configurable per phase):
  ```python
  engine.sac_bottom = 20  # L/min at surface
  engine.sac_deco = 17    # L/min at surface  
  engine.sac_ascent = 17  # optional, defaults to sac_deco
  ```
- Calculate litres consumed per gas at each step
- Report remaining gas in each cylinder at end:
  ```python
  result.gas_usage["back"].consumed_litres  # 2891
  result.gas_usage["back"].remaining_bar    # 82
  result.gas_usage["ean50"].consumed_litres # 412
  ```

### 2.4 Descent Profile / Waypoints

**Priority:** Medium  
**Why:** Real dives include stops during descent (S-drills, bubble checks, team regrouping). Modelling these gives more accurate tissue loading.

**Requirements:**

- Allow defining waypoints during descent:
  ```python
  engine.add_descent_stop(depth=5, duration=1.0)  # 1 min at 5m for S-drill
  engine.add_descent_stop(depth=25, duration=0.5) # 30s bubble check
  ```
- Tissue loading calculated correctly during holds (using ambient pressure at hold depth)
- Descent time between waypoints uses configured descent rate
- `bottom_time` semantics unchanged: still measures from surface to leaving bottom depth
- Waypoints are optional; default behaviour (straight descent) preserved

---

## Phase 3: Performance & API

### 3.1 Summary-Only Calculation Mode

**Priority:** High  
**Why:** Full step materialisation (300+ Step objects per dive) is wasteful for batch operations like binary-searching max bottom times across multiple contingency scenarios.

**Requirements:**

- Add `engine.calculate_summary()` that returns only final results without yielding intermediate steps:
  ```python
  @dataclass
  class DiveSummary:
      runtime: float
      total_deco_time: float
      stops: list[Stop]        # only the deco stops, not every metre
      gas_usage: dict[str, GasUsage]
      cns_percent: float
      otu: float
      max_depth: float
      tissues_final: TissueState
      ndl: float | None        # if no deco required
  ```
- Internally: same Schreiner equation math, but only accumulates totals; does not allocate Step objects for every metre/minute
- Target: **5-10x faster** than `list(engine.calculate(...))` for equivalent dive
- `engine.calculate()` (full step generator) remains available for plotting/analysis

### 3.2 High-Level Planning API

**Priority:** Medium  
**Why:** Current API is low-level (configure engine, iterate steps, extract data yourself). A planning layer makes common use cases trivial.

**Requirements:**

```python
from decotengu import plan_dive, Gas, Cylinder

result = plan_dive(
    depth=50,
    bottom_time=25,
    back_gas=Gas(22, 27),
    deco_gases=[Gas(50, 0, switch_depth=21), Gas(100, 0, switch_depth=6)],
    cylinders={
        "back": Cylinder(24.4, 200),
        "ean50": Cylinder(11.1, 200),
        "o2": Cylinder(11.1, 200),
    },
    gf=(50, 70),
    descent_rate=20,
    ascent_rate=10,
    sac=(20, 17),  # (bottom, deco)
    last_stop_depth=3,
    model=ZHL16C,
)

print(result.runtime)        # 65
print(result.stops)          # [(21, 1), (18, 1), (15, 2), (12, 2), (9, 3), (6, 4), (3, 12)]
print(result.gas_remaining)  # {"back": 82, "ean50": 148, "o2": 173}
print(result.cns_percent)    # 34.2
```

- Wraps `Engine` configuration and `calculate_summary()` into a single call
- Returns a `DivePlan` object with all commonly-needed data
- Sensible defaults for everything (air, no deco gas, GF 100/100, 3m last stop)

### 3.3 Configurable Last Stop Depth

**Priority:** Low (simple fix)  
**Why:** Current API only offers `last_stop_6m: bool`. Should accept any depth.

**Requirements:**

```python
engine.last_stop_depth = 3   # metres (default)
engine.last_stop_depth = 6   # alternative
engine.last_stop_depth = 9   # unusual but valid
```

- Deprecate `last_stop_6m` boolean, keep as alias for one release cycle
- Validate: must be multiple of 3 (standard stop spacing), minimum 3m

---

## Phase 4: Testing & Validation

### 4.1 Test Suite Modernisation

**Requirements:**

- Migrate all existing tests to pytest
- Add parametrized tests for coefficient tables (verify against published Bühlmann tables)
- Add integration tests comparing against known-good plans:
  - Subsurface (open source, ZHL-16C + GF)
  - Shearwater Perdix 2 firmware output
  - Published tables from Bühlmann's original papers
- Add property-based tests (hypothesis) for:
  - Deeper dive always produces >= deco time of shallower dive (same gas, same BT)
  - Higher He fraction always produces <= deco time (same depth, same BT, same O2)
  - Lower GF always produces >= deco time

### 4.2 Numerical Precision

**Requirements:**

- Document precision expectations: ±1 minute on stops, ±1 bar on gas calculations
- Add tolerance-based comparisons in tests (not exact float equality)
- Consider using `decimal.Decimal` for tissue calculations if float precision issues found

---

## Phase 5: Optional Enhancements

### 5.1 Multi-Level Dive Support

- Allow ascent to shallower depth, further bottom time, then final ascent
- Track tissue state across profile changes

### 5.2 Repetitive Dive Support

- Surface interval modelling (off-gassing at surface pressure)
- Residual tissue loading carried into next dive
- CNS recovery during surface interval

### 5.3 Altitude Diving

- Configurable surface pressure (default 1.01325 bar)
- Altitude-adjusted ceiling calculations

### 5.4 Streaming/Async API

- For web applications: async generator that yields steps
- WebSocket-friendly for real-time plan display

---

## Non-Goals

- **VPM-B implementation** — Limited real-world adoption, Suunto abandoning it, would significantly complicate the codebase for minimal benefit.
- **Recreational planner features** — No-fly time, safety stops, etc. This is a technical diving library.
- **Dive log integration** — Parsing/importing dive computer logs is a separate concern (see libdivecomputer, Subsurface).

---

## Migration Path

### From existing decotengu (0.14.1):

1. `engine.add_gas(depth, o2, he)` → `engine.add_gas(o2, he, switch_depth=depth)` (swap arg order for clarity)
2. `engine.last_stop_6m = True` → `engine.last_stop_depth = 6`
3. Tissue data now includes He pressures (new field, non-breaking for consumers that only read N2)
4. `calculate()` still returns a generator of Steps (backward compatible)
5. New `calculate_summary()` is additive, not a replacement

### Versioning:

- Fork as v1.0.0 (clean break from 0.14.1)
- Follow semver strictly from v1.0.0 onward

---

## Architecture Notes

```
decotengu/
├── __init__.py          # Public API exports
├── engine.py            # Core Engine class, step calculation
├── models/
│   ├── __init__.py
│   ├── base.py          # Abstract model interface
│   ├── zhl16c.py        # ZHL-16C coefficients + ceiling calc
│   └── zhl16b.py        # ZHL-16B (legacy)
├── tissues.py           # TissueState, Schreiner equation
├── gases.py             # Gas, Cylinder dataclasses
├── tracking/
│   ├── cns.py           # CNS% calculator
│   ├── otu.py           # OTU/UPTD calculator
│   └── gas_usage.py     # Gas consumption tracker
├── planning.py          # High-level plan_dive() API
├── types.py             # Shared type definitions
└── py.typed             # PEP 561 marker
```

---

## Reference Materials

- Bühlmann, A.A. (1984, 1995) "Tauchmedizin" — original coefficient tables
- Baker, Erik (1998) "Understanding M-Values" — gradient factor explanation
- Baker, Erik (1998) "Clearing Up the Confusion About Deep Stops" — GF implementation
- Subsurface source code (C): `deco.c` — reference ZHL-16C implementation with He
- Shearwater technical documentation — GF implementation notes
