class FlightDepartureEvent:

    def __init__(self, flight):

        self.flight = flight

    def process(self, engine):

        if self.flight.cancelled:
            self.flight.arrived = False
            return

        actual_departure = max(
            float(self.flight.scheduled_departure),
            float(engine.time),
        ) + float(self.flight.delay_minutes)
        engine.schedule(
            actual_departure + float(self.flight.duration),
            FlightArrivalEvent(self.flight),
        )


class FlightArrivalEvent:

    def __init__(self, flight):

        self.flight = flight

    def process(self, engine):

        self.flight.arrived = True
