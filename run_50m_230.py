"""Run 50m plan with 230 bar back gas fill, fixed Tx 22/27.

Edit the variables below to change the plan parameters.
"""
from dive_plan import generate_planning_table

# === GAS ===
back_gas = (22, 27)          # (O2%, He%) - back gas mix

# === DEPTH & TIME ===
depth = 48                   # m - target depth
bottom_time = None           # min - None = auto-find max safe bottom time

# === CYLINDER PRESSURES ===
back_gas_pressure = 230      # bar - back gas fill pressure
deco_50_pressure = 200       # bar - EAN50 fill pressure
deco_o2_pressure = 200       # bar - O2 fill pressure

# === DECOMPRESSION MODEL ===
gf_low = 0.50                # gradient factor low (at first stop)
gf_high = 0.80               # gradient factor high (at surface)

# === RATES ===
descent_rate = 20            # m/min
ascent_rate = 10             # m/min

# === DESCENT STOP (S-DRILL) ===
# Set descent_stop_depth to add a stop during descent (e.g. for S-drills).
# descent_stop_depth = 5     # m - depth of the stop (None = no stop)
# descent_stop_time = 5      # min - duration of the stop
descent_stop_depth = 5    # m - set to a depth (e.g. 5) to enable
descent_stop_time = 1        # min - duration of the descent stop

# === GAS CONSUMPTION ===
sac_bottom = 20              # L/min at surface (bottom / stressed ascent)
sac_deco = 17                # L/min at surface (deco stops)

# === OUTPUT ===
csv_path = f"plan_{depth}m_Tx{back_gas[0]}_{back_gas[1]}_{back_gas_pressure}bar.csv"

# --- Run ---
print(f"Fixed mix: Tx {back_gas[0]}/{back_gas[1]}")

generate_planning_table(
    depth,
    back_gas=back_gas,
    bottom_time=bottom_time,
    back_gas_pressure=back_gas_pressure,
    deco_50_pressure=deco_50_pressure,
    deco_o2_pressure=deco_o2_pressure,
    gf_low=gf_low,
    gf_high=gf_high,
    descent_rate=descent_rate,
    ascent_rate=ascent_rate,
    sac_bottom=sac_bottom,
    sac_deco=sac_deco,
    descent_stop_depth=descent_stop_depth,
    descent_stop_time=descent_stop_time,
    csv_path=csv_path,
)
