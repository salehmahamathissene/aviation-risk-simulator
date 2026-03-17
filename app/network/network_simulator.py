import numpy as np
import pandas as pd


class NetworkSimulator:

    def __init__(self, runs=1000):
        self.runs = runs
        self.data = pd.read_csv("data/flights.csv")

    def simulate_network(self):
        delays = []

        for i, row in self.data.iterrows():

            base_delay = np.random.normal(row["avg_delay"], 10)

            if i > 0:
                propagation = 0.5 * delays[i - 1]
            else:
                propagation = 0

            total_delay = base_delay + propagation
            delays.append(total_delay)

        return delays

    def run(self):
        all_runs = []

        for _ in range(self.runs):
            all_runs.extend(self.simulate_network())

        arr = np.array(all_runs)

        return {
            "mean_network_delay": float(np.mean(arr)),
            "p95_network_delay": float(np.percentile(arr, 95)),
            "max_delay": float(np.max(arr))
        }
