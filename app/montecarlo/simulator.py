import numpy as np
import pandas as pd


class GlobalMonteCarlo:

    def __init__(self, runs=2000, seed=None, data_path="data/flights.csv"):
        if isinstance(runs, bool) or not isinstance(runs, int):
            raise ValueError("runs must be a positive integer")
        if runs <= 0:
            raise ValueError("runs must be a positive integer")

        self.runs = runs
        self.seed = seed
        self.data = pd.read_csv(data_path)
        self._validate_data()

        if seed is not None:
            np.random.seed(seed)

    def _validate_data(self):
        required_columns = {"avg_delay", "cancel_prob"}
        missing_columns = required_columns.difference(self.data.columns)
        if missing_columns:
            raise ValueError(
                "Missing required columns: "
                + ", ".join(sorted(missing_columns))
            )
        if self.data.empty:
            raise ValueError("Simulation dataset is empty")

        for column in ("avg_delay", "cancel_prob"):
            if self.data[column].isna().any():
                raise ValueError(f"{column} contains missing values")

        try:
            avg_delays = pd.to_numeric(self.data["avg_delay"], errors="raise")
            cancel_probs = pd.to_numeric(self.data["cancel_prob"], errors="raise")
        except (TypeError, ValueError) as exc:
            raise ValueError("Simulation dataset contains invalid numeric values") from exc

        if avg_delays.lt(0).any():
            raise ValueError("avg_delay values must be non-negative")
        if cancel_probs.lt(0).any() or cancel_probs.gt(1).any():
            raise ValueError("cancel_prob values must be between 0 and 1")

    def simulate_once(self):
        delays = []
        cancellations = 0

        for _, row in self.data.iterrows():
            delay = max(0.0, float(np.random.normal(row["avg_delay"], 10)))
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
