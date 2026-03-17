import random

class DelayPropagation:

    def propagate_delays(self, flights):

        disrupted = []

        # choose disrupted hub
        hub = random.choice(flights).origin

        for flight in flights:

            if flight.origin == hub:

                extra_delay = random.randint(30,120)

                flight.delay_minutes += extra_delay

            disrupted.append(flight)

        return disrupted
