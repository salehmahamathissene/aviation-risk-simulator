from datetime import datetime


class Flight:
    def __init__(self, flight_number, origin, destination, departure, arrival):
        self.flight_number = flight_number
        self.origin = origin
        self.destination = destination
        self.departure = departure
        self.arrival = arrival
        self.delay_minutes = 0

    def apply_delay(self, minutes):
        self.delay_minutes += minutes

    def info(self):
        return {
            "flight": self.flight_number,
            "origin": self.origin,
            "destination": self.destination,
            "delay": self.delay_minutes
        }
