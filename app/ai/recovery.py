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

def suggest_recovery(delay, congestion):

    score_cancel = delay * 0.7 + congestion * 100
    score_swap = delay * 0.5
    score_reroute = congestion * 120

    scores = {
        "Cancel & Rebook": score_cancel,
        "Swap Aircraft": score_swap,
        "Reroute Passengers": score_reroute,
        "Hold": 10
    }

    return max(scores, key=scores.get)

def suggest_recovery(delay, congestion):

    scores = {
        "Cancel Flights": delay * 0.8 + congestion * 50,
        "Swap Aircraft": delay * 0.6,
        "Reroute Passengers": congestion * 120,
        "Hold": 20
    }

    return max(scores, key=scores.get)
