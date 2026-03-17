import random
import networkx as nx
from app.models.flight import Flight


class AirlineNetwork:

    def generate_network(self, airports):

        graph = nx.DiGraph()
        flights = []

        for airport in airports:
            graph.add_node(airport)

        # create many flights
        for _ in range(500):

            origin = random.choice(airports)
            destination = random.choice(airports)

            if origin == destination:
                continue

            delay = random.randint(0, 60)

            flight = Flight(
                origin=origin,
                destination=destination,
                delay_minutes=delay
            )

            flights.append(flight)

            graph.add_edge(origin, destination)

        return graph, flights
