import random

class PassengerFlowEngine:

    def estimate_disruption_cost(self, flights):

        cost = 0

        for flight in flights:

            if flight.delay_minutes > 60:

                passengers = random.randint(80, 180)

                compensation = passengers * 250

                cost += compensation

        return cost
