"""Compare O2-narcotic vs O2-non-narcotic END models for 50m plan."""
from dive_plan import (calculate_best_mix, generate_planning_table,
                       SURFACE_PRESSURE, BACK_GAS_VOL)

DEPTH = 50
TARGET_END = 30
FILL_PRESSURE = 230

# === Model 1: O2 narcotic (current) ===
# END = (depth+10) × (1 - He_frac) - 10
print("=" * 70)
print("  MODEL 1: O2 IS NARCOTIC")
print("  END = (depth+10) × (1 - He_frac) - 10")
print("=" * 70)
mix1 = calculate_best_mix(DEPTH, target_end=TARGET_END)
back_gas1 = (mix1['o2'], mix1['he'])
print(f"  Best mix: Tx {mix1['o2']}/{mix1['he']} (END={mix1['end']:.0f}m, PO2={mix1['po2_at_depth']:.2f})")
generate_planning_table(DEPTH, back_gas=back_gas1, back_gas_pressure=FILL_PRESSURE)

# === Model 2: O2 non-narcotic ===
# END = (depth+10) × N2_frac / 0.79 - 10
# Solve: N2_frac = (END+10) × 0.79 / (depth+10)
# He = 1 - O2 - N2
print("\n" + "=" * 70)
print("  MODEL 2: O2 IS NOT NARCOTIC")
print("  END = (depth+10) × N2_frac / 0.79 - 10")
print("=" * 70)

ambient_bar = SURFACE_PRESSURE + DEPTH / 10.0
o2_frac = 1.4 / ambient_bar
o2_pct = int(o2_frac * 100)
o2_frac = o2_pct / 100.0

n2_frac_needed = (TARGET_END + 10) * 0.79 / (DEPTH + 10)
he_frac = 1.0 - o2_frac - n2_frac_needed
he_pct = max(0, round(he_frac * 100))
n2_pct = 100 - o2_pct - he_pct
actual_end_nn = (DEPTH + 10) * (n2_pct / 100) / 0.79 - 10

back_gas2 = (o2_pct, he_pct)
print(f"  Best mix: Tx {o2_pct}/{he_pct} (END={actual_end_nn:.0f}m [N2/0.79], PO2={ambient_bar * o2_frac:.2f})")
generate_planning_table(DEPTH, back_gas=back_gas2, back_gas_pressure=FILL_PRESSURE)

# === Cost comparison ===
print("\n" + "=" * 70)
print("  HELIUM COST COMPARISON (at $0.13/litre)")
print("=" * 70)
he_litres_1 = FILL_PRESSURE * BACK_GAS_VOL * (mix1['he'] / 100)
he_litres_2 = FILL_PRESSURE * BACK_GAS_VOL * (he_pct / 100)
cost_1 = he_litres_1 * 0.13
cost_2 = he_litres_2 * 0.13
saving = cost_1 - cost_2
print(f"  O2-narcotic:     Tx {mix1['o2']}/{mix1['he']} -> {he_litres_1:.0f}L He = ${cost_1:.2f}")
print(f"  O2-non-narcotic: Tx {o2_pct}/{he_pct} -> {he_litres_2:.0f}L He = ${cost_2:.2f}")
print(f"  Saving: {he_litres_1 - he_litres_2:.0f}L He = ${saving:.2f} per fill")
print("=" * 70)
