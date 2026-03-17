import random


class RecoveryEngine:

    def reroute(self, flight):

        alternatives = [
            ("CDG", "AMS"),
            ("AMS", "JFK"),
            ("CDG", "LHR"),
            ("LHR", "JFK")
        ]

        return random.choice(alternatives)

    def recover(self, disrupted_flights):

        recovery_plan = {}

        for f in disrupted_flights:
            recovery_plan[f] = self.reroute(f)

        return recovery_plan
