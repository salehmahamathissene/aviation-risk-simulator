class FlightDepartureEvent:

    def __init__(self, flight):

        self.flight = flight

    def process(self, engine):

        if self.flight.delay > 0:
            engine.schedule(engine.time + self.flight.delay, self)

        else:
            engine.schedule(
                engine.time + self.flight.duration,
                FlightArrivalEvent(self.flight)
            )


class FlightArrivalEvent:

    def __init__(self, flight):

        self.flight = flight

    def process(self, engine):

        self.flight.arrived = True
