import random

class PassengerImpactEngine:

    def compute_cost(self, graph):

        cost = 0

        for u, v, data in graph.edges(data=True):

            delay = data["delay"]

            if delay > 60:

                passengers = random.randint(80,200)

                compensation = passengers * 250

                cost += compensation

        return cost
