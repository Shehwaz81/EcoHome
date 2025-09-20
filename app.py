from flask import Flask, render_template, request
import pandas as pd
import numpy as np
import json

app = Flask(__name__)

@app.route("/")
def index():
    weather = request.args.get("weather", "sunny")
    day_temp = float(request.args.get("day_temp", 25))
    house_size = float(request.args.get("house_size", 120))
    
    # Generate simulation data
    hours = np.arange(0, 24)
    outdoor_temp = day_temp * np.sin((hours - 6) * np.pi / 12)
    indoor_temp = 20 + np.random.normal(0, 0.5, size=24)
    load = np.abs(outdoor_temp - 20) * 0.2
    
    if weather == "sunny":
        pv_output = np.maximum(0, 5 * np.sin((hours - 6) * np.pi / 12) * 1.2)
    elif weather == "cloudy":
        pv_output = np.maximum(0, 5 * np.sin((hours - 6) * np.pi / 12) * 0.7)
    else:
        pv_output = np.maximum(0, 5 * np.sin((hours - 6) * np.pi / 12) * 0.4)
    
    battery_soc = np.cumsum(pv_output - load)
    battery_soc = np.clip(battery_soc, 0, 10)
    
    # Calculate metrics for CGSP
    daily_consumption = np.sum(load)
    annual_consumption = daily_consumption * 365
    energy_per_sqm = annual_consumption / house_size
    solar_efficiency = (np.sum(pv_output) / (5 * 12)) * 100  # Max possible vs actual
    battery_utilization = (np.sum(battery_soc > 0) / 24) * 100
    cost_savings = annual_consumption * 0.15  # Assume $0.15/kWh saved
    
    # Prepare data for Chart.js (convert numpy arrays to Python lists)
    chart_data = {
        'hours': [f"{h}:00" for h in hours],
        'temperature': {
            'indoor': [round(temp, 1) for temp in indoor_temp],
            'outdoor': [round(temp, 1) for temp in outdoor_temp]
        },
        'energy': {
            'load': [round(load_val, 2) for load_val in load],
            'pv_output': [round(pv_val, 2) for pv_val in pv_output]
        },
        'battery': [round(soc, 2) for soc in battery_soc]
    }
    
    suggestion = f"Optimize energy usage during peak solar hours (11 AM - 2 PM). Current solar efficiency: {solar_efficiency:.1f}%"
    
    return render_template(
        "index.html",
        chart_data=json.dumps(chart_data),
        suggestion=suggestion,
        weather=weather,
        day_temp=int(day_temp),
        house_size=int(house_size),
        energy_per_sqm=round(energy_per_sqm, 1),
        solar_efficiency=round(solar_efficiency),
        battery_utilization=round(battery_utilization),
        cost_savings=round(cost_savings),
        current_year=2024
    )

if __name__ == '__main__':
    app.run(debug=True)