import random


class DisruptionEngine:

    def apply(self, flight):

        if getattr(flight, "cancelled", False):
            return flight

        r = random.random()

        if r < 0.05:
            flight.delay = flight.delay_minutes + random.randint(30, 180)

        elif r < 0.08:
            flight.delay = flight.delay_minutes + random.randint(60, 240)

        elif r < 0.10:
            flight.delay = flight.delay_minutes + random.randint(30, 120)

        return flight
