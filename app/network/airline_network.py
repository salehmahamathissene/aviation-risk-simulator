import random
import networkx as nx
from app.models.flight import Flight
from app.models.flight import (
    LEGACY_DURATION_MINUTES,
    LEGACY_TURNAROUND_MINUTES,
)


class AirlineNetwork:

    def generate_network(self, airports):

        graph = nx.DiGraph()
        flights = []

        for airport in airports:
            graph.add_node(airport)

        # create many flights
        for i in range(500):

            origin = random.choice(airports)
            destination = random.choice(airports)

            if origin == destination:
                continue

            delay = random.randint(0, 60)

            flight = Flight(
                flight_id=f"AL{i}",
                origin=origin,
                destination=destination,
                scheduled_departure=float(i),
                duration=LEGACY_DURATION_MINUTES,
                aircraft_id=f"LEGACY-A{i % 5}",
                minimum_turnaround_minutes=LEGACY_TURNAROUND_MINUTES,
                delay_minutes=delay,
                schedule_mode="legacy",
                aircraft_assignment_authoritative=False,
                aircraft_id_source="synthetic_demo",
            )

            flights.append(flight)

            graph.add_edge(origin, destination)

        return graph, flights
