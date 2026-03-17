class RiskEngine:

    def compute_cost(self, flights):

        total_cost = 0

        for flight in flights:

            cost = flight.delay * flight.passengers * 5

            total_cost += cost

        return total_cost
