import random


class DisruptionEngine:

    def apply(self, flight):

        r = random.random()

        if r < 0.05:
            flight.delay += random.randint(30, 180)

        elif r < 0.08:
            flight.delay += random.randint(60, 240)

        elif r < 0.10:
            flight.delay += random.randint(30, 120)
