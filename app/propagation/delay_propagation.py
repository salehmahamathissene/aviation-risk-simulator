import random

class DelayPropagation:

    def propagate_delays(self, flights):

        disrupted = []

        eligible = [flight for flight in flights if not flight.cancelled]
        if not eligible:
            return list(flights)

        # choose disrupted hub
        hub = random.choice(eligible).origin

        for flight in flights:

            if flight.cancelled:
                disrupted.append(flight)
                continue

            if flight.origin == hub:

                extra_delay = random.randint(30,120)

                flight.delay = flight.delay_minutes + extra_delay

            disrupted.append(flight)

        return disrupted
