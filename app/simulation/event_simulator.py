import simpy


class AirlineSimulation:

    def __init__(self):

        self.env = simpy.Environment()
        self.flights = []

    def add_flight(self, flight):

        self.flights.append(flight)

    def flight_process(self, flight):

        yield self.env.timeout(flight.departure_time)

        if flight.delay > 0:
            yield self.env.timeout(flight.delay)

        yield self.env.timeout(flight.duration)

        flight.arrived = True

    def run(self):

        for flight in self.flights:
            self.env.process(self.flight_process(flight))

        self.env.run()
