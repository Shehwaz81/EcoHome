import pandas as pd
import numpy as np

# creates an array from 0 -> 23 (0 based)
hours = np.arange(0, 24)

# Outdoor temperature (°C): sine wave (cold night, warm day)
outdoor_temp = 10 + 10 * np.sin((hours - 6) * np.pi / 12)

# Indoor temperature (°C): held near 20°C, small noise
indoor_temp = 20 + np.random.normal(0, 0.5, size=24)

# Heating/cooling load (kWh): proportional to difference from 20°C
load = np.abs(outdoor_temp - 20) * 0.2  

# PV output (kWh): peaks midday
pv_output = np.maximum(0, 5 * np.sin((hours - 6) * np.pi / 12))

# Battery SOC (kWh): running balance
battery_soc = np.cumsum(pv_output - load)
battery_soc = np.clip(battery_soc, 0, 10)  # 10 kWh max capacity

# Save to CSV
df = pd.DataFrame({
    "hour": hours,
    "outdoor_temp": outdoor_temp,
    "indoor_temp": indoor_temp,
    "load": load,
    "pv_output": pv_output,
    "battery_soc": battery_soc
})

df.to_csv("data.csv", index=False)
print("✅ Simulation saved to data.csv")