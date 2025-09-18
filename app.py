from flask import Flask, render_template
import pandas as pd
import plotly.express as px

app = Flask(__name__)

@app.route("/")
def index():
    df = pd.read_csv("data.csv")   # loads fresh data
    fig = px.line(df, x="hour", y=["outdoor_temp", "indoor_temp"])
    graph_html = fig.to_html(full_html=False)

    suggestion = "Best time to run appliances is 12–15h when PV peaks."
    return render_template("index.html", graph=graph_html, suggestion=suggestion)