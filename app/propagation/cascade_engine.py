class CascadeEngine:

    def propagate(self, network):

        for flight in network.flights:

            if flight.delay > 120:

                downstream = network.get_downstream(flight)

                for f in downstream:

                    f.delay += 20

def run_simulation(network):

    results = []

    for i in range(100000):

        scenario = network.simulate()

        results.append(scenario)

    return results
