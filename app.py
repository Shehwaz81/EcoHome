from flask import Flask, render_template, request
import numpy as np
import json

app = Flask(__name__)

# --- Constants ---
HOUSE_SIZE_DEFAULT = 120  # m²
PV_PANELS = 13
PV_PANEL_W = 330  # W
PV_SYSTEM_KW = PV_PANELS * PV_PANEL_W / 1000  # 4.29 kW system
DAILY_PV_KWH_BASE = 17.16  # average daily PV energy (adjusted by weather/season)
HOUSE_CONSUMPTION_KWH_DAY = 11  # max daily to meet IB constraints
BATTERY_CAPACITY_KWH = 10
COST_PER_M = 43784
EMBODIED_CARBON = 180  # kg CO₂e/m²
WATER_SAVING = 30  # %

# Seasonal solar factor (Shirakawa)
MONTH_FACTORS = {
    'Jan':0.6, 'Feb':0.7, 'Mar':0.8, 'Apr':0.9, 'May':1.0,
    'Jun':1.0, 'Jul':1.0, 'Aug':0.95, 'Sep':0.85, 'Oct':0.75, 'Nov':0.65, 'Dec':0.6
}

@app.route("/")
def index():
    weather = request.args.get("weather", "sunny")
    month = request.args.get("month", "Jan")
    house_size = float(request.args.get("house_size", HOUSE_SIZE_DEFAULT))

    # Adjust PV for weather & month
    weather_factor = {"sunny":1.0, "cloudy":0.7, "rainy":0.4}
    pv_daily = DAILY_PV_KWH_BASE * weather_factor.get(weather,1.0) * MONTH_FACTORS.get(month,1.0)

    # hourly load prof
    hours = np.arange(24)
    base_load = np.full(24, HOUSE_CONSUMPTION_KWH_DAY/24)
    peak_profile = np.array([0.2,0.3,0.5,0.6,0.8,1,1,0.9,0.7,0.6,0.5,0.4,
                             0.4,0.5,0.6,0.8,1,1,0.8,0.6,0.4,0.3,0.2,0.2])
    peak_profile = peak_profile - np.mean(peak_profile)  # center around 0
    # Scale peak_profile to fit daily energy limit
    peak_scale = 1.0
    while np.sum(base_load + peak_profile*peak_scale) > HOUSE_CONSUMPTION_KWH_DAY:
        peak_scale *= 0.95
    load_hourly = base_load + peak_profile*peak_scale

    # --- PV hourly profile ---
    pv_hourly = pv_daily * np.sin((hours - 6) * np.pi / 12)
    pv_hourly = np.clip(pv_hourly, 0, None)

    # --- Battery simulation ---
    EFFICIENCY = 0.9
    MIN_SOC = 1  # kWh
    soc = 0
    battery_soc = np.zeros(24)
    for i in range(24):
        net = pv_hourly[i] - load_hourly[i]
        if net > 0:
            soc += net * EFFICIENCY
        else:
            soc += net / EFFICIENCY
        soc = min(max(soc, MIN_SOC), BATTERY_CAPACITY_KWH)
        battery_soc[i] = soc

    # --- Metrics ---
    daily_consumption = np.sum(load_hourly)
    energy_per_sqm = daily_consumption*365/house_size
    annual_pv = DAILY_PV_KWH_BASE * 365 * weather_factor.get(weather,1.0) * np.mean(list(MONTH_FACTORS.values())) * 0.85  # include ~15% system losses
    annual_consumption = HOUSE_CONSUMPTION_KWH_DAY * 365

    solar_coverage = round(min((annual_pv / annual_consumption) * 100, 100), 1)
    battery_utilization = (np.sum(battery_soc > MIN_SOC)/24)*100
    total_cost = int(COST_PER_M * house_size)

    # --- Dynamic AI suggestions ---
    if battery_utilization < 50:
        suggestion = "Battery underused. Store excess PV or shift appliance usage to daytime."
    elif battery_utilization > 90:
        suggestion = "Battery often full. Shift appliances to peak solar hours (11-14h)."
    else:
        suggestion = "Shift high-energy appliances to peak solar hours (11-14h)."

    # --- Chart data ---
    chart_data = {
        'months': list(MONTH_FACTORS.keys()),
        'consumption':[HOUSE_CONSUMPTION_KWH_DAY*30]*12,
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
        energy_per_sqm=round(energy_per_sqm,1),
        solar_coverage=round(solar_coverage,1),
        battery_utilization=round(battery_utilization),
        total_cost=total_cost,
        embodied_carbon=EMBODIED_CARBON,
        water_saving=WATER_SAVING
    )

if __name__ == "__main__":
    app.run(debug=True)