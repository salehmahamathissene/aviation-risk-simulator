import numpy as np
import pandas as pd


class GlobalMonteCarlo:

    def __init__(self, runs=2000):
        self.runs = runs
        self.data = pd.read_csv("data/flights.csv")

    def simulate_once(self):
        delays = []
        cancellations = 0

        for _, row in self.data.iterrows():
            delay = np.random.normal(row["avg_delay"], 10)
            cancel = np.random.rand() < row["cancel_prob"]

            delays.append(delay)

            if cancel:
                cancellations += 1

        return delays, cancellations

    def run(self):
        all_delays = []
        total_cancellations = 0

        for _ in range(self.runs):
            delays, cancels = self.simulate_once()
            all_delays.extend(delays)
            total_cancellations += cancels

        all_delays = np.array(all_delays)

        mean_delay = float(np.mean(all_delays))
        p95_delay = float(np.percentile(all_delays, 95))

        economic_loss = self.compute_loss(mean_delay, total_cancellations)

        return {
            "mean_delay": mean_delay,
            "p95_delay": p95_delay,
            "cancelled_flights": int(total_cancellations),
            "economic_loss_usd": economic_loss,
            "runs": self.runs
        }

    def compute_loss(self, mean_delay, cancellations):
        return mean_delay * 100 + cancellations * 50000
