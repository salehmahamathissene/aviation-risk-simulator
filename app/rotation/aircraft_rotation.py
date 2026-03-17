from collections import defaultdict


class AircraftRotation:

    def __init__(self, flights):

        self.flights = flights
        self.rotation = defaultdict(list)

    def build(self):

        for f in self.flights:
            self.rotation[f.aircraft_id].append(f)

        # sort by departure time
        for ac in self.rotation:
            self.rotation[ac].sort(key=lambda x: x.departure_time)

        return self.rotation

    def propagate_delay(self, delay_map):

        for ac, flights in self.rotation.items():

            accumulated_delay = 0

            for f in flights:

                if f.flight_id in delay_map:
                    accumulated_delay += delay_map[f.flight_id]

                f.departure_time += accumulated_delay
