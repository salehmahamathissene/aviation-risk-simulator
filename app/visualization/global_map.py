import pandas as pd
import plotly.graph_objects as go


def plot_global_network():

    df = pd.read_csv("data/global/airports.csv")

    fig = go.Figure(go.Scattergeo(
        lat=df["lat"],
        lon=df["lon"],
        text=df["iata"],
        mode='markers'
    ))

    fig.update_layout(
        title="Global Airline Network (Real Airports)",
        geo=dict(scope="world")
    )

    fig.show()
