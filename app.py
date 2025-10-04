from flask import Flask, render_template, request
import numpy as np
import json

app = Flask(__name__)

# --- Constants ---
HOUSE_SIZE_DEFAULT = 120  # m²
CONSUMPTION_PER_M2_DAY = 0.09  # kWh/m²/day
BATTERY_CAPACITY_KWH = 10
COST_PER_M = 43784
EMBODIED_CARBON = 180  # kg CO₂e/m²
WATER_SAVING = 30  # %
MAX_BUDGET = 2_000_000  # ¥
DAILY_PV_KWH_BASE = 17.16  # Base PV output for scaling

# Seasonal solar factor (Shirakawa)
MONTH_FACTORS = {
    'Jan':0.7, 'Feb':0.72, 'Mar':0.82, 'Apr':0.88, 'May':1.0,
    'Jun':0.83, 'Jul':0.78, 'Aug':0.77, 'Sep':0.70, 'Oct':0.70, 'Nov':0.70, 'Dec':0.69
}

# Hourly peak profile (centered)
PEAK_PROFILE = np.array([
    0.2,0.3,0.5,0.6,0.8,1,1,0.9,0.7,0.6,0.5,0.4,
    0.4,0.5,0.6,0.8,1,1,0.8,0.6,0.4,0.3,0.2,0.2
])
PEAK_PROFILE -= np.mean(PEAK_PROFILE)

# --- Helper Functions ---
def scale_peak(load_base):
    scale = 1.0
    while np.sum(load_base + PEAK_PROFILE*scale) > np.sum(load_base):
        scale *= 0.95
    return scale

def battery_sim(pv_hourly, load_hourly, capacity=BATTERY_CAPACITY_KWH, efficiency=0.9):
    soc = 0
    MIN_SOC = 1
    battery_soc = np.zeros(24)
    for i in range(24):
        net = pv_hourly[i] - load_hourly[i]
        soc += net*efficiency if net > 0 else net/efficiency
        soc = np.clip(soc, MIN_SOC, capacity)
        battery_soc[i] = soc
    return battery_soc

@app.route("/")
def index():
    weather = request.args.get("weather", "sunny")
    month = request.args.get("month", "Jan")
    house_size = float(request.args.get("house_size", HOUSE_SIZE_DEFAULT))

    # --- House daily consumption ---
    house_daily_consumption = CONSUMPTION_PER_M2_DAY * house_size

    # --- PV scaling relative to consumption ---
    # PV aims to cover ~75% of daily consumption, capped by base PV system
    target_coverage = 0.75
    weather_factor = {"sunny":1.0, "cloudy":0.7, "rainy":0.4}
    pv_daily = min(DAILY_PV_KWH_BASE, house_daily_consumption * target_coverage)
    pv_daily *= weather_factor.get(weather,1.0) * MONTH_FACTORS.get(month,1.0)

    # --- Load Profile ---
    base_load = np.full(24, house_daily_consumption / 24)
    peak_scale = scale_peak(base_load)
    load_hourly = base_load + PEAK_PROFILE * peak_scale

    # --- PV Hourly Profile ---
    hours = np.arange(24)
    pv_hourly = pv_daily * np.sin((hours - 6) * np.pi / 12)
    pv_hourly = np.clip(pv_hourly, 0, None)

    # --- Battery Simulation ---
    battery_soc = battery_sim(pv_hourly, load_hourly)
    battery_utilization = (np.sum(battery_soc > 1) / 24) * 100

    # --- Metrics ---
    annual_pv = pv_daily * 365 * 0.85  # include ~15% system losses
    annual_consumption = house_daily_consumption * 365
    solar_coverage = round(min((annual_pv / annual_consumption) * 100, 100), 1)
    total_cost = int(COST_PER_M * house_size)

    # --- Dynamic AI Suggestion ---
    if battery_utilization < 50:
        suggestion = "Battery underused. Store excess PV or shift appliance usage to daytime."
    elif battery_utilization > 90:
        suggestion = "Battery often full. Shift appliances to peak solar hours (11-14h)."
    else:
        suggestion = "Shift high-energy appliances to peak solar hours (11-14h)."

    # --- Chart Data ---
    chart_data = {
        'months': list(MONTH_FACTORS.keys()),
        'consumption':[house_daily_consumption*30]*12,
        'pv_output':[pv_daily*30]*12,
        'hourly_profiles':{
            'Jan': {'hours':[f"{h}:00" for h in hours], 'load':load_hourly.tolist(), 'pv_output':pv_hourly.tolist()},
            'Jul': {'hours':[f"{h}:00" for h in hours], 'load':load_hourly.tolist(), 'pv_output':pv_hourly.tolist()}
        }
    }

    return render_template(
        "index.html",
        chart_data=json.dumps(chart_data),
        suggestion=suggestion,
        weather=weather,
        month=month,
        house_size=int(house_size),
        energy_per_sqm=round(annual_consumption/house_size,1),
        solar_coverage=solar_coverage,
        battery_utilization=round(battery_utilization),
        total_cost=total_cost,
        embodied_carbon=EMBODIED_CARBON,
        water_saving=WATER_SAVING
    )

if __name__ == "__main__":
    app.run(debug=True)
