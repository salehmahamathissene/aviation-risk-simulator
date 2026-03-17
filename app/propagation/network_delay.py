import random

class NetworkDelayPropagation:

    def propagate(self, graph):

        total_delay = 0

        for u, v, data in graph.edges(data=True):

            if random.random() < 0.25:

                extra_delay = random.randint(15,120)

                data["delay"] += extra_delay

                total_delay += extra_delay

        return total_delay
