# Dive Planner — Ideas & Backlog

## Safety & Validation

- **Gas density warning** ✅ — Warn if gas density exceeds ~6.2 g/L (GUE/WKPP limit). Already tracked per-scenario; just needs a UI callout.
- **CNS%/OTU flag** ✅ — Warn if CNS ≥ 80% in any scenario (the single-dive limit).
- **Back gas ppO2 warning** ✅ — Warn if back gas ppO2 exceeds limit at depth (e.g. 32% O2 at 45m = 1.54 bar, close to or over the 1.4 bar bottom limit).

## Planning Aids

- **Rule of thirds on gas pressure chart** ✅ — Show the 1/3 turn pressure as a horizontal line on the gas pressure graph for back gas.
- **NDL display** 🤔 — Engine returns NDL for no-deco dives. The counter-argument: NDL resolves on ascent so a true NDL needs to be computed at depth, not at surface. May be useful for the Bounce scenario. Worth revisiting if multi-level profiles are added.
- **Best mix calculator** 💡 — Given a depth and target END, calculate the optimal trimix (O2 capped by ppO2 limit, He fills the rest). Toggle whether O2 counts as narcotic. Code skeleton already exists in `dive_plan.py` (`calculate_best_mix`). This would go in the sidebar at the bottom
- **fill cost** if we enter a price per litre for 02 and he, and a blending charge for trimix and another for nitrox, it will show a cost for filling these tanks for this dive. This will disregard any gas already in the tanks, but we can do that as a later thing. This can probably go down at the bottom next to the export buttons
- **Segmented ascent speeds** we should be able to set ascent speeds for the ascent to 6m and a different ascent speed for the 6m to the surface segment. The 6 to 0 section should be able to go in 0.5m/minute increments.

  **Library spec for decodaitengu:** Currently `plan_dive()` accepts a single `ascent_rate` parameter (float, m/min). To support segmented ascent the library would need to accept either:
  - `ascent_rate: float | list[tuple[float, float]]` — where each tuple is `(max_depth_m, rate_m_per_min)` applied from that depth to the next segment, e.g. `[(6, 10), (0, 0.5)]` means "10 m/min until 6m, then 0.5 m/min to surface", OR
  - Two dedicated params: `ascent_rate_deep` (m/min, applies from bottom to `last_stop_depth`) and `ascent_rate_shallow` (m/min, applies from `last_stop_depth` to surface), with `ascent_rate` kept as a fallback for both.
  The second option is simpler to implement and document. The slow shallow rate (0.5–3 m/min) significantly extends deco time and affects CNS/OTU, so ceiling calculations must account for it properly — the deco algorithm should treat the slow ascent segment as additional time at each shallow stop depth..

## Multi-level Dives 💡

Allow a stepped profile (e.g. 40m → 30m → 20m), common in wreck diving. The descent stops mechanism already exists; the main work is:
- UI to define depth/time waypoints
- Ceiling computation across the full stepped profile
- Deciding how scenarios (deeper, longer) interact with a multi-level plan

## Export

- **Wrist slate PNG** ✅ — Compact, Niimbot-printable image of the planning table. Subset of scenarios (probably just main + D&L, and emergency). Subset of rows (depths and stop times, not gas stats). high contrast, striped rows, indicate gas with - for lean and * for rich. Option to drop stop time and just have runtimes.

## docs

- adding a link to the decodaitengu repo and docs
- adding some explanitory text that this is really about testing the decodaitangu module.
- add a caveat about not trusting these until you've tested them out elsewhere.

## Rejected / Deferred

- *No-rich deco penalty warning* — the scenario columns already show the difference visually.
- *GF ceiling line on profile* — the emergency (GF 99/99) ascent line already serves this purpose.
- *"What GF gives me X deco time?" slider* — encourages risky GF selection.
- *QR code for URL* — not needed.
- *Side-by-side GF comparison* — not needed.
- *"What does adding O2 stage buy me?" comparison* — not needed.
