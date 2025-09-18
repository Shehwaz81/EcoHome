from flask import Flask, render_template, request
import pandas as pd
import numpy as np
import plotly.express as px

app = Flask(__name__)

@app.route("/")
def index():
    # Read parameters from frontend
    weather = request.args.get("weather", "sunny")
    day_temp = float(request.args.get("day_temp", 25))

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

    df = pd.DataFrame({
        "hour": hours,
        "outdoor_temp": outdoor_temp,
        "indoor_temp": indoor_temp,
        "load": load,
        "pv_output": pv_output,
        "battery_soc": battery_soc
    })

    # Plot
    fig_temp = px.line(df, x="hour", y=["indoor_temp", "outdoor_temp"])
    fig_load = px.bar(df, x="hour", y=["load", "pv_output"])
    fig_battery = px.line(df, x="hour", y="battery_soc")

    graph_temp = fig_temp.to_html(full_html=False)
    graph_load = fig_load.to_html(full_html=False)
    graph_battery = fig_battery.to_html(full_html=False)

    suggestion = "Run appliances when PV output peaks."

    return render_template(
        "index.html",
        graph_temp=graph_temp,
        graph_load=graph_load,
        graph_battery=graph_battery,
        suggestion=suggestion,
        weather=weather,
        day_temp=int(day_temp)
    )