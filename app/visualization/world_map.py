import plotly.graph_objects as go
from app.data.airports import AIRPORT_COORDS


class WorldMapVisualizer:

    def plot_flights(self, flights):

        fig = go.Figure()

        for flight in flights:

            if flight.origin not in AIRPORT_COORDS:
                continue

            if flight.destination not in AIRPORT_COORDS:
                continue

            lat1, lon1 = AIRPORT_COORDS[flight.origin]
            lat2, lon2 = AIRPORT_COORDS[flight.destination]

            fig.add_trace(go.Scattergeo(
                locationmode='ISO-3',
                lon=[lon1, lon2],
                lat=[lat1, lat2],
                mode='lines',
                line=dict(width=1),
            ))

        fig.update_layout(
            title="Global Airline Network",
            geo=dict(
                showland=True,
                landcolor="rgb(243, 243, 243)",
                countrycolor="rgb(204, 204, 204)",
            )
        )

        fig.show()
