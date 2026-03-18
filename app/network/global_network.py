import networkx as nx
import pandas as pd


class GlobalAirNetwork:

    def __init__(self):
        self.graph = nx.DiGraph()

    def load_data(self):
        airports = pd.read_csv("data/global/airports.csv")
        flights = pd.read_csv("data/flights.csv")

        for _, row in airports.iterrows():
            self.graph.add_node(
                row["iata"],
                name=row["name"],
                lat=row["latitude"],
                lon=row["longitude"]
            )

        for _, row in flights.iterrows():
            self.graph.add_edge(
                row["origin"],
                row["destination"],
                avg_delay=row["avg_delay"],
                cancel_prob=row["cancel_prob"]
            )

    def get_graph(self):
        return self.graph
