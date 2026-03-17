import networkx as nx
import random

class AirlineNetworkGraph:

    def __init__(self):
        self.graph = nx.DiGraph()

    def build_network(self, airports, flights=500):

        for airport in airports:
            self.graph.add_node(airport)

        for i in range(flights):

            origin = random.choice(airports)
            destination = random.choice(airports)

            if origin != destination:

                delay = random.randint(0,30)

                self.graph.add_edge(
                    origin,
                    destination,
                    flight_number=f"FL{i}",
                    delay=delay
                )

        return self.graph
