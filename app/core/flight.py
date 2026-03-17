class Flight:

    def __init__(
        self,
        flight_id,
        origin,
        destination,
        departure_time,
        arrival_time,
        aircraft,
        passengers
    ):

        self.flight_id = flight_id
        self.origin = origin
        self.destination = destination

        self.departure_time = departure_time
        self.arrival_time = arrival_time

        self.aircraft = aircraft
        self.passengers = passengers

        self.delay = 0
        self.cancelled = False
