import random
from app.models.flight import Flight

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
                    departure_time=random.randint(0, 1440)
                )

                flights.append(flight)

        return flights
