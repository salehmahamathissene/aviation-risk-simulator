import random
from app.models.flight import Flight
from app.models.flight import (
    LEGACY_DURATION_MINUTES,
    LEGACY_TURNAROUND_MINUTES,
)

class FlightNetwork:

    def generate_network(self, airports):

        flights = []

        for i in range(200):

            origin = random.choice(airports)
            destination = random.choice(airports)

            if origin != destination:

                flight = Flight(
                    flight_id=f"FL{i}",
                    origin=origin,
                    destination=destination,
                    scheduled_departure=random.randint(0, 1440),
                    duration=LEGACY_DURATION_MINUTES,
                    aircraft_id=f"LEGACY-A{i % 5}",
                    minimum_turnaround_minutes=LEGACY_TURNAROUND_MINUTES,
                    schedule_mode="legacy",
                    aircraft_assignment_authoritative=False,
                    aircraft_id_source="synthetic_demo",
                )

                flights.append(flight)

        return flights
