import random


class MonteCarloSimulator:

    def run(self, airports, runs=1000):

        total_costs = []

        for _ in range(runs):

            cost = self.simulate_network(airports)

            total_costs.append(cost)

        return {
            "runs": runs,
            "average_cost": int(sum(total_costs) / len(total_costs)),
            "max_cost": int(max(total_costs)),
            "min_cost": int(min(total_costs))
        }


    def simulate_network(self, airports):

        total_cost = 0

        for airport in airports:

            # probability of disruption
            if random.random() < 0.2:

                delay_minutes = random.randint(30, 180)

                passengers = random.randint(50, 300)

                cost = delay_minutes * passengers * 10

                total_cost += cost

        return total_cost
